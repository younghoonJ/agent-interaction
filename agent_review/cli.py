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
from dataclasses import replace as dc_replace
from datetime import datetime, timezone
from pathlib import Path

import yaml

from agent_review.config.loader import load_config
from agent_review.messaging.rabbitmq import (
    EXCHANGE_TASKS,
    RabbitMQClient,
    queue_for_agent,
    routing_for_agent,
)
from agent_review.messaging.schemas import MODE_REVIEW_ONLY, MODE_VERIFY, STATUS_COMPLETED, ReviewReport, TaskMessage
from agent_review.orchestrator.main import Orchestrator
from agent_review.orchestrator.report_builder import ReportBuilder
from agent_review.orchestrator.scanner import FileScanner
from agent_review.orchestrator.scheduler import Scheduler
from agent_review.orchestrator.state_store import StateStore
from agent_review.orchestrator.task_builder import TaskBuilder
from agent_review.workers.base_worker import ReviewWorker
from agent_review.workers.runners import CommandRunner

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

    verify_parser = subparsers.add_parser("verify", help="Verify consistency of files, directories, or globs.")
    verify_parser.add_argument("files", nargs="+", help="Files, directories, or globs to verify.")
    verify_parser.add_argument("--project", type=Path, default=None, help="Project root (default: current directory).")
    verify_parser.add_argument("--prompt", default=None, help="Verification question (default: generic consistency check).")
    verify_parser.add_argument("--max-rounds", type=int, default=None)
    verify_parser.add_argument("--no-publish", action="store_true", help="Write task contract without publishing.")
    verify_parser.set_defaults(handler=_cmd_verify)

    worker_parser = subparsers.add_parser("worker", help="Run a worker consumer.")
    worker_parser.add_argument("agent", help="Agent name as defined in config (e.g. agent_a).")
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

    up_parser = subparsers.add_parser("up", help="Start all workers and orchestrator.")
    up_parser.add_argument("project", type=Path, nargs="?", default=Path("."))
    up_parser.set_defaults(handler=_cmd_up)

    run_parser = subparsers.add_parser("run", help="Run agents inline without RabbitMQ.")
    run_parser.add_argument(
        "targets",
        nargs="+",
        metavar="FILE_OR_PROMPT",
        help="Files, directories, or globs. If the last argument does not resolve to a path, it is used as the prompt.",
    )
    run_parser.add_argument("--project", type=Path, default=None, help="Project root (default: auto-detected).")
    run_parser.add_argument("--max-rounds", type=int, default=None)
    run_parser.set_defaults(handler=_cmd_run)
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
    config = load_config(args.config)
    project_config = _mapping(config, "project")
    review_config = _mapping(config, "review")
    retry_config = _mapping(config, "retry")

    if args.project is not None:
        project_root = args.project.resolve()
        abs_files = _collect_absolute_files(args.files, project_root, project_config)
    else:
        abs_files = _collect_absolute_files(args.files, None, project_config)
        if not abs_files:
            print("No files found.")
            return 0
        project_root = _common_parent(abs_files)
    report_dir = project_root / _string(project_config, "report_dir")

    try:
        files = [p.relative_to(project_root).as_posix() for p in sorted(abs_files)]
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not files:
        print("No files found.")
        return 0

    prompt = args.prompt if args.prompt is not None else DEFAULT_VERIFY_PROMPT
    max_rounds = args.max_rounds if args.max_rounds is not None else _int(review_config, "max_rounds")

    now = datetime.now(timezone.utc).astimezone()
    state_store = StateStore(report_dir)
    start_index = state_store.next_sequence_for_date(now.strftime("%Y-%m-%d"))
    builder = _task_builder(project_root, max_rounds, review_config)
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
    review_config = _mapping(config, "review")
    agent_sequence = _string_list(review_config, "agent_sequence")
    client = _rabbitmq_client(config)
    client.setup(agent_sequence)
    worker = _create_worker(args.agent, config, project_root, report_dir, client)
    queue = queue_for_agent(args.agent)
    client.channel.basic_qos(prefetch_count=1)
    client.channel.basic_consume(queue=queue, on_message_callback=worker.handle_delivery)
    print(f"Consuming {queue}.")
    client.channel.start_consuming()
    return 0


def _cmd_orchestrator(args: argparse.Namespace) -> int:
    project_root, report_dir, config = _load_context(args)
    review_config = _mapping(config, "review")
    retry_config = _mapping(config, "retry")
    agent_sequence = _string_list(review_config, "agent_sequence")
    client = _rabbitmq_client(config)
    client.setup(agent_sequence)
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


