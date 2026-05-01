# Codex × Claude Code Alternating Review System — System Design

**Author:** Claude (Anthropic) — based on design by Younghoon  
**Based on:** `codex_claude_rabbitmq_alternating_review_design.md`  
**Date:** 2026-05-01  
**Status:** Draft v1.0

---

## 1. Goal

Codex와 Claude Code가 프로젝트 파일을 번갈아 검토하며 개선 제안을 생성하는 시스템을 구축한다.

초기 목표는 **비파괴적 검증과 제안 생성(review_only)** 이다.

에이전트는 소스 파일을 직접 수정하지 않으며 다음 산출물만 생성한다.

- 문제점 발견 (findings)
- 개선 제안 (suggestions)
- 위험도 평가 (severity)
- 다음 에이전트에게 전달할 검토 포인트 (next_agent_focus)
- JSON + Markdown 리포트

### 1.1 실행 모드

| Mode | 설명 |
|------|------|
| `review_only` | 소스 수정 없음, 리포트만 생성 (MVP) |
| `patch_proposal` | `.agent_reports/patches/*.patch` 파일 생성 (planned) |
| `apply_patch` | 별도 git worktree에서만 패치 적용 (planned) |

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         User / CLI                               │
│         agent-review start <project> --mode review_only          │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Orchestrator                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ FileScanner │  │ TaskBuilder  │  │    StateStore          │  │
│  │             │  │              │  │  (.agent_reports/      │  │
│  │ project/    │  │ task contract│  │   state.json / SQLite) │  │
│  │ → file list │  │ → task queue │  │                        │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                         RabbitMQ                                 │
│                                                                  │
│   Exchanges                    Queues                            │
│   ─────────────────────────    ─────────────────────────────     │
│   agent.tasks   (direct)  ──►  agent.task.codex                  │
│                            ──►  agent.task.claude                │
│   agent.results (direct)  ──►  agent.result.orchestrator         │
│   agent.events  (topic)   ──►  (monitoring/logging)              │
│   agent.dlx     (direct)  ──►  agent.dead                        │
└──────────┬───────────────────────────────────┬───────────────────┘
           │                                   │
           ▼                                   ▼
┌─────────────────────┐             ┌─────────────────────────┐
│   Codex Worker      │             │   Claude Code Worker    │
│ ─────────────────── │             │ ─────────────────────── │
│ codex exec < prompt │             │ claude -p "$(cat ...)"  │
│                     │             │                         │
│ - correctness       │             │ - architecture          │
│ - implementation    │             │ - maintainability       │
│ - test coverage     │             │ - edge cases            │
│ - local refactoring │             │ - doc quality           │
└─────────┬───────────┘             └───────────┬─────────────┘
          │                                     │
          └─────────────────┬───────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                       Report Store                               │
│   .agent_reports/                                                │
│     state.json                                                   │
│     tasks/TASK-<id>/                                             │
│       contract.yaml                                              │
│       round-01-codex.json  round-01-codex.md                     │
│       round-02-claude.json round-02-claude.md                    │
│       ...                                                        │
│       final.md                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Design Principles

### 3.1 Non-destructive First

```
MUST generate proposals.
MUST NOT modify source files in review_only mode.
MUST check git diff before and after each worker run.
MUST fail the task if source files changed unexpectedly.
```

### 3.2 Alternating Agent Loop

```
Round 1: Codex   → 코드 구조, 구현, 테스트 관점 리뷰
Round 2: Claude  → 설계 일관성, 유지보수성, edge case 리뷰
Round 3: Codex   → Claude 피드백 반영한 구체적 제안
Round 4: Claude  → 최종 권고 및 정리
```

각 round는 이전 round의 결과를 반드시 참조한다.

### 3.3 Task Contract Based Execution

모든 작업은 명시적인 task contract를 가지며 닫힌 범위를 가진다.

### 3.4 Traceable Output

모든 에이전트 결과는 `task_id + agent + round` 로 완전히 추적 가능해야 한다.

---

## 4. Synchronization Model

에이전트 간 동기화는 RabbitMQ + Orchestrator의 상태 머신으로 구현한다.

### 4.1 핵심 원칙

