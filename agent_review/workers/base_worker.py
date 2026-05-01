"""Base worker implementation with safety gate and ack protocol.

Purpose:
    Convert task messages into prompts, run an agent command, validate JSON output, and write reports.
Parameters:
    ReviewWorker receives an agent runner, project root, report directory, and optional RabbitMQ client.
Return Value:
    handle_task returns a ResultMessage; handle_delivery performs RabbitMQ ack/nack side effects.
Raised Exceptions:
    SafetyViolation: If review_only mode source mutation is detected.
    ValueError: If task or report JSON is invalid.
    AgentCommandError: If the runner command fails.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from agent_review.messaging.rabbitmq import EXCHANGE_RESULTS, ROUTING_RESULT_ORCHESTRATOR, RabbitMQClient
from agent_review.messaging.schemas import MODE_VERIFY, ResultMessage, ReviewReport, STATUS_COMPLETED, TaskMessage
from agent_review.reports.json_report import write_report as write_json_report
from agent_review.reports.markdown_report import write_report as write_markdown_report
from agent_review.workers.prompt_builder import build_prompt, build_verify_prompt
from agent_review.workers.runners import AgentCommandError

REPORT_DIR_NAME = ".agent_reports"


class SafetyViolation(RuntimeError):
    """Raised when an agent modifies source files in review_only mode.

    Args:
        message: Human-readable safety failure detail.

    Returns:
        RuntimeError subclass for worker failure handling.

    Raises:
        None during initialization.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """


class AgentRunner(Protocol):
    """Protocol for agent command runners.

    Args:
        prompt_path: Generated prompt file path.
        project_root: Project root used as command working directory.

    Returns:
        Agent stdout as a string.

    Raises:
        AgentCommandError: If the command fails.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    def run(self, prompt_path: Path, project_root: Path) -> str:
        """Run an agent command.

        Args:
            prompt_path: Generated prompt file path.
            project_root: Project root used as command working directory.

        Returns:
            Agent stdout.

        Raises:
            AgentCommandError: If command execution fails.
        """


