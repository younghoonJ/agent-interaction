"""Build review task contracts from scanned files.

Purpose:
    Convert deterministic file lists into one-file task messages for the v0.1 MVP.
Parameters:
    TaskBuilder receives project settings and an explicit clock timestamp.
Return Value:
    build_tasks returns validated TaskMessage instances.
Raised Exceptions:
    ValueError: If agent sequencing or round settings are invalid.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from agent_review.messaging.schemas import (
    AGENT_A,
    AGENT_B,
    MODE_REVIEW_ONLY,
    MODE_VERIFY,
    TaskMessage,
)
from agent_review.orchestrator.state_access import (
    allow_empty_string_list,
    require_int,
    require_string,
)

DEFAULT_FORBIDDEN_ACTIONS = ("modify_file", "git_commit", "delete_file")
DEFAULT_REVIEW_FOCUS = (
    "correctness",
    "implementation_feasibility",
    "test_coverage",
    "api_compatibility",
    "maintainability",
)


@dataclass(frozen=True)
class TaskBuilder:
    """Factory for one-file review task contracts.

    Args:
        project_root: Root path embedded in task contracts.
        max_rounds: Maximum alternating review rounds.
        first_agent: Agent assigned to round one.
        agent_sequence: Alternating agent sequence.
        mode: Execution mode; v0.1 supports review_only.

    Returns:
        A builder that creates TaskMessage values.

    Raises:
        ValueError: If settings are invalid during initialization or build.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    project_root: Path
    max_rounds: int = 4
    first_agent: str = AGENT_A
    agent_sequence: tuple[str, ...] = (AGENT_A, AGENT_B)
    mode: str = MODE_REVIEW_ONLY
    review_focus: tuple[str, ...] = DEFAULT_REVIEW_FOCUS
    forbidden_actions: tuple[str, ...] = DEFAULT_FORBIDDEN_ACTIONS

    def build_tasks(self, files: list[str], created_at: datetime, start_index: int = 1) -> list[TaskMessage]:
        """Build one task per file.

        Args:
            files: Sorted relative paths selected by the scanner.
            created_at: Timestamp used for deterministic task IDs and message metadata.
            start_index: One-based sequence number for the first task ID.

        Returns:
            Validated task messages in input order.

        Raises:
            ValueError: If settings or file paths are invalid.
        """

        self._validate_settings()
        if start_index < 1:
            raise ValueError("start_index must be positive.")

        tasks: list[TaskMessage] = []
        for offset, file_path in enumerate(files):
            task_index = start_index + offset
            task_id = f"TASK-{created_at.strftime('%Y-%m-%d')}-{task_index:03d}"
            tasks.append(TaskMessage(
                task_id=task_id,
                project_root=str(self.project_root),
                target_files=[file_path],
                mode=self.mode,
                current_agent=self.first_agent,
                next_agent=self._agent_after(self.first_agent),
                round=1,
                max_rounds=self.max_rounds,
                review_focus=list(self.review_focus),
                previous_reports=[],
                forbidden_actions=list(self.forbidden_actions),
                created_at=created_at.isoformat(),
            ))
        return tasks

    def next_round_task(self, task_state: dict[str, object], created_at: datetime) -> TaskMessage:
        """Build a task contract for the next round from stored state.

        Args:
            task_state: StateStore task record.
            created_at: Timestamp for the new message metadata.

        Returns:
            A validated TaskMessage.

        Raises:
            ValueError: If the stored state is incomplete or invalid.
        """

        current_agent = require_string(task_state, "current_agent")
        current_round = require_int(task_state, "current_round")
        reports = allow_empty_string_list(task_state, "reports")
        target_files = allow_empty_string_list(task_state, "target_files")
        next_agent = self._agent_after(current_agent)
        return TaskMessage(
            task_id=require_string(task_state, "task_id"),
            project_root=str(self.project_root),
            target_files=target_files,
            mode=self.mode,
            current_agent=current_agent,
            next_agent=next_agent,
            round=current_round,
            max_rounds=require_int(task_state, "max_rounds"),
            review_focus=list(self.review_focus),
            previous_reports=reports,
            forbidden_actions=list(self.forbidden_actions),
            created_at=created_at.isoformat(),
        )

    def build_verify_task(
        self,
        files: list[str],
        user_prompt: str,
        created_at: datetime,
        start_index: int = 1,
    ) -> TaskMessage:
        """Build a single task covering all files for consistency verification.

        Args:
            files: Sorted relative paths to verify together.
            user_prompt: User-supplied verification question or instruction.
            created_at: Timestamp for task ID and message metadata.
            start_index: Sequence number suffix for the task ID.

        Returns:
            A validated TaskMessage with mode=verify and all files in one task.

        Raises:
            ValueError: If files is empty or user_prompt is blank.
        """

        if not files:
            raise ValueError("At least one file is required for verify task.")
        if not user_prompt.strip():
            raise ValueError("user_prompt must not be empty.")
        if self.max_rounds < 1:
            raise ValueError("max_rounds must be positive.")

        task_id = f"TASK-{created_at.strftime('%Y-%m-%d')}-{start_index:03d}"
        return TaskMessage(
            task_id=task_id,
            project_root=str(self.project_root),
            target_files=files,
            mode=MODE_VERIFY,
            current_agent=self.first_agent,
            next_agent=self._agent_after(self.first_agent),
            round=1,
            max_rounds=self.max_rounds,
            review_focus=list(self.review_focus),
            previous_reports=[],
            forbidden_actions=list(self.forbidden_actions),
            created_at=created_at.isoformat(),
            user_prompt=user_prompt,
        )

    def _validate_settings(self) -> None:
        if self.mode not in {MODE_REVIEW_ONLY, MODE_VERIFY}:
            raise ValueError(f"Unsupported mode: {self.mode}")
        if self.max_rounds < 1:
            raise ValueError("max_rounds must be positive.")
        if self.first_agent not in self.agent_sequence:
            raise ValueError("first_agent must appear in agent_sequence.")
        import re
        for agent in self.agent_sequence:
            if not re.match(r'^[a-z][a-z0-9_]*$', agent):
                raise ValueError(f"Invalid agent name in sequence: {agent}")

    def _agent_after(self, agent: str) -> str:
        index = self.agent_sequence.index(agent)
        return self.agent_sequence[(index + 1) % len(self.agent_sequence)]