```
두 에이전트는 동시에 같은 task의 동일 round를 실행하지 않는다.
다음 round는 이전 round 결과가 result queue에 도착한 후에만 시작한다.
Orchestrator가 유일한 순서 결정자다.
```

### 4.2 Round 진행 흐름 (시퀀스)

```
Orchestrator          RabbitMQ               Agent Worker
     │                    │                       │
     │── publish task ──►  │                       │
     │   (task.codex)      │── deliver task ──────►│
     │                     │                       │── run review
     │                     │                       │── write report
     │                     │◄─ publish result ─────│
     │◄── consume result ──│                       │
     │                     │◄────────── ack ───────│
     │
     │  [Orchestrator: update state, check round < max_rounds]
     │
     │── publish next task ──► (task.claude)
     │                    ...
```

### 4.3 완료 조건 (Orchestrator 체크)

다음 조건 중 하나를 만족하면 해당 task를 완료 처리한다.

```
- round == max_rounds
- 두 에이전트 모두 findings 없음 (stop_when_no_findings: true)
- severity == critical 및 human review 필요
- failure_count >= max_retries
```

### 4.4 Orchestrator 상태 머신

```
               ┌─────────┐
               │ CREATED │
               └────┬────┘
                    │ publish first task
                    ▼
               ┌─────────┐
         ┌────►│ RUNNING │◄────┐
         │     └────┬────┘     │
         │          │           │ next round (round < max)
         │          │ result received
         │          ▼
         │     ┌───────────────┐    round == max
         │     │ ROUND_COMPLETE├──────────────────► DONE
         │     └───────┬───────┘
         │             │ critical finding / human needed
         │             ▼
         │     ┌───────────────┐
         │     │ AWAITING_HUMAN│
         │     └───────────────┘
         │
         │ retry (failure_count < max_retries)
         │
         │     ┌─────────┐
         └─────┤  FAILED │
               └─────────┘
                    │ failure_count >= max_retries
                    ▼
               ┌──────────┐
               │  DEAD    │ (→ agent.dead queue)
               └──────────┘
```

### 4.5 Worker Ack 프로토콜

```
1. receive message (no ack yet)
2. validate contract schema
3. run agent command
4. parse & validate output JSON
5. write report files
6. publish result to agent.result.orchestrator
7. basic_ack  ← 여기서만 ack

실패 시:
  - publish failure result
  - basic_nack (requeue=False) → dead-letter queue로 이동
```

Orchestrator가 dead-letter queue를 모니터링하며 `failure_count < max_retries` 이면 재발행한다.

---

## 5. RabbitMQ Design

### 5.1 Exchange 구성

| Exchange | Type | Purpose |
|----------|------|---------|
| `agent.tasks` | direct | worker에게 작업 전달 |
| `agent.results` | direct | worker 결과 수집 |
| `agent.events` | topic | 상태 이벤트 발행 |
| `agent.dlx` | direct | 실패 메시지 보관 |

### 5.2 Queue 구성

| Queue | Consumer | Purpose |
|-------|----------|---------|
| `agent.task.codex` | Codex worker | Codex 작업 |
| `agent.task.claude` | Claude worker | Claude 작업 |
| `agent.result.orchestrator` | Orchestrator | 결과 수집 |
| `agent.dead` | Operator / Orchestrator | 실패 작업 |

### 5.3 Routing Keys

```
task.codex              → agent.task.codex
task.claude             → agent.task.claude
result.orchestrator     → agent.result.orchestrator
event.task.created
event.task.completed
event.task.failed
event.round.completed
dead.task               → agent.dead
```

### 5.4 Message Durability

```
delivery_mode = persistent
queue durable = true
manual ack = true
```

### 5.5 Retry 전략

```yaml
max_retries: 3
retry_delays:
  - 10s
  - 60s
  - 300s
```

MVP: `failure_count < 3` → Orchestrator가 재발행, `failure_count >= 3` → `agent.dead`

---

## 6. Message Schemas

### 6.1 Task Message

