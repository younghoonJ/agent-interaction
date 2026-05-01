"""Final Markdown report builder.

Purpose:
    Combine per-round JSON reports into a deterministic final Markdown summary.
Parameters:
    ReportBuilder receives a project root and report directory.
Return Value:
    build writes final.md and returns its path.
Raised Exceptions:
    KeyError: If the task is unknown.
    ValueError: If report JSON is invalid.
    OSError: If report files cannot be read or written.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_review.messaging.schemas import ReviewReport
from agent_review.orchestrator.state_access import allow_empty_string_list, require_string
from agent_review.orchestrator.state_store import StateStore


class ReportBuilder:
    """Build task final reports from stored round reports.

    Args:
        project_root: Project root used to resolve relative report paths.
        report_dir: Report directory containing state and task folders.

    Returns:
        ReportBuilder instance.

    Raises:
        None during initialization.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    def __init__(
        self,
        project_root: Path,
        report_dir: Path,
        state_store: StateStore | None = None,
    ) -> None:
        self.project_root = project_root
        self.report_dir = report_dir
        self.state_store = state_store if state_store is not None else StateStore(report_dir)

    def build(self, task_id: str) -> Path:
        """Build final.md for a task.

        Args:
            task_id: Task identifier.

        Returns:
            Path to the generated final report.

        Raises:
            KeyError: If the task is unknown.
            ValueError: If report JSON is invalid.
            OSError: If report files cannot be read or written.
        """

        task = self.state_store.get_task(task_id)
        report_paths = allow_empty_string_list(task, "reports")
        reports = [self._load_report(path) for path in report_paths]
        final_path = self.report_dir / "tasks" / task_id / "final.md"
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.write_text(self._render(task, reports), encoding="utf-8")
        self.state_store.update_task(task_id, {"final_report": _relative_to_project(final_path, self.project_root)})
        return final_path

    def _load_report(self, relative_path: str) -> ReviewReport:
        path = self.project_root / relative_path
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError(f"Report JSON must be an object: {path}")
        return ReviewReport.from_dict(data)

    def _render(self, task: dict[str, object], reports: list[ReviewReport]) -> str:
        target_files = allow_empty_string_list(task, "target_files")
        lines = [
            f"# Final Review Report: {require_string(task, 'task_id')}",
            "",
            "## Target Files",
            "",
        ]
        lines.extend(f"- `{file_path}`" for file_path in target_files)
        lines.extend(["", "## Round Summaries", ""])

        if not reports:
            lines.append("No completed round reports are available.")
        for report in reports:
            lines.append(f"### Round {report.round}: {report.agent}")
            lines.append("")
            lines.append(report.summary)
            lines.append("")
            lines.append(f"- Findings: {len(report.findings)}")
            lines.append(f"- Suggestions: {len(report.suggestions)}")
            lines.append(f"- Requires human review: {str(report.requires_human_review).lower()}")
            lines.append("")

        findings = [finding for report in reports for finding in report.findings]
        lines.extend(["## Findings", ""])
        if findings:
            for finding in findings:
                location = f"{finding.file}:{finding.line}" if finding.line else finding.file
                lines.append(f"- [{finding.severity}] {finding.id} `{location}` - {finding.title}")
        else:
            lines.append("No findings were reported.")

        suggestions = [suggestion for report in reports for suggestion in report.suggestions]
        lines.extend(["", "## Suggestions", ""])
        if suggestions:
            for suggestion in suggestions:
                files = ", ".join(f"`{file_path}`" for file_path in suggestion.affected_files)
                lines.append(f"- [{suggestion.type}] {suggestion.id} {suggestion.title} ({files})")
        else:
            lines.append("No suggestions were reported.")

        questions = [question for report in reports for question in report.questions]
        lines.extend(["", "## Open Questions", ""])
        if questions:
            lines.extend(f"- {question}" for question in questions)
        else:
            lines.append("No open questions were reported.")

        lines.append("")
        return "\n".join(lines)


def _relative_to_project(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


