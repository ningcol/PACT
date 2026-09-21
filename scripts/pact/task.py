#!/usr/bin/env python3
"""High-level PACT task lifecycle helpers.

This command composes existing PACT primitives. It does not replace the
low-level commands or invent semantic Evidence/Convergence on the Agent's behalf.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

from task_contract import validate as validate_contract
from runtime_exec import runtime_command
from workspace import task_workspace_baseline, task_changed_files
from protocol_ids import validate_task_id, confined_child


ROOT = pathlib.Path(__file__).resolve().parents[2]
TASK_ROOT = ROOT / ".pact" / "tasks"
COMPLETION_ROOT = ROOT / ".pact" / "completions"
TMP_ROOT = ROOT / ".pact" / "tmp"


def generated_task_id(task: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = hashlib.sha256(task.encode("utf-8")).hexdigest()[:8].upper()
    return f"TASK-{stamp}-{suffix}"


def write_json(path: pathlib.Path, data: dict) -> None:
    """Atomically publish JSON state without following an existing leaf symlink."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.pact-task-",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = pathlib.Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            if temporary.exists():
                temporary.unlink()
        except OSError:
            pass


def read_task_manifest(path: pathlib.Path) -> dict:
    if path.is_symlink():
        raise ValueError(f"task manifest path must not be a symlink: {path}")
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid task manifest JSON: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"invalid task manifest object: {path}")
    return data


def read_jsonl_records(path: pathlib.Path) -> list[dict]:
    if path.is_symlink():
        raise ValueError(f"JSONL history path must not be a symlink: {path}")
    if not path.is_file():
        return []

    records: list[dict] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"invalid JSONL history at {path}:{line_number}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise ValueError(
                f"invalid JSONL history object at {path}:{line_number}"
            )
        records.append(value)
    return records


def append_jsonl_atomic(path: pathlib.Path, data: dict) -> None:
    """Append one JSONL record by atomically replacing the complete valid history."""
    path.parent.mkdir(parents=True, exist_ok=True)
    records = read_jsonl_records(path)
    records.append(data)
    payload = "".join(
        json.dumps(record, ensure_ascii=False) + "\n"
        for record in records
    )

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.pact-task-",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = pathlib.Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            if temporary.exists():
                temporary.unlink()
        except OSError:
            pass


