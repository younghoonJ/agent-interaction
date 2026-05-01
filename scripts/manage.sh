#!/usr/bin/env bash
# manage.sh — Agent Review process manager
#
# Usage:
#   ./scripts/manage.sh start   [agent-review start options]
#   ./scripts/manage.sh stop
#   ./scripts/manage.sh restart [agent-review start options]
#   ./scripts/manage.sh resume
#   ./scripts/manage.sh status
#   ./scripts/manage.sh logs
#   ./scripts/manage.sh init
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/.agent_reports"
LOG_DIR="$REPORT_DIR/logs"
PIDFILE="$REPORT_DIR/.pids"
CONTAINER="agent-review-rabbitmq"

QUEUES=(
    agent.task.claude_a
    agent.task.claude_b
    agent.result.orchestrator
    agent.dead
)

# ── helpers ───────────────────────────────────────────────────────────────────

log()  { echo "[$(date '+%H:%M:%S')] $*"; }
die()  { echo "error: $*" >&2; exit 1; }
ok()   { echo "[$(date '+%H:%M:%S')] ✓ $*"; }

usage() {
    cat <<EOF
Usage: $(basename "$0") <command> [options]

Commands:
  start       Scan files, create review tasks, launch workers & orchestrator
              RabbitMQ and Docker are started automatically if needed.
  verify      Consistency verification: bundle files into one task with a prompt
  run         Launch workers & orchestrator only (when tasks are already queued)
  stop        Stop workers and orchestrator (preserves queue and state)
  restart     Full reset: stop → purge queues → clear reports → start fresh
  resume      Restart workers & orchestrator and republish interrupted tasks
  status      Show task status summary and running PIDs
  logs        Tail worker and orchestrator logs (Ctrl-C to exit)
  init        One-time RabbitMQ setup (called automatically by start/verify)

Options for 'start' and 'restart':
  --include GLOB        Files to review — required, repeatable
                        example: --include 'agent_review/**' --include 'tests/**'
  --max-rounds N        Alternating review rounds (default: 4)
  --no-publish          Write contracts to disk without queuing

Options for 'verify':
  --prompt TEXT         Verification question or instruction (optional; default: generic consistency check)
  --scan-dir DIR        Directory to scan for files (default: project root)
  --include GLOB        Glob relative to --scan-dir — required, repeatable
  --max-rounds N        Rounds (default: 4)
EOF
    exit 1
}

# ── rabbitmq ──────────────────────────────────────────────────────────────────

_docker_check() {
    if ! docker info &>/dev/null; then
        echo ""
        echo "  Docker daemon is not running."
        echo "  Start Docker Desktop (Mac/Windows) or run: sudo systemctl start docker"
        echo ""
        die "Docker required but not available"
    fi
}

_rabbitmq_wait() {
    log "Waiting for RabbitMQ to be ready..."
    for i in $(seq 1 40); do
        if docker exec "$CONTAINER" rabbitmqctl status &>/dev/null; then
            ok "RabbitMQ ready"
            return
        fi
        sleep 1
    done
    die "RabbitMQ did not become ready in 40 seconds. Check: docker logs $CONTAINER"
}

_rabbitmq_ensure() {
    _docker_check
    if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER}$"; then
        log "Starting RabbitMQ container..."
        docker compose -f "$PROJECT_ROOT/docker-compose.yaml" up -d rabbitmq
        _rabbitmq_wait
    elif ! docker exec "$CONTAINER" rabbitmqctl status &>/dev/null; then
        log "RabbitMQ container running but not ready — waiting..."
        _rabbitmq_wait
    fi
}

_queues_purge() {
    log "Purging queues..."
    for q in "${QUEUES[@]}"; do
        docker exec "$CONTAINER" rabbitmqctl purge_queue "$q" 2>/dev/null \
            && log "  purged $q" \
            || log "  $q not found (skipped)"
    done
}

_topology_setup() {
    log "Declaring exchanges and queues..."
    cd "$PROJECT_ROOT"
    python3 -m agent_review.messaging.setup
    ok "Topology ready"
}

# ── process management ────────────────────────────────────────────────────────

_procs_stop() {
    if [[ -f "$PIDFILE" ]]; then
        log "Stopping processes..."
        while IFS= read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" && log "  stopped pid $pid"
            fi
        done < "$PIDFILE"
        rm -f "$PIDFILE"
    fi
    # catch any strays not recorded in the pidfile
    pkill -f "agent-review worker" 2>/dev/null || true
    pkill -f "agent-review orchestrator" 2>/dev/null || true
    sleep 1
    ok "All processes stopped"
}

