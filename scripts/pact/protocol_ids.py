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


def confined_repository_path(
    root: pathlib.Path,
    value: str,
    *,
    field: str,
) -> pathlib.Path:
    """Resolve one repository-owned relative path without allowing escapes."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty repository-relative path")

    relative = pathlib.Path(value).expanduser()
    if relative.is_absolute():
        raise ValueError(f"{field} must be repository-relative")

    root_resolved = root.resolve()
    try:
        resolved = (root_resolved / relative).resolve()
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"{field} cannot be resolved safely: {value!r}") from exc

    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"{field} escapes repository root: {value!r}") from exc

    return resolved
