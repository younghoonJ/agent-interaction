#!/usr/bin/env bash
set -euo pipefail

agent-review worker claude "${1:-.}"
