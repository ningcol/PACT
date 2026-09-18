#!/usr/bin/env python3
"""Safely upgrade framework-managed PACT files in an adopted project.

The upgrade is transactional at the framework-file level:
if any framework-managed file has both local modifications and a newer source
version, --apply refuses the entire automatic update.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys

from distribution import (
    github_actions_entry,
    manifest_record,
    runtime_version,
    sha256_file,
    source_manifest,
)

SCRIPT_ROOT = pathlib.Path(__file__).resolve().parents[2]
INSTALL_MANIFEST = pathlib.Path(".pact/install.json")


def load_manifest(target: pathlib.Path) -> dict:
    path = target / INSTALL_MANIFEST
    if not path.exists():
        raise FileNotFoundError(
            "missing .pact/install.json; this project predates tracked PACT installs "
            "or was not initialized with a manifest"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        raise ValueError("invalid install manifest")
    return data


def desired_entries(source_root: pathlib.Path, target: pathlib.Path, manifest: dict) -> list[dict]:
    entries = source_manifest(source_root)

    workflow_path = ".github/workflows/pact-project-check.yml"
    tracked = manifest.get("files", {}).get(workflow_path)
    if tracked or (target / workflow_path).exists():
        workflow = github_actions_entry(source_root)
        if workflow:
            entries.append(workflow)

    return entries


def plan_upgrade(source_root: pathlib.Path, target: pathlib.Path, manifest: dict) -> dict:
    tracked = manifest.get("files", {})
    entries = desired_entries(source_root, target, manifest)
    desired_by_path = {entry["target"].as_posix(): entry for entry in entries}

    operations: list[dict] = []
    conflicts: list[dict] = []
    notices: list[dict] = []

    for path, entry in sorted(desired_by_path.items()):
        destination = target / path
        source = pathlib.Path(entry["source"])
        source_sha = sha256_file(source)
        record = tracked.get(path)

        if entry["management"] == "seed":
            if not destination.exists():
                operations.append({
                    "action": "create-seed",
                    "path": path,
                    "reason": "new project seed introduced by newer PACT",
                    "source_sha256": source_sha,
                })
                continue

            if record and record.get("management") == "seed":
                old_source_sha = record.get("source_sha256")
                if old_source_sha and old_source_sha != source_sha:
                    notices.append({
                        "kind": "seed-update-available",
                        "path": path,
                        "reason": "framework seed/template changed; project-owned file will not be overwritten",
                    })
            elif not record:
                notices.append({
                    "kind": "untracked-seed",
                    "path": path,
                    "reason": "existing project-owned file is intentionally not adopted or overwritten",
                })
            continue

        # Framework-managed path.
        if not destination.exists():
            operations.append({
                "action": "create-framework",
                "path": path,
                "reason": "new or missing framework-managed file",
                "source_sha256": source_sha,
            })
            continue

        current_sha = sha256_file(destination)

        if not record:
            if current_sha == source_sha:
                notices.append({
                    "kind": "untracked-framework-identical",
                    "path": path,
                    "reason": "file matches source but has no install provenance; not auto-adopted",
                })
            else:
                conflicts.append({
                    "path": path,
                    "reason": "framework path exists but is not tracked by install manifest",
                    "current_sha256": current_sha,
                    "source_sha256": source_sha,
                })
            continue

        if record.get("management") != "framework":
            notices.append({
                "kind": "ownership-changed",
                "path": path,
                "reason": "previous install marked this path project-owned; upgrade will not overwrite it",
            })
            continue

        installed_sha = record.get("installed_sha256")
        old_source_sha = record.get("source_sha256")

        if current_sha == source_sha:
            operations.append({
                "action": "refresh-manifest",
                "path": path,
                "reason": "target already matches new framework source",
                "source_sha256": source_sha,
            })
        elif current_sha == installed_sha:
            operations.append({
                "action": "update-framework",
                "path": path,
                "reason": "target unchanged since prior install and framework source changed",
                "source_sha256": source_sha,
            })
        elif old_source_sha == source_sha:
            notices.append({
                "kind": "local-framework-modification",
                "path": path,
                "reason": "target was locally modified, but this framework file has no upstream change in this upgrade",
            })
        else:
            conflicts.append({
                "path": path,
                "reason": "both target and framework source changed since prior install",
                "installed_sha256": installed_sha,
                "current_sha256": current_sha,
                "previous_source_sha256": old_source_sha,
                "source_sha256": source_sha,
            })

    desired_paths = set(desired_by_path)
    for path, record in sorted(tracked.items()):
        if record.get("management") == "framework" and path not in desired_paths:
            notices.append({
                "kind": "obsolete-framework-file",
                "path": path,
                "reason": "tracked framework file no longer exists in the new source; never deleted automatically",
            })

    return {
        "from_runtime_version": manifest.get("runtime_version", "unknown"),
        "to_runtime_version": runtime_version(source_root),
        "operations": operations,
        "conflicts": conflicts,
        "notices": notices,
    }


def apply_upgrade(
    source_root: pathlib.Path,
    target: pathlib.Path,
    manifest: dict,
    plan: dict,
) -> None:
    if plan["conflicts"]:
        raise RuntimeError("upgrade has framework conflicts; refusing partial automatic apply")

    desired = {
        entry["target"].as_posix(): entry
        for entry in desired_entries(source_root, target, manifest)
    }
    files = dict(manifest.get("files", {}))

    for op in plan["operations"]:
        path = op["path"]
        entry = desired[path]
        destination = target / path

        if op["action"] in {"create-framework", "update-framework", "create-seed"}:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry["source"], destination)

        if op["action"] == "refresh-manifest":
            pass

        if destination.is_file():
            files[path] = manifest_record(entry, destination)

    new_manifest = {
        "format_version": 1,
        "runtime_version": plan["to_runtime_version"],
        "files": files,
    }
    path = target / INSTALL_MANIFEST
    path.write_text(json.dumps(new_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely upgrade an adopted PACT project")
    parser.add_argument("--target", required=True)
    parser.add_argument(
        "--source",
        help="PACT source root providing the newer runtime; defaults to this checkout",
    )
    parser.add_argument("--apply", action="store_true", help="apply only when there are no framework conflicts")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    target = pathlib.Path(args.target).expanduser().resolve()
    source_root = (
        pathlib.Path(args.source).expanduser().resolve()
        if args.source
        else SCRIPT_ROOT
    )

    try:
        manifest = load_manifest(target)
        plan = plan_upgrade(source_root, target, manifest)
    except Exception as exc:
        print(f"PACT upgrade: cannot plan upgrade: {exc}", file=sys.stderr)
        return 2

    result = {
        "target": str(target),
        "source": str(source_root),
        "mode": "apply" if args.apply else "dry-run",
        **plan,
    }

    if args.apply:
        if plan["conflicts"]:
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print("PACT upgrade: conflicts detected; no files were changed.", file=sys.stderr)
                for conflict in plan["conflicts"]:
                    print(f"- {conflict['path']}: {conflict['reason']}", file=sys.stderr)
            return 1

        try:
            apply_upgrade(source_root, target, manifest, plan)
            result["applied"] = True
        except Exception as exc:
            print(f"PACT upgrade: apply failed: {exc}", file=sys.stderr)
            return 2
    else:
        result["applied"] = False

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(
        f"PACT upgrade: {plan['from_runtime_version']} -> "
        f"{plan['to_runtime_version']} ({result['mode']})"
    )
    for op in plan["operations"]:
        print(f"- [{op['action'].upper()}] {op['path']}: {op['reason']}")
    for notice in plan["notices"]:
        print(f"- [NOTICE:{notice['kind']}] {notice['path']}: {notice['reason']}")
    for conflict in plan["conflicts"]:
        print(f"- [CONFLICT] {conflict['path']}: {conflict['reason']}")

    if not args.apply:
        print("No files were changed. Re-run with --apply after reviewing the plan.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
