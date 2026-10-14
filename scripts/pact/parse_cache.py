"""Per-file parse cache for disposable PACT indexes."""

from __future__ import annotations

import hashlib
import json
import pathlib

from cache import atomic_write_json, file_sha256
from collections.abc import Callable
from typing import Any


def parsed_digest(value: Any) -> str:
    """Detect accidental cached parse-payload edits independently of source SHA.

    This is a self-check for disposable data, not an authentication primitive:
    someone able to edit the cache can also recompute this digest.
    """
    serialized = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def signature(path: pathlib.Path) -> dict[str, int | str]:
    stat = path.stat()
    return {
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
        "sha256": file_sha256(path),
    }


def load_cache(path: pathlib.Path, *, version: int) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"version": version, "entries": {}}

    if not isinstance(data, dict) or data.get("version") != version:
        return {"version": version, "entries": {}}

    entries = data.get("entries")
    if not isinstance(entries, dict):
        entries = {}
    return {"version": version, "entries": entries}


def save_cache(path: pathlib.Path, data: dict) -> None:
    atomic_write_json(path, data)


def parse_with_cache(
    *,
    root: pathlib.Path,
    paths: list[pathlib.Path],
    cache_path: pathlib.Path,
    cache_version: int,
    parser: Callable[[pathlib.Path], Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    old = load_cache(cache_path, version=cache_version)
    old_entries = old["entries"]
    new_entries: dict[str, dict] = {}
    parsed: dict[str, Any] = {}
    parsed_count = 0
    reused_count = 0

    for path in paths:
        relative = path.relative_to(root).as_posix()
        # A visible source that disappears must trigger a scan retry, not
        # silently vanish from a successfully published index.
        current_signature = signature(path)

        previous = old_entries.get(relative)
        if (
            isinstance(previous, dict)
            and previous.get("signature") == current_signature
            and "parsed" in previous
            and isinstance(previous.get("parsed_sha256"), str)
            and previous["parsed_sha256"] == parsed_digest(previous["parsed"])
        ):
            value = previous["parsed"]
            reused_count += 1
        else:
            value = parser(path)
            parsed_count += 1

        # The content used to build the parsed record must still be the
        # content identified by its signature. Otherwise the index and its
        # fingerprint can describe different versions of the same file.
        if signature(path) != current_signature:
            raise OSError(f"source changed while parsing: {relative}")

        parsed[relative] = value
        new_entries[relative] = {
            "signature": current_signature,
            "parsed": value,
            "parsed_sha256": parsed_digest(value),
        }

    save_cache(
        cache_path,
        {
            "version": cache_version,
            "entries": new_entries,
        },
    )
    return parsed, {
        "parsed": parsed_count,
        "reused": reused_count,
        "removed": max(len(old_entries) - len(new_entries), 0),
    }
