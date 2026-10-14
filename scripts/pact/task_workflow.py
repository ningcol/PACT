"""Safe mechanical helpers for prepared task Evidence and review scaffolds.

A verification command proves that the command ran. Only an Agent reviewing
product meaning may decide whether that result satisfies an acceptance criterion.
This module never synthesizes aligned Convergence or completed Owner Reports.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import uuid
from contextlib import contextmanager
from typing import Iterator

from evidence import validate as validate_evidence
from protocol_ids import (
    confined_child,
    confined_repository_path,
    confined_state_root,
    validate_task_id,
)
from runtime_exec import runtime_command
from task import (
    ROOT,
    TASK_ROOT,
    COMPLETION_ROOT,
    completion_bundle_path,
    read_status_contract,
    read_task_manifest,
    validate_finish_manifest,
    write_json,
)


RUN_ROOT = ROOT / ".pact" / "runs"
CLAIM_ID_PATTERN = re.compile(r"^EV-[A-Z0-9]+(?:-[A-Z0-9]+)*$")


def _prepared(task_id: str) -> tuple[dict, dict, pathlib.Path]:
    validate_task_id(task_id)
    task_dir = confined_child(TASK_ROOT, task_id, repository_root=ROOT)
    manifest = read_task_manifest(task_dir / "task.json")
    if manifest.get("task_id") != task_id:
        raise ValueError("prepared task identity does not match the requested task")
    if manifest.get("status") != "prepared":
        raise ValueError("only prepared, not already completed, tasks can be updated")

    errors = validate_finish_manifest(manifest, root=ROOT)
    if errors:
        raise ValueError("invalid/stale prepared task: " + "; ".join(errors))

    contract_path = confined_repository_path(
        ROOT, manifest["contract"], field="contract"
    )
    contract = read_status_contract(contract_path)
    if contract.get("task_id") != task_id:
        raise ValueError("prepared Task Contract identity mismatch")

    bundle = completion_bundle_path(manifest, task_id)
    try:
        bundle.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(
            "automated Evidence writes require a repository-local completion bundle"
        ) from exc
    # Reject aliases and symlinked parents, not merely path escapes.
    confined_state_root(ROOT, bundle, field="completion bundle")
    return manifest, contract, bundle


@contextmanager
def _exclusive_bundle(bundle: pathlib.Path) -> Iterator[None]:
    bundle.mkdir(parents=True, exist_ok=True)
    lock_path = bundle / ".task-workflow.lock"
    try:
        fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ValueError(
            "another task Evidence writer holds the completion-bundle lock"
        ) from exc
    try:
        os.close(fd)
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def _initial_evidence(manifest: dict) -> dict:
    return {
        "version": 1,
        "task_id": manifest["task_id"],
        "task": manifest["task"],
        "risk_level": manifest["risk_level"],
        "task_contract_sha256": manifest["contract_sha256"],
        "claims": [],
        "limitations": [],
    }


def _existing_evidence(path: pathlib.Path, manifest: dict) -> dict:
    if path.is_symlink():
        raise ValueError("Evidence file must not be a symlink")
    if not path.exists():
        return _initial_evidence(manifest)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Evidence file must contain an object")
    errors = validate_evidence(data)
    if errors:
        raise ValueError("invalid existing Evidence: " + "; ".join(errors))
    for key, value in (
        ("task_id", manifest["task_id"]),
        ("task", manifest["task"]),
        ("risk_level", manifest["risk_level"]),
        ("task_contract_sha256", manifest["contract_sha256"]),
    ):
        if data.get(key) != value:
            raise ValueError(f"existing Evidence has stale/mismatched {key}")
    ids = [claim["id"] for claim in data["claims"]]
    if len(ids) != len(set(ids)):
        raise ValueError("existing Evidence has duplicate claim IDs")
    return data


def _write_new_json(path: pathlib.Path, data: dict) -> bool:
    """Create a draft only if absent; never replace user-edited review files."""
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        return True
    except FileExistsError:
        return False


def draft(args) -> int:
    try:
        manifest, _, bundle = _prepared(args.task_id)
        with _exclusive_bundle(bundle):
            evidence_path = bundle / "evidence.json"
            # Existing Evidence is never clobbered, and invalid Evidence is
            # not silently treated as an absent source.
            _existing_evidence(evidence_path, manifest)
            created = []
            evidence = _initial_evidence(manifest)
            convergence = {
                "version": 1,
                "task_id": args.task_id,
                "change": manifest["task"],
                "owner_summary": "Review pending; no semantic alignment claimed.",
                "context_sha256": manifest["context_sha256"],
                "evidence": [],
                "coverage": [],
                "change_coverage": [],
                "findings": [{
                    "classification": "partial",
                    "severity": "medium",
                    "subject": "Convergence review not yet performed",
                    "observed": "The task is awaiting semantic review.",
                    "expected": "Explicitly review relevant knowledge and task changes.",
                    "authority": "Prepared Task Contract and Context",
                    "evidence": ["Prepared Task Context"],
                    "recommended_action": "Replace draft findings and provide verified coverage.",
                }],
            }
            owner = {
                "version": 1,
                "task_id": args.task_id,
                "status": "partial",
                "summary": "Task completion has not been established.",
                "before": "Not yet reviewed.",
                "after": "Not yet verified.",
                "verification": [],
                "consistency": {
                    "status": "needs-reconciliation",
                    "summary": "Review Convergence and Evidence before completion.",
                },
                "owner_decisions": [],
            }
            for filename, value in (
                ("evidence.json", evidence),
                ("convergence.json", convergence),
                ("owner-report.json", owner),
            ):
                if _write_new_json(bundle / filename, value):
                    created.append(filename)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"PACT task draft: {exc}", file=sys.stderr)
        return 2

    result = {
        "task_id": args.task_id,
        "bundle": bundle.relative_to(ROOT).as_posix(),
        "created": created,
        "requires_semantic_review": True,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"PACT task draft: {args.task_id} ({', '.join(created) or 'unchanged'})")
        print("Review required: Evidence does not establish all acceptance or alignment.")
    return 0


def verify(args) -> int:
    command = list(args.verification_command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("PACT task verify: verification command required after --", file=sys.stderr)
        return 2
    if not args.claim.strip():
        print("PACT task verify: --claim cannot be blank", file=sys.stderr)
        return 2

    try:
        manifest, contract, bundle = _prepared(args.task_id)
        allowed = {item["id"] for item in contract["acceptance_criteria"]}
        criteria = list(args.criteria)
        if len(criteria) != len(set(criteria)) or not set(criteria) <= allowed:
            raise ValueError("criterion IDs must be distinct and exist in the Task Contract")
        claim_id = args.claim_id
        if claim_id is not None and not CLAIM_ID_PATTERN.fullmatch(claim_id):
            raise ValueError("invalid --claim-id (expected EV-... stable ID)")

        # Fail before executing if earlier Evidence is corrupt or belongs to
        # a different task/contract. A successful run must not launder it.
        _existing_evidence(bundle / "evidence.json", manifest)
        run_dir = confined_child(RUN_ROOT, args.task_id, repository_root=ROOT)
        run_dir.mkdir(parents=True, exist_ok=True)
        receipt_path = run_dir / f"verify-{uuid.uuid4().hex}.json"

        with _exclusive_bundle(bundle):
            evidence_path = bundle / "evidence.json"
            data = _existing_evidence(evidence_path, manifest)
            used_ids = {item["id"] for item in data["claims"]}
            if claim_id is not None and claim_id in used_ids:
                raise ValueError(f"Evidence claim ID already exists: {claim_id}")
            if claim_id is None:
                counter = 1
                while f"EV-VERIFY-{counter}" in used_ids:
                    counter += 1
                claim_id = f"EV-VERIFY-{counter}"

            run_args = [
                "--task-id", args.task_id,
                "--cwd", str(ROOT),
                "--output", str(receipt_path),
                "--quiet",
            ]
            for source in args.sources:
                run_args.extend(["--source", source])
            if args.allow_external_inputs:
                run_args.append("--allow-external-inputs")
            proc = subprocess.run(
                runtime_command("run", *run_args, "--", *command),
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            if not receipt_path.is_file():
                raise ValueError(
                    "pact run produced no validated receipt; "
                    + (proc.stderr.strip() or "verification did not complete")
                )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if (
                receipt.get("task_id") != args.task_id
                or receipt.get("exit_code") != proc.returncode
                or receipt.get("status") not in {"pass", "fail"}
            ):
                raise ValueError("verification receipt does not match executed command")
            data["claims"].append({
                "id": claim_id,
                "claim": args.claim,
                "required": True,
                "status": receipt["status"],
                "criteria": criteria,
                "evidence": [{
                    "kind": args.kind,
                    "provenance": "pact-run",
                    "ref": receipt_path.relative_to(ROOT).as_posix(),
                }],
            })
            errors = validate_evidence(data)
            if errors:
                raise ValueError("generated invalid Evidence: " + "; ".join(errors))
            write_json(evidence_path, data)

    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"PACT task verify: {exc}", file=sys.stderr)
        return 2

    result = {
        "task_id": args.task_id,
        "claim_id": claim_id,
        "criteria": criteria,
        "claim": args.claim,
        "status": receipt["status"],
        "exit_code": receipt["exit_code"],
        "run_receipt": receipt_path.relative_to(ROOT).as_posix(),
        "evidence": evidence_path.relative_to(ROOT).as_posix(),
        "requires_semantic_review": True,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"PACT task verify: {receipt['status']} ({claim_id}); "
            "acceptance/convergence still require semantic review"
        )
    return proc.returncode