```json
{
  "message_type": "agent_task",
  "schema_version": "1.0",
  "task_id": "TASK-2026-05-01-001",
  "project_root": "/path/to/project",
  "target_files": [
    "src/compiler/graph.py",
    "src/compiler/pass.py"
  ],
  "mode": "review_only",
  "current_agent": "codex",
  "next_agent": "claude",
  "round": 1,
  "max_rounds": 4,
  "review_focus": ["correctness", "testability", "maintainability"],
  "previous_reports": [],
  "forbidden_actions": ["modify_file", "git_commit", "delete_file"],
  "created_at": "2026-05-01T00:00:00+09:00"
}
```

### 6.2 Result Message (성공)

```json
{
  "message_type": "agent_result",
  "schema_version": "1.0",
  "task_id": "TASK-2026-05-01-001",
  "agent": "codex",
  "round": 1,
  "status": "completed",
  "report_json_path": ".agent_reports/tasks/TASK-2026-05-01-001/round-01-codex.json",
  "report_md_path": ".agent_reports/tasks/TASK-2026-05-01-001/round-01-codex.md",
  "summary": "Found 3 potential issues and 2 test improvement opportunities.",
  "next_agent": "claude",
  "next_focus": [
    "Check whether proposed test cases reflect architecture invariants.",
    "Review whether suggested refactoring changes public behavior."
  ],
  "created_at": "2026-05-01T00:01:30+09:00"
}
```

### 6.3 Result Message (실패)

```json
{
  "message_type": "agent_result",
  "schema_version": "1.0",
  "task_id": "TASK-2026-05-01-001",
  "agent": "codex",
  "round": 1,
  "status": "failed",
  "error_type": "agent_timeout",
  "error_message": "Codex command timed out.",
  "retryable": true,
  "failure_count": 1,
  "created_at": "2026-05-01T00:01:30+09:00"
}
```

### 6.4 Review Report (JSON)

```json
{
  "task_id": "TASK-2026-05-01-001",
  "agent": "codex",
  "round": 1,
  "status": "completed",
  "summary": "Short summary.",
  "target_files": ["src/compiler/graph.py"],
  "findings": [
    {
      "id": "F001",
      "severity": "medium",
      "category": "correctness",
      "file": "src/compiler/graph.py",
      "line": 120,
      "title": "Potential missing shape validation",
      "description": "The function assumes rank-4 input but does not validate it.",
      "suggestion": "Add explicit rank check or document the invariant.",
      "confidence": 0.78
    }
  ],
  "suggestions": [
    {
      "id": "S001",
      "type": "test",
      "title": "Add rank mismatch test",
      "description": "Add a test case for non-rank-4 input.",
      "affected_files": ["tests/test_graph.py"]
    }
  ],
  "questions": [
    "Is rank-4 guaranteed by a previous canonicalization pass?"
  ],
  "next_agent_focus": [
    "Validate whether rank-4 is an invariant in earlier passes."
  ],
  "requires_human_review": false
}
```

---

## 7. Component Specifications

### 7.1 Orchestrator

```
책임:
  - 프로젝트 폴더 스캔 (FileScanner)
  - 파일 그룹 생성 및 task contract 발행
  - round 순서 관리 (다음 에이전트 결정)
  - StateStore 갱신
  - 실패 작업 재시도 또는 dead 처리
  - 최종 리포트 생성

구현:
  agent_review/orchestrator/
    main.py           ← 메인 루프 (result queue 소비)
    scanner.py        ← 파일 탐색, 그룹핑
    task_builder.py   ← task contract 생성
    scheduler.py      ← 다음 에이전트/round 결정
    state_store.py    ← 상태 저장/조회
    report_builder.py ← final.md 생성
```

### 7.2 File Scanner

```yaml
include_extensions: [.py, .md, .yaml, .yml, .json, .toml, .sh, .cpp, .hpp, .c, .h, .ts, .js]
exclude_dirs: [.git, .venv, node_modules, build, dist, __pycache__, .cache]
exclude_patterns: ["*.pyc", "*.so", "*.dll", "*.png", "*.jpg"]
```

### 7.3 Codex Worker

```
주요 검토 관점:
  - correctness
  - implementation feasibility
  - test coverage
  - API compatibility
  - local refactoring opportunity
  - obvious bug patterns

명령 추상화:
  codex exec --sandbox read-only < prompt.md
  또는: codex < prompt.md
```

### 7.4 Claude Code Worker

