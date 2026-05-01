#!/usr/bin/env bash
set -euo pipefail

agent-review worker codex "${1:-.}"
