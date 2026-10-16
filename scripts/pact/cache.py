"""Freshness helpers for disposable PACT indexes."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import tempfile
import time
from typing import Callable, Iterable


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint_files(root: pathlib.Path, paths: Iterable[pathlib.Path]) -> str:
    """Content-integrity fingerprint for disposable indexes.

    Size/mtime are intentionally insufficient: restore/sync/generator tools can
    preserve timestamps while replacing equal-size content.
    """
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda p: p.as_posix()):
        # Never treat an unreadable/disappearing input as an absent source.
        # A fresh index must represent the full enumerated source set.
        relative = path.relative_to(root).as_posix()
        content_sha = file_sha256(path)
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        digest.update(content_sha.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def git_head(root: pathlib.Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


WINDOWS_CACHE_REPLACE_MAX_ATTEMPTS = 12
WINDOWS_CACHE_REPLACE_RETRY_SECONDS = 0.01


def _retryable_windows_cache_replace_error(error: OSError) -> bool:
    """Do not retry arbitrary permission errors or suppress real denials."""
    return (
        os.name == "nt"
        and isinstance(error, PermissionError)
        and getattr(error, "winerror", None) in {5, 32}
    )


def _replace_cache_with_bounded_windows_retry(
    temporary: pathlib.Path, target: pathlib.Path
) -> None:
    """Windows readers may briefly hold destination sharing locks.

    Retry only recognized WinError 5/32, with a strictly finite deadline.
    The staged file stays complete and unopened by readers until replacement.
    """
    for attempt in range(WINDOWS_CACHE_REPLACE_MAX_ATTEMPTS):
        try:
            os.replace(temporary, target)
            return
        except OSError as exc:
            if (
                attempt + 1 >= WINDOWS_CACHE_REPLACE_MAX_ATTEMPTS
                or not _retryable_windows_cache_replace_error(exc)
            ):
                raise
            time.sleep(WINDOWS_CACHE_REPLACE_RETRY_SECONDS * (attempt + 1))


def atomic_write_json(path: pathlib.Path, data: dict) -> None:
    """Publish one complete JSON cache atomically using a unique sibling file.

    The previous target remains intact on write/replace failure. This only
    guarantees single-file atomicity, not a transaction across cache files.
    """
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.pact-cache-",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = pathlib.Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _replace_cache_with_bounded_windows_retry(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def read_json(path: pathlib.Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def cache_is_fresh(
    path: pathlib.Path,
    *,
    format_version: int,
    source_fingerprint: str,
    validator: Callable[[dict], bool] | None = None,
) -> bool:
    data = read_json(path)
    if not data:
        return False
    if (
        data.get("format_version") != format_version
        or data.get("source_fingerprint") != source_fingerprint
    ):
        return False
    try:
        return validator(data) if validator is not None else True
    except (ValueError, TypeError, KeyError, AttributeError):
        # Broken cached structures are rebuildable, never trusted as a hit.
        return False