```
주요 검토 관점:
  - architecture consistency
  - maintainability
  - hidden coupling
  - missing edge cases
  - documentation quality
  - review quality of previous agent

명령 추상화:
  claude -p "$(cat prompt.md)"
  또는: claude < prompt.md
```

### 7.5 Agent Prompt Contract

```markdown
# Agent Review Task

## Role
You are the {agent} review worker.

## Mode
review_only
You MUST NOT modify files.
You MUST NOT commit.
You MUST NOT delete files.
You MUST only generate a review report.

## Project Root
{project_root}

## Target Files
{target_files}

## Previous Reports
{previous_reports}

## Review Focus
{review_focus}

## Required Output
Generate both JSON and Markdown reports.
JSON MUST follow the report schema defined in the task contract.
```

---

## 8. File Grouping Strategy

| Phase | Strategy | 설명 |
|-------|----------|------|
| MVP (v0.1) | one file per task | 구현 단순, 실패 격리 용이 |
| v0.2 (planned) | directory-based | 문맥 풍부, 구조적 리뷰 가능 |
| v0.3 (planned) | dependency-aware | source + test + interface 묶음 |

---

## 9. Orchestrator State Store

### 9.1 MVP: JSON 파일

```json
{
  "tasks": {
    "TASK-2026-05-01-001": {
      "status": "running",
      "current_round": 2,
      "max_rounds": 4,
      "current_agent": "claude",
      "target_files": ["src/compiler/graph.py"],
      "reports": [
        ".agent_reports/tasks/TASK-2026-05-01-001/round-01-codex.json"
      ],
      "failure_count": 0
    }
  }
}
```

### 9.2 확장: SQLite → PostgreSQL (planned)

---

## 10. Report Store Layout

```
.agent_reports/
  state.json
  index.json
  tasks/
    TASK-2026-05-01-001/
      contract.yaml
      round-01-codex.json
      round-01-codex.md
      round-02-claude.json
      round-02-claude.md
      round-03-codex.json
      round-03-codex.md
      round-04-claude.json
      round-04-claude.md
      final.md
```

---

## 11. Safety Rules

```
MUST run agents in read-only mode if possible.
MUST write reports only under .agent_reports/.
MUST NOT allow agent to commit.
MUST NOT allow agent to delete files.
MUST NOT allow agent to modify source files in review_only mode.
MUST check git diff --name-only before and after each worker run.
MUST fail the task if source files changed unexpectedly.
```

```python
# Safety gate (worker에서 수행)
before = set(subprocess.check_output(["git", "diff", "--name-only"]).split())
run_agent(task)
after = set(subprocess.check_output(["git", "diff", "--name-only"]).split())

unexpected = (after - before) - set(allowed_write_dirs)
if unexpected:
    raise SafetyViolation(f"Unexpected file changes: {unexpected}")
```

---

## 12. Default Configuration

```yaml
rabbitmq:
  url: "amqp://agent:agent@localhost:5672/%2F"

project:
  root: "."
  report_dir: ".agent_reports"
  include_extensions: [".py", ".md", ".yaml", ".yml", ".json", ".toml", ".sh"]
  exclude_dirs: [".git", ".venv", "node_modules", "build", "dist", "__pycache__"]

review:
  mode: "review_only"
  max_rounds: 4
  first_agent: "codex"
  agent_sequence: ["codex", "claude"]
  stop_when_no_findings: true

safety:
  allow_source_modification: false
  allowed_write_dirs: [".agent_reports"]
  fail_on_unexpected_git_diff: true

retry:
  max_retries: 3
  retry_delays_seconds: [10, 60, 300]
```

---

## 13. Docker Compose

```yaml
services:
  rabbitmq:
    image: rabbitmq:3-management
    container_name: agent-review-rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: agent
      RABBITMQ_DEFAULT_PASS: agent
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

volumes:
  rabbitmq_data:
```

Management UI: `http://localhost:15672` (user: agent / agent)

---

## 14. Repository Layout

