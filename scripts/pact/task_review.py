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

OWNER_AUTOGEN_MARKER = ".pact-assist-generated.json"
OWNER_AUTOGEN_MAX_BYTES = 128 * 1024


def owner_payload_sha256(owner: dict) -> str:
    """Match task.write_json's exact on-disk byte serialization."""
    payload = json.dumps(owner, ensure_ascii=False, indent=2) + "\n"
    # task.write_json opens a UTF-8 *text* stream with newline=None: Windows
    # translates the formatting LF bytes to CRLF on disk. Bind the marker to
    # those actual persisted bytes, not to an LF-only in-memory serialization.
    return hashlib.sha256(payload.replace("\n", os.linesep).encode("utf-8")).hexdigest()


def generated_owner_marker(bundle: pathlib.Path, task_id: str) -> dict | None:
    path = bundle / OWNER_AUTOGEN_MARKER
    if path.exists() and path.stat().st_size > OWNER_AUTOGEN_MAX_BYTES:
        raise ValueError("generated Owner marker exceeds size bound")
    data = checked_json(path, "generated Owner acceptance provenance")
    if data is None:
        return None
    if (
        data.get("version") != 1
        or data.get("task_id") != task_id
        or not isinstance(data.get("owner_sha256"), str)
        or not re.fullmatch(r"[a-f0-9]{64}", data["owner_sha256"])
        or not isinstance(data.get("generated_acceptance"), list)
    ):
        raise ValueError("generated Owner acceptance provenance is invalid")
    return data


def owner_marker_matches(
    marker: dict | None,
    owner: dict,
    *,
    sha256: str,
) -> bool:
    return bool(
        marker
        and marker["owner_sha256"] == sha256
        and marker["generated_acceptance"] == owner.get("acceptance", [])
    )


