"""Shared protocol identifier validation."""

from __future__ import annotations

import pathlib
import re


TASK_ID_PATTERN = r"^TASK-[A-Z0-9]+(?:[._-][A-Z0-9]+)*$"
TASK_ID = re.compile(TASK_ID_PATTERN)


def validate_task_id(value: str) -> str:
    if not isinstance(value, str) or not TASK_ID.fullmatch(value):
        raise ValueError(
            "task_id must match "
            + TASK_ID_PATTERN
            + " (uppercase alphanumerics with internal . _ - separators)"
        )
    return value


def confined_child(root: pathlib.Path, task_id: str) -> pathlib.Path:
    """Return a validated child path rooted under root."""
    validate_task_id(task_id)
    root = root.resolve()
    candidate = (root / task_id).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"task_id escapes state root: {task_id!r}") from exc
    return candidate
