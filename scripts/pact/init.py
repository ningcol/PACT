#!/usr/bin/env python3
"""Safely scaffold PACT into an existing repository.

Dry-run is the default. --apply writes only missing files and never overwrites.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys

SOURCE_ROOT = pathlib.Path(__file__).resolve().parents[2]

TARGET_AGENTS = """# Project Agent Guide

This repository uses PACT (Project AI Control Plane).

## Core rules

1. Preserve confirmed Product Truth.
2. Acquire sufficient context before changing behavior; do not read everything by default.
3. AI owns implementation decisions unless they change product meaning, permissions/policy, irreversible outcomes, material risk, or cost.
4. Distinguish what should be true from what the system currently does.
5. Verify observable outcomes before claiming completion.
6. Reconcile drift by authority; never make Product Truth follow code automatically.
7. Report owner-facing results in product/business language by default.

## Knowledge router

- Governance: `docs/governance/`
- Product Truth and vocabulary: `docs/product/`
- Current architecture: `docs/architecture/`
- Durable engineering rationale: `.agents/decisions/`
- Active/completed change intent: `docs/changes/`
- Drift: `docs/drift/`
- Reusable procedures: `.agents/skills/`

## Decision boundary

Do not ask the owner to choose ordinary implementation mechanisms.

Escalate only when a decision changes user-observable behavior, business/data meaning, permissions/policy, irreversible outcomes, or material risk/cost.

## Completion boundary

"Done" requires appropriate evidence and convergence, not only code changes or green tests.
"""


def source_manifest() -> list[tuple[pathlib.Path, pathlib.Path]]:
    pairs: list[tuple[pathlib.Path, pathlib.Path]] = []

    def add(source_rel: str, target_rel: str | None = None) -> None:
        source = SOURCE_ROOT / source_rel
        target = pathlib.Path(target_rel or source_rel)
        if source.exists():
            pairs.append((source, target))

    for path in sorted((SOURCE_ROOT / "docs" / "governance").glob("*.md")):
        pairs.append((path, path.relative_to(SOURCE_ROOT)))

    for rel in [
        "docs/product/README.md",
        "docs/product/glossary/README.md",
        "docs/product/domains/README.md",
        "docs/product/domains/TEMPLATE.md",
        "docs/product/rules/README.md",
        "docs/product/rules/TEMPLATE.md",
        "docs/architecture/README.md",
        "docs/changes/README.md",
        "docs/changes/TEMPLATE.md",
        "docs/changes/active/README.md",
        "docs/changes/completed/README.md",
        "docs/changes/abandoned/README.md",
        "docs/drift/README.md",
        "docs/drift/TEMPLATE.md",
        "docs/drift/known/README.md",
        "docs/drift/resolved/README.md",
        "docs/drift/accepted/README.md",
        "docs/initialization.md",
        "docs/initialization-checklist.md",
        ".agents/decisions/README.md",
        ".agents/decisions/TEMPLATE.md",
        ".agents/decisions/proposed/README.md",
        ".agents/decisions/implemented/README.md",
        ".agents/decisions/rejected/README.md",
        ".agents/decisions/archived/README.md",
    ]:
        add(rel)

    for path in sorted((SOURCE_ROOT / ".agents" / "skills").glob("*.md")):
        pairs.append((path, path.relative_to(SOURCE_ROOT)))

    for path in sorted((SOURCE_ROOT / ".pact" / "schema").glob("*.json")):
        pairs.append((path, path.relative_to(SOURCE_ROOT)))

    for path in sorted((SOURCE_ROOT / "scripts" / "pact").iterdir()):
        if path.is_file() and path.suffix in {".py", ".md", ".txt"}:
            pairs.append((path, path.relative_to(SOURCE_ROOT)))

    add(".pact/config.example.yaml", ".pact/config.yaml")
    return pairs


def bootstrap_snippet() -> str:
    return """# PACT Agent Bootstrap

An existing `AGENTS.md` was detected, so PACT did not overwrite it.

Merge these concepts into the existing project agent guide:

