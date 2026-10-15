"""Read-only task completion diagnostics and deliberately minimal evidence export.

No semantic completion, automatic owner approval, or task-state transitions live
here. Mechanical Owner fields are copied only from valid explicit AC/Claim links.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import tempfile
import re
import sys

from converge import validate as validate_convergence
from evidence import (
    provenance_review, resolve_ref as resolve_evidence_ref,
)
from protocol_ids import (
    confined_child, confined_repository_path, confined_state_root,
    validate_task_id,
)
from report import OWNER_SCHEMA, validate as validate_owner
from task import (
    ROOT, TASK_ROOT, completion_bundle_path, read_status_contract,
    read_task_manifest, validate_finish_manifest, write_json,
)
from task_workflow import (
    RUN_ROOT, _existing_evidence, _exclusive_bundle, _prepared,
)
from workspace import task_changed_files


EXPORT_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}\.json$")


def checked_json(path: pathlib.Path, label: str) -> dict | None:
    """Read an existing JSON object but never follow a leaf symlink."""
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a JSON object")
    return data


def _review_sources(task_id: str):
    manifest, contract, bundle = _prepared(task_id)
    context_file = confined_repository_path(ROOT, manifest["context"], field="context")
    context = checked_json(context_file, "prepared Task Context")
    if context is None:
        raise ValueError("prepared Task Context is missing")
    evidence = _existing_evidence(bundle / "evidence.json", manifest)
    convergence = checked_json(bundle / "convergence.json", "Convergence")
    owner = checked_json(bundle / "owner-report.json", "Owner Report")
    if convergence is not None:
        errors = validate_convergence(convergence)
        if errors:
            raise ValueError("invalid Convergence: " + "; ".join(errors))
    if owner is not None:
        errors = validate_owner(owner, OWNER_SCHEMA, "owner")
        if errors:
            raise ValueError("invalid Owner Report: " + "; ".join(errors))
    return manifest, contract, context, bundle, evidence, convergence, owner


def _diagnose(
    manifest: dict, contract: dict, context: dict, evidence: dict,
    convergence: dict | None, owner: dict | None, task_change: dict,
    provenance_errors: list[str], policy_gaps: list[str],
) -> dict:
    """Explain mechanically missing evidence; no product inference."""
    criteria = contract["acceptance_criteria"]
    passing_claims = [
        claim for claim in evidence["claims"]
        if claim.get("required") and claim.get("status") == "pass"
    ]
    eligible = not provenance_errors and not policy_gaps
    by_criterion = {
        item["id"]: [claim for claim in passing_claims
                     if item["id"] in claim.get("criteria", [])]
        if eligible else []
        for item in criteria
    }
    uncovered_ac = [
        item["id"] for item in criteria if not by_criterion[item["id"]]
    ]
    covered_context = {
        item.get("path") for item in (convergence or {}).get("coverage", [])
        if isinstance(item, dict)
    }
    missed_knowledge = [
        item["path"] for item in context.get("artifacts", [])
        if item.get("path") not in covered_context
    ]
    changed = task_change.get("changed_files", [])
    change_covered = {
        item.get("path")
        for item in (convergence or {}).get("change_coverage", [])
        if isinstance(item, dict)
    }
    missed_changes = (
        [path for path in changed if path not in change_covered]
        if task_change.get("supported") else []
    )
    owner_criteria = {
        item.get("criterion_id")
        for item in (owner or {}).get("acceptance", [])
    }
    unreported = [
        item["id"] for item in criteria
        if item["id"] not in owner_criteria
    ]
    verification_draft = [
        {"claim": claim["claim"], "evidence_ids": [claim["id"]]}
        for claim in passing_claims
    ] if eligible else []
    acceptance_draft = [
        {
            "criterion_id": item["id"], "summary": item["text"],
            "evidence_ids": [claim["id"] for claim in by_criterion[item["id"]]],
        }
        for item in criteria if by_criterion[item["id"]]
    ]
    return {
        "task_id": manifest["task_id"],
        "status": manifest["status"],
        "risk_level": manifest["risk_level"],
        "contract_sha256": manifest["contract_sha256"],
        "context_sha256": manifest["context_sha256"],
        "unverified_criteria": uncovered_ac,
        "missing_context_coverage": missed_knowledge,
        "missing_change_coverage": missed_changes,
        "change_attribution_supported": bool(task_change.get("supported")),
        "change_attribution_unknown": task_change.get("reason")
            if not task_change.get("supported") else None,
        "owner_acceptance_unreported": unreported,
        "missing_completion_files": [
            name for name, obj in (
                ("convergence.json", convergence), ("owner-report.json", owner)
            ) if obj is None
        ],
        "provenance_errors": provenance_errors,
        "policy_gaps": policy_gaps,
        "safe_mechanical_verification": verification_draft,
        "safe_mechanical_acceptance": acceptance_draft,
        "requires_semantic_review": True,
        "owner_completed_automatically": False,
    }


def _snapshot(task_id: str):
    state = _review_sources(task_id)
    manifest, contract, context, bundle, evidence, convergence, owner = state
    errors, gaps, _ = provenance_review(evidence, ROOT)
    task_change = task_changed_files(ROOT, manifest["workspace_baseline"])
    diagnosis = _diagnose(
        manifest, contract, context, evidence, convergence, owner, task_change,
        errors, gaps,
    )
    return diagnosis, bundle, owner


def assist(args) -> int:
    try:
        result, bundle, owner = _snapshot(args.task_id)
        result["draft_written"] = False
        if args.write_draft:
            # Entire re-read under the existing task Evidence lock to prevent
            # laundering concurrent changes between evaluation and publication.
            with _exclusive_bundle(bundle):
                result, _, owner = _snapshot(args.task_id)
                result["draft_written"] = False
                if owner is None:
                    raise ValueError("run 'task draft' before --write-draft")
                if owner.get("status") != "partial":
                    raise ValueError("automatic fields require a partial Owner draft")
                if result["provenance_errors"] or result["policy_gaps"]:
                    raise ValueError("cannot fill Owner from invalid/stale Evidence")
                owner_path = bundle / "owner-report.json"
                # Do not overwrite human/Agent-authored content in either array.
                changed = False
                if not owner.get("verification") and result["safe_mechanical_verification"]:
                    owner["verification"] = result["safe_mechanical_verification"]
                    changed = True
                if not owner.get("acceptance") and result["safe_mechanical_acceptance"]:
                    owner["acceptance"] = result["safe_mechanical_acceptance"]
                    changed = True
                if changed:
                    validation = validate_owner(owner, OWNER_SCHEMA, "owner")
                    if validation:
                        raise ValueError("generated invalid Owner draft: " + "; ".join(validation))
                    write_json(owner_path, owner)
                result["draft_written"] = changed
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"PACT task assist: {args.task_id}")
            print(f"- unverified ACs: {', '.join(result['unverified_criteria']) or 'none'}")
            print(f"- missing Context coverage: {len(result['missing_context_coverage'])}")
            print(f"- missing changed-file coverage: {len(result['missing_change_coverage'])}")
            print(f"- policy gaps: {len(result['policy_gaps'])}")
            print("- semantic review required before task finish")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"PACT task assist: {exc}", file=sys.stderr)
        return 2


def _export_prepared_or_completed(task_id: str):
    validate_task_id(task_id)
    task_dir = confined_child(TASK_ROOT, task_id, repository_root=ROOT)
    manifest = read_task_manifest(task_dir / "task.json")
    if manifest.get("task_id") != task_id:
        raise ValueError("task manifest ID mismatch")
    if manifest.get("status") not in {"prepared", "completed"}:
        raise ValueError("task is not prepared or completed")
    preflight = validate_finish_manifest(manifest, root=ROOT)
    if preflight:
        raise ValueError("invalid prepared task: " + "; ".join(preflight))
    contract_path = confined_repository_path(ROOT, manifest["contract"], field="contract")
    read_status_contract(contract_path)
    bundle = completion_bundle_path(manifest, task_id)
    confined_state_root(ROOT, bundle, field="completion bundle")
    evidence = _existing_evidence(bundle / "evidence.json", manifest)
    return manifest, evidence, bundle


def export(args) -> int:
    """Export auditable, currently valid metadata without elevating its trust."""
    try:
        if not EXPORT_FILENAME.fullmatch(args.filename):
            raise ValueError("--filename must be a single safe .json basename")
        # State paths must belong to this PACT project; no arbitrary output path.
        manifest, _, bundle = _export_prepared_or_completed(args.task_id)
        run_root = RUN_ROOT
        confined_state_root(ROOT, run_root, field="run evidence")
        output_dir = confined_child(run_root, args.task_id, repository_root=ROOT)
        confined_state_root(ROOT, output_dir, field="task run evidence")

        # Hold the same bundle lock as task verify/checkpoint while re-reading
        # Evidence and the workspace. Do not publish a pre-lock stale snapshot.
        with _exclusive_bundle(bundle):
            manifest, evidence, checked_bundle = _export_prepared_or_completed(args.task_id)
            if checked_bundle != bundle:
                raise ValueError("completion bundle changed during evidence export")
            errors, gaps, stats = provenance_review(evidence, ROOT)
            if errors or gaps:
                raise ValueError("invalid/stale Evidence cannot be exported: "
                                 + "; ".join([*errors, *gaps]))

            claims = []
            for claim in evidence["claims"]:
                if claim.get("status") != "pass":
                    continue
                receipts = []
                for item in claim.get("evidence", []):
                    if item.get("provenance") != "pact-run":
                        continue
                    relative = pathlib.PurePosixPath(item["ref"])
                    if relative.is_absolute() or ".." in relative.parts:
                        raise ValueError("export receipt reference is unsafe")
                    unresolved = ROOT / relative.as_posix()
                    if unresolved.is_symlink():
                        raise ValueError("export run receipt must not be a symlink")
                    receipt_path = resolve_evidence_ref(ROOT, item["ref"])
                    if not receipt_path.is_file():
                        raise ValueError("export run receipt is missing")
                    receipts.append({
                        "kind": item["kind"],
                        "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                    })
                if receipts:
                    claims.append({
                        "claim_id": claim["id"],
                        "required": bool(claim.get("required")),
                        "receipts": receipts,
                        "criteria": list(claim.get("criteria", [])),
                    })
            if not claims:
                raise ValueError("no valid passing pact-run receipts to export")

            exported = {
                "version": 1,
                "task_id": args.task_id,
                "risk_level": manifest["risk_level"],
                "task_contract_sha256": manifest["contract_sha256"],
                "task_context_sha256": manifest["context_sha256"],
                "current_workspace_sha256": stats["current_workspace"]["sha256"],
                "passing_execution_claims": claims,
                "completion_attestation": False,
                "note": "Audit-only metadata; does not confer semantic completion or portable replay",
            }
            output_dir.mkdir(parents=True, exist_ok=True)
            destination = output_dir / args.filename
            if destination.exists() or destination.is_symlink():
                raise ValueError("export destination already exists; choose a new basename")

            # Durable temp + atomic hard-link publication gives no-overwrite
            # semantics even if another writer creates this basename after
            # checking. A half-written file never appears under the final name.
            payload = json.dumps(exported, ensure_ascii=False, indent=2) + "\n"
            fd, staged = tempfile.mkstemp(
                prefix=f".{args.filename}.pact-export-",
                suffix=".tmp", dir=output_dir,
            )
            temporary = pathlib.Path(staged)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                try:
                    os.link(temporary, destination)
                except FileExistsError as exc:
                    raise ValueError("export destination was created concurrently") from exc
            finally:
                temporary.unlink(missing_ok=True)

        result = {
            "task_id": args.task_id,
            "output": destination.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "completion_attestation": False,
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"PACT task export: {result['output']} (audit metadata only)")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"PACT task export: {exc}", file=sys.stderr)
        return 2
