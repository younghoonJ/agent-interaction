"""Load and merge Agent Review configuration files.

Purpose:
    Provide deterministic configuration loading from the packaged default YAML and optional user overrides.
Parameters:
    Config paths are passed to public functions as pathlib.Path values.
Return Value:
    Public functions return plain dictionaries suitable for the other package components.
Raised Exceptions:
    FileNotFoundError: If an explicit override path is missing.
    ValueError: If a configuration document is not a mapping.
Author:
    Codex (OpenAI), generated 2026-05-01.
"""

from __future__ import annotations

from copy import deepcopy
from importlib.resources import files
from pathlib import Path
from typing import Mapping

import yaml

ConfigMap = dict[str, object]


def load_config(path: Path | None = None) -> ConfigMap:
    """Load the default configuration and merge an optional override.

    Args:
        path: Optional path to a YAML file whose values override packaged defaults.

    Returns:
        A merged configuration dictionary.

    Raises:
        FileNotFoundError: If the override path does not exist.
        ValueError: If either YAML document is not a mapping.
    """

    default_path = files("agent_review.config").joinpath("default.yaml")
    with default_path.open("r", encoding="utf-8") as file:
        raw_default = yaml.safe_load(file) or {}
    if not isinstance(raw_default, dict):
        raise ValueError("Default configuration must be a mapping.")

    config = deepcopy(raw_default)
    if path is None:
        return config

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        raw_override = yaml.safe_load(file) or {}
    if not isinstance(raw_override, dict):
        raise ValueError("Configuration override must be a mapping.")

    return _deep_merge(config, raw_override)


def _deep_merge(base: ConfigMap, override: Mapping[str, object]) -> ConfigMap:
    merged = deepcopy(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, Mapping):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = deepcopy(value)
    return merged