```
agent-review-system/
  README.md
  pyproject.toml
  docker-compose.yaml

  agent_review/
    __init__.py

    orchestrator/
      main.py
      scanner.py
      task_builder.py
      scheduler.py
      state_store.py
      report_builder.py

    messaging/
      rabbitmq.py      ← RabbitMQClient (exchange/queue setup, publish/consume)
      schemas.py       ← Pydantic models (TaskMessage, ResultMessage, ReviewReport)

    workers/
      base_worker.py   ← handle_message, safety gate, ack protocol
      codex_worker.py
      claude_worker.py
      prompt_builder.py

    reports/
      json_report.py
      markdown_report.py

    config/
      default.yaml

  scripts/
    run_rabbitmq.sh
    start_orchestrator.sh
    start_codex_worker.sh
    start_claude_worker.sh

  examples/
    task_contract.yaml
    report.json
```

---

## 15. Core Python Abstractions

### 15.1 RabbitMQ Client

```python
import json
import pika

class RabbitMQClient:
    def __init__(self, url: str):
        self.connection = pika.BlockingConnection(pika.URLParameters(url))
        self.channel = self.connection.channel()

    def setup(self):
        ch = self.channel
        ch.exchange_declare("agent.tasks",   exchange_type="direct", durable=True)
        ch.exchange_declare("agent.results", exchange_type="direct", durable=True)
        ch.exchange_declare("agent.events",  exchange_type="topic",  durable=True)
        ch.exchange_declare("agent.dlx",     exchange_type="direct", durable=True)

        dlx_args = {"x-dead-letter-exchange": "agent.dlx",
                    "x-dead-letter-routing-key": "dead.task"}
        ch.queue_declare("agent.task.codex",            durable=True, arguments=dlx_args)
        ch.queue_declare("agent.task.claude",           durable=True, arguments=dlx_args)
        ch.queue_declare("agent.result.orchestrator",   durable=True)
        ch.queue_declare("agent.dead",                  durable=True)

        ch.queue_bind("agent.task.codex",          "agent.tasks",   "task.codex")
        ch.queue_bind("agent.task.claude",         "agent.tasks",   "task.claude")
        ch.queue_bind("agent.result.orchestrator", "agent.results", "result.orchestrator")
        ch.queue_bind("agent.dead",                "agent.dlx",     "dead.task")

    def publish_json(self, exchange: str, routing_key: str, payload: dict):
        self.channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=json.dumps(payload, ensure_ascii=False).encode(),
            properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
        )
```

### 15.2 Base Worker

```python
def handle_message(channel, method, properties, body):
    task = json.loads(body)

    try:
        validate_contract(task)
        before_files = get_git_diff_files()

        report = run_agent(task)          # CodexRunner or ClaudeRunner
        validate_report_schema(report)

        after_files = get_git_diff_files()
        check_safety_gate(before_files, after_files)

        write_report_files(task, report)
        publish_result(task, report)
        channel.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        publish_failure(task, e)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
```

### 15.3 Agent Runner Abstraction

```python
class CodexRunner:
    def run(self, prompt_path: str, project_root: str) -> str:
        # codex exec --sandbox read-only < prompt_path
        ...

class ClaudeRunner:
    def run(self, prompt_path: str, project_root: str) -> str:
        # claude -p "$(cat prompt_path)"
        ...
```

---

## 16. CLI Design

```bash
agent-review init
agent-review start /path/to/project
agent-review start /path/to/project --include "src/**/*.py" --max-rounds 4
agent-review status
agent-review show TASK-2026-05-01-001
agent-review final TASK-2026-05-01-001
agent-review resume
agent-review stop
```

---

## 17. Git Integration

```
MVP:
  - source tree는 clean 상태에서 시작
  - agent report만 .agent_reports/ 에 생성
  - final report 확인 후 사람이 별도 issue/task 생성

v0.2 (patch_proposal):
  - .agent_reports/patches/*.patch 생성만 허용

v0.3 (apply_patch):
  - git worktree 별도 브랜치에서만 패치 적용
  - Human Approval Gate 필수:
    LLM proposal → human selection → patch generation → verification → merge
```

---

## 18. Scaling

### 18.1 Worker 수평 확장

```
agent.task.codex  → codex-worker-1, codex-worker-2, ...
agent.task.claude → claude-worker-1, claude-worker-2, ...
```

단, 같은 task_id의 round 순서는 Orchestrator가 보장한다.

### 18.2 Agent 추가

