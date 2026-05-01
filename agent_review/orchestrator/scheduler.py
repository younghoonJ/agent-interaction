"""Round scheduler for alternating agent review tasks.

Purpose:
    Decide whether a task is done, paused for human review, retried, dead, or ready for the next round.
Parameters:
    Scheduler receives agent sequence and completion policy settings.
Return Value:
    evaluate_completed and evaluate_failed return ScheduleDecision values.
Raised Exceptions:
    ValueError: If scheduler settings are invalid.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_review.messaging.schemas import AGENT_A, AGENT_B, ReviewReport

STATE_AWAITING_HUMAN = "awaiting_human"
STATE_DEAD = "dead"
STATE_DONE = "done"
STATE_FAILED = "failed"
STATE_RUNNING = "running"
STATE_STOPPED = "stopped"


@dataclass(frozen=True)
class ScheduleDecision:
    """Decision returned by the scheduler.

    Args:
        status: Next task state.
        next_round: Optional next round number.
        next_agent: Optional next agent name.
        reason: Human-readable decision reason.

    Returns:
        Immutable scheduling decision value.

    Raises:
        None.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    status: str
    next_round: int | None
    next_agent: str | None
    reason: str
    consecutive_no_finding_rounds: int = 0


@dataclass(frozen=True)
class Scheduler:
    """Alternating round scheduler.

    Args:
        agent_sequence: Ordered agent rotation.
        stop_when_no_findings: Whether to stop early after an empty completed report.
        max_retries: Maximum retry count before dead state.

    Returns:
        Scheduler instance for deterministic state transitions.

    Raises:
        ValueError: If the agent sequence is empty or unsupported.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    agent_sequence: tuple[str, ...] = (AGENT_A, AGENT_B)
    stop_when_no_findings: bool = True
    max_retries: int = 3

    def __post_init__(self) -> None:
        """Validate scheduler configuration.

        Args:
            None.

        Returns:
            None.

        Raises:
            ValueError: If settings are invalid.
        """

        if not self.agent_sequence:
            raise ValueError("agent_sequence must not be empty.")
        import re
        for agent in self.agent_sequence:
            if not re.match(r'^[a-z][a-z0-9_]*$', agent):
                raise ValueError(f"Invalid agent name in sequence: {agent}")
        if self.max_retries < 1:
            raise ValueError("max_retries must be positive.")

    def evaluate_completed(
        self,
        report: ReviewReport,
        max_rounds: int,
        prior_consecutive_no_finding_rounds: int = 0,
    ) -> ScheduleDecision:
        """Evaluate a completed worker report.

        Args:
            report: Validated worker review report.
            max_rounds: Maximum allowed rounds for the task.
            prior_consecutive_no_finding_rounds: Number of immediately preceding no-finding rounds.

        Returns:
            A scheduling decision.

        Raises:
            ValueError: If max_rounds is invalid.
        """

        if max_rounds < 1:
            raise ValueError("max_rounds must be positive.")
        if prior_consecutive_no_finding_rounds < 0:
            raise ValueError("prior_consecutive_no_finding_rounds must not be negative.")

        no_finding_rounds = prior_consecutive_no_finding_rounds + 1 if not report.findings else 0
        if report.has_critical_finding() or report.requires_human_review:
            return ScheduleDecision(STATE_AWAITING_HUMAN, None, None, "critical finding requires human review", no_finding_rounds)
        if report.round >= max_rounds:
            return ScheduleDecision(STATE_DONE, None, None, "max rounds reached", no_finding_rounds)

        no_finding_threshold = min(len(self.agent_sequence), max_rounds)
        if self.stop_when_no_findings and no_finding_rounds >= no_finding_threshold:
            return ScheduleDecision(STATE_DONE, None, None, "all agents reported no findings", no_finding_rounds)

        next_agent = self.next_agent(report.agent)
        return ScheduleDecision(STATE_RUNNING, report.round + 1, next_agent, "next round", no_finding_rounds)

    def evaluate_failed(self, failure_count: int, retryable: bool) -> ScheduleDecision:
        """Evaluate a failed worker result.

        Args:
            failure_count: Updated failure count for the task.
            retryable: Whether the worker marked the error as retryable.

        Returns:
            A scheduling decision.

        Raises:
            ValueError: If failure_count is negative.
        """

        if failure_count < 0:
            raise ValueError("failure_count must not be negative.")
        if not retryable:
            return ScheduleDecision(STATE_FAILED, None, None, "non-retryable failure")
        if failure_count >= self.max_retries:
            return ScheduleDecision(STATE_DEAD, None, None, "max retries reached")
        return ScheduleDecision(STATE_RUNNING, None, None, "retry")

    def next_agent(self, agent: str) -> str:
        """Return the next agent in the configured rotation.

        Args:
            agent: Current agent name.

        Returns:
            Next agent name.

        Raises:
            ValueError: If the agent is not in the sequence.
        """

        index = self.agent_sequence.index(agent)
        return self.agent_sequence[(index + 1) % len(self.agent_sequence)]
