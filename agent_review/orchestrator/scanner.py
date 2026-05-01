"""Project file scanner for review task creation.

Purpose:
    Discover reviewable project files while excluding generated, dependency, and report directories.
Parameters:
    FileScanner receives a project root and optional include/exclude settings.
Return Value:
    scan returns deterministic, sorted, POSIX-style relative paths.
Raised Exceptions:
    FileNotFoundError: If the project root does not exist.
    NotADirectoryError: If the project root is not a directory.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

DEFAULT_INCLUDE_EXTENSIONS = (
    ".py",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".sh",
    ".cpp",
    ".hpp",
    ".c",
    ".h",
    ".ts",
    ".js",
)
DEFAULT_EXCLUDE_DIRS = (
    ".git",
    ".venv",
    "venv",
    "env",
    "test_env",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
    ".cache",
    ".agent_reports",
)
DEFAULT_EXCLUDE_PATTERNS = ("*.pyc", "*.so", "*.dll", "*.png", "*.jpg")


@dataclass(frozen=True)
class FileScanner:
    """Deterministic scanner for project files.

    Args:
        project_root: Directory to scan.
        include_extensions: File suffixes allowed in review tasks.
        exclude_dirs: Directory names to skip at any depth.
        exclude_patterns: Filename patterns to skip.

    Returns:
        A scanner object whose scan method returns reviewable files.

    Raises:
        FileNotFoundError: If project_root does not exist during scan.
        NotADirectoryError: If project_root is not a directory during scan.

    Author:
        Codex (OpenAI), generated 2026-05-01.
    """

    project_root: Path
    include_extensions: tuple[str, ...] = DEFAULT_INCLUDE_EXTENSIONS
    exclude_dirs: tuple[str, ...] = DEFAULT_EXCLUDE_DIRS
    exclude_patterns: tuple[str, ...] = DEFAULT_EXCLUDE_PATTERNS
    include_globs: tuple[str, ...] = field(default_factory=tuple)

    def scan(self) -> list[str]:
        """Return reviewable files under the project root.

        Args:
            None.

        Returns:
            Sorted POSIX-style relative file paths.

        Raises:
            FileNotFoundError: If project_root does not exist.
            NotADirectoryError: If project_root is not a directory.
        """

        root = self.project_root.resolve()
        if not root.exists():
            raise FileNotFoundError(f"Project root does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Project root is not a directory: {root}")

        files: list[str] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if self._is_excluded(relative):
                continue
            if path.suffix not in self.include_extensions:
                continue
            relative_posix = relative.as_posix()
            if self.include_globs and not self._matches_include_globs(relative_posix):
                continue
            files.append(relative_posix)
        return sorted(files)

    def _is_excluded(self, relative: Path) -> bool:
        if any(part in self.exclude_dirs for part in relative.parts):
            return True
        name = relative.name
        return any(fnmatch(name, pattern) for pattern in self.exclude_patterns)

    def _matches_include_globs(self, relative_posix: str) -> bool:
        return any(
            fnmatch(relative_posix, pattern) or Path(relative_posix).match(pattern)
            for pattern in self.include_globs
        )