새 agent 추가 시 queue와 routing key만 늘린다.

```
agent.task.gemini
agent.task.static_analyzer
agent.task.test_runner
```

### 18.3 Static Analyzer Worker 추가 (planned, v0.3)

```
Codex → Static Analyzer → Claude → Codex
```

Static analyzer (ruff, mypy, eslint, tsc, clang-tidy 등)는 LLM보다 신뢰도 높은 hard signal을 제공한다.

---

## 19. Implementation Roadmap

### v0.1 (MVP)

목표: Codex와 Claude가 번갈아 파일을 리뷰하고 Markdown 리포트를 생성한다.

포함:
- RabbitMQ docker-compose
- file scanner (single file per task)
- task contract 생성
- codex / claude / result queue
- report store
- max_rounds 제어
- read-only safety gate

제외:
- 자동 수정, PR 생성, 병렬 worktree, dependency-aware grouping, retry delay queue

### v0.2 (planned)

추가:
- directory-based grouping
- JSON schema validation (Pydantic)
- final report builder
- failure retry + dead-letter monitoring
- CLI status command

### v0.3 (planned)

추가:
- static analyzer worker
- patch proposal mode
- git worktree isolation
- dependency-aware grouping
- web dashboard

---

## 20. Initial Setup Steps

```bash
# Step 1: RabbitMQ 실행
docker compose up -d rabbitmq

# Step 2: Queue 초기화
python -m agent_review.messaging.setup

# Step 3: 프로젝트 스캔 및 태스크 생성
agent-review start . --mode review_only --max-rounds 4

# Step 4: Worker 실행 (각각 별도 터미널)
agent-review worker codex
agent-review worker claude
agent-review orchestrator

# Step 5: 결과 확인
agent-review status
agent-review final
```

---

## 21. Implementation Notes

### 21.1 LLM 출력 신뢰하지 않기

```
invalid JSON        → task failed
missing required fields → task failed
source modified unexpectedly → task failed (safety gate)
```

### 21.2 작은 단위로 실행

```
small target → better review quality
large target → vague suggestions
```

### 21.3 리뷰와 패치 분리

```
Review phase:  produces findings
Patch phase:   consumes accepted findings → produces patch
```

### 21.4 Human Approval Gate (patch 단계)

```
LLM proposal → human selection → patch generation → verification → merge
```

---

## 22. Example Round Trace

**Round 1 — Codex**
```
Input: src/compiler/shape_inference.py
Finding: Missing validation for symbolic dimension merge.
Suggestion: Add explicit conflict check when merging known and symbolic dimensions.
Next focus: Check whether this invariant belongs here or in graph normalization.
```

**Round 2 — Claude**
```
Input: target file + Codex round-01 report
Finding: Codex's finding is valid, but responsibility may belong to normalization pass.
Suggestion: Document the invariant in normalization and add test at boundary.
Next focus: Propose minimal test cases and verify call path.
```

**Round 3 — Codex**
```
Suggestion: Add tests:
  - known dim vs symbolic dim
  - conflicting known dims
  - unknown dim propagation
Patch proposal: Not generated (mode: review_only).
```

**Round 4 — Claude**
```
Final recommendation:
  Implement validation in normalization pass.
  Add boundary tests in shape inference test suite.
```

---

## 23. Summary

| Component | 역할 |
|-----------|------|
| RabbitMQ | task/result transport, retry, dead-letter |
| Orchestrator | state machine, round 순서 제어, 실패 복구 |
| Codex Worker | 구현 중심 리뷰어 |
| Claude Code Worker | 아키텍처 중심 리뷰어 |
| Report Store | 추적 가능한 산출물 저장 |
| Safety Gate | read-only 강제, git diff 검증 |

핵심 설계 포인트:

1. 모든 작업은 task contract로 닫힌 범위를 가진다.
2. 두 에이전트는 번갈아 실행되며, 순서는 Orchestrator가 보장한다.
3. RabbitMQ는 durable queue + manual ack + dead-letter로 메시지 유실을 방지한다.
4. 동기화는 result queue 소비 후 Orchestrator가 다음 round를 발행하는 방식으로 구현한다.
5. 결과는 JSON + Markdown으로 저장되어 사람이 검토 가능하다.
