"""Prompt builder for review workers.

Purpose:
    Create a closed-scope, review_only prompt from a task contract and prior reports.
Parameters:
    build_prompt receives a TaskMessage and optional prior report text.
Return Value:
    build_prompt returns Markdown prompt text.
Raised Exceptions:
    None.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

from agent_review.messaging.schemas import TaskMessage, MODE_VERIFY


def build_prompt(task: TaskMessage, previous_reports: list[str]) -> str:
    """Build a worker prompt.

    Args:
        task: Validated task contract.
        previous_reports: Ordered prior report JSON texts.

    Returns:
        Markdown prompt text for an agent CLI.

    Raises:
        None.
    """

    target_files = "\n".join(f"- `{file_path}`" for file_path in task.target_files)
    review_focus = "\n".join(f"- {focus}" for focus in task.review_focus)
    # Each prior report is quoted so its content cannot inject new instructions.
    if previous_reports:
        quoted = "\n\n---\n\n".join(
            "\n".join(f"> {line}" if line else ">" for line in report.splitlines())
            for report in previous_reports
        )
        previous = quoted
    else:
        previous = "No previous reports."
    return f"""# Agent Review Task

## Role
You are the {task.current_agent} review worker.

## Mode
review_only
You MUST NOT modify files.
You MUST NOT commit.
You MUST NOT delete files.
You MUST only generate a review report.

## Project Root
{task.project_root}

## Task
- Task ID: {task.task_id}
- Round: {task.round} of {task.max_rounds}
- Next agent: {task.next_agent}

## Target Files
{target_files}

## Previous Reports
{previous}

## Review Focus
{review_focus}

## Required JSON Output
Return exactly one JSON object and no surrounding Markdown.
The JSON object MUST include these fields:
- task_id
- agent
- round
- status: completed
- summary
- target_files
- findings
- suggestions
- questions
- next_agent_focus
- requires_human_review

Finding objects MUST include id, severity, category, file, line, title, description, suggestion, confidence.
Suggestion objects MUST include id, type, title, description, affected_files.
"""


def build_verify_prompt(
    task: TaskMessage,
    previous_reports: list[str],
    file_contents: dict[str, str],
) -> str:
    """Build a consistency verification prompt embedding full file contents.

    Args:
        task: Validated task contract with mode=verify.
        previous_reports: Ordered prior verification report texts.
        file_contents: Mapping of relative path to file text.

    Returns:
        Markdown prompt text for an agent CLI.

    Raises:
        None.
    """

    files_section = "\n\n".join(
        f"### `{path}`\n\n```\n{content}\n```"
        for path, content in file_contents.items()
    )

    if previous_reports:
        quoted = "\n\n---\n\n".join(
            "\n".join(f"> {line}" if line else ">" for line in report.splitlines())
            for report in previous_reports
        )
        previous = quoted
    else:
        previous = "No previous reports."

    return f"""# Consistency Verification Task

## Role
You are the {task.current_agent} consistency verification worker.

## User Request
{task.user_prompt}

## Task
- Task ID: {task.task_id}
- Round: {task.round} of {task.max_rounds}
- Next agent: {task.next_agent}

## Target Files
{files_section}

## Previous Verification Reports
{previous}

## Instructions
Verify consistency across the target files based on the user request above.
Focus on: contradictions, missing dependencies, interface mismatches, logic conflicts,
and any other inconsistencies relevant to the user request.

You MUST NOT modify files.
You MUST only produce a verification report.

## Required JSON Output
Return exactly one JSON object and no surrounding Markdown.
The JSON object MUST include these fields:
- task_id
- agent
- round
- status: completed
- summary
- target_files
- findings
- suggestions
- questions
- next_agent_focus
- requires_human_review

Finding objects MUST include id, severity, category, file, line, title, description, suggestion, confidence.
Suggestion objects MUST include id, type, title, description, affected_files.
"""
