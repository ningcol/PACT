#!/usr/bin/env python3
"""Produce a deterministic PACT repository health inventory."""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import subprocess
import sys

from runtime_exec import runtime_command

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_MAP = pathlib.Path(".pact/cache/project-map.json")


def build_map(root: pathlib.Path = ROOT) -> dict:
    output = root / DEFAULT_MAP
    result = subprocess.run(
        runtime_command(
            "map",
            "--output",
            str(output),
            "--ensure",
            root=root,
        ),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not output.is_file():
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "map failed"
        )
    return json.loads(output.read_text(encoding="utf-8"))


def evaluate(index: dict, *, deterministic_check: str) -> dict:
    docs = index.get("documents", [])
    type_counts = collections.Counter(
        d.get("artifact_type", "document") for d in docs
    )
    status_counts = collections.Counter(
        f"{d.get('artifact_type')}:{d.get('status')}"
        for d in docs
        if d.get("status")
    )

    active_changes = [
        {"id": d.get("id"), "title": d["title"], "path": d["path"]}
        for d in docs
        if d.get("artifact_type") == "change"
        and d.get("status") == "active"
    ]
    known_drift = [
        {"id": d.get("id"), "title": d["title"], "path": d["path"]}
        for d in docs
        if d.get("artifact_type") == "drift"
        and d.get("status") == "known"
    ]

    semantic_review_targets = [
        {
            "reason": "active change should eventually converge and close",
            **item,
        }
        for item in active_changes
    ] + [
        {
            "reason": "known drift remains unresolved",
            **item,
        }
        for item in known_drift
    ]

    return {
        "deterministic_check": deterministic_check,
        "artifact_counts": dict(sorted(type_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "active_changes": active_changes,
        "known_drift": known_drift,
        "semantic_review_targets": semantic_review_targets,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit PACT repository health")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    check = subprocess.run(
        runtime_command("check"),
        capture_output=True,
        text=True,
    )
    deterministic_check = "pass" if check.returncode == 0 else "fail"

    try:
        index = build_map(ROOT)
    except Exception as exc:
        print(f"PACT audit: cannot build project map: {exc}", file=sys.stderr)
        return 2

    result = evaluate(
        index,
        deterministic_check=deterministic_check,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"PACT audit: deterministic check = "
            f"{result['deterministic_check']}"
        )
        print("Artifact inventory:")
        for kind, count in sorted(result["artifact_counts"].items()):
            print(f"- {kind}: {count}")
        print(f"Active changes: {len(result['active_changes'])}")
        print(f"Known drift: {len(result['known_drift'])}")
        if result["semantic_review_targets"]:
            print("Semantic review targets:")
            for item in result["semantic_review_targets"]:
                label = item.get("id") or item["path"]
                print(f"- {label}: {item['reason']}")

    return 0 if check.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