def run_impact_atomically(
    command: list[str],
    destination: pathlib.Path,
) -> subprocess.CompletedProcess[str]:
    """Run Impact against a staged output path and atomically publish on success."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.pact-task-",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(fd)
    temporary = pathlib.Path(temporary_name)
    staged_command = list(command)
    try:
        output_index = staged_command.index("--output") + 1
    except (ValueError, IndexError):
        temporary.unlink(missing_ok=True)
        raise ValueError("Impact command is missing --output")

    staged_command[output_index] = str(temporary)
    try:
        result = run(staged_command)
        if result.returncode == 0:
            os.replace(temporary, destination)
        return result
    finally:
        try:
            if temporary.exists():
                temporary.unlink()
        except OSError:
            pass


def completion_blockers(errors: list[str]) -> list[str]:
    text = "\n".join(str(value) for value in errors)
    blockers: list[str] = []
    checks = [
        ("stale-workspace", ("stale pact-run receipt", "verified workspace")),
        ("stale-task-contract", ("task_contract_sha256",)),
        ("acceptance-gap", ("acceptance criterion", "Owner Report acceptance")),
        ("convergence-coverage", ("convergence coverage:",)),
        ("change-coverage", ("change coverage:", "Task changed file missing")),
        ("ci-metadata-required", ("CI-metadata Evidence",)),
    ]
    for code, needles in checks:
        if any(needle in text for needle in needles):
            blockers.append(code)
    return blockers


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True)


def prepare(args) -> int:
    task_id = args.task_id or generated_task_id(args.task)
    try:
        validate_task_id(task_id)
        task_dir = confined_child(TASK_ROOT, task_id)
        completion_dir = confined_child(COMPLETION_ROOT, task_id)
    except ValueError as exc:
        print(f"PACT task prepare: invalid task id: {exc}", file=sys.stderr)
        return 2

    if (task_dir.exists() or completion_dir.exists()) and not args.force:
        existing = task_dir if task_dir.exists() else completion_dir
        print(
            f"PACT task prepare: generated task state already exists: {existing} "
            "(use --force to rebuild preparation and invalidate old completion state)",
            file=sys.stderr,
        )
        return 2

    preflight = run(runtime_command("check", "--artifact-only"))
    if preflight.returncode != 0:
        print(
            "PACT task prepare: deterministic repository checks failed; "
            "fix machine-established repository errors before preparing work.",
            file=sys.stderr,
        )
        if preflight.stdout:
            print(preflight.stdout, end="", file=sys.stderr)
        if preflight.stderr:
            print(preflight.stderr, end="", file=sys.stderr)
        return preflight.returncode

    acceptance_items = [
        ("outcome", text)
        for text in [args.success, *args.acceptance]
    ] + [
        ("constraint", text)
        for text in args.constraint
    ]
    contract = {
        "version": 1,
        "task_id": task_id,
        "intent": args.goal or args.task,
        "acceptance_criteria": [
            {"id": f"AC-{index}", "kind": kind, "text": text}
            for index, (kind, text) in enumerate(acceptance_items, start=1)
        ],
    }
    contract_errors = validate_contract(contract)
    if contract_errors:
        print("PACT task prepare: generated invalid Task Contract", file=sys.stderr)
        for error in contract_errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    try:
        workspace_baseline = task_workspace_baseline(ROOT)
    except Exception as exc:
        print(
            f"PACT task prepare: cannot capture workspace baseline: {exc}",
            file=sys.stderr,
        )
        return 2

    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    TASK_ROOT.mkdir(parents=True, exist_ok=True)
    COMPLETION_ROOT.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix=".prepare-",
        dir=TMP_ROOT,
    ) as tmp:
        transaction = pathlib.Path(tmp)
        staged_task = transaction / "task"
        staged_task.mkdir()

        staged_contract = staged_task / "contract.json"
        write_json(staged_contract, contract)
        contract_sha256 = hashlib.sha256(
            staged_contract.read_bytes()
        ).hexdigest()

        staged_context = staged_task / "context.json"
        context_cmd = runtime_command(
            "context",
            args.task,
            "--success",
            "; ".join(text for _, text in acceptance_items),
            "--risk",
            args.risk,
            "--output",
            str(staged_context),
        )
        if args.goal:
            context_cmd.extend(["--goal", args.goal])
        # High-level task preparation always preserves the owner's task wording
        # as primary retrieval intent. Repeatable --query values are additional
        # search hypotheses, matching the recommended inspect surface.
        context_cmd.extend(["--query", args.task])
        for query in args.query:
            context_cmd.extend(["--query", query])
        if args.token_budget is not None:
            context_cmd.extend(["--token-budget", str(args.token_budget)])
        if args.code is True:
            context_cmd.append("--code")
        elif args.code is False:
            context_cmd.append("--no-code")

        context_result = run(context_cmd)
        if context_result.returncode != 0:
            print(context_result.stdout, end="")
            print(context_result.stderr, end="", file=sys.stderr)
            return context_result.returncode

        context_sha256 = hashlib.sha256(
            staged_context.read_bytes()
        ).hexdigest()

        staged_impact = None
        impact_state = "deferred"
        if args.files or args.base:
            staged_impact = staged_task / "impact.json"
            impact_cmd = runtime_command(
                "impact",
                "--risk",
                args.risk,
                "--output",
                str(staged_impact),
            )
            if args.files:
                impact_cmd.extend(["--files", *args.files])
            else:
                impact_cmd.extend(["--base", args.base, "--head", args.head])
            if args.code is True:
                impact_cmd.append("--code")
            elif args.code is False:
                impact_cmd.append("--no-code")

            impact_result = run(impact_cmd)
            if impact_result.returncode != 0:
                print(impact_result.stdout, end="")
                print(impact_result.stderr, end="", file=sys.stderr)
                return impact_result.returncode
            impact_state = "prepared"

        final_contract = task_dir / "contract.json"
        final_context = task_dir / "context.json"
        final_impact = task_dir / "impact.json" if staged_impact else None
        manifest = {
            "version": 1,
            "task_id": task_id,
            "status": "prepared",
            "task": args.task,
            "goal": args.goal or args.task,
            "observable_success": args.success,
            "risk_level": args.risk,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "contract": final_contract.relative_to(ROOT).as_posix(),
            "contract_sha256": contract_sha256,
            "acceptance_criteria_count": len(contract["acceptance_criteria"]),
            "context": final_context.relative_to(ROOT).as_posix(),
            "context_sha256": context_sha256,
            "impact": (
                final_impact.relative_to(ROOT).as_posix()
                if final_impact is not None
                else None
            ),
            "impact_state": impact_state,
            "workspace_baseline": workspace_baseline,
            "completion_bundle": completion_dir.relative_to(ROOT).as_posix(),
        }
        write_json(staged_task / "task.json", manifest)

        old_task = transaction / "old-task"
        old_completion = transaction / "old-completion"
        moved_task = False
        moved_completion = False

        try:
            if task_dir.exists():
                os.replace(task_dir, old_task)
                moved_task = True
            if completion_dir.exists():
                os.replace(completion_dir, old_completion)
                moved_completion = True

            os.replace(staged_task, task_dir)
        except Exception as exc:
            if task_dir.exists() and not moved_task:
                try:
                    if task_dir.is_dir():
                        import shutil
                        shutil.rmtree(task_dir)
                    else:
                        task_dir.unlink()
                except OSError:
                    pass
            if moved_task and old_task.exists() and not task_dir.exists():
                os.replace(old_task, task_dir)
            if (
                moved_completion
                and old_completion.exists()
                and not completion_dir.exists()
            ):
                os.replace(old_completion, completion_dir)
            print(
                f"PACT task prepare: atomic publish failed: {exc}",
                file=sys.stderr,
            )
            return 2

    result = {
        **manifest,
        "task_dir": task_dir.relative_to(ROOT).as_posix(),
        "next": (
            "Implement and verify every Task Contract acceptance criterion. "
            "Evidence claims that prove acceptance must list the relevant "
            "criteria IDs. Convergence must bind the prepared context_sha256 "
            "and explicitly cover every context.artifacts entry. At finish, "
            "PACT will derive the files actually changed by this task and "
            "require convergence.change_coverage rationale for each one. Create "
            "evidence.json, convergence.json, and owner-report.json in the "
            "completion bundle, then run "
            f"'pact task finish {task_id}'."
        ),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"PACT task prepared: {task_id}")
        print(f"- risk: {args.risk}")
        print(
            f"- contract: {manifest['contract']} "
            f"({manifest['acceptance_criteria_count']} acceptance criteria)"
        )
        print(
            f"- context: {manifest['context']} "
            f"(sha256={manifest['context_sha256'][:12]}...)"
        )
        print(f"- impact: {impact_state}")
        if impact_state == "deferred":
            print(
                "- impact note: no changed-file/base input was supplied; run "
                "low-level impact later or rebuild preparation with --files/--base."
            )
        print(f"- completion bundle: {manifest['completion_bundle']}")
        print("- next: " + result["next"])

    return 0


def finish(args) -> int:
    try:
        validate_task_id(args.task_id)
        task_dir = confined_child(TASK_ROOT, args.task_id)
    except ValueError as exc:
        print(f"PACT task finish: invalid task id: {exc}", file=sys.stderr)
        return 2
    manifest_path = task_dir / "task.json"
    try:
        manifest = read_task_manifest(manifest_path)
    except FileNotFoundError:
        print(
            f"PACT task finish: task was not prepared: {args.task_id}. "
            "Use 'pact task prepare' first.",
            file=sys.stderr,
        )
        return 2
    except ValueError as exc:
        print(f"PACT task finish: {exc}", file=sys.stderr)
        return 2

    if manifest.get("task_id") != args.task_id:
        print(
            "PACT task finish: task manifest task_id does not match requested task "
            f"({manifest.get('task_id')!r} != {args.task_id!r})",
            file=sys.stderr,
        )
        return 2

    required_manifest_fields = (
        "contract",
        "context",
        "context_sha256",
        "workspace_baseline",
        "risk_level",
    )
    missing_fields = [
        field for field in required_manifest_fields
        if not manifest.get(field)
    ]
    if missing_fields:
        print(
            "PACT task finish: prepared task manifest is incomplete; missing "
            + ", ".join(missing_fields),
            file=sys.stderr,
        )
        return 2

    bundle = pathlib.Path(args.bundle) if args.bundle else confined_child(COMPLETION_ROOT, args.task_id)
    if not bundle.is_absolute():
        bundle = ROOT / bundle

    try:
        task_change = task_changed_files(
            ROOT,
            manifest["workspace_baseline"],
        )
    except Exception as exc:
        print(
            f"PACT task finish: cannot derive task changed files: {exc}",
            file=sys.stderr,
        )
        return 2

    changed_files = task_change.get("changed_files", [])
    trust_warnings: list[str] = []
    if not task_change.get("supported"):
        trust_warnings.append(
            "Exact task changed-file attribution is unavailable: "
            + str(
                task_change.get("reason")
                or "the current workspace does not support exact attribution"
            )
        )

    final_impact = None
    if task_change.get("supported") and changed_files:
        final_impact = task_dir / "final-impact.json"
        impact_cmd = runtime_command(
            "impact",
            "--risk",
            manifest.get("risk_level", "medium"),
            "--output",
            str(final_impact),
            "--files",
            *changed_files,
        )
        try:
            impact_result = run_impact_atomically(impact_cmd, final_impact)
        except (OSError, ValueError) as exc:
            print(
                f"PACT task finish: cannot publish final Impact: {exc}",
                file=sys.stderr,
            )
            return 2
        if impact_result.returncode != 0:
            print(impact_result.stdout, end="")
            print(impact_result.stderr, end="", file=sys.stderr)
            return impact_result.returncode

    manifest["task_change"] = task_change
    manifest["final_impact"] = (
        final_impact.relative_to(ROOT).as_posix()
        if final_impact is not None
        else None
    )
    try:
        write_json(manifest_path, manifest)
    except OSError as exc:
        print(
            f"PACT task finish: cannot persist task change state: {exc}",
            file=sys.stderr,
        )
        return 2

    command = runtime_command(
        "complete",
        str(bundle),
        "--root",
        str(ROOT),
        "--json",
    )
    if args.require_ci_metadata:
        command.append("--require-ci-metadata")

    try:
        contract_path = (ROOT / manifest["contract"]).resolve()
        context_path = (ROOT / manifest["context"]).resolve()
        contract_path.relative_to(ROOT.resolve())
        context_path.relative_to(ROOT.resolve())
    except (ValueError, TypeError) as exc:
        print(
            f"PACT task finish: prepared task path escapes repository: {exc}",
            file=sys.stderr,
        )
        return 2

    command.extend(["--contract", str(contract_path)])
    command.extend(["--context", str(context_path)])
    command.extend(["--context-sha256", manifest["context_sha256"]])
    command.extend(["--expected-risk", manifest["risk_level"]])
    if task_change.get("supported"):
        command.append("--check-change-coverage")
        for path in changed_files:
            command.extend(["--changed-file", path])

    completed = run(command)
    output = None
    if completed.stdout.strip():
        try:
            output = json.loads(completed.stdout)
            output["task_change"] = task_change
            output["final_impact"] = manifest.get("final_impact")
            output["trust_warnings"] = trust_warnings
        except json.JSONDecodeError:
            pass

    attempt = {
        "version": 1,
        "attempted_at": datetime.now(timezone.utc).isoformat(),
        "returncode": int(completed.returncode),
        "result_available": output is not None,
        "complete": bool(output.get("complete")) if output is not None else False,
        "errors": output.get("errors", []) if output is not None else [],
        "blockers": completion_blockers(
            output.get("errors", []) if output is not None else []
        ),
        "policy_gaps": output.get("policy_gaps", []) if output is not None else [],
        "acceptance": output.get("acceptance") if output is not None else None,
        "task_change": task_change,
        "final_impact": manifest.get("final_impact"),
        "trust_warnings": trust_warnings,
    }
    try:
        append_jsonl_atomic(task_dir / "completion-attempts.jsonl", attempt)
    except (OSError, ValueError) as exc:
        print(
            f"PACT task finish: cannot persist completion attempt history: {exc}",
            file=sys.stderr,
        )
        return 2

    if completed.returncode == 0:
        manifest["status"] = "completed"
        manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
        try:
            bundle_display = bundle.relative_to(ROOT).as_posix()
        except ValueError:
            bundle_display = str(bundle)
        manifest["completion_bundle"] = bundle_display
        try:
            write_json(manifest_path, manifest)
        except OSError as exc:
            print(
                f"PACT task finish: completion gate passed but completed task state "
                f"could not be persisted: {exc}",
                file=sys.stderr,
            )
            return 2

    if args.json and output is not None:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        for warning in trust_warnings:
            print(f"PACT task finish WARNING: {warning}", file=sys.stderr)

    return completed.returncode


def manifest_path_field(
    manifest: dict,
    field: str,
    *,
    default: str | None = None,
) -> str | None:
    value = manifest.get(field, default)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"task manifest field {field!r} must be a non-empty string path"
        )
    return value


def read_status_contract(path: pathlib.Path) -> dict:
    if not path.is_file():
        raise ValueError(f"task contract file is missing: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read task contract: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"invalid task contract object: {path}")
    errors = validate_contract(data)
    if errors:
        raise ValueError(
            "invalid task contract: " + "; ".join(errors)
        )
    return data


def completion_bundle_path(manifest: dict, task_id: str) -> pathlib.Path:
    value = manifest_path_field(
        manifest,
        "completion_bundle",
        default=f".pact/completions/{task_id}",
    )
    assert value is not None
    bundle = pathlib.Path(value).expanduser()
    return bundle if bundle.is_absolute() else ROOT / bundle


def task_status(args) -> int:
    try:
        validate_task_id(args.task_id)
        task_dir = confined_child(TASK_ROOT, args.task_id)
    except ValueError as exc:
        print(f"PACT task status: invalid task id: {exc}", file=sys.stderr)
        return 2
    manifest_path = task_dir / "task.json"
    try:
        manifest = read_task_manifest(manifest_path)
    except FileNotFoundError:
        print(f"PACT task status: unknown task {args.task_id}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"PACT task status: {exc}", file=sys.stderr)
        return 2

    try:
        bundle = completion_bundle_path(manifest, args.task_id)
        contract_path = manifest_path_field(manifest, "contract")
    except ValueError as exc:
        print(f"PACT task status: {exc}", file=sys.stderr)
        return 2

    completion_files = {
        name: (bundle / filename).is_file()
        for name, filename in {
            "evidence": "evidence.json",
            "convergence": "convergence.json",
            "owner_report": "owner-report.json",
        }.items()
    }

    contract = None
    if contract_path:
        path = ROOT / contract_path
        try:
            contract = read_status_contract(path)
        except ValueError as exc:
            print(f"PACT task status: {exc}", file=sys.stderr)
            return 2

    result = {
        **manifest,
        "acceptance_criteria": contract.get("acceptance_criteria", []) if contract else [],
        "completion_files": completion_files,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"PACT task {args.task_id}: {manifest.get('status')}")
        print(f"- risk: {manifest.get('risk_level')}")
        print(f"- acceptance criteria: {len(result['acceptance_criteria'])}")
        print(f"- context: {manifest.get('context')}")
        print(f"- impact: {manifest.get('impact_state')}")
        print(
            "- completion files: "
            + ", ".join(
                f"{name}={'yes' if present else 'no'}"
                for name, present in completion_files.items()
            )
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="PACT high-level task surface")
    sub = parser.add_subparsers(dest="command", required=True)

    prep = sub.add_parser("prepare", help="prepare risk-adaptive task context")
    prep.add_argument("task")
    prep.add_argument("--success", required=True)
    prep.add_argument(
        "--accept",
        dest="acceptance",
        action="append",
        default=[],
        help="additional observable acceptance criterion (repeatable)",
    )
    prep.add_argument(
        "--constraint",
        action="append",
        default=[],
        help="task constraint that must be preserved (repeatable)",
    )
    prep.add_argument("--goal")
    prep.add_argument("--risk", choices=["low", "medium", "high"], default="medium")
    prep.add_argument(
        "--query",
        action="append",
        default=[],
        help="additional discovery query; repeat to fuse business/code vocabulary while preserving the task wording",
    )
    prep.add_argument(
        "--token-budget",
        type=int,
        help="override soft estimated materialization token budget",
    )
    prep.add_argument("--task-id")
    prep.add_argument("--files", nargs="+")
    prep.add_argument("--base")
    prep.add_argument("--head", default="HEAD")
    prep.add_argument("--force", action="store_true")
    code = prep.add_mutually_exclusive_group()
    code.add_argument("--code", dest="code", action="store_true")
    code.add_argument("--no-code", dest="code", action="store_false")
    prep.set_defaults(code=None)
    prep.add_argument("--json", action="store_true")

    finish_parser = sub.add_parser("finish", help="validate an existing task completion bundle")
    finish_parser.add_argument("task_id")
    finish_parser.add_argument("--bundle")
    finish_parser.add_argument("--require-ci-metadata", action="store_true")
    finish_parser.add_argument("--json", action="store_true")

    status_parser = sub.add_parser("status", help="show one prepared task")
    status_parser.add_argument("task_id")
    status_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "prepare":
        if args.files and args.base:
            parser.error("--files and --base are mutually exclusive")
        if args.token_budget is not None and args.token_budget < 0:
            parser.error("--token-budget must be >= 0")
        return prepare(args)
    if args.command == "finish":
        return finish(args)
    return task_status(args)


if __name__ == "__main__":
    raise SystemExit(main())
