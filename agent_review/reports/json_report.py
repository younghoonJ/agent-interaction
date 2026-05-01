"""JSON report persistence helpers.

Purpose:
    Write validated review reports as deterministic JSON.
Parameters:
    write_report receives a ReviewReport and destination path.
Return Value:
    write_report returns the path it wrote.
Raised Exceptions:
    OSError: If the destination cannot be written.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_review.messaging.schemas import ReviewReport


def write_report(report: ReviewReport, path: Path) -> Path:
    """Write a review report as JSON.

    Args:
        report: Validated review report.
        path: Destination path.

    Returns:
        The destination path.

    Raises:
        OSError: If the destination cannot be written.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(report.to_dict(), file, indent=2, ensure_ascii=False, sort_keys=True)
        file.write("\n")
    return path
