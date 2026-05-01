"""Agent command runner abstractions.

Purpose:
    Execute Codex or Claude CLI commands with read-only review prompts.
Parameters:
    Runners receive command lists and timeout settings.
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
class CodexRunner:
    """Run Codex in read-only review mode.

    Args:
        command: Command prefix used to invoke Codex.
        timeout_seconds: Maximum execution time.

    Returns:
        Runner whose run method returns stdout.

    Raises:
        AgentCommandError: If Codex exits non-zero or times out.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    command: tuple[str, ...] = ("codex", "exec", "--sandbox", "read-only")
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    def run(self, prompt_path: Path, project_root: Path) -> str:
        """Run Codex with prompt text on stdin.

        Args:
            prompt_path: Path to the generated prompt.
            project_root: Working directory for the agent.

        Returns:
            Agent stdout.

        Raises:
            AgentCommandError: If Codex fails or times out.
            OSError: If the prompt cannot be read or the command cannot start.
        """

        prompt = prompt_path.read_text(encoding="utf-8")
        return _run_command(self.command, prompt, project_root, self.timeout_seconds)


@dataclass(frozen=True)
class ClaudeRunner:
    """Run Claude Code in prompt mode.

    Args:
        command: Command prefix used to invoke Claude.
        timeout_seconds: Maximum execution time.

    Returns:
        Runner whose run method returns stdout.

    Raises:
        AgentCommandError: If Claude exits non-zero or times out.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    # --print enables non-interactive mode; prompt is passed via stdin to avoid ARG_MAX limits.
    command: tuple[str, ...] = ("claude", "--print")
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    def run(self, prompt_path: Path, project_root: Path) -> str:
        """Run Claude with the prompt on stdin.

        Args:
            prompt_path: Path to the generated prompt.
            project_root: Working directory for the agent.

        Returns:
            Agent stdout.

        Raises:
            AgentCommandError: If Claude fails or times out.
            OSError: If the prompt cannot be read or the command cannot start.
        """

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
