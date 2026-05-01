"""Command-line interface for Agent Review.

Purpose:
    Provide init, start, worker, orchestrator, status, show, final, resume, and stop commands.
Parameters:
    main receives optional argv for tests; command handlers receive parsed argparse namespaces.
Return Value:
    main returns a process status integer.
Raised Exceptions:
    Command handlers convert expected operational failures into non-zero return codes.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from agent_review.config.loader import load_config
from agent_review.messaging.rabbitmq import (
    EXCHANGE_TASKS,
    QUEUE_CLAUDE,
    QUEUE_CODEX,
    RabbitMQClient,
    ROUTING_TASK_CLAUDE,
    ROUTING_TASK_CODEX,
)
from agent_review.messaging.schemas import AGENT_CLAUDE, AGENT_CODEX, MODE_REVIEW_ONLY, TaskMessage
from agent_review.orchestrator.main import Orchestrator
from agent_review.orchestrator.report_builder import ReportBuilder
from agent_review.orchestrator.scanner import FileScanner
from agent_review.orchestrator.scheduler import Scheduler
from agent_review.orchestrator.state_store import StateStore
from agent_review.orchestrator.task_builder import TaskBuilder
from agent_review.workers.claude_worker import create_worker as create_claude_worker
from agent_review.workers.codex_worker import create_worker as create_codex_worker

DEFAULT_VERIFY_PROMPT = (
    "Verify the consistency of the provided files. "
    "Identify any contradictions, ambiguities, or misalignments between "
    "definitions, rules, examples, and procedures."
)


def main(argv: list[str] | None = None) -> int:
    """Run the Agent Review CLI.

    Args:
        argv: Optional argument vector for tests. When None, sys.argv is used.

    Returns:
        Process status code.

    Raises:
        None. Expected failures are printed and returned as status 1.
    """

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (RuntimeError, ValueError, OSError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-review", description="Alternating Codex/Claude review system.")
    parser.add_argument("--config", type=Path, default=None, help="Optional YAML config override.")
    subparsers = parser.add_subparsers(required=True)

    init_parser = subparsers.add_parser("init", help="Create the local report directory and state file.")
    init_parser.add_argument("project", type=Path, nargs="?", default=Path("."))
    init_parser.set_defaults(handler=_cmd_init)

    start_parser = subparsers.add_parser("start", help="Scan a project and create review tasks.")
    start_parser.add_argument("project", type=Path)
    start_parser.add_argument("--mode", default=MODE_REVIEW_ONLY, choices=[MODE_REVIEW_ONLY])
    start_parser.add_argument("--include", action="append", default=[], help="Include glob; may be repeated.")
    start_parser.add_argument("--max-rounds", type=int, default=None)
    start_parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Write contracts and state without RabbitMQ publish.",
    )
    start_parser.set_defaults(handler=_cmd_start)

    verify_parser = subparsers.add_parser("verify", help="Run a consistency verification across files.")
    verify_parser.add_argument("project", type=Path)
    verify_parser.add_argument("--prompt", default=None, help="Verification question or instruction (default: generic consistency check).")
    verify_parser.add_argument("--include", action="append", default=[], help="Include glob; may be repeated.")
    verify_parser.add_argument("--scan-dir", type=Path, default=None, help="Directory to scan for files (default: project root).")
    verify_parser.add_argument("--max-rounds", type=int, default=None)
    verify_parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Write task contract without publishing to queue.",
    )
    verify_parser.set_defaults(handler=_cmd_verify)

    worker_parser = subparsers.add_parser("worker", help="Run a worker consumer.")
    worker_parser.add_argument("agent", choices=[AGENT_CODEX, AGENT_CLAUDE])
    worker_parser.add_argument("project", type=Path, nargs="?", default=Path("."))
    worker_parser.set_defaults(handler=_cmd_worker)

    orchestrator_parser = subparsers.add_parser("orchestrator", help="Run the result orchestrator.")
    orchestrator_parser.add_argument("project", type=Path, nargs="?", default=Path("."))
    orchestrator_parser.set_defaults(handler=_cmd_orchestrator)

    status_parser = subparsers.add_parser("status", help="Show task state summary.")
    status_parser.add_argument("project", type=Path, nargs="?", default=Path("."))
    status_parser.set_defaults(handler=_cmd_status)

    show_parser = subparsers.add_parser("show", help="Show one task state.")
    show_parser.add_argument("project", type=Path)
    show_parser.add_argument("task_id")
    show_parser.set_defaults(handler=_cmd_show)

    final_parser = subparsers.add_parser("final", help="Build and print final.md for a task.")
    final_parser.add_argument("project", type=Path)
    final_parser.add_argument("task_id", nargs="?")
    final_parser.set_defaults(handler=_cmd_final)

    resume_parser = subparsers.add_parser("resume", help="Republish running tasks from state.")
    resume_parser.add_argument("project", type=Path, nargs="?", default=Path("."))
    resume_parser.set_defaults(handler=_cmd_resume)

    stop_parser = subparsers.add_parser("stop", help="Mark running tasks as stopped.")
    stop_parser.add_argument("project", type=Path, nargs="?", default=Path("."))
    stop_parser.set_defaults(handler=_cmd_stop)
    return parser


def _cmd_init(args: argparse.Namespace) -> int:
    project_root, report_dir, _config = _load_context(args)
    StateStore(report_dir).save({"tasks": {}})
    _write_index(report_dir, [])
    display_path = report_dir.relative_to(project_root) if report_dir.is_relative_to(project_root) else report_dir
    print(f"Initialized report store at {display_path}")
    return 0


def _cmd_start(args: argparse.Namespace) -> int:
    if not args.include:
        print("error: --include is required. Specify at least one glob to avoid unintended full-project scans.", file=sys.stderr)
        print("  example: agent-review start . --include 'agent_review/**'", file=sys.stderr)
        return 1

    project_root, report_dir, config = _load_context(args, project_override=args.project)
    project_config = _mapping(config, "project")
    review_config = _mapping(config, "review")
    retry_config = _mapping(config, "retry")

    max_rounds = args.max_rounds if args.max_rounds is not None else _int(review_config, "max_rounds")
    scanner = FileScanner(
        project_root=project_root,
        include_extensions=tuple(_string_list(project_config, "include_extensions")),
        exclude_dirs=tuple(_string_list(project_config, "exclude_dirs")),
        exclude_patterns=tuple(_string_list(project_config, "exclude_patterns")),
        include_globs=tuple(args.include),
    )
    files = scanner.scan()
    if not files:
        print("No reviewable files found.")
        return 0

    now = datetime.now(timezone.utc).astimezone()
    state_store = StateStore(report_dir)
    start_index = state_store.next_sequence_for_date(now.strftime("%Y-%m-%d"))
    builder = _task_builder(project_root, max_rounds, review_config)
    tasks = builder.build_tasks(files, now, start_index=start_index)

    client = None if args.no_publish else _rabbitmq_client(config)
    try:
        for task in tasks:
            _write_contract(report_dir, task)
            state_store.upsert_task(
                task.task_id,
                _initial_task_state(task, max_retries=_int(retry_config, "max_retries")),
            )
            if client is not None:
                client.publish_json(EXCHANGE_TASKS, _routing_for_agent(task.current_agent), task.to_dict())
    finally:
        if client is not None:
            client.close()

    _write_index(report_dir, tasks)
    action = "created" if args.no_publish else "created and published"
    print(f"{action} {len(tasks)} task(s).")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    if not args.include:
        print("error: --include is required. Specify at least one glob to limit scope.", file=sys.stderr)
        print("  example: agent-review verify . --include 'agent_review/**'", file=sys.stderr)
        return 1

    project_root, report_dir, config = _load_context(args, project_override=args.project)
    project_config = _mapping(config, "project")
    review_config = _mapping(config, "review")
    retry_config = _mapping(config, "retry")

    prompt = args.prompt if args.prompt is not None else DEFAULT_VERIFY_PROMPT
    scan_root = args.scan_dir.resolve() if args.scan_dir is not None else project_root
    max_rounds = args.max_rounds if args.max_rounds is not None else _int(review_config, "max_rounds")
    scanner = FileScanner(
        project_root=scan_root,
        include_extensions=tuple(_string_list(project_config, "include_extensions")),
        exclude_dirs=tuple(_string_list(project_config, "exclude_dirs")),
        exclude_patterns=tuple(_string_list(project_config, "exclude_patterns")),
        include_globs=tuple(args.include),
    )
    files = scanner.scan()
    if not files:
        print("No files found matching the given globs.")
        return 0

    now = datetime.now(timezone.utc).astimezone()
    state_store = StateStore(report_dir)
    start_index = state_store.next_sequence_for_date(now.strftime("%Y-%m-%d"))
    builder = _task_builder(scan_root, max_rounds, review_config)
    task = builder.build_verify_task(files, prompt, now, start_index=start_index)

    client = None if args.no_publish else _rabbitmq_client(config)
    try:
        _write_contract(report_dir, task)
        state_store.upsert_task(
            task.task_id,
            _initial_task_state(task, max_retries=_int(retry_config, "max_retries")),
        )
        if client is not None:
            client.publish_json(EXCHANGE_TASKS, _routing_for_agent(task.current_agent), task.to_dict())
    finally:
        if client is not None:
            client.close()

    _write_index(report_dir, [task])
    action = "created" if args.no_publish else "created and published"
    print(f"{action} verify task {task.task_id} covering {len(files)} file(s).")
    print(f"Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
    return 0


def _cmd_worker(args: argparse.Namespace) -> int:
    project_root, report_dir, config = _load_context(args)
    client = _rabbitmq_client(config)
    client.setup()
    worker = (
        create_codex_worker(project_root, report_dir, client)
        if args.agent == AGENT_CODEX
        else create_claude_worker(project_root, report_dir, client)
    )
    queue = QUEUE_CODEX if args.agent == AGENT_CODEX else QUEUE_CLAUDE
    client.channel.basic_qos(prefetch_count=1)
    client.channel.basic_consume(queue=queue, on_message_callback=worker.handle_delivery)
    print(f"Consuming {queue}.")
    client.channel.start_consuming()
    return 0


def _cmd_orchestrator(args: argparse.Namespace) -> int:
    project_root, report_dir, config = _load_context(args)
    review_config = _mapping(config, "review")
    retry_config = _mapping(config, "retry")
    client = _rabbitmq_client(config)
    client.setup()
    orchestrator = Orchestrator(
        project_root=project_root,
        report_dir=report_dir,
        client=client,
        scheduler=Scheduler(
            agent_sequence=tuple(_string_list(review_config, "agent_sequence")),
            stop_when_no_findings=_bool(review_config, "stop_when_no_findings"),
            max_retries=_int(retry_config, "max_retries"),
        ),
        task_builder=_task_builder(project_root, _int(review_config, "max_rounds"), review_config),
    )
    print("Consuming agent.result.orchestrator.")
    orchestrator.run()
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    _project_root, report_dir, _config = _load_context(args)
    records = StateStore(report_dir).list_tasks()
    counts: dict[str, int] = {}
    for record in records:
        status = str(record.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    if not counts:
        print("No tasks.")
        return 0
    for status in sorted(counts):
        print(f"{status}: {counts[status]}")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    _project_root, report_dir, _config = _load_context(args)
    task = StateStore(report_dir).get_task(args.task_id)
    print(json.dumps(task, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


def _cmd_final(args: argparse.Namespace) -> int:
    project_root, report_dir, _config = _load_context(args)
    task_id = args.task_id or _latest_task_id(StateStore(report_dir))
    path = ReportBuilder(project_root, report_dir).build(task_id)
    print(path.read_text(encoding="utf-8"))
    return 0


def _cmd_resume(args: argparse.Namespace) -> int:
    project_root, report_dir, config = _load_context(args)
    review_config = _mapping(config, "review")
    state_store = StateStore(report_dir)
    client = _rabbitmq_client(config)
    builder = _task_builder(project_root, _int(review_config, "max_rounds"), review_config)
    published = 0
    try:
        for task_state in state_store.list_tasks():
            if task_state.get("status") not in {"running", "queued"}:
                continue
            task = builder.next_round_task(task_state, datetime.now(timezone.utc).astimezone())
            client.publish_json(EXCHANGE_TASKS, _routing_for_agent(task.current_agent), task.to_dict())
            published += 1
    finally:
        client.close()
    print(f"Republished {published} task(s).")
    return 0


def _cmd_stop(args: argparse.Namespace) -> int:
    _project_root, report_dir, _config = _load_context(args)
    state_store = StateStore(report_dir)
    stopped = 0
    for task_state in state_store.list_tasks():
        if task_state.get("status") in {"running", "queued"}:
            state_store.update_task(_string(task_state, "task_id"), {"status": "stopped"})
            stopped += 1
    print(f"Stopped {stopped} task(s).")
    return 0


def _load_context(
    args: argparse.Namespace,
    project_override: Path | None = None,
) -> tuple[Path, Path, dict[str, object]]:
    config = load_config(args.config)
    project_config = _mapping(config, "project")
    project_root = (project_override or getattr(args, "project", Path(_string(project_config, "root")))).resolve()
    report_dir = project_root / _string(project_config, "report_dir")
    return project_root, report_dir, config


def _task_builder(project_root: Path, max_rounds: int, review_config: dict[str, object]) -> TaskBuilder:
    sequence = tuple(_string_list(review_config, "agent_sequence"))
    return TaskBuilder(
        project_root=project_root,
        max_rounds=max_rounds,
        first_agent=_string(review_config, "first_agent"),
        agent_sequence=sequence,
        mode=_string(review_config, "mode"),
    )


def _write_contract(report_dir: Path, task: TaskMessage) -> None:
    task_dir = report_dir / "tasks" / task.task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    contract_path = task_dir / "contract.yaml"
    with contract_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(task.to_dict(), file, allow_unicode=True, sort_keys=True)


def _write_index(report_dir: Path, tasks: list[TaskMessage]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    index_path = report_dir / "index.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "tasks": [
            {
                "task_id": task.task_id,
                "target_files": list(task.target_files),
                "contract_path": f".agent_reports/tasks/{task.task_id}/contract.yaml",
            }
            for task in tasks
        ],
    }
    with index_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False, sort_keys=True)
        file.write("\n")


def _initial_task_state(task: TaskMessage, max_retries: int) -> dict[str, object]:
    return {
        "task_id": task.task_id,
        "status": "queued",
        "current_round": task.round,
        "max_rounds": task.max_rounds,
        "current_agent": task.current_agent,
        "target_files": list(task.target_files),
        "reports": [],
        "failure_count": 0,
        "consecutive_no_finding_rounds": 0,
        "max_retries": max_retries,
        "contract_path": f".agent_reports/tasks/{task.task_id}/contract.yaml",
        "created_at": task.created_at,
    }


def _rabbitmq_client(config: dict[str, object]) -> RabbitMQClient:
    rabbitmq_config = _mapping(config, "rabbitmq")
    return RabbitMQClient(_string(rabbitmq_config, "url"))


def _routing_for_agent(agent: str) -> str:
    if agent == AGENT_CODEX:
        return ROUTING_TASK_CODEX
    if agent == AGENT_CLAUDE:
        return ROUTING_TASK_CLAUDE
    raise ValueError(f"Unsupported agent: {agent}")


def _latest_task_id(state_store: StateStore) -> str:
    records = state_store.list_tasks()
    if not records:
        raise RuntimeError("No tasks available.")
    task_id = records[-1].get("task_id")
    if not isinstance(task_id, str):
        raise RuntimeError("Latest task is missing task_id.")
    return task_id


def _mapping(data: dict[str, object], key: str) -> dict[str, object]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"Missing configuration section: {key}")
    return value


def _string(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"Missing string value: {key}")
    return value


def _int(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise RuntimeError(f"Missing integer value: {key}")
    return value


def _bool(data: dict[str, object], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise RuntimeError(f"Missing boolean value: {key}")
    return value


def _string_list(data: dict[str, object], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise RuntimeError(f"Missing string list value: {key}")
    return list(value)


if __name__ == "__main__":
    raise SystemExit(main())
