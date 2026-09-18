#!/usr/bin/env python3
"""Build a candidate PACT Task Context Envelope from Project Discovery."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile

from schema_validate import load_schema, validate_instance

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = ROOT / ".pact" / "schema" / "context-envelope.schema.json"


def run_discovery(query: str, limit: int, code: bool = False) -> dict:
    with tempfile.TemporaryDirectory(prefix="pact-context-") as tmp:
        index = pathlib.Path(tmp) / "project-map.json"
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "pact" / "map.py"), "--output", str(index)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        command = [
            sys.executable,
            str(ROOT / "scripts" / "pact" / "discover.py"),
            query,
            "--index",
            str(index),
            "--limit",
            str(limit),
            "--json",
        ]
        if code:
            code_index = pathlib.Path(tmp) / "code-map.json"
            command.extend([
                "--code",
                "--code-index",
                str(code_index),
                "--code-limit",
                str(limit),
            ])

        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode not in {0, 1}:
            raise RuntimeError(result.stderr.strip() or "discovery failed")
        if not result.stdout.strip():
            return {"query": query, "result_count": 0, "results": []}
        return json.loads(result.stdout)


def validate(envelope: dict) -> list[str]:
    return validate_instance(envelope, load_schema(SCHEMA))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a candidate PACT task context")
    parser.add_argument("task")
    parser.add_argument("--goal")
    parser.add_argument("--success", required=True, help="observable success condition")
    parser.add_argument("--risk", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--query", help="discovery query; defaults to task")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument(
        "--code",
        action="store_true",
        help="include generated code search/import neighbors in candidate context",
    )
    parser.add_argument("--output")
    args = parser.parse_args()

    goal = args.goal or args.task
    query = args.query or args.task

    try:
        discovery = run_discovery(query, max(args.limit, 1), code=args.code)
    except Exception as exc:
        print(f"PACT context: discovery failed: {exc}", file=sys.stderr)
        return 2

    results = discovery.get("results", [])
    domains = sorted({
        domain
        for result in results
        for domain in result.get("domains", [])
    })

    rules = sorted({
        result["id"] or result["path"]
        for result in results
        if result.get("artifact_type") == "rule"
        and result.get("status") == "confirmed"
    })
    decisions = sorted({
        result["id"] or result["path"]
        for result in results
        if result.get("artifact_type") == "decision"
        and result.get("status") == "implemented"
    })
    verification = sorted({
        target
        for result in results
        for target in result.get("verification", [])
    })

    code_results = discovery.get("code_results", [])

    unknowns = []
    if not results:
        unknowns.append(
            "Deterministic Project Discovery found no matching artifact; expand search semantically."
        )
    if not rules:
        unknowns.append(
            "No confirmed Product Rule was discovered deterministically; candidate rules must not be treated as normative truth."
        )
    if args.code and not code_results:
        unknowns.append(
            "Code-aware discovery found no matching code artifact; expand with project-specific code analysis if needed."
        )

    envelope = {
        "version": 1,
        "status": "candidate",
        "task": args.task,
        "goal": goal,
        "observable_success": args.success,
        "risk_level": args.risk,
        "discovery_query": query,
        "domains": domains,
        "artifacts": [
            {
                "path": r["path"],
                "id": r.get("id"),
                "artifact_type": r["artifact_type"],
                "title": r["title"],
                "score": r["score"],
                "reasons": r.get("reasons", []),
            }
            for r in results
        ],
        "code_artifacts": [
            {
                "path": r["path"],
                "language": r["language"],
                "is_test": r["is_test"],
                "symbols": r.get("symbols", []),
                "score": r["score"],
                "reasons": r.get("reasons", []),
                "relation": r.get("relation", "direct-match"),
            }
            for r in code_results
        ],
        "applicable_rules": rules,
        "decisions": decisions,
        "verification_targets": verification,
        "known_unknowns": unknowns,
    }

    errors = validate(envelope)
    if errors:
        print("PACT context: generated invalid envelope", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    rendered = json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        path = pathlib.Path(args.output)
        if not path.is_absolute():
            path = ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        print(f"PACT context: candidate envelope -> {path}")
    else:
        print(rendered, end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
