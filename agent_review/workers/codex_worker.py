"""Codex worker factory.

Purpose:
    Construct a ReviewWorker using the Codex runner.
Parameters:
    create_worker receives project and report paths plus an optional RabbitMQ client.
Return Value:
    create_worker returns a configured ReviewWorker.
Raised Exceptions:
    None during construction.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

from pathlib import Path

from agent_review.messaging.rabbitmq import RabbitMQClient
from agent_review.workers.base_worker import ReviewWorker
from agent_review.workers.runners import CodexRunner


def create_worker(project_root: Path, report_dir: Path, client: RabbitMQClient | None = None) -> ReviewWorker:
    """Create a Codex review worker.

    Args:
        project_root: Project root.
        report_dir: Report directory.
        client: Optional RabbitMQ client for result publishing.

    Returns:
        Configured ReviewWorker.

    Raises:
        None.
    """

    return ReviewWorker(CodexRunner(), project_root, report_dir, client=client)