_procs_start() {
    mkdir -p "$LOG_DIR"

    PYTHONUNBUFFERED=1 agent-review worker claude_a "$PROJECT_ROOT" >> "$LOG_DIR/claude_a.log" 2>&1 &
    echo $! >> "$PIDFILE"
    log "  claude_a worker pid=$!   log=logs/claude_a.log"

    PYTHONUNBUFFERED=1 agent-review worker claude_b "$PROJECT_ROOT" >> "$LOG_DIR/claude_b.log" 2>&1 &
    echo $! >> "$PIDFILE"
    log "  claude_b worker pid=$!   log=logs/claude_b.log"

    PYTHONUNBUFFERED=1 agent-review orchestrator  "$PROJECT_ROOT" >> "$LOG_DIR/orch.log"  2>&1 &
    echo $! >> "$PIDFILE"
    log "  orchestrator    pid=$!   log=logs/orch.log"

    ok "Workers and orchestrator running"
}

# ── commands ──────────────────────────────────────────────────────────────────

cmd_init() {
    _rabbitmq_ensure
    _topology_setup
    mkdir -p "$LOG_DIR"
    agent-review init "$PROJECT_ROOT"
    ok "Init complete. Run: ./scripts/manage.sh start"
}

cmd_start() {
    _rabbitmq_ensure
    _topology_setup
    mkdir -p "$LOG_DIR"

    log "Creating review tasks..."
    cd "$PROJECT_ROOT"
    agent-review start "$PROJECT_ROOT" "$@"
    echo ""
    agent-review status "$PROJECT_ROOT"
    echo ""

    _procs_start

    echo ""
    log "Follow logs:  ./scripts/manage.sh logs"
    log "Check status: ./scripts/manage.sh status"
}

cmd_stop() {
    _procs_stop
}

cmd_restart() {
    _procs_stop
    _rabbitmq_ensure
    _queues_purge

    log "Resetting report directory..."
    rm -rf "$REPORT_DIR"
    mkdir -p "$LOG_DIR"

    _topology_setup

    log "Creating review tasks..."
    cd "$PROJECT_ROOT"
    agent-review start "$PROJECT_ROOT" "$@"
    echo ""
    agent-review status "$PROJECT_ROOT"
    echo ""

    _procs_start

    echo ""
    log "Follow logs:  ./scripts/manage.sh logs"
    log "Check status: ./scripts/manage.sh status"
}

cmd_verify() {
    # Purge queues and reset reports, then create a single verify task and launch processes.
    _procs_stop
    _rabbitmq_ensure
    _queues_purge

    log "Resetting report directory..."
    rm -rf "$REPORT_DIR"
    mkdir -p "$LOG_DIR"

    _topology_setup

    log "Creating verify task..."
    cd "$PROJECT_ROOT"
    agent-review verify "$PROJECT_ROOT" "$@"
    echo ""
    agent-review status "$PROJECT_ROOT"
    echo ""

    _procs_start
    log "Follow logs:  ./scripts/manage.sh logs"
    log "Check status: ./scripts/manage.sh status"
}

cmd_run() {
    # Launch workers and orchestrator without touching state or queues.
    # Use this when tasks are already queued (e.g. after a fresh 'start').
    _procs_stop
    _rabbitmq_ensure
    _procs_start
    log "Follow logs:  ./scripts/manage.sh logs"
    log "Check status: ./scripts/manage.sh status"
}

cmd_resume() {
    _procs_stop
    _rabbitmq_ensure

    log "Republishing running tasks..."
    cd "$PROJECT_ROOT"
    agent-review resume "$PROJECT_ROOT"
    echo ""
    agent-review status "$PROJECT_ROOT"
    echo ""

    _procs_start

    log "Follow logs:  ./scripts/manage.sh logs"
}

cmd_status() {
    cd "$PROJECT_ROOT"
    agent-review status "$PROJECT_ROOT"

    echo ""
    if [[ -f "$PIDFILE" ]]; then
        log "Running pids:"
        while IFS= read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                ps -p "$pid" -o pid=,comm= 2>/dev/null | sed 's/^/  /' || true
            else
                echo "  pid $pid (exited)"
            fi
        done < "$PIDFILE"
    else
        log "No recorded pids (processes may not be running)"
    fi
}

cmd_logs() {
    mkdir -p "$LOG_DIR"
    LOGS=()
    for f in "$LOG_DIR/claude_a.log" "$LOG_DIR/claude_b.log" "$LOG_DIR/orch.log"; do
        touch "$f"
        LOGS+=("$f")
    done
    log "Tailing logs (Ctrl-C to stop)..."
    tail -f "${LOGS[@]}"
}

# ── dispatch ──────────────────────────────────────────────────────────────────

COMMAND="${1:-}"
shift || true

case "$COMMAND" in
    init)    cmd_init "$@" ;;
    start)   cmd_start "$@" ;;
    run)     cmd_run ;;
    verify)  cmd_verify "$@" ;;
    stop)    cmd_stop ;;
    restart) cmd_restart "$@" ;;
    resume)  cmd_resume ;;
    status)  cmd_status ;;
    logs)    cmd_logs ;;
    *)       usage ;;
esac
