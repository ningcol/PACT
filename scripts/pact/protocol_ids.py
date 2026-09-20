"""Shared protocol identifier validation."""

from __future__ import annotations

import pathlib
import re


TASK_ID_PATTERN = r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$"
TASK_ID = re.compile(TASK_ID_PATTERN)


def validate_task_id(value: str) -> str:
    if not isinstance(value, str) or not TASK_ID.fullmatch(value):
        raise ValueError(
            "task_id must match "
            + TASK_ID_PATTERN
            + " (alphanumerics with internal . _ - separators)"
        )
    return value


def confined_child(root: pathlib.Path, task_id: str) -> pathlib.Path:
    """Return one real direct child rooted under state root, never a path alias."""
    validate_task_id(task_id)
    root = root.resolve()
    candidate = root / task_id

    try:
        resolved = candidate.resolve()
    except (OSError, RuntimeError) as exc:
        raise ValueError(
            f"task_id state path cannot be resolved safely: {task_id!r}"
        ) from exc

    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"task_id escapes state root: {task_id!r}") from exc

    if candidate.is_symlink() or (candidate.exists() and resolved != candidate):
        raise ValueError(
            f"task_id state path must be a real direct child, not a symlink/alias: "
            f"{task_id!r}"
        )

    return candidate