class ReviewWorker:
    """Base worker that executes one review task.

    Args:
        runner: Agent runner implementation.
        project_root: Project root.
        report_dir: Directory where reports may be written.
        allowed_write_dirs: Relative directories allowed to change.
        client: Optional RabbitMQ client for result publishing.

    Returns:
        ReviewWorker instance.

    Raises:
        None during initialization.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    def __init__(
        self,
        runner: AgentRunner,
        project_root: Path,
        report_dir: Path,
        allowed_write_dirs: tuple[str, ...] = (REPORT_DIR_NAME,),
        client: RabbitMQClient | None = None,
    ) -> None:
        self.runner = runner
        self.project_root = project_root
        self.report_dir = report_dir
        self.allowed_write_dirs = allowed_write_dirs
        self.client = client

    def handle_task(self, task: TaskMessage, failure_count: int = 0) -> ResultMessage:
        """Run one task and return a result message.

        Args:
            task: Validated task contract.
            failure_count: Prior failure count for retry accounting.

        Returns:
            Completed or failed result message.

        Raises:
            None. Failures are converted to failed ResultMessage values.
        """

        try:
            prompt_path = self._write_prompt(task)
            task_root = Path(task.project_root) if task.project_root else self.project_root
            before = get_git_diff_files(task_root)
            stdout = self.runner.run(prompt_path, task_root)
            after = get_git_diff_files(task_root)
            check_safety_gate(before, after, self.allowed_write_dirs)
            report = parse_review_report(stdout, task)
            json_path, markdown_path = self._write_reports(task, report)
            result = ResultMessage.completed(
                task=task,
                report_json_path=_relative_to_project(json_path, self.project_root),
                report_md_path=_relative_to_project(markdown_path, self.project_root),
                summary=report.summary,
                next_focus=report.next_agent_focus,
                created_at=_now_iso(),
            )
            return result
        except (AgentCommandError, SafetyViolation, ValueError, OSError, subprocess.SubprocessError) as exc:
            return ResultMessage.failed(
                task=task,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
                retryable=not isinstance(exc, (SafetyViolation, ValueError)),
                failure_count=failure_count + 1,
                created_at=_now_iso(),
            )

    def handle_delivery(self, channel: object, method: object, properties: object, body: bytes) -> None:
        """Handle a RabbitMQ delivery with manual ack/nack protocol.

        Args:
            channel: RabbitMQ channel object.
            method: RabbitMQ delivery method object.
            properties: RabbitMQ properties object.
            body: Raw JSON task body.

        Returns:
            None.

        Raises:
            Exception: If publishing a result or ack/nack fails.
        """

        del properties
        task_data = json.loads(body.decode("utf-8"))
        if not isinstance(task_data, dict):
            raise ValueError("Task message must decode to a JSON object.")
        task = TaskMessage.from_dict(task_data)
        print(f"[{task.current_agent}] Processing task {task.task_id} round {task.round}...")
        result = self.handle_task(task)
        print(f"[{task.current_agent}] Result: {result.status}")
        if result.status != STATUS_COMPLETED:
            print(f"[{task.current_agent}] Error: {getattr(result, 'error_type', '?')} - {getattr(result, 'error_message', '?')}")
        if self.client is not None:
            self.client.publish_json(EXCHANGE_RESULTS, ROUTING_RESULT_ORCHESTRATOR, result.to_dict())

        if result.status == STATUS_COMPLETED:
            channel.basic_ack(delivery_tag=method.delivery_tag)
        else:
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _write_prompt(self, task: TaskMessage) -> Path:
        previous_reports = [self._read_previous_report(path) for path in task.previous_reports]
        task_dir = self.report_dir / "tasks" / task.task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = task_dir / f"round-{task.round:02d}-{task.current_agent}-prompt.md"
        if task.mode == MODE_VERIFY:
            file_contents = {
                path: (Path(task.project_root) / path).read_text(encoding="utf-8")
                for path in task.target_files
            }
            prompt_text = build_verify_prompt(task, previous_reports, file_contents)
        else:
            prompt_text = build_prompt(task, previous_reports)
        prompt_path.write_text(prompt_text, encoding="utf-8")
        return prompt_path

    def _read_previous_report(self, relative_path: str) -> str:
        return (self.project_root / relative_path).read_text(encoding="utf-8")

    def _write_reports(self, task: TaskMessage, report: ReviewReport) -> tuple[Path, Path]:
        task_dir = self.report_dir / "tasks" / task.task_id
        json_path = task_dir / f"round-{task.round:02d}-{task.current_agent}.json"
        markdown_path = task_dir / f"round-{task.round:02d}-{task.current_agent}.md"
        write_json_report(report, json_path)
        write_markdown_report(report, markdown_path)
        return json_path, markdown_path


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_review_report(stdout: str, task: TaskMessage) -> ReviewReport:
    """Parse and validate agent output, extracting the first JSON object found.

    Args:
        stdout: Raw agent stdout.
        task: Task contract used to check identity fields.

    Returns:
        Validated ReviewReport.

    Raises:
        ValueError: If stdout contains no JSON object or it is invalid.
    """

    match = _JSON_OBJECT_RE.search(stdout)
    if match is None:
        raise ValueError("Agent output contains no JSON object.")
    data = json.loads(match.group())
    if not isinstance(data, dict):
        raise ValueError("Agent output must be a JSON object.")
    report = ReviewReport.from_dict(data)
    return report


def get_git_diff_files(project_root: Path) -> set[str]:
    """Return all changed paths: unstaged, staged, and untracked.

    Uses ``git status --porcelain`` so that newly created files and staged
    changes are caught in addition to unstaged modifications.

    Args:
        project_root: Project root where git is expected to run.

    Returns:
        POSIX-style relative paths that appear in git status output.

    Raises:
        subprocess.SubprocessError: If git is unavailable or the project is not a git repository.
    """

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "git status --porcelain failed"
        raise subprocess.SubprocessError(detail)

    files: set[str] = set()
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path_part = line[3:].strip()
        # Renames are reported as "old -> new"; collect both paths.
        if " -> " in path_part:
            for part in path_part.split(" -> "):
                files.add(part.strip())
        else:
            files.add(path_part)
    return files


def check_safety_gate(before: set[str], after: set[str], allowed_write_dirs: tuple[str, ...]) -> None:
    """Validate that only allowed paths changed during an agent run.

    Args:
        before: Git-diff path set captured before the agent command.
        after: Git-diff path set captured after the agent command.
        allowed_write_dirs: Relative directory prefixes allowed to change.

    Returns:
        None.

    Raises:
        SafetyViolation: If a newly changed path is outside allowed directories.
    """

    unexpected = sorted(path for path in after - before if not _is_allowed_path(path, allowed_write_dirs))
    if unexpected:
        joined = ", ".join(unexpected)
        raise SafetyViolation(f"Unexpected source file changes: {joined}")


def _is_allowed_path(path: str, allowed_write_dirs: tuple[str, ...]) -> bool:
    normalized = path.strip("/")
    return any(
        normalized == allowed.strip("/") or normalized.startswith(f"{allowed.strip('/')}/")
        for allowed in allowed_write_dirs
    )


def _relative_to_project(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()
