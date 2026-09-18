#!/usr/bin/env python3
"""Build a disposable PACT project discovery index."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
from datetime import datetime, timezone

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / ".pact" / "cache" / "project-map.json"
FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
TITLE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
MD_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def parse_document(path: pathlib.Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    pact: dict = {}
    body = raw

    match = FRONT_MATTER.match(raw)
    if match:
        data = yaml.safe_load(match.group(1))
        if isinstance(data, dict) and isinstance(data.get("pact"), dict):
            pact = data["pact"]
        body = raw[match.end():]

    heading = TITLE.search(body)
    title = heading.group(1).strip() if heading else path.stem

    aliases = pact.get("aliases", [])
    if not isinstance(aliases, list):
        aliases = []

    related = pact.get("related", [])
    if not isinstance(related, list):
        related = []

    domains = pact.get("domains", [])
    if not isinstance(domains, list):
        domains = []

    links = [
        link for link in MD_LINK.findall(body)
        if not link.startswith(("http://", "https://", "#", "mailto:"))
    ]

    return {
        "path": rel(path),
        "title": title,
        "artifact_type": pact.get("type", "document"),
        "id": pact.get("id"),
        "status": pact.get("status"),
        "domains": domains,
        "aliases": aliases,
        "related": related,
        "links": sorted(set(links)),
        "text": body.strip(),
    }


def should_index(path: pathlib.Path) -> bool:
    r = rel(path)
    if r.startswith(".pact/cache/"):
        return False
    if "/TEMPLATE.md" in r or r.endswith("/TEMPLATE.md"):
        return False
    return (
        r in {"README.md", "AGENTS.md"}
        or r.startswith("docs/")
        or r.startswith(".agents/")
    )


def build_index() -> dict:
    documents = [
        parse_document(path)
        for path in sorted(ROOT.rglob("*.md"))
        if should_index(path)
    ]

    ids = {
        doc["id"]: doc["path"]
        for doc in documents
        if doc.get("id")
    }

    return {
        "format_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository_root": ".",
        "documents": documents,
        "id_to_path": ids,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PACT project discovery map")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    output = pathlib.Path(args.output)
    if not output.is_absolute():
        output = ROOT / output

    index = build_index()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"PACT map: indexed {len(index['documents'])} document(s) -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
