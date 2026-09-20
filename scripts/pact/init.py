#!/usr/bin/env python3
"""Safely scaffold PACT into an existing repository.

Dry-run is the default. --apply writes only missing files and never overwrites.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import sys
import tempfile

from distribution import (
    github_actions_entry,
    manifest_record,
    runtime_version,
    source_manifest,
    read_install_manifest,
)
from runtime_bundle import ensure_runtime_bundle

SOURCE_ROOT = pathlib.Path(__file__).resolve().parents[2]
INSTALL_MANIFEST = pathlib.Path(".pact/install.json")

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

PACT starts physically minimal. These durable locations are created only when
the project has real knowledge worth preserving:

- Governance extensions: `docs/governance/`
- Product Truth and vocabulary: `docs/product/`
- Current architecture: `docs/architecture/`
- Durable engineering rationale: `.agents/decisions/`
- Active/completed change intent: `docs/changes/`
- Drift: `docs/drift/`
- Reusable procedures: `.agents/skills/`
- Adoption readiness: `.pact/baseline.toml`

An absent optional knowledge directory means "not materialized yet", not
"healthy knowledge is missing". Do not create empty folders/templates merely
to satisfy PACT.

## Default task workflow

Use the high-level surface first:

1. `python pact.py status` / `inspect` when project state or history is unclear.
2. `python pact.py task prepare "<task>" --success "<observable outcome>" --risk <level>`.
3. Implement ordinary technical details autonomously within the prepared Task Contract and Context.
4. Run relevant verification through `python pact.py run ...` so Evidence can bind to machine receipts.
5. Before completion, create Evidence, Convergence, and Owner Report in the task's expected completion bundle. Convergence must bind the prepared Context, explicitly disposition every selected knowledge artifact, and provide `change_coverage` rationale for every file PACT identifies as changed by the task; an empty finding list is not a substitute for coverage.
6. `python pact.py task finish <TASK-ID>` is the completion gate. Do not claim done if it fails.

Use `python pact.py task status <TASK-ID> --json` to recover the prepared contract/context paths and expected bundle location.

## Decision boundary

Do not ask the owner to choose ordinary implementation mechanisms.

Escalate only when a decision changes user-observable behavior, business/data meaning, permissions/policy, irreversible outcomes, or material risk/cost.

## Completion boundary

"Done" requires appropriate evidence and convergence, not only code changes or green tests.

## Baseline boundary

`pact init` creates structure; it does not certify project knowledge.

If `pact readiness` reports pending baseline reviews, treat those areas as potentially incomplete rather than inventing missing truth.

## Owner communication

Before owner-facing output, read the validated Owner Profile:

```bash
python pact.py owner --json
```

Honor its language, technical depth, consequence-first translation, and progressive-disclosure preferences.
"""


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
- consult `.pact/baseline.toml` and do not invent truth for pending baseline areas;
- communicate owner-facing results using the project Owner Profile in `.pact/config.toml`;
- use product/business consequences before unnecessary implementation detail.

Default PACT task loop to merge into the project guide:

- prepare work with `python pact.py task prepare ...` and follow its Task Contract/Context;
- verify observable outcomes through `python pact.py run ...` where practical;
- create Evidence + Convergence + Owner Report before completion;
- Convergence must bind the prepared Context, disposition every selected knowledge artifact, and review every task-changed file reported at finish;
- finish with `python pact.py task finish <TASK-ID>`; a failed gate means the task is not done;
- use `python pact.py task status <TASK-ID> --json` to recover task paths after a long conversation.

Suggested knowledge router (materialize a location only when real durable
project knowledge exists):

- Governance extensions: `docs/governance/`
- Product Truth: `docs/product/`
- Architecture: `docs/architecture/`
- Decisions: `.agents/decisions/`
- Changes: `docs/changes/`
- Drift: `docs/drift/`
- Skills: `.agents/skills/`
- Readiness: `.pact/baseline.toml`