def publish_generated_owner(
    bundle: pathlib.Path,
    owner: dict,
    *,
    task_id: str,
    generated_acceptance: bool,
) -> None:
    """Record tool ownership first, then publish Owner. Fail closed on partial writes."""
    if generated_acceptance:
        write_json(
            bundle / OWNER_AUTOGEN_MARKER,
            {
                "version": 1,
                "task_id": task_id,
                "owner_sha256": owner_payload_sha256(owner),
                "generated_acceptance": owner.get("acceptance", []),
            },
        )
    write_json(bundle / "owner-report.json", owner)



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
    scope = context.get("scope_route")
    unique_scope = isinstance(scope, dict) and scope.get("status") == "unique"
    materialized = {
        item["path"] for item in context.get("artifacts", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    routed_domain_paths = [
        item["path"] for item in (scope.get("domains", []) if unique_scope else [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    missing_scoped_domain_artifacts = sorted(
        set(routed_domain_paths) - materialized
    )
    scope_integrity_gaps = [
        f"Domain-first routed Domain absent from prepared Context: {path!r}; "
        "reprepare with the Domain materialized"
        for path in missing_scoped_domain_artifacts
    ]
    if unique_scope and not routed_domain_paths:
        scope_integrity_gaps.append(
            "Domain-first unique route has no recorded Domain; reprepare task"
        )
    if unique_scope:
        candidates = scope.get("candidates")
        total = scope.get("total_candidates")
        truncated = scope.get("truncated_candidates")
        # Match the hard Convergence gate, not just the 12 visible hints.
        # A truncated or inconsistent list cannot justify a completion-ready
        # draft even when every listed candidate has Convergence coverage.
        if (
            not isinstance(candidates, list)
            or type(total) is not int
            or type(truncated) is not int
            or truncated != 0
            or total != len(candidates)
        ):
            scope_integrity_gaps.append(
                "Domain-first route has unlisted or inconsistent authority "
                "candidates; review the complete Domain sources and reprepare "
                "without --scope-first before task assist can draft acceptance"
            )
    # A deferred Decision is not applicable authority by lexical score alone,
    # but its original source must be checked before Owner acceptance drafts.
    # Reuse the same full source binding checks for explicit and default hints.
    deferred_decision_paths: list[str] = []
    deferred_integrity_gaps: list[str] = []
    hint_sets = (
        ("nonfunctional_decision_hints", "Nonfunctional", "without --nonfunctional"),
        ("weak_decision_hints", "Weak lexical", "with --full-decisions"),
    )
    observed_paths: set[str] = set()
    covered_hints = {
        item.get("path")
        for item in (convergence or {}).get("coverage", [])
        if isinstance(item, dict)
    }
    for field, label, rerun in hint_sets:
        payload = context.get(field)
        if payload is None:
            continue
        items = payload.get("candidates") if isinstance(payload, dict) else None
        total = payload.get("total_candidates") if isinstance(payload, dict) else None
        truncated = payload.get("truncated_candidates") if isinstance(payload, dict) else None
        if (
            not isinstance(items, list)
            or type(total) is not int or type(truncated) is not int
            or total < 0 or truncated < 0 or truncated > 0
            or total != len(items) or len(items) > 5
        ):
            deferred_integrity_gaps.append(
                f"{label} Context has unlisted or inconsistent Decision "
                f"candidates; reprepare {rerun} before drafting Owner acceptance"
            )
        if not isinstance(items, list):
            continue
        group_paths: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                deferred_integrity_gaps.append(f"{label} Decision hint is malformed")
                continue
            path, sha, ident = (
                item.get("path"), item.get("sha256"), item.get("id")
            )
            if (
                not isinstance(path, str) or not path
                or not isinstance(ident, str) or not ident.startswith("DEC-")
                or not isinstance(sha, str) or len(sha) != 64
                or any(c not in "0123456789abcdef" for c in sha)
                or path in observed_paths
            ):
                deferred_integrity_gaps.append(
                    f"{label} Decision hint has invalid source/identity"
                )
                continue
            observed_paths.add(path)
            group_paths.append(path)
            deferred_decision_paths.append(path)
            try:
                source = (ROOT / path).resolve()
                source.relative_to(ROOT.resolve())
                if (
                    (ROOT / path).is_symlink() or not source.is_file()
                    or hashlib.sha256(source.read_bytes()).hexdigest() != sha
                ):
                    raise ValueError("source changed")
            except (ValueError, OSError):
                deferred_integrity_gaps.append(
                    f"{label} Decision source no longer matches "
                    f"prepared Context: {path!r}"
                )
        missing = sorted(set(group_paths) - covered_hints)
        if missing:
            deferred_integrity_gaps.append(
                f"{label} deferred Decision candidates lack explicit "
                "Convergence review: " + ", ".join(missing)
            )
    # Mechanical Owner drafts are still partial, editable work, NOT a
    # completion gate. Keep historical assist diagnostics usable in non-Git
    # projects, while clearly reporting the hard finish blocker separately.
    finish_blocked_by_non_git = (
        not task_change.get("supported")
        and manifest.get("risk_level") in {"medium", "high"}
    )
    effective_policy_gaps = [*policy_gaps, *scope_integrity_gaps, *deferred_integrity_gaps]
    passing_claims = [
        claim for claim in evidence["claims"]
        if claim.get("required") and claim.get("status") == "pass"
    ]
    eligible = not provenance_errors and not effective_policy_gaps
    required_nonpass_by_criterion = {
        item["id"]: [
            claim["id"] for claim in evidence["claims"]
            if claim.get("required")
            and claim.get("status") != "pass"
            and item["id"] in claim.get("criteria", [])
        ]
        for item in criteria
    }
    # Any unresolved *required* Claim blocks mechanical Owner acceptance for
    # its AC, whether it failed or was never verified. Other independently
    # verified criteria may still be drafted as partial, not completed, work.
    by_criterion = {
        item["id"]: [claim for claim in passing_claims
                     if item["id"] in claim.get("criteria", [])]
        if eligible and not required_nonpass_by_criterion[item["id"]] else []
        for item in criteria
    }
    uncovered_ac = [
        item["id"] for item in criteria if not by_criterion[item["id"]]
    ]
    # Distinguish a known failing explicit Claim from a criterion that was
    # never checked. Neither condition should be described as business PASS.
    criterion_diagnostics = []
    for item in criteria:
        attached = [
            claim for claim in evidence["claims"]
            if item["id"] in claim.get("criteria", [])
        ]
        # Informational passing IDs do not depend on acceptance eligibility:
        # a failed/pending sibling must block Owner acceptance while the
        # genuinely executed successful check remains visible to reviewers.
        verified_ids = [
            claim["id"] for claim in attached
            if claim.get("required") and claim["status"] == "pass"
        ]
        failed_ids = [
            claim["id"] for claim in attached if claim["status"] == "fail"
        ]
        unknown_ids = [
            claim["id"] for claim in attached
            if claim["status"] == "unverified"
        ]
        blocking_fails = [
            claim["id"] for claim in attached
            if claim.get("required") and claim["status"] == "fail"
        ]
        blocking_unknown = [
            claim["id"] for claim in attached
            if claim.get("required") and claim["status"] == "unverified"
        ]
        criterion_diagnostics.append({
            "criterion_id": item["id"],
            "claim_ids": [claim["id"] for claim in attached],
            "execution_pass_claim_ids": verified_ids,
            "failed_claim_ids": failed_ids,
            "blocking_required_failed_claim_ids": blocking_fails,
            "blocking_required_unverified_claim_ids": blocking_unknown,
            "unverified_claim_ids": unknown_ids,
            "status": (
                "failed" if blocking_fails
                else "unverified" if blocking_unknown or not eligible
                else "evidence-pass-awaits-semantic-review" if verified_ids
                else "failed" if failed_ids
                else "unverified"
            ),
        })
    covered_context = {
        item.get("path") for item in (convergence or {}).get("coverage", [])
        if isinstance(item, dict)
    }
    # Match the exact completion gate's Domain-first metadata-only authority
    # coverage, rather than making task assist claim no missing Context while
    # task finish correctly rejects unreviewed linked Rules/Decisions.
    review_paths = [
        item["path"] for item in context.get("artifacts", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    seen_paths = set(review_paths)
    if unique_scope:
        # Show omitted Domain pages even in legacy Context packets. Candidate
        # coverage by itself must not masquerade as a complete scope review.
        for path in routed_domain_paths:
            if path not in seen_paths:
                seen_paths.add(path)
                review_paths.append(path)
        for item in scope.get("candidates", []):
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            if isinstance(path, str) and path not in seen_paths:
                seen_paths.add(path)
                review_paths.append(path)
    for path in deferred_decision_paths:
        if path not in seen_paths:
            seen_paths.add(path)
            review_paths.append(path)
    # Preserve legacy Context artifact ordering when the opt-in route is absent.
    missed_knowledge = [
        path for path in review_paths if path not in covered_context
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
    # Any previously drafted acceptance that has lost its trusted required
    # Evidence is explicitly stale. Do not use it as a completion suggestion.
    allowed = {
        item["id"]: {claim["id"] for claim in by_criterion[item["id"]]}
        for item in criteria
    }
    stale_owner_acceptance = sorted({
        item["criterion_id"]
        for item in (owner or {}).get("acceptance", [])
        if (
            item["criterion_id"] not in allowed
            or not allowed[item["criterion_id"]]
            or not set(item.get("evidence_ids", [])).issubset(
                allowed[item["criterion_id"]]
            )
        )
    })
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
    # The Owner Report v1 schema cannot acquire arbitrary extra fields.
    # Provide exact receipt and SHA traceability separately as read-only
    # diagnostic metadata; it must never be copied into Owner Report arrays
    # or described as a semantic product assertion.
    provenance_for_review = [
        {
            "claim_id": claim["id"],
            "task_id": manifest["task_id"],
            "criterion_ids": list(claim.get("criteria", [])),
            "run_receipt_refs": [
                ref["ref"] for ref in claim.get("evidence", [])
                if ref.get("provenance") == "pact-run"
            ],
            "task_contract_sha256": manifest["contract_sha256"],
            "task_context_sha256": manifest["context_sha256"],
        }
        for claim in passing_claims
    ] if eligible else []
    return {
        "task_id": manifest["task_id"],
        "status": manifest["status"],
        "risk_level": manifest["risk_level"],
        "contract_sha256": manifest["contract_sha256"],
        "context_sha256": manifest["context_sha256"],
        "unverified_criteria": uncovered_ac,
        "criterion_diagnostics": criterion_diagnostics,
        "failed_claim_ids": sorted({
            claim["id"] for claim in evidence["claims"]
            if claim["status"] == "fail"
        }),
        "missing_context_coverage": missed_knowledge,
        "missing_scoped_domain_artifacts": missing_scoped_domain_artifacts,
        "missing_change_coverage": missed_changes,
        "change_attribution_supported": bool(task_change.get("supported")),
        "finish_blocked_by_unsupported_change_attribution": finish_blocked_by_non_git,
        "change_attribution_unknown": task_change.get("reason")
            if not task_change.get("supported") else None,
        "owner_acceptance_unreported": unreported,
        "stale_owner_acceptance_criteria": stale_owner_acceptance,
        "missing_completion_files": [
            name for name, obj in (
                ("convergence.json", convergence), ("owner-report.json", owner)
            ) if obj is None
        ],
        "provenance_errors": provenance_errors,
        "policy_gaps": effective_policy_gaps,
        "safe_mechanical_verification": verification_draft,
        "safe_mechanical_acceptance": acceptance_draft,
        "claim_provenance_for_review": provenance_for_review,
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
            # Finish/verify/draft/checkpoint also take the task primary lock.
            # Re-read under BOTH locks to prevent a completed task from
            # receiving new generated Owner data.
            task_dir = confined_child(TASK_ROOT, args.task_id, repository_root=ROOT)
            with _exclusive_bundle(task_dir), _exclusive_bundle(bundle):
                result, _, owner = _snapshot(args.task_id)
                result["draft_written"] = False
                result["retracted_generated_acceptance"] = []
                if owner is None:
                    raise ValueError("run 'task draft' before --write-draft")
                if owner.get("status") != "partial":
                    raise ValueError("automatic fields require a partial Owner draft")
                owner_path = bundle / "owner-report.json"
                marker = generated_owner_marker(bundle, args.task_id)
                old_owner_hash = hashlib.sha256(owner_path.read_bytes()).hexdigest()
                marker_matches = owner_marker_matches(
                    marker, owner, sha256=old_owner_hash
                )
                stale = result["stale_owner_acceptance_criteria"]
                if stale and not marker_matches:
                    raise ValueError(
                        "Owner acceptance is stale for " + ", ".join(stale)
                        + "; cannot overwrite manually edited or unmarked "
                        "Owner entries; reconcile them by semantic review"
                    )

                changed = False
                generated_acceptance = marker_matches
                if stale:
                    stale_ids = set(stale)
                    owner["acceptance"] = [
                        item for item in owner.get("acceptance", [])
                        if item["criterion_id"] not in stale_ids
                    ]
                    # Retraction of proven generated text is safe even when
                    # current provenance itself is stale. Do not add new
                    # passing claims under that condition.
                    result["retracted_generated_acceptance"] = stale
                    changed = True

                admissible = not (
                    result["provenance_errors"] or result["policy_gaps"]
                )
                if not admissible and not stale:
                    raise ValueError("cannot fill Owner from invalid/stale Evidence")
                if admissible:
                    if (
                        not owner.get("verification")
                        and result["safe_mechanical_verification"]
                    ):
                        owner["verification"] = result["safe_mechanical_verification"]
                        changed = True
                    if (
                        not owner.get("acceptance")
                        and result["safe_mechanical_acceptance"]
                    ):
                        owner["acceptance"] = result["safe_mechanical_acceptance"]
                        generated_acceptance = True
                        changed = True
                if changed:
                    validation = validate_owner(owner, OWNER_SCHEMA, "owner")
                    if validation:
                        raise ValueError(
                            "generated invalid Owner draft: " + "; ".join(validation)
                        )
                    publish_generated_owner(
                        bundle, owner,
                        task_id=args.task_id,
                        generated_acceptance=generated_acceptance,
                    )
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

        # Share the task-level lock with finish, then acquire the existing
        # Evidence-bundle lock in a consistent global order.
        task_dir = confined_child(TASK_ROOT, args.task_id, repository_root=ROOT)
        with _exclusive_bundle(task_dir), _exclusive_bundle(bundle):
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
