#!/usr/bin/env python3
"""Plan and transactionally apply framework-managed PACT upgrades."""

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
    sha256_file,
    source_manifest,
    read_install_manifest,
    resolve_install_target,
)
from schema_validate import load_schema, validate_instance


SCRIPT_ROOT = pathlib.Path(__file__).resolve().parents[2]
INSTALL_MANIFEST = pathlib.Path(".pact/install.json")
MUTATING_ACTIONS = {
    "create-framework",
    "update-framework",
    "create-seed",
    "remove-framework",
}


class UpgradeApplyError(RuntimeError):
    def __init__(self, message: str, *, rolled_back: bool):
        super().__init__(message)
        self.rolled_back = rolled_back


def path_present(path: pathlib.Path) -> bool:
    """Treat any leaf symlink, including a broken one, as an existing path."""
    return path.exists() or path.is_symlink()


def load_manifest(target: pathlib.Path) -> dict:
    manifest_path = resolve_install_target(target, INSTALL_MANIFEST.as_posix())
    if not manifest_path.is_file():
        raise FileNotFoundError(
            "missing .pact/install.json; initialize the project with PACT first"
        )
    data = read_install_manifest(target)
    if data is None:
        raise FileNotFoundError(
            "missing .pact/install.json; initialize the project with PACT first"
        )
    return data


def desired_entries(source_root: pathlib.Path, target: pathlib.Path, manifest: dict) -> list[dict]:
    entries = source_manifest(source_root)

    workflow_path = ".github/workflows/pact-project-check.yml"
    tracked = manifest.get("files", {}).get(workflow_path)
    workflow_target = resolve_install_target(
        target,
        workflow_path,
        allow_leaf_symlink=True,
    )
    if tracked or path_present(workflow_target):
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
        destination = resolve_install_target(
            target,
            path,
            allow_leaf_symlink=entry["management"] == "seed",
        )
        source = pathlib.Path(entry["source"])
        source_sha = sha256_file(source)
        record = tracked.get(path)

        if entry["management"] == "seed":
            if not path_present(destination):
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
                        "reason": (
                            "framework seed/template changed; project-owned file "
                            "will not be overwritten"
                        ),
                    })
            elif not record:
                notices.append({
                    "kind": "untracked-seed",
                    "path": path,
                    "reason": (
                        "existing project-owned file is intentionally not adopted "
                        "or overwritten"
                    ),
                })
            continue

        if not path_present(destination):
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
                    "reason": (
                        "file matches source but has no install provenance; "
                        "not auto-adopted"
                    ),
                })
            else:
                conflicts.append({
                    "path": path,
                    "reason": (
                        "framework path exists but is not tracked by install manifest"
                    ),
                    "current_sha256": current_sha,
                    "source_sha256": source_sha,
                })
            continue

        if record.get("management") != "framework":
            notices.append({
                "kind": "ownership-changed",
                "path": path,
                "reason": (
                    "previous install marked this path project-owned; "
                    "upgrade will not overwrite it"
                ),
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
                "reason": (
                    "target unchanged since prior install and framework source changed"
                ),
                "source_sha256": source_sha,
            })
        elif old_source_sha == source_sha:
            conflicts.append({
                "path": path,
                "reason": (
                    "framework-managed file was locally modified; automatic "
                    "upgrade refuses to preserve stale framework ownership"
                ),
                "installed_sha256": installed_sha,
                "current_sha256": current_sha,
                "previous_source_sha256": old_source_sha,
                "source_sha256": source_sha,
            })
        else:
            conflicts.append({
                "path": path,
                "reason": (
                    "both target and framework source changed since prior install"
                ),
                "installed_sha256": installed_sha,
                "current_sha256": current_sha,
                "previous_source_sha256": old_source_sha,
                "source_sha256": source_sha,
            })

    desired_paths = set(desired_by_path)
    for path, record in sorted(tracked.items()):
        if record.get("management") != "framework" or path in desired_paths:
            continue

        destination = resolve_install_target(target, path)
        if not path_present(destination):
            operations.append({
                "action": "remove-framework",
                "path": path,
                "reason": "obsolete tracked framework path is already absent",
                "already_absent": True,
            })
            continue

        if not destination.is_file():
            operations.append({
                "action": "detach-framework",
                "path": path,
                "reason": (
                    "obsolete tracked framework path is no longer a regular file; "
                    "preserve it but stop framework management"
                ),
            })
            notices.append({
                "kind": "obsolete-framework-nonfile",
                "path": path,
                "reason": (
                    "obsolete tracked framework path is no longer a regular file; "
                    "preserved and detached from framework management"
                ),
            })
            continue

        current_sha = sha256_file(destination)
        installed_sha = record.get("installed_sha256")
        if isinstance(installed_sha, str) and current_sha == installed_sha:
            operations.append({
                "action": "remove-framework",
                "path": path,
                "reason": (
                    "obsolete framework file is unchanged since prior install "
                    "and can be removed safely"
                ),
                "already_absent": False,
                "installed_sha256": installed_sha,
            })
        else:
            operations.append({
                "action": "detach-framework",
                "path": path,
                "reason": (
                    "obsolete framework file has local modifications; "
                    "preserve it but stop framework management"
                ),
            })
            notices.append({
                "kind": "obsolete-framework-local-modification",
                "path": path,
                "reason": (
                    "obsolete framework file was modified after install; "
                    "preserved and detached from framework management"
                ),
            })

    return {
        "from_runtime_version": manifest.get("runtime_version", "unknown"),
        "to_runtime_version": runtime_version(source_root),
        "operations": operations,
        "conflicts": conflicts,
        "notices": notices,
    }