def _cmd_up(args: argparse.Namespace) -> int:
    import signal
    import subprocess
    import threading

    project_root, report_dir, config = _load_context(args)
    review_config = _mapping(config, "review")
    agent_sequence = _string_list(review_config, "agent_sequence")

    if not (report_dir / "state.json").exists():
        StateStore(report_dir).save({"tasks": {}})
        _write_index(report_dir, [])

    exe = sys.executable
    base_cmd = [exe, "-m", "agent_review.cli", "--config", str(args.config)] if args.config else [exe, "-m", "agent_review.cli"]

    procs: list[subprocess.Popen[str]] = []
    labels: list[str] = []
    for agent in agent_sequence:
        procs.append(subprocess.Popen(
            base_cmd + ["worker", agent, str(project_root)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        ))
        labels.append(agent)
    procs.append(subprocess.Popen(
        base_cmd + ["orchestrator", str(project_root)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    ))
    labels.append("orchestrator")

    def _stream(proc: subprocess.Popen[str], label: str) -> None:
        assert proc.stdout
        for line in proc.stdout:
            print(f"[{label}] {line}", end="", flush=True)

    threads = [threading.Thread(target=_stream, args=(p, l), daemon=True) for p, l in zip(procs, labels)]
    for t in threads:
        t.start()

    def _shutdown(sig: int, frame: object) -> None:
        print("\nShutting down...", flush=True)
        for p in procs:
            p.terminate()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    agents_str = ", ".join(agent_sequence)
    print(f"Started workers ({agents_str}) + orchestrator. Ctrl-C to stop.")
    for p in procs:
        p.wait()
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    project_config = _mapping(config, "project")
    review_config = _mapping(config, "review")
    retry_config = _mapping(config, "retry")

    targets, prompt = _split_targets_and_prompt(list(args.targets))

    if args.project is not None:
        project_root = args.project.resolve()
        abs_files = _collect_absolute_files(targets, project_root, project_config)
    else:
        abs_files = _collect_absolute_files(targets, None, project_config)
        if not abs_files:
            print("No files found.", file=sys.stderr)
            return 1
        project_root = _common_parent(abs_files)

    try:
        rel_files = sorted(p.relative_to(project_root).as_posix() for p in abs_files)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not rel_files:
        print("No files found.", file=sys.stderr)
        return 1

    prompt = prompt or DEFAULT_VERIFY_PROMPT
    max_rounds = args.max_rounds if args.max_rounds is not None else _int(review_config, "max_rounds")
    report_dir = project_root / _string(project_config, "report_dir")

    now = datetime.now(timezone.utc).astimezone()
    state_store = StateStore(report_dir)
    start_index = state_store.next_sequence_for_date(now.strftime("%Y-%m-%d"))
    task = _task_builder(project_root, max_rounds, review_config).build_verify_task(
        rel_files, prompt, now, start_index=start_index
    )
    scheduler = Scheduler(
        agent_sequence=tuple(_string_list(review_config, "agent_sequence")),
        stop_when_no_findings=_bool(review_config, "stop_when_no_findings"),
        max_retries=_int(retry_config, "max_retries"),
    )

    print(f"Task {task.task_id}: {len(rel_files)} file(s), up to {max_rounds} round(s)")
    print(f"Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}\n")
    return _run_inline_loop(task, scheduler, config, project_root, report_dir)


def _run_inline_loop(
    task: TaskMessage,
    scheduler: Scheduler,
    config: dict[str, object],
    project_root: Path,
    report_dir: Path,
) -> int:
    consecutive_no_finding_rounds = 0
    failure_count = 0

    while True:
        worker = _create_worker(task.current_agent, config, project_root, report_dir)
        print(f"[round {task.round}/{task.max_rounds}] {task.current_agent}...", flush=True)
        result = worker.handle_task(task, failure_count=failure_count)

        if result.status != STATUS_COMPLETED:
            print(f"  error ({result.error_type}): {result.error_message}", file=sys.stderr)
            failure_count = int(result.failure_count or failure_count + 1)
            decision = scheduler.evaluate_failed(failure_count, bool(result.retryable))
            if decision.status != "running":
                print(f"Stopping: {decision.reason}", file=sys.stderr)
                return 1
            print("  retrying...")
            continue

        report_path = project_root / (result.report_json_path or "")
        report = ReviewReport.from_dict(json.loads(report_path.read_text(encoding="utf-8")))
        _print_round_summary(result.summary or "", report)

        decision = scheduler.evaluate_completed(report, task.max_rounds, consecutive_no_finding_rounds)
        consecutive_no_finding_rounds = decision.consecutive_no_finding_rounds

        if decision.status != "running":
            print(f"Done ({decision.reason}).")
            return 0

        assert decision.next_agent is not None and decision.next_round is not None
        updated_previous = list(task.previous_reports) + [result.report_json_path or ""]
        task = dc_replace(
            task,
            round=decision.next_round,
            current_agent=decision.next_agent,
            next_agent=scheduler.next_agent(decision.next_agent),
            previous_reports=updated_previous,
        )
        failure_count = 0


def _print_round_summary(summary: str, report: ReviewReport) -> None:
    print(f"  summary: {summary}")
    if report.findings:
        print(f"  {len(report.findings)} finding(s):")
        for finding in report.findings:
            loc = f":{finding.line}" if finding.line else ""
            print(f"    [{finding.severity}] {finding.file}{loc} — {finding.title}")
    else:
        print("  no findings.")
    if report.next_agent_focus:
        print(f"  next focus: {'; '.join(report.next_agent_focus[:3])}")
    print()


def _split_targets_and_prompt(targets: list[str]) -> tuple[list[str], str | None]:
    """Treat the last target as a prompt string if it does not resolve to an existing path or glob."""
    if not targets:
        return [], None
    last = targets[-1]
    resolved = Path(last) if Path(last).is_absolute() else (Path.cwd() / last).resolve()
    if not resolved.exists() and not list(Path.cwd().glob(last)):
        return targets[:-1], last
    return targets, None


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


def _collect_absolute_files(
    targets: list[str],
    project_root: Path | None,
    project_config: dict[str, object],
) -> set[Path]:
    """Resolve targets (files, dirs, globs) to a set of absolute Paths."""
    include_extensions = tuple(_string_list(project_config, "include_extensions"))
    exclude_dirs = tuple(_string_list(project_config, "exclude_dirs"))
    exclude_patterns = tuple(_string_list(project_config, "exclude_patterns"))
    result: set[Path] = set()
    for target in targets:
        p = Path(target)
        resolved = p if p.is_absolute() else (Path.cwd() / p).resolve()
        if resolved.is_file():
            result.add(resolved)
        elif resolved.is_dir():
            for f in FileScanner(
                project_root=resolved,
                include_extensions=include_extensions,
                exclude_dirs=exclude_dirs,
                exclude_patterns=exclude_patterns,
            ).scan():
                result.add((resolved / f).resolve())
        else:
            base = project_root or Path.cwd()
            matched = [m.resolve() for m in base.glob(target) if m.is_file()]
            if not matched:
                print(f"warning: no files matched '{target}'", file=sys.stderr)
            result.update(matched)
    return result


def _common_parent(paths: set[Path]) -> Path:
    """Return the deepest common directory of a set of absolute paths."""
    parts_list = [p.parent.parts for p in paths]
    common = parts_list[0]
    for parts in parts_list[1:]:
        common = common[:len([a for a, b in zip(common, parts) if a == b])]
    return Path(*common) if common else Path("/")


def _rabbitmq_client(config: dict[str, object]) -> RabbitMQClient:
    rabbitmq_config = _mapping(config, "rabbitmq")
    return RabbitMQClient(_string(rabbitmq_config, "url"))


def _routing_for_agent(agent: str) -> str:
    return routing_for_agent(agent)


def _create_worker(
    agent_name: str,
    config: dict[str, object],
    project_root: Path,
    report_dir: Path,
    client: RabbitMQClient | None = None,
) -> ReviewWorker:
    agents_config = _mapping(config, "agents")
    agent_cfg = _mapping(agents_config, agent_name)
    command = tuple(_string_list(agent_cfg, "command"))
    timeout = int(agent_cfg.get("timeout_seconds", 900))
    runner = CommandRunner(command=command, timeout_seconds=timeout)
    perspectives = {
        name: {
            "role_desc": str(acfg.get("role_desc", "")),
            "focus": str(acfg.get("focus", "")),
        }
        for name, acfg in agents_config.items()
        if isinstance(acfg, dict)
    }
    return ReviewWorker(runner, project_root, report_dir, client=client, agent_perspectives=perspectives)


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