Delete this bootstrap file after the existing `AGENTS.md` has been integrated.
"""


def generated_entry(path: str, management: str = "seed") -> dict:
    return {
        "source": None,
        "source_path": None,
        "target": pathlib.Path(path),
        "management": management,
    }


def path_present(path: pathlib.Path) -> bool:
    """Treat any leaf symlink, including a broken one, as an existing path."""
    return path.exists() or path.is_symlink()


def safe_init_target(target: pathlib.Path, relative: str) -> pathlib.Path:
    """Return an init destination without following a parent symlink outside target."""
    pure = pathlib.PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise RuntimeError(f"unsafe init path: {relative!r}")

    target_root = target.resolve()
    destination = target / pathlib.Path(*pure.parts)
    parent = destination.parent.resolve()
    if parent != target_root and target_root not in parent.parents:
        raise RuntimeError(f"init path escapes target through symlink: {relative!r}")
    return destination


def plan(target: pathlib.Path, github_actions: bool = False) -> list[dict]:
    operations: list[dict] = []

    for entry in source_manifest(SOURCE_ROOT):
        destination = safe_init_target(target, entry["target"].as_posix())
        present = path_present(destination)
        action = "skip" if present else "create"
        reason = "already exists" if present else "missing scaffold"

        operations.append({
            "action": action,
            "path": entry["target"].as_posix(),
            "source": entry["source_path"],
            "management": entry["management"],
            "reason": reason,
        })

    agents = safe_init_target(target, "AGENTS.md")
    if path_present(agents):
        rel = pathlib.Path(".pact/AGENT_BOOTSTRAP.md")
        destination = safe_init_target(target, rel.as_posix())
        operations.append({
            "action": "skip" if path_present(destination) else "create-generated",
            "path": rel.as_posix(),
            "source": None,
            "management": "seed",
            "reason": "preserve existing AGENTS.md",
        })
    else:
        operations.append({
            "action": "create-generated",
            "path": "AGENTS.md",
            "source": None,
            "management": "seed",
            "reason": "no existing AGENTS.md",
        })

    if github_actions:
        entry = github_actions_entry(SOURCE_ROOT)
        if entry:
            destination = safe_init_target(target, entry["target"].as_posix())
            operations.append({
                "action": "skip" if path_present(destination) else "create",
                "path": entry["target"].as_posix(),
                "source": entry["source_path"],
                "management": entry["management"],
                "reason": (
                    "existing PACT workflow preserved"
                    if path_present(destination)
                    else "opt-in PACT project CI integration"
                ),
            })

    return operations


def operation_entry(op: dict) -> dict:
    if op["source"]:
        source = (
            ensure_runtime_bundle(SOURCE_ROOT)
            if op["path"] == ".pact/pact.pyz"
            else SOURCE_ROOT / op["source"]
        )
        return {
            "source": source,
            "source_path": op["source"],
            "target": pathlib.Path(op["path"]),
            "management": op["management"],
        }
    return generated_entry(op["path"], management=op["management"])


def build_install_manifest(
    target: pathlib.Path,
    operations: list[dict],
    created_paths: set[str],
) -> dict:
    existing = read_install_manifest(target)
    files = dict(existing.get("files", {})) if existing else {}

    for op in operations:
        if op["path"] not in created_paths:
            continue
        destination = safe_init_target(target, op["path"])
        if not destination.is_file():
            raise RuntimeError(f"created init file missing before manifest commit: {op['path']}")
        entry = operation_entry(op)
        files[op["path"]] = manifest_record(entry, destination)

    return {
        "format_version": 1,
        "runtime_version": (
            existing.get("runtime_version")
            if existing
            else runtime_version(SOURCE_ROOT)
        ),
        "files": files,
    }


def cleanup_empty_parents(path: pathlib.Path, stop: pathlib.Path) -> None:
    stop = stop.resolve()
    current = path.resolve()
    while current != stop and stop in current.parents:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def render_operation_to_stage(op: dict, destination: pathlib.Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if op["source"]:
        source = (
            ensure_runtime_bundle(SOURCE_ROOT)
            if op["path"] == ".pact/pact.pyz"
            else SOURCE_ROOT / op["source"]
        )
        shutil.copy2(source, destination)
    elif op["path"] == "AGENTS.md":
        destination.write_text(TARGET_AGENTS, encoding="utf-8")
    elif op["path"] == ".pact/AGENT_BOOTSTRAP.md":
        destination.write_text(bootstrap_snippet(), encoding="utf-8")
    else:
        raise RuntimeError(f"unsupported generated init path: {op['path']}")


def apply(target: pathlib.Path, operations: list[dict]) -> set[str]:
    create_ops = [
        op for op in operations
        if op["action"].startswith("create")
    ]
    if not create_ops:
        return set()

    target_parent = target.parent
    target_parent.mkdir(parents=True, exist_ok=True)

    manifest_path = safe_init_target(target, INSTALL_MANIFEST.as_posix())
    if manifest_path.is_symlink():
        raise RuntimeError("init install manifest path must not be a symlink")
    manifest_existed = manifest_path.is_file()
    manifest_backup = (
        manifest_path.read_bytes()
        if manifest_existed
        else None
    )

    with tempfile.TemporaryDirectory(
        prefix=".pact-init-txn-",
        dir=target_parent,
    ) as tmp:
        txn = pathlib.Path(tmp)
        stage_root = txn / "stage"
        stage_root.mkdir()

        # Render every source/generated file before mutating the target.
        for op in create_ops:
            render_operation_to_stage(
                op,
                stage_root / pathlib.Path(op["path"]),
            )

        created: list[str] = []
        fail_after_raw = os.environ.get("PACT_TEST_FAIL_INIT_AFTER_CREATE")
        fail_after = int(fail_after_raw) if fail_after_raw else None

        try:
            target.mkdir(parents=True, exist_ok=True)
            for op in create_ops:
                relative = op["path"]
                destination = safe_init_target(target, relative)
                if path_present(destination):
                    # Re-check at publish time to preserve no-overwrite semantics
                    # if another process created the path after planning.
                    continue

                destination.parent.mkdir(parents=True, exist_ok=True)
                staged = stage_root / pathlib.Path(relative)
                temp_destination = destination.parent / (
                    f".{destination.name}.pact-init-tmp"
                )
                if path_present(temp_destination):
                    temp_destination.unlink()
                shutil.copy2(staged, temp_destination)
                os.replace(temp_destination, destination)
                created.append(relative)

                if fail_after is not None and len(created) >= fail_after:
                    raise RuntimeError(
                        f"simulated init failure after {len(created)} create(s)"
                    )

            created_set = set(created)
            manifest = build_install_manifest(
                target,
                operations,
                created_set,
            )
            staged_manifest = txn / "install.json"
            staged_manifest.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged_manifest, manifest_path)

            # Validate the final recorded hashes after manifest commit.
            for relative in created:
                record = manifest["files"].get(relative)
                destination = safe_init_target(target, relative)
                if not record or not destination.is_file():
                    raise RuntimeError(
                        f"init final state missing recorded file: {relative}"
                    )
                actual = manifest_record(
                    operation_entry(
                        next(op for op in operations if op["path"] == relative)
                    ),
                    destination,
                )["installed_sha256"]
                if actual != record.get("installed_sha256"):
                    raise RuntimeError(
                        f"init final hash mismatch for {relative}"
                    )

            return created_set

        except Exception:
            # Manifest was committed last, so rollback only removes files this
            # transaction created and restores the prior manifest if any.
            for relative in reversed(created):
                destination = safe_init_target(target, relative)
                try:
                    if destination.is_file() or destination.is_symlink():
                        destination.unlink()
                    cleanup_empty_parents(destination.parent, target)
                except OSError:
                    pass

            try:
                if manifest_existed and manifest_backup is not None:
                    manifest_path.parent.mkdir(parents=True, exist_ok=True)
                    restore = txn / "restore-install.json"
                    restore.write_bytes(manifest_backup)
                    os.replace(restore, manifest_path)
                elif path_present(manifest_path):
                    manifest_path.unlink()
                    cleanup_empty_parents(manifest_path.parent, target)
            except OSError:
                pass

            # Remove an empty target created only by this transaction.
            try:
                target.rmdir()
            except OSError:
                pass
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely scaffold PACT into a repository")
    parser.add_argument("--target", required=True)
    parser.add_argument("--apply", action="store_true", help="write missing files; default is dry-run")
    parser.add_argument(
        "--github-actions",
        action="store_true",
        help="also create a separate PACT project workflow if that path is missing",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    target = pathlib.Path(args.target).expanduser().resolve()
    if target.exists() and not target.is_dir():
        print("PACT init: target must be a directory", file=sys.stderr)
        return 2

    try:
        manifest_path = safe_init_target(target, INSTALL_MANIFEST.as_posix())
        if manifest_path.is_symlink():
            raise ValueError("invalid .pact/install.json: path must not be a symlink")
        existing_manifest = read_install_manifest(target)
        operations = plan(target, github_actions=args.github_actions)
    except (ValueError, RuntimeError) as exc:
        print(f"PACT init: {exc}", file=sys.stderr)
        return 2

    if args.apply and existing_manifest:
        installed_version = existing_manifest.get("runtime_version", "unknown")
        source_version = runtime_version(SOURCE_ROOT)
        if installed_version != source_version:
            print(
                "PACT init: this project is already tracked by a different PACT "
                f"runtime ({installed_version} != {source_version}). "
                "Use 'pact upgrade --target ...' instead of init.",
                file=sys.stderr,
            )
            return 2

    created_paths: set[str] = set()
    if args.apply:
        try:
            created_paths = apply(target, operations)
        except Exception as exc:
            print(
                f"PACT init: transactional apply failed and rollback was attempted: {exc}",
                file=sys.stderr,
            )
            return 2

    summary = {
        "target": str(target),
        "mode": "apply" if args.apply else "dry-run",
        "source_runtime_version": runtime_version(SOURCE_ROOT),
        "github_actions": args.github_actions,
        "create": len([o for o in operations if o["action"].startswith("create")]),
        "skip": len([o for o in operations if o["action"] == "skip"]),
        "warn": len([o for o in operations if o["action"] == "warn"]),
        "created_paths": sorted(created_paths),
        "install_manifest": (
            str(target / INSTALL_MANIFEST)
            if args.apply
            else None
        ),
        "operations": operations,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"PACT init: {summary['mode']} -> {target}")
        print(f"Source runtime: {summary['source_runtime_version']}")
        for op in operations:
            print(f"- [{op['action'].upper()}] {op['path']}: {op['reason']}")
        if args.apply:
            print(f"Install manifest: {target / INSTALL_MANIFEST}")
        else:
            print("No files were written. Re-run with --apply to create missing scaffold.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
