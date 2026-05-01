"""JSON state store for Agent Review.

Purpose:
    Persist task lifecycle state under .agent_reports/state.json for the v0.1 MVP.
Parameters:
    StateStore receives the report directory path.
Return Value:
    Public methods load, save, update, and query JSON-compatible state records.
Raised Exceptions:
    ValueError: If persisted state is malformed.
    OSError: If filesystem reads or writes fail.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

INITIAL_STATE: dict[str, object] = {"tasks": {}}


class StateStore:
    """JSON file backed state store.

    Args:
        report_dir: Directory containing state.json and task reports.

    Returns:
        StateStore instance bound to a report directory.

    Raises:
        None during initialization.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    def __init__(self, report_dir: Path) -> None:
        self.report_dir = report_dir
        self.path = report_dir / "state.json"

    def load(self) -> dict[str, object]:
        """Load state from disk.

        Args:
            None.

        Returns:
            A JSON-compatible state dictionary.

        Raises:
            ValueError: If the state file is malformed.
            OSError: If the state file cannot be read.
        """

        if not self.path.exists():
            return deepcopy(INITIAL_STATE)
        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict) or not isinstance(data.get("tasks"), dict):
            raise ValueError(f"Malformed state file: {self.path}")
        return data

    def save(self, state: dict[str, object]) -> None:
        """Persist state atomically.

        Args:
            state: JSON-compatible state dictionary.

        Returns:
            None.

        Raises:
            ValueError: If the state object is malformed.
            OSError: If the state file cannot be written.
        """

        if not isinstance(state.get("tasks"), dict):
            raise ValueError("State must contain a tasks mapping.")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(state, file, indent=2, ensure_ascii=False, sort_keys=True)
            file.write("\n")
        temporary.replace(self.path)

    def upsert_task(self, task_id: str, task_state: dict[str, object]) -> None:
        """Insert or replace a task state record.

        Args:
            task_id: Task identifier.
            task_state: JSON-compatible task state.

        Returns:
            None.

        Raises:
            ValueError: If state is malformed.
            OSError: If the state file cannot be written.
        """

        state = self.load()
        tasks = _tasks(state)
        record = dict(task_state)
        record["task_id"] = task_id
        tasks[task_id] = record
        self.save(state)

    def get_task(self, task_id: str) -> dict[str, object]:
        """Return one task state record.

        Args:
            task_id: Task identifier.

        Returns:
            A copy of the task state record.

        Raises:
            KeyError: If task_id is unknown.
            ValueError: If state is malformed.
        """

        state = self.load()
        tasks = _tasks(state)
        value = tasks[task_id]
        if not isinstance(value, dict):
            raise ValueError(f"Malformed task state for {task_id}")
        return deepcopy(value)

    def update_task(self, task_id: str, updates: dict[str, object]) -> dict[str, object]:
        """Update one task state record and persist it.

        Args:
            task_id: Task identifier.
            updates: JSON-compatible fields to merge into the task state.

        Returns:
            Updated task state.

        Raises:
            KeyError: If task_id is unknown.
            ValueError: If state is malformed.
        """

        state = self.load()
        tasks = _tasks(state)
        value = tasks[task_id]
        if not isinstance(value, dict):
            raise ValueError(f"Malformed task state for {task_id}")
        value.update(updates)
        self.save(state)
        return deepcopy(value)

    def list_tasks(self) -> list[dict[str, object]]:
        """Return all task records sorted by task_id.

        Args:
            None.

        Returns:
            Sorted task state records.

        Raises:
            ValueError: If state is malformed.
        """

        state = self.load()
        tasks = _tasks(state)
        records: list[dict[str, object]] = []
        for task_id in sorted(tasks):
            value = tasks[task_id]
            if not isinstance(value, dict):
                raise ValueError(f"Malformed task state for {task_id}")
            records.append(deepcopy(value))
        return records

    def next_sequence_for_date(self, date_prefix: str) -> int:
        """Return the next task sequence for a date prefix.

        Args:
            date_prefix: Date prefix formatted as YYYY-MM-DD.

        Returns:
            One-based next integer suffix for task IDs on that date.

        Raises:
            ValueError: If state is malformed.
        """

        highest = 0
        prefix = f"TASK-{date_prefix}-"
        for task in self.list_tasks():
            task_id = task.get("task_id")
            if not isinstance(task_id, str) or not task_id.startswith(prefix):
                continue
            suffix = task_id.removeprefix(prefix)
            if suffix.isdigit():
                highest = max(highest, int(suffix))
        return highest + 1


def _tasks(state: dict[str, object]) -> dict[str, object]:
    tasks = state.get("tasks")
    if not isinstance(tasks, dict):
        raise ValueError("State must contain a tasks mapping.")
    return tasks
