#!/usr/bin/env bash
set -euo pipefail

docker compose up -d rabbitmq
python -m agent_review.messaging.setup
