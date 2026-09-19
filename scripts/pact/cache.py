"""Freshness helpers for disposable PACT indexes."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
from typing import Iterable


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
        try:
            relative = path.relative_to(root).as_posix()
            content_sha = file_sha256(path)
        except (OSError, ValueError):
            continue
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


def read_json(path: pathlib.Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def cache_is_fresh(
    path: pathlib.Path,
    *,
    format_version: int,
    source_fingerprint: str,
) -> bool:
    data = read_json(path)
    if not data:
        return False
    return (
        data.get("format_version") == format_version
        and data.get("source_fingerprint") == source_fingerprint
    )
