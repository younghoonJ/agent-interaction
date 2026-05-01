"""Markdown report rendering helpers.

Purpose:
    Render validated review reports into deterministic Markdown for human inspection.
Parameters:
    render_report receives a ReviewReport; write_report also receives a destination path.
Return Value:
    render_report returns Markdown text; write_report returns the path it wrote.
Raised Exceptions:
    OSError: If the destination cannot be written.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

from pathlib import Path

from agent_review.messaging.schemas import ReviewReport


def render_report(report: ReviewReport) -> str:
    """Render a review report as Markdown.

    Args:
        report: Validated review report.

    Returns:
        Markdown text.

    Raises:
        None.
    """

    lines = [
        f"# Review Report: {report.task_id}",
        "",
        f"- Agent: `{report.agent}`",
        f"- Round: {report.round}",
        f"- Status: `{report.status}`",
        f"- Requires human review: {str(report.requires_human_review).lower()}",
        "",
        "## Summary",
        "",
        report.summary,
        "",
        "## Target Files",
        "",
    ]
    lines.extend(f"- `{file_path}`" for file_path in report.target_files)
    lines.extend(["", "## Findings", ""])
    if report.findings:
        for finding in report.findings:
            location = f"{finding.file}:{finding.line}" if finding.line else finding.file
            lines.append(f"### {finding.id}: {finding.title}")
            lines.append("")
            lines.append(f"- Severity: `{finding.severity}`")
            lines.append(f"- Category: `{finding.category}`")
            lines.append(f"- Location: `{location}`")
            lines.append(f"- Confidence: {finding.confidence:.2f}")
            lines.append("")
            lines.append(finding.description)
            lines.append("")
            lines.append(f"Suggestion: {finding.suggestion}")
            lines.append("")
    else:
        lines.append("No findings were reported.")
        lines.append("")

    lines.extend(["## Suggestions", ""])
    if report.suggestions:
        for suggestion in report.suggestions:
            files = ", ".join(f"`{file_path}`" for file_path in suggestion.affected_files)
            lines.append(f"- {suggestion.id} [{suggestion.type}] {suggestion.title} ({files})")
            lines.append(f"  {suggestion.description}")
    else:
        lines.append("No suggestions were reported.")

    lines.extend(["", "## Questions", ""])
    if report.questions:
        lines.extend(f"- {question}" for question in report.questions)
    else:
        lines.append("No questions were reported.")

    lines.extend(["", "## Next Agent Focus", ""])
    if report.next_agent_focus:
        lines.extend(f"- {focus}" for focus in report.next_agent_focus)
    else:
        lines.append("No next-agent focus items were provided.")

    lines.append("")
    return "\n".join(lines)


def write_report(report: ReviewReport, path: Path) -> Path:
    """Write a review report as Markdown.

    Args:
        report: Validated review report.
        path: Destination path.

    Returns:
        The destination path.

    Raises:
        OSError: If the destination cannot be written.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(report), encoding="utf-8")
    return path