def validate_new_manifest(
    target: pathlib.Path,
    new_manifest: dict,
    touched_paths: list[str],
) -> None:
    schema_path = SCRIPT_ROOT / ".pact" / "schema" / "install-manifest.schema.json"
    errors = validate_instance(new_manifest, load_schema(schema_path))
    if errors:
        raise RuntimeError("new install manifest is invalid: " + "; ".join(errors))

    version_path = resolve_install_target(target, ".pact/VERSION")
    actual_version = (
        version_path.read_text(encoding="utf-8").strip()
        if version_path.exists()
        else None
    )
    if actual_version != new_manifest.get("runtime_version"):
        raise RuntimeError(
            f"runtime version mismatch after apply: VERSION={actual_version!r}, "
            f"manifest={new_manifest.get('runtime_version')!r}"
        )

    files = new_manifest.get("files", {})
    for path in touched_paths:
        destination = resolve_install_target(target, path)
        record = files.get(path)
        if not destination.is_file() or not record:
            raise RuntimeError(f"upgraded file missing from final state: {path}")
        actual_sha = sha256_file(destination)
        if actual_sha != record.get("installed_sha256"):
            raise RuntimeError(
                f"upgraded file hash mismatch for {path}: "
                f"{actual_sha} != {record.get('installed_sha256')}"
            )


def cleanup_empty_parents(path: pathlib.Path, stop: pathlib.Path) -> None:
    current = path
    stop = stop.resolve()
    while current != stop and stop in current.resolve().parents:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def assert_planned_target_unchanged(
    target: pathlib.Path,
    operation: dict,
    manifest: dict,
) -> None:
    """Enforce the observed plan's target identity before acting on it.

    The target may be missing at plan time (create/remove-absent), or be a
    regular file with a known SHA. Do not overwrite new local files or detach
    trust in locally modified files. Caller decides rollback semantics.
    """
    action = operation["action"]
    path = operation["path"]
    if action not in MUTATING_ACTIONS and action != "refresh-manifest":
        return

    destination = resolve_install_target(target, path)
    must_be_missing = (
        action in {"create-framework", "create-seed"}
        or (action == "remove-framework" and operation.get("already_absent"))
    )
    if must_be_missing:
        if path_present(destination):
            raise RuntimeError(
                f"upgrade target changed after plan: {path} was absent but now exists"
            )
        return

    if action == "update-framework":
        record = manifest.get("files", {}).get(path, {})
        expected_sha = record.get("installed_sha256")
    elif action == "refresh-manifest":
        expected_sha = operation.get("source_sha256")
    elif action == "remove-framework":
        expected_sha = operation.get("installed_sha256")
    else:
        return

    if not isinstance(expected_sha, str) or not destination.is_file():
        raise RuntimeError(
            f"upgrade target changed after plan: {path} is not a regular file"
        )
    actual_sha = sha256_file(destination)
    if actual_sha != expected_sha:
        raise RuntimeError(
            f"upgrade target changed after plan: {path} SHA256 differs "
            f"({actual_sha!r} != {expected_sha!r})"
        )


