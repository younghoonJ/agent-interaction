# Agent Review

> Last updated: 2026-05-01
> Author: Claude (Anthropic) — reviewed by Younghoon

Alternating Codex and Claude Code review and consistency-verification system.
Workers exchange structured JSON reports over RabbitMQ, converging over N rounds.

---

## Prerequisites

- Python 3.10+
- Docker (RabbitMQ runs in a container — started automatically)
- `codex` CLI and `claude` CLI on `PATH`

Install the package:

```bash
pip install -e .
```

---

## Quick Start

Everything is managed through a single script:

```bash
# Code review — alternating Codex ↔ Claude
./scripts/manage.sh start \
  --include "agent_review/**" \
  --include "tests/**"

# Consistency verification with a custom prompt
./scripts/manage.sh verify \
  --prompt "Check that all public APIs in messaging/ are consistently used across workers/" \
  --include "agent_review/messaging/**" \
  --include "agent_review/workers/**"
```

Docker and RabbitMQ are started automatically on first use.
Logs go to `.agent_reports/logs/`. Results go to `.agent_reports/tasks/`.

---

## Commands

| Command | When to use |
|---|---|
| `start` | Begin a new code review run |
| `verify` | Begin a consistency verification run |
| `stop` | Stop workers and orchestrator, keep queue and state |
| `restart` | Full reset: stop → purge queues → clear reports → start fresh |
| `run` | Relaunch processes when tasks are already in the queue |
| `resume` | Restart processes and republish interrupted tasks |
| `status` | Show task counts and running PIDs |
| `logs` | Tail all logs simultaneously |

### start

Scans files matching `--include` globs and creates one review task per file.
Alternates between Codex and Claude for up to `--max-rounds` rounds.

```bash
./scripts/manage.sh start --include "src/**" --include "tests/**"
./scripts/manage.sh start --include "src/**" --max-rounds 2
```

### verify

Bundles all matched files into a **single task** and runs consistency verification
using the user-supplied `--prompt`. Each round, one agent reviews the other's output.

```bash
./scripts/manage.sh verify \
  --prompt "Do the schemas in messaging/ match how workers/ use them?" \
  --include "agent_review/messaging/**" \
  --include "agent_review/workers/**"

./scripts/manage.sh verify \
  --prompt "Are the guidelines internally consistent? List any contradictions." \
  --include "guidelines/**" \
  --max-rounds 6
```

### restart

Stops everything, purges all queues, deletes `.agent_reports/`, and starts fresh.
Use this when you want a clean slate.

```bash
./scripts/manage.sh restart --include "src/**"
./scripts/manage.sh restart --include "src/**" --max-rounds 2
```

### resume

Restarts workers and orchestrator and republishes any tasks that were interrupted
mid-run (e.g. after a crash). State and queue contents are preserved.

```bash
./scripts/manage.sh resume
```

### status / logs

```bash
./scripts/manage.sh status   # task counts + running PIDs
./scripts/manage.sh logs     # tail codex.log, claude.log, orch.log (Ctrl-C to exit)
```

---

## How It Works

```
start / verify
  └─ Scans files → creates TaskMessage contracts → publishes to RabbitMQ

Codex worker     ←─ agent.task.codex queue
  └─ runs codex CLI → parses JSON report → publishes ResultMessage

Claude worker    ←─ agent.task.claude queue
  └─ runs claude CLI → parses JSON report → publishes ResultMessage

Orchestrator     ←─ agent.result.orchestrator queue
  └─ evaluates report → publishes next-round task or marks done
```

Reports are written to `.agent_reports/tasks/<TASK-ID>/`:

```
round-01-codex.json      ← structured findings
round-01-codex.md        ← human-readable summary
round-02-claude.json
round-02-claude.md
...
final.md                 ← combined report on completion
```

---

## Configuration

Default settings are in `agent_review/config/default.yaml`.
Override with `--config path/to/override.yaml`:

```yaml
rabbitmq:
  url: "amqp://agent:agent@localhost:5672/%2F"

review:
  max_rounds: 4
  first_agent: "codex"          # which agent goes first
  agent_sequence: [codex, claude]
  stop_when_no_findings: true   # stop early if both agents find nothing

retry:
  max_retries: 3
```

To change the RabbitMQ credentials, update both `docker-compose.yaml` and `default.yaml`.

---

## Safety

Workers run in `review_only` mode by default. A git-diff safety gate runs before
and after each agent invocation. Any modification to source files outside
`.agent_reports/` is treated as a task failure — the agent cannot alter your code.