- preserve confirmed Product Truth;
- distinguish normative truth from current implementation behavior;
- retrieve sufficient task context from Product, Architecture, Decisions, and Changes;
- let AI decide ordinary technical implementation;
- escalate only product/risk decisions;
- require evidence and convergence before claiming completion;
- communicate owner-facing results in product/business language.

Suggested knowledge router:

- Governance: `docs/governance/`
- Product Truth: `docs/product/`
- Architecture: `docs/architecture/`
- Decisions: `.agents/decisions/`
- Changes: `docs/changes/`
- Drift: `docs/drift/`
- Skills: `.agents/skills/`

Delete this bootstrap file after the existing `AGENTS.md` has been integrated.
"""


def plan(target: pathlib.Path) -> list[dict]:
    operations: list[dict] = []

    for source, target_rel in source_manifest():
        destination = target / target_rel
        operations.append({
            "action": "skip" if destination.exists() else "create",
            "path": target_rel.as_posix(),
            "source": source.relative_to(SOURCE_ROOT).as_posix(),
            "reason": "already exists" if destination.exists() else "missing scaffold",
        })

    agents = target / "AGENTS.md"
    if agents.exists():
        rel = pathlib.Path("docs/governance/PACT_AGENT_BOOTSTRAP.md")
        destination = target / rel
        operations.append({
            "action": "skip" if destination.exists() else "create-generated",
            "path": rel.as_posix(),
            "source": "<generated>",
            "reason": "preserve existing AGENTS.md",
        })
    else:
        operations.append({
            "action": "create-generated",
            "path": "AGENTS.md",
            "source": "<generated>",
            "reason": "no existing AGENTS.md",
        })

    gitignore = target / ".gitignore"
    if gitignore.exists():
        text = gitignore.read_text(encoding="utf-8", errors="ignore")
        if ".pact/cache/" not in text:
            operations.append({
                "action": "warn",
                "path": ".gitignore",
                "source": "<none>",
                "reason": "add .pact/cache/ manually; existing .gitignore is never modified",
            })
    else:
        operations.append({
            "action": "create-generated",
            "path": ".gitignore",
            "source": "<generated>",
            "reason": "ignore derived PACT cache",
        })

    return operations


def apply(target: pathlib.Path, operations: list[dict]) -> None:
    manifest = {target_rel.as_posix(): source for source, target_rel in source_manifest()}
    target.mkdir(parents=True, exist_ok=True)

    for op in operations:
        if not op["action"].startswith("create"):
            continue

        destination = target / op["path"]
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)

        if op["source"] != "<generated>":
            shutil.copy2(manifest[op["path"]], destination)
        elif op["path"] == "AGENTS.md":
            destination.write_text(TARGET_AGENTS, encoding="utf-8")
        elif op["path"] == "docs/governance/PACT_AGENT_BOOTSTRAP.md":
            destination.write_text(bootstrap_snippet(), encoding="utf-8")
        elif op["path"] == ".gitignore":
            destination.write_text(".pact/cache/\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely scaffold PACT into a repository")
    parser.add_argument("--target", required=True)
    parser.add_argument("--apply", action="store_true", help="write missing files; default is dry-run")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    target = pathlib.Path(args.target).expanduser().resolve()
    if target.exists() and not target.is_dir():
        print("PACT init: target must be a directory", file=sys.stderr)
        return 2

    operations = plan(target)
    if args.apply:
        apply(target, operations)

    summary = {
        "target": str(target),
        "mode": "apply" if args.apply else "dry-run",
        "create": len([o for o in operations if o["action"].startswith("create")]),
        "skip": len([o for o in operations if o["action"] == "skip"]),
        "warn": len([o for o in operations if o["action"] == "warn"]),
        "operations": operations,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"PACT init: {summary['mode']} -> {target}")
        for op in operations:
            print(f"- [{op['action'].upper()}] {op['path']}: {op['reason']}")
        if not args.apply:
            print("No files were written. Re-run with --apply to create missing scaffold.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