def apply_upgrade(
    source_root: pathlib.Path,
    target: pathlib.Path,
    manifest: dict,
    plan: dict,
) -> dict:
    if plan["conflicts"]:
        raise UpgradeApplyError(
            "upgrade has framework conflicts; refusing automatic apply",
            rolled_back=False,
        )

    # plan_upgrade() is normally called immediately before apply_upgrade(),
    # but both can observe a concurrent writer. Recheck the complete
    # ownership/operation decision before creating transaction state.
    try:
        if load_manifest(target) != manifest:
            raise RuntimeError("install manifest changed after planning")
        refreshed_plan = plan_upgrade(source_root, target, manifest)
        if refreshed_plan != plan:
            raise RuntimeError("upgrade source or target changed after planning")
        for operation in plan["operations"]:
            assert_planned_target_unchanged(target, operation, manifest)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        raise UpgradeApplyError(
            f"stale upgrade plan; no target changes applied: {exc}",
            rolled_back=False,
        ) from exc

    desired = {
        entry["target"].as_posix(): entry
        for entry in desired_entries(source_root, target, manifest)
    }
    files = dict(manifest.get("files", {}))

    pact_dir = resolve_install_target(target, ".pact")
    pact_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = resolve_install_target(target, INSTALL_MANIFEST.as_posix())

    mutating_ops = [
        op for op in plan["operations"]
        if op["action"] in MUTATING_ACTIONS
    ]
    refresh_ops = [
        op for op in plan["operations"]
        if op["action"] == "refresh-manifest"
    ]

    with tempfile.TemporaryDirectory(
        prefix=".upgrade-txn-",
        dir=pact_dir,
    ) as tmp:
        txn = pathlib.Path(tmp)
        stage_root = txn / "stage"
        backup_root = txn / "backup"
        stage_root.mkdir()
        backup_root.mkdir()

        try:
            # Stage and validate every source before target mutation begins.
            staged: dict[str, pathlib.Path] = {}
            for op in mutating_ops:
                if op["action"] == "remove-framework":
                    continue
                path = op["path"]
                entry = desired[path]
                staged_path = stage_root / pathlib.Path(path)
                staged_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(entry["source"], staged_path)
                actual_sha = sha256_file(staged_path)
                if actual_sha != op["source_sha256"]:
                    raise UpgradeApplyError(
                        f"staged source hash mismatch for {path}",
                        rolled_back=False,
                    )
                staged[path] = staged_path

            original_exists: dict[str, bool] = {}
            backups: dict[str, pathlib.Path] = {}
            for op in mutating_ops:
                path = op["path"]
                destination = resolve_install_target(target, path)
                original_exists[path] = destination.is_file()
                if destination.is_file():
                    backup = backup_root / pathlib.Path(path)
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(destination, backup)
                    backups[path] = backup

            manifest_backup = backup_root / "install.json"
            shutil.copy2(manifest_path, manifest_backup)
            original_manifest_sha256 = sha256_file(manifest_backup)
            if sha256_file(manifest_path) != original_manifest_sha256:
                raise UpgradeApplyError(
                    "install manifest changed while staging upgrade; refusing apply",
                    rolled_back=False,
                )
            # The on-disk object must still be the one we planned against.
            if load_manifest(target) != manifest:
                raise UpgradeApplyError(
                    "install manifest changed while staging upgrade; refusing apply",
                    rolled_back=False,
                )

        except UpgradeApplyError:
            raise
        except Exception as exc:
            raise UpgradeApplyError(
                f"upgrade staging or backup failed before target mutation: {exc}",
                rolled_back=False,
            ) from exc

        replaced: list[str] = []
        created: list[str] = []
        # For safe rollback, remember what PACT actually intended to write.
        written_targets: dict[str, str | None] = {}
        manifest_committed = False
        committed_manifest_sha256: str | None = None
        fail_after_raw = os.environ.get("PACT_TEST_FAIL_AFTER_REPLACE")
        fail_after = int(fail_after_raw) if fail_after_raw else None

        try:
            removed: list[str] = []
            for op in mutating_ops:
                path = op["path"]
                # Last possible non-locking guard before destructive writes.
                assert_planned_target_unchanged(target, op, manifest)
                destination = resolve_install_target(target, path)

                if op["action"] == "remove-framework":
                    if destination.is_file():
                        destination.unlink()
                    replaced.append(path)
                    written_targets[path] = None  # PACT left the target absent
                    removed.append(path)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    fd, temp_name = tempfile.mkstemp(
                        prefix=f".{destination.name}.pact-upgrade-",
                        suffix=".tmp", dir=destination.parent,
                    )
                    os.close(fd)
                    temp_destination = pathlib.Path(temp_name)
                    try:
                        shutil.copy2(staged[path], temp_destination)
                        os.replace(temp_destination, destination)
                    finally:
                        temp_destination.unlink(missing_ok=True)

                    replaced.append(path)
                    written_targets[path] = op["source_sha256"]
                    if not original_exists[path]:
                        created.append(path)

                if fail_after is not None and len(replaced) >= fail_after:
                    raise RuntimeError(
                        f"simulated upgrade failure after {len(replaced)} replacement(s)"
                    )

            for path in removed:
                files.pop(path, None)
            for op in plan["operations"]:
                if op["action"] == "detach-framework":
                    files.pop(op["path"], None)

            touched = []
            for op in [
                *[item for item in mutating_ops if item["action"] != "remove-framework"],
                *refresh_ops,
            ]:
                path = op["path"]
                entry = desired[path]
                destination = resolve_install_target(target, path)
                if op["action"] == "refresh-manifest":
                    assert_planned_target_unchanged(target, op, manifest)
                if destination.is_file():
                    record = manifest_record(entry, destination)
                    if record.get("source_sha256") != op.get("source_sha256"):
                        raise RuntimeError(
                            f"upgrade source changed after staging: {path}"
                        )
                    files[path] = record
                    touched.append(path)

            new_manifest = {
                "format_version": 1,
                "runtime_version": plan["to_runtime_version"],
                "files": files,
            }
            validate_new_manifest(target, new_manifest, touched)

            staged_manifest = txn / "new-install.json"
            staged_manifest.write_text(
                json.dumps(new_manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            committed_manifest_sha256 = sha256_file(staged_manifest)
            if sha256_file(manifest_path) != original_manifest_sha256:
                raise RuntimeError(
                    "install manifest changed during upgrade; refusing to overwrite"
                )
            os.replace(staged_manifest, manifest_path)
            manifest_committed = True

            # Re-validate after committing manifest.
            validate_new_manifest(target, new_manifest, touched)

            for path in removed:
                destination = resolve_install_target(target, path)
                cleanup_empty_parents(destination.parent, target)

            return {
                "rolled_back": False,
                "replaced_files": len(replaced),
                "created_files": len(created),
                "removed_files": len(removed),
            }

        except Exception as exc:
            rollback_errors: list[str] = []

            for path in reversed(replaced):
                try:
                    destination = resolve_install_target(target, path)
                    expected_sha = written_targets[path]
                    if expected_sha is None:
                        if path_present(destination):
                            raise RuntimeError(
                                "changed concurrently after upgrade removal; "
                                "cannot safely restore previous bytes"
                            )
                    elif (
                        not destination.is_file()
                        or sha256_file(destination) != expected_sha
                    ):
                        raise RuntimeError(
                            "changed concurrently after upgrade replacement; "
                            "cannot safely roll back over newer bytes"
                        )

                    if original_exists.get(path):
                        backup = backups[path]
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        os.replace(backup, destination)
                    else:
                        if path_present(destination):
                            destination.unlink()
                        cleanup_empty_parents(destination.parent, target)
                except Exception as rollback_exc:
                    rollback_errors.append(f"{path}: {rollback_exc}")

            # Prior to commit, the manifest was not modified by PACT:
            # preserving it is safer than restoring a potentially stale copy
            # over an external concurrent edit. After commit, restore only
            # if it still holds the exact bytes we wrote.
            if manifest_committed:
                try:
                    if (
                        committed_manifest_sha256 is None
                        or not manifest_path.is_file()
                        or sha256_file(manifest_path) != committed_manifest_sha256
                    ):
                        rollback_errors.append(
                            "install manifest: changed concurrently after commit; "
                            "cannot safely restore older bytes"
                        )
                    else:
                        os.replace(manifest_backup, manifest_path)
                except Exception as rollback_exc:
                    rollback_errors.append(f"install manifest: {rollback_exc}")

            message = f"upgrade apply failed and rollback was attempted: {exc}"
            if rollback_errors:
                message += "; rollback errors: " + "; ".join(rollback_errors)
            raise UpgradeApplyError(
                message,
                rolled_back=not rollback_errors,
            ) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely upgrade an adopted PACT project")
    parser.add_argument("--target", required=True)
    parser.add_argument(
        "--source",
        help="PACT source root providing the newer runtime; defaults to this checkout",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="transactionally apply only when there are no framework conflicts",
    )
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
            result["applied"] = False
            result["rolled_back"] = False
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(
                    "PACT upgrade: conflicts detected; no files were changed.",
                    file=sys.stderr,
                )
                for conflict in plan["conflicts"]:
                    print(
                        f"- {conflict['path']}: {conflict['reason']}",
                        file=sys.stderr,
                    )
            return 1

        try:
            transaction = apply_upgrade(source_root, target, manifest, plan)
            result["applied"] = True
            result.update(transaction)
        except UpgradeApplyError as exc:
            result["applied"] = False
            result["rolled_back"] = exc.rolled_back
            result["apply_error"] = str(exc)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"PACT upgrade: {exc}", file=sys.stderr)
            return 2
    else:
        result["applied"] = False
        result["rolled_back"] = False

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

    if args.apply:
        print(
            f"Transactional apply complete: replaced={result.get('replaced_files', 0)}, "
            f"created={result.get('created_files', 0)}, "
            f"removed={result.get('removed_files', 0)}"
        )
    else:
        print("No files were changed. Re-run with --apply after reviewing the plan.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
