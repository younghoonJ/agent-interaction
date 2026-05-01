"""RabbitMQ setup command module.

Purpose:
    Initialize Agent Review exchanges, queues, bindings, and dead-letter routing.
Parameters:
    The optional --config argument selects a YAML configuration override.
Return Value:
    The module prints a short status line and exits with process status 0 on success.
Raised Exceptions:
    RuntimeError: If RabbitMQ dependencies or broker connectivity are unavailable.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_review.config.loader import load_config
from agent_review.messaging.rabbitmq import RabbitMQClient


def main() -> None:
    """Run RabbitMQ topology setup.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: If configuration or RabbitMQ setup fails.
    """

    parser = argparse.ArgumentParser(description="Initialize Agent Review RabbitMQ topology.")
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    rabbitmq = _mapping(config, "rabbitmq")
    url = _string(rabbitmq, "url")
    client = RabbitMQClient(url)
    try:
        client.setup()
    finally:
        client.close()
    print("RabbitMQ topology initialized.")


def _mapping(data: dict[str, object], key: str) -> dict[str, object]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"Missing configuration section: {key}")
    return value


def _string(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"Missing configuration value: {key}")
    return value


if __name__ == "__main__":
    main()
