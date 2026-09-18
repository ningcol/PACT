#!/usr/bin/env python3
"""Build or refresh the disposable PACT project discovery index."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
from datetime import datetime, timezone

from cache import cache_is_fresh, fingerprint_files, git_head
from formats import parse_markdown_metadata


DEFAULT_ROOT = pathlib.Path(__file__).resolve().parents[2]
FORMAT_VERSION = 3
TITLE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
MD_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def rel(path: pathlib.Path, root: pathlib.Path) -> str:
    return path.relative_to(root).as_posix()


def as_list(value) -> list:
    return value if isinstance(value, list) else []


def should_index(path: pathlib.Path, root: pathlib.Path) -> bool:
    r = rel(path, root)
    if r.startswith(".pact/cache/"):
        return False
    if "/TEMPLATE.md" in r or r.endswith("/TEMPLATE.md"):
        return False
    return (
        r in {"README.md", "AGENTS.md"}
        or r.startswith("docs/")
        or r.startswith(".agents/")
    )


def source_paths(root: pathlib.Path) -> list[pathlib.Path]:
    return [
        path
        for path in root.rglob("*.md")
        if path.is_file() and should_index(path, root)
    ]


def parse_document(path: pathlib.Path, root: pathlib.Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    data, body, metadata_format = parse_markdown_metadata(raw)
    pact = data.get("pact", {}) if isinstance(data, dict) else {}
    if not isinstance(pact, dict):
        pact = {}

    heading = TITLE.search(body)
    title = heading.group(1).strip() if heading else path.stem

    links = [
        link for link in MD_LINK.findall(body)
        if not link.startswith(("http://", "https://", "#", "mailto:"))
    ]

    return {
        "path": rel(path, root),
        "title": title,
        "artifact_type": pact.get("type", "document"),
        "id": pact.get("id"),
        "status": pact.get("status"),
        "domains": as_list(pact.get("domains")),
        "aliases": as_list(pact.get("aliases")),
        "paths": as_list(pact.get("paths")),
        "related": as_list(pact.get("related")),
        "verification": as_list(pact.get("verification")),
        "links": sorted(set(links)),
        "metadata_format": metadata_format,
        "text": body.strip(),
    }


def build_index(
    root: pathlib.Path,
    paths: list[pathlib.Path],
    source_fingerprint: str,
) -> dict:
    documents = [
        parse_document(path, root)
        for path in sorted(paths)
    ]

    ids = {
        doc["id"]: doc["path"]
        for doc in documents
        if doc.get("id")
    }

    return {
        "format_version": FORMAT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository_root": ".",
        "source_fingerprint": source_fingerprint,
        "git_head": git_head(root),
        "documents": documents,
        "id_to_path": ids,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PACT project discovery map")
    parser.add_argument(
        "--root",
        help="repository root; defaults to this script's repository",
    )
    parser.add_argument("--output")
    parser.add_argument(
        "--ensure",
        action="store_true",
        help="reuse the existing index when its source fingerprint is current",
    )
    args = parser.parse_args()

    root = pathlib.Path(args.root).expanduser().resolve() if args.root else DEFAULT_ROOT
    output = pathlib.Path(args.output) if args.output else pathlib.Path(".pact/cache/project-map.json")
    if not output.is_absolute():
        output = root / output

    paths = source_paths(root)
    source_fingerprint = fingerprint_files(root, paths)

    if args.ensure and cache_is_fresh(
        output,
        format_version=FORMAT_VERSION,
        source_fingerprint=source_fingerprint,
    ):
        print(f"PACT map: fresh -> {output}")
        return 0

    index = build_index(root, paths, source_fingerprint)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"PACT map: indexed {len(index['documents'])} document(s) -> {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
