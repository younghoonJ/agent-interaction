"""Message and report schemas for the alternating review system.

Purpose:
    Validate task contracts, worker results, and review reports without trusting LLM output.
Parameters:
    Public constructors accept typed Python values; from_dict methods accept JSON-like mappings.
Return Value:
    Public to_dict methods return JSON-serializable dictionaries.
Raised Exceptions:
    ValueError: If required fields are absent or have invalid values.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Mapping

AGENT_A = "agent_a"
AGENT_B = "agent_b"
MESSAGE_TYPE_TASK = "agent_task"
MESSAGE_TYPE_RESULT = "agent_result"
MODE_REVIEW_ONLY = "review_only"
MODE_VERIFY = "verify"
SUPPORTED_MODES = {MODE_REVIEW_ONLY, MODE_VERIFY}
SCHEMA_VERSION = "1.0"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
SEVERITIES = {"critical", "high", "major", "medium", "minor", "low", "info", "warning"}


@dataclass(frozen=True)
class Finding:
    """A single review finding.

    Args:
        id: Stable finding identifier within a report.
        severity: Risk level for the finding.
        category: Review category such as correctness or maintainability.
        file: Relative target file path.
        line: Optional one-based line number.
        title: Short finding title.
        description: Explanation of the issue.
        suggestion: Recommended next action.
        confidence: Confidence score between 0 and 1.

    Returns:
        Finding instances are immutable value objects.

    Raises:
        ValueError: If a field is invalid during from_dict validation.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    id: str
    severity: str
    category: str
    file: str
    line: int | None
    title: str
    description: str
    suggestion: str
    confidence: float

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "Finding":
        """Build a finding from a JSON mapping.

        Args:
            data: JSON-like mapping loaded from a worker report.

        Returns:
            A validated Finding.

        Raises:
            ValueError: If required fields are missing or invalid.
        """

        severity = _required_string(data, "severity").lower()
        line = _optional_int(data, "line")
        if line is not None and line < 1:
            raise ValueError("Finding line must be a positive integer.")
        confidence = _required_number(data, "confidence")
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError("Finding confidence must be between 0 and 1.")

        return cls(
            id=_required_string(data, "id"),
            severity=severity,
            category=_required_string(data, "category"),
            file=_validate_relative_path(_required_string(data, "file"), "finding file"),
            line=line,
            title=_required_string(data, "title"),
            description=_required_string(data, "description"),
            suggestion=_required_string(data, "suggestion"),
            confidence=confidence,
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize the finding.

        Args:
            None.

        Returns:
            A JSON-serializable dictionary.

        Raises:
            None.
        """

        return {
            "id": self.id,
            "severity": self.severity,
            "category": self.category,
            "file": self.file,
            "line": self.line,
            "title": self.title,
            "description": self.description,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class Suggestion:
    """A non-finding improvement suggestion.

    Args:
        id: Stable suggestion identifier within a report.
        type: Suggestion kind, such as test, refactor, or docs.
        title: Short suggestion title.
        description: Explanation of the improvement.
        affected_files: Relative paths affected by the suggestion.

    Returns:
        Suggestion instances are immutable value objects.

    Raises:
        ValueError: If a field is invalid during from_dict validation.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    id: str
    type: str
    title: str
    description: str
    affected_files: list[str]

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "Suggestion":
        """Build a suggestion from a JSON mapping.

        Args:
            data: JSON-like mapping loaded from a worker report.

        Returns:
            A validated Suggestion.

        Raises:
            ValueError: If required fields are missing or invalid.
        """

        return cls(
            id=_required_string(data, "id"),
            type=_required_string(data, "type"),
            title=_required_string(data, "title"),
            description=_required_string(data, "description"),
            affected_files=_relative_path_list(data, "affected_files"),
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize the suggestion.

        Args:
            None.

        Returns:
            A JSON-serializable dictionary.

        Raises:
            None.
        """

        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "affected_files": list(self.affected_files),
        }


@dataclass(frozen=True)
class ReviewReport:
    """Structured JSON review report produced by a worker.

    Args:
        task_id: Task identifier.
        agent: Worker name.
        round: One-based round number.
        status: Report status.
        summary: Short report summary.
        target_files: Relative file paths reviewed by the worker.
        findings: Review findings.
        suggestions: Non-finding suggestions.
        questions: Open questions for a human or next agent.
        next_agent_focus: Focus points for the next worker.
        requires_human_review: Whether the task should pause for human review.

    Returns:
        ReviewReport instances are immutable value objects.

    Raises:
        ValueError: If a field is invalid during from_dict validation.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    task_id: str
    agent: str
    round: int
    status: str
    summary: str
    target_files: list[str]
    findings: list[Finding]
    suggestions: list[Suggestion]
    questions: list[str]
    next_agent_focus: list[str]
    requires_human_review: bool

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "ReviewReport":
        """Build a review report from JSON data.

        Args:
            data: JSON-like report mapping.

        Returns:
            A validated ReviewReport.

        Raises:
            ValueError: If the report is invalid.
        """

        status = _required_string(data, "status")
        if status != STATUS_COMPLETED:
            raise ValueError("Review report status must be completed.")
        findings = [Finding.from_dict(item) for item in _mapping_list(data, "findings")]
        suggestions = [Suggestion.from_dict(item) for item in _mapping_list(data, "suggestions")]

        return cls(
            task_id=_required_string(data, "task_id"),
            agent=_validate_agent(_required_string(data, "agent")),
            round=_positive_int(data, "round"),
            status=status,
            summary=_required_string(data, "summary"),
            target_files=_relative_path_list(data, "target_files"),
            findings=findings,
            suggestions=suggestions,
            questions=_string_list(data, "questions"),
            next_agent_focus=_string_list(data, "next_agent_focus"),
            requires_human_review=_required_bool(data, "requires_human_review"),
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize the report.

        Args:
            None.

        Returns:
            A JSON-serializable dictionary.

        Raises:
            None.
        """

        return {
            "task_id": self.task_id,
            "agent": self.agent,
            "round": self.round,
            "status": self.status,
            "summary": self.summary,
            "target_files": list(self.target_files),
            "findings": [finding.to_dict() for finding in self.findings],
            "suggestions": [suggestion.to_dict() for suggestion in self.suggestions],
            "questions": list(self.questions),
            "next_agent_focus": list(self.next_agent_focus),
            "requires_human_review": self.requires_human_review,
        }

    def has_critical_finding(self) -> bool:
        """Return whether the report contains a critical finding.

        Args:
            None.

        Returns:
            True when any finding severity is critical.

        Raises:
            None.
        """

        return any(finding.severity == "critical" for finding in self.findings)


@dataclass(frozen=True)
class TaskMessage:
    """RabbitMQ task contract delivered to a review worker.

    Args:
        task_id: Task identifier.
        project_root: Absolute or relative project root path.
        target_files: Closed list of relative file paths to review.
        mode: Execution mode. MVP supports review_only.
        current_agent: Worker that should execute this round.
        next_agent: Worker expected after this round.
        round: One-based current round.
        max_rounds: Maximum number of alternating rounds.
        review_focus: Ordered review focus list.
        previous_reports: Relative report JSON paths available to the worker.
        forbidden_actions: Actions the worker prompt forbids.
        created_at: ISO-8601 creation time.

    Returns:
        TaskMessage instances are immutable value objects.

    Raises:
        ValueError: If a field is invalid during from_dict validation.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    task_id: str
    project_root: str
    target_files: list[str]
    mode: str
    current_agent: str
    next_agent: str
    round: int
    max_rounds: int
    review_focus: list[str]
    previous_reports: list[str]
    forbidden_actions: list[str]
    created_at: str
    user_prompt: str = ""
    schema_version: str = SCHEMA_VERSION
    message_type: str = MESSAGE_TYPE_TASK

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "TaskMessage":
        """Build a task message from JSON data.

        Args:
            data: JSON-like task contract mapping.

        Returns:
            A validated TaskMessage.

        Raises:
            ValueError: If the task contract is invalid.
        """

        if _required_string(data, "message_type") != MESSAGE_TYPE_TASK:
            raise ValueError("Task message_type must be agent_task.")
        if _required_string(data, "schema_version") != SCHEMA_VERSION:
            raise ValueError(f"Unsupported task schema_version; expected {SCHEMA_VERSION}.")
        mode = _required_string(data, "mode")
        if mode not in SUPPORTED_MODES:
            raise ValueError(f"Unsupported mode: {mode}. Supported: {', '.join(sorted(SUPPORTED_MODES))}")
        current_round = _positive_int(data, "round")
        max_rounds = _positive_int(data, "max_rounds")
        if current_round > max_rounds:
            raise ValueError("Task round cannot exceed max_rounds.")

        return cls(
            task_id=_required_string(data, "task_id"),
            project_root=_required_string(data, "project_root"),
            target_files=_relative_path_list(data, "target_files"),
            mode=mode,
            current_agent=_validate_agent(_required_string(data, "current_agent")),
            next_agent=_validate_agent(_required_string(data, "next_agent")),
            round=current_round,
            max_rounds=max_rounds,
            review_focus=_string_list(data, "review_focus"),
            previous_reports=_relative_path_list(data, "previous_reports"),
            forbidden_actions=_string_list(data, "forbidden_actions"),
            created_at=_required_string(data, "created_at"),
            user_prompt=str(data.get("user_prompt", "")),
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize the task contract.

        Args:
            None.

        Returns:
            A JSON-serializable dictionary.

        Raises:
            None.
        """

        return {
            "message_type": self.message_type,
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "project_root": self.project_root,
            "target_files": list(self.target_files),
            "mode": self.mode,
            "current_agent": self.current_agent,
            "next_agent": self.next_agent,
            "round": self.round,
            "max_rounds": self.max_rounds,
            "review_focus": list(self.review_focus),
            "previous_reports": list(self.previous_reports),
            "forbidden_actions": list(self.forbidden_actions),
            "created_at": self.created_at,
            "user_prompt": self.user_prompt,
        }


@dataclass(frozen=True)
class ResultMessage:
    """RabbitMQ result message sent to the orchestrator.

    Args:
        task_id: Task identifier.
        agent: Worker name.
        round: One-based round number.
        status: completed or failed.
        created_at: ISO-8601 creation time.
        report_json_path: Relative report JSON path for completed results.
        report_md_path: Relative report Markdown path for completed results.
        summary: Short result summary.
        next_agent: Next worker name for completed results.
        next_focus: Focus points for the next worker.
        error_type: Machine-readable failure type.
        error_message: Human-readable failure message.
        retryable: Whether the failure may be retried.
        failure_count: Number of failures observed for the task.

    Returns:
        ResultMessage instances are immutable value objects.

    Raises:
        ValueError: If a field is invalid during from_dict validation.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    task_id: str
    agent: str
    round: int
    status: str
    created_at: str
    report_json_path: str | None = None
    report_md_path: str | None = None
    summary: str | None = None
    next_agent: str | None = None
    next_focus: list[str] = field(default_factory=list)
    error_type: str | None = None
    error_message: str | None = None
    retryable: bool | None = None
    failure_count: int | None = None
    schema_version: str = SCHEMA_VERSION
    message_type: str = MESSAGE_TYPE_RESULT

    @classmethod
    def completed(
        cls,
        task: TaskMessage,
        report_json_path: str,
        report_md_path: str,
        summary: str,
        next_focus: list[str],
        created_at: str,
    ) -> "ResultMessage":
        """Create a successful result message.

        Args:
            task: Task contract that produced the report.
            report_json_path: Relative path to the JSON report.
            report_md_path: Relative path to the Markdown report.
            summary: Short report summary.
            next_focus: Focus points for the next agent.
            created_at: ISO-8601 creation time.

        Returns:
            A completed ResultMessage.

        Raises:
            None.
        """

        return cls(
            task_id=task.task_id,
            agent=task.current_agent,
            round=task.round,
            status=STATUS_COMPLETED,
            created_at=created_at,
            report_json_path=report_json_path,
            report_md_path=report_md_path,
            summary=summary,
            next_agent=task.next_agent,
            next_focus=list(next_focus),
        )

    @classmethod
    def failed(
        cls,
        task: TaskMessage,
        error_type: str,
        error_message: str,
        retryable: bool,
        failure_count: int,
        created_at: str,
    ) -> "ResultMessage":
        """Create a failed result message.

        Args:
            task: Task contract that failed.
            error_type: Machine-readable failure type.
            error_message: Human-readable failure message.
            retryable: Whether retry is allowed.
            failure_count: Updated task failure count.
            created_at: ISO-8601 creation time.

        Returns:
            A failed ResultMessage.

        Raises:
            None.
        """

        return cls(
            task_id=task.task_id,
            agent=task.current_agent,
            round=task.round,
            status=STATUS_FAILED,
            created_at=created_at,
            error_type=error_type,
            error_message=error_message,
            retryable=retryable,
            failure_count=failure_count,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "ResultMessage":
        """Build a result message from JSON data.

        Args:
            data: JSON-like result mapping.

        Returns:
            A validated ResultMessage.

        Raises:
            ValueError: If the result message is invalid.
        """

        if _required_string(data, "message_type") != MESSAGE_TYPE_RESULT:
            raise ValueError("Result message_type must be agent_result.")
        if _required_string(data, "schema_version") != SCHEMA_VERSION:
            raise ValueError(f"Unsupported result schema_version; expected {SCHEMA_VERSION}.")

        status = _required_string(data, "status")
        if status == STATUS_COMPLETED:
            return cls(
                task_id=_required_string(data, "task_id"),
                agent=_validate_agent(_required_string(data, "agent")),
                round=_positive_int(data, "round"),
                status=status,
                created_at=_required_string(data, "created_at"),
                report_json_path=_validate_relative_path(
                    _required_string(data, "report_json_path"),
                    "report_json_path",
                ),
                report_md_path=_validate_relative_path(_required_string(data, "report_md_path"), "report_md_path"),
                summary=_required_string(data, "summary"),
                next_agent=_validate_agent(_required_string(data, "next_agent")),
                next_focus=_string_list(data, "next_focus"),
            )

        if status == STATUS_FAILED:
            return cls(
                task_id=_required_string(data, "task_id"),
                agent=_validate_agent(_required_string(data, "agent")),
                round=_positive_int(data, "round"),
                status=status,
                created_at=_required_string(data, "created_at"),
                error_type=_required_string(data, "error_type"),
                error_message=_required_string(data, "error_message"),
                retryable=_required_bool(data, "retryable"),
                failure_count=_non_negative_int(data, "failure_count"),
            )

        raise ValueError(f"Invalid result status: {status}")

    def to_dict(self) -> dict[str, object]:
        """Serialize the result message.

        Args:
            None.

        Returns:
            A JSON-serializable dictionary.

        Raises:
            None.
        """

        base: dict[str, object] = {
            "message_type": self.message_type,
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "agent": self.agent,
            "round": self.round,
            "status": self.status,
            "created_at": self.created_at,
        }
        if self.status == STATUS_COMPLETED:
            base.update(
                {
                    "report_json_path": self.report_json_path or "",
                    "report_md_path": self.report_md_path or "",
                    "summary": self.summary or "",
                    "next_agent": self.next_agent or "",
                    "next_focus": list(self.next_focus),
                }
            )
            return base

        base.update(
            {
                "error_type": self.error_type or "",
                "error_message": self.error_message or "",
                "retryable": bool(self.retryable),
                "failure_count": int(self.failure_count or 0),
            }
        )
        return base


def _required_string(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing or invalid string field: {key}")
    return value


def _required_bool(data: Mapping[str, object], key: str) -> bool:
    value = data.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "1")
    return bool(value) if value is not None else False


def _required_number(data: Mapping[str, object], key: str) -> float:
    value = data.get(key)
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _optional_int(data: Mapping[str, object], key: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _positive_int(data: Mapping[str, object], key: str) -> int:
    value = _optional_int(data, key)
    if value is None or value < 1:
        raise ValueError(f"Missing or invalid positive integer field: {key}")
    return value


def _non_negative_int(data: Mapping[str, object], key: str) -> int:
    value = _optional_int(data, key)
    if value is None or value < 0:
        raise ValueError(f"Missing or invalid non-negative integer field: {key}")
    return value


def _string_list(data: Mapping[str, object], key: str) -> list[str]:
    value = data.get(key)
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    raise ValueError(f"Invalid string list field: {key}")


def _relative_path_list(data: Mapping[str, object], key: str) -> list[str]:
    return [_validate_relative_path(item, key) for item in _string_list(data, key)]


def _mapping_list(data: Mapping[str, object], key: str) -> list[Mapping[str, object]]:
    value = data.get(key)
    if not isinstance(value, list):
        raise ValueError(f"Missing or invalid list field: {key}")

    mappings: list[Mapping[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(f"Invalid mapping item in field: {key}")
        mappings.append(item)
    return mappings


def _validate_agent(value: str) -> str:
    import re
    if not re.match(r'^[a-z][a-z0-9_]*$', value):
        raise ValueError(f"Invalid agent name '{value}': must be lowercase alphanumeric with underscores.")
    return value


def _validate_relative_path(value: str, field_name: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field_name} must be a relative path without parent traversal.")
    return path.as_posix()
