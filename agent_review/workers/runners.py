"""Agent command runner abstractions.

Purpose:
    Execute a configurable CLI command with a review prompt passed via stdin.
Parameters:
    Runners receive command tuples and timeout settings.
Return Value:
    run returns stdout from the agent command.
Raised Exceptions:
    AgentCommandError: If the command fails or times out.
    OSError: If prompt files cannot be read or commands cannot be started.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS = 900


class AgentCommandError(RuntimeError):
    """Agent command execution failure.

    Args:
        message: Human-readable failure detail.

    Returns:
        RuntimeError subclass for worker failure handling.

    Raises:
        None during initialization.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """


@dataclass(frozen=True)
class CommandRunner:
    """Run any agent CLI in prompt mode.

    Args:
        command: Command to invoke; prompt is passed via stdin.
        timeout_seconds: Maximum execution time.

    Returns:
        Runner whose run method returns stdout.

    Raises:
        AgentCommandError: If the command exits non-zero or times out.
    """

    command: tuple[str, ...] = ("claude", "--print")
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    def run(self, prompt_path: Path, project_root: Path) -> str:
        prompt = prompt_path.read_text(encoding="utf-8")
        return _run_command(self.command, prompt, project_root, self.timeout_seconds)


def _run_command(command: tuple[str, ...], prompt: str, project_root: Path, timeout_seconds: int) -> str:
    try:
        result = subprocess.run(
            list(command),
            input=prompt,
            text=True,
            cwd=project_root,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AgentCommandError(f"Agent command timed out after {timeout_seconds} seconds.") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        raise AgentCommandError(f"Agent command failed: {detail}")
    return result.stdout
