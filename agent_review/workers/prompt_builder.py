"""Prompt builder for review workers."""

from __future__ import annotations

from agent_review.messaging.schemas import MODE_VERIFY, TaskMessage

OUTPUT_SCHEMA = """\
Return a single JSON object with no surrounding Markdown:
- task_id, agent, round, status ("completed"), summary
- target_files (list)
- findings: [{id, severity, category, file, line, title, description, suggestion, confidence}]
- suggestions: [{id, type, title, description, affected_files}]
- questions (list), next_agent_focus (list), requires_human_review (bool)"""


def build_prompt(
    task: TaskMessage,
    previous_reports: list[str],
    perspective: dict[str, str] | None = None,
) -> str:
    """Build a worker prompt for any mode.

    Args:
        task: Validated task contract.
        previous_reports: Ordered prior report texts.
        perspective: Optional {"role_desc", "focus"} for verify mode.

    Returns:
        Prompt text passed to the agent via stdin.
    """

    target_files = "\n".join(f"- `{f}`" for f in task.target_files)
    previous_section = _quote_reports(previous_reports) if previous_reports else ""

    if task.mode == MODE_VERIFY:
        role_line = f"\nRole: {perspective['role_desc']}" if perspective and perspective.get("role_desc") else ""
        focus_section = f"\n## Focus\n{perspective['focus']}\n" if perspective and perspective.get("focus") else ""
        previous_block = f"\n## Previous Reports\n{previous_section}\n" if previous_section else ""
        return f"""\
# Verification Task{role_line}

{task.user_prompt}

Round {task.round}/{task.max_rounds} · {task.task_id} · next: {task.next_agent}

## Files
{target_files}
{focus_section}{previous_block}
## Output
{OUTPUT_SCHEMA}
"""

    review_focus = "\n".join(f"- {f}" for f in task.review_focus)
    previous_block = f"\n## Previous Reports\n{previous_section}\n" if previous_section else ""
    return f"""\
# Code Review

Round {task.round}/{task.max_rounds} · {task.task_id} · next: {task.next_agent}

## Files
{target_files}

## Focus
{review_focus}
{previous_block}
## Output
{OUTPUT_SCHEMA}
"""


def _quote_reports(reports: list[str]) -> str:
    return "\n\n---\n\n".join(
        "\n".join(f"> {line}" if line else ">" for line in report.splitlines())
        for report in reports
    )
