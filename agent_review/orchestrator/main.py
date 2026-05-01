"""RabbitMQ orchestrator loop for Agent Review.

Purpose:
    Consume worker results, update task state, publish next-round tasks, and build final reports.
Parameters:
    Orchestrator receives project paths, RabbitMQ client, scheduler, and task builder instances.
Return Value:
    Public methods process result messages or run the blocking result consumer.
Raised Exceptions:
    ValueError: If result or state data is invalid.
    OSError: If state or report files cannot be written.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agent_review.messaging.rabbitmq import (
    EXCHANGE_TASKS,
    QUEUE_RESULTS,
    RabbitMQClient,
    routing_for_agent,
)
from agent_review.messaging.schemas import ResultMessage, ReviewReport, STATUS_COMPLETED, STATUS_FAILED
from agent_review.orchestrator.report_builder import ReportBuilder
from agent_review.orchestrator.scheduler import STATE_DEAD, STATE_DONE, STATE_RUNNING, Scheduler
from agent_review.orchestrator.state_access import allow_empty_string_list, optional_int, require_int
from agent_review.orchestrator.state_store import StateStore
from agent_review.orchestrator.task_builder import TaskBuilder


class Orchestrator:
    """State machine that advances alternating review rounds.

    Args:
        project_root: Root of the project being reviewed.
        report_dir: Report directory.
        client: RabbitMQ client used to publish next tasks.
        scheduler: Scheduling policy.
        task_builder: Builder used to construct next-round task messages.

    Returns:
        Orchestrator instance.

    Raises:
        None during initialization.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    def __init__(
        self,
        project_root: Path,
        report_dir: Path,
        client: RabbitMQClient,
        scheduler: Scheduler,
        task_builder: TaskBuilder,
    ) -> None:
        self.project_root = project_root
        self.report_dir = report_dir
        self.client = client
        self.scheduler = scheduler
        self.task_builder = task_builder
        self.state_store = StateStore(report_dir)
        self.report_builder = ReportBuilder(project_root, report_dir, self.state_store)

    def run(self) -> None:
        """Start the blocking RabbitMQ result consumer.

        Args:
            None.

        Returns:
            None.

        Raises:
            Exception: If RabbitMQ consumption fails.
        """

        self.client.consume_json(QUEUE_RESULTS, self.process_result_dict)

    def process_result_dict(self, data: dict[str, object]) -> None:
        """Process one decoded result message.

        Args:
            data: JSON-like result message.

        Returns:
            None.

        Raises:
            ValueError: If the result message is invalid.
        """

        self.process_result(ResultMessage.from_dict(data))

    def process_result(self, result: ResultMessage) -> None:
        """Apply a worker result to state and publish the next task if needed.

        Args:
            result: Validated worker result message.

        Returns:
            None.

        Raises:
            KeyError: If the task is unknown.
            ValueError: If state or report data is invalid.
        """

        task_state = self.state_store.get_task(result.task_id)
        if result.status == STATUS_FAILED:
            self._process_failure(result, task_state)
            return
        if result.status != STATUS_COMPLETED:
            raise ValueError(f"Unsupported result status: {result.status}")

        report_path = result.report_json_path or ""
        report = self._load_report(report_path)
        reports = allow_empty_string_list(task_state, "reports")
        if report_path and report_path not in reports:
            reports.append(report_path)

        decision = self.scheduler.evaluate_completed(
            report,
            require_int(task_state, "max_rounds"),
            prior_consecutive_no_finding_rounds=optional_int(task_state, "consecutive_no_finding_rounds"),
        )
        updates: dict[str, object] = {
            "status": decision.status,
            "reports": reports,
            "consecutive_no_finding_rounds": decision.consecutive_no_finding_rounds,
            "last_result_at": result.created_at,
            "last_decision": decision.reason,
        }

        if decision.status == STATE_RUNNING:
            if decision.next_round is None or decision.next_agent is None:
                raise ValueError("Running decision must include next round and agent.")
            updates.update({"current_round": decision.next_round, "current_agent": decision.next_agent})
            # Publish before committing state: if publish fails the result message is
            # not acked and RabbitMQ redelivers it, keeping state consistent.
            # If state write fails after a successful publish the redelivery is a
            # harmless duplicate that overwrites the same values.
            next_task = self.task_builder.next_round_task(
                {**task_state, **updates}, datetime.now(timezone.utc).astimezone()
            )
            self.client.publish_json(EXCHANGE_TASKS, _routing_for_agent(next_task.current_agent), next_task.to_dict())
            self.state_store.update_task(result.task_id, updates)
            return

        self.state_store.update_task(result.task_id, updates)
        if decision.status == STATE_DONE:
            self.report_builder.build(result.task_id)

    def _process_failure(self, result: ResultMessage, task_state: dict[str, object]) -> None:
        failure_count = int(result.failure_count or (require_int(task_state, "failure_count") + 1))
        decision = self.scheduler.evaluate_failed(failure_count, bool(result.retryable))
        updates: dict[str, object] = {
            "status": decision.status,
            "failure_count": failure_count,
            "last_error_type": result.error_type or "",
            "last_error_message": result.error_message or "",
            "last_result_at": result.created_at,
            "last_decision": decision.reason,
        }
        if decision.status == STATE_RUNNING:
            retry_task = self.task_builder.next_round_task(
                {**task_state, **updates}, datetime.now(timezone.utc).astimezone()
            )
            self.client.publish_json(EXCHANGE_TASKS, _routing_for_agent(retry_task.current_agent), retry_task.to_dict())
        self.state_store.update_task(result.task_id, updates)
        if decision.status == STATE_DEAD:
            self.report_builder.build(result.task_id)

    def _load_report(self, relative_path: str) -> ReviewReport:
        path = self.project_root / relative_path
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError(f"Report JSON must be an object: {path}")
        return ReviewReport.from_dict(data)


def _routing_for_agent(agent: str) -> str:
    return routing_for_agent(agent)


