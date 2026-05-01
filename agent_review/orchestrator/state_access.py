"""State dict accessor helpers shared across orchestrator modules."""

from __future__ import annotations


def require_string(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing state string: {key}")
    return value


def require_int(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"Missing state integer: {key}")
    return value


def optional_int(data: dict[str, object], key: str) -> int:
    value = data.get(key, 0)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"Invalid optional state integer: {key}")
    return value


def require_string_list(data: dict[str, object], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"Missing state string list: {key}")
    return list(value)


def allow_empty_string_list(data: dict[str, object], key: str) -> list[str]:
    """Return a list that may contain empty strings (e.g. previous_reports: [])."""
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Missing state string list: {key}")
    return list(value)
