"""Minimal local checkpoint and read-only cross-session task recovery.

Narrative text is *untrusted Agent-supplied context*, never confirmed Product
Truth, an Evidence Claim, a verified task status, or a command to execute.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
from datetime import datetime, timezone

from evidence import provenance_review
from protocol_ids import (
    confined_child, confined_repository_path, validate_task_id,
)
from schema_validate import load_schema, validate_instance
from task import (
    ROOT, TASK_ROOT, read_task_manifest, read_status_contract,
    validate_finish_manifest, write_json,
)
from task_workflow import _exclusive_bundle, _existing_evidence, _prepared
from workspace import task_changed_files, workspace_snapshot


MAX_ENTRIES = 24
MAX_TEXT_ITEMS = 8
MAX_TEXT_LENGTH = 400
MAX_DOCUMENT_BYTES = 96 * 1024
MAX_REFS = 8
CLAIM_ID = re.compile(r"^EV-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
RUN_SCHEMA = ROOT / ".pact" / "schema" / "run-receipt.schema.json"


def _task_dir_manifest(task_id: str) -> tuple[pathlib.Path, dict]:
    validate_task_id(task_id)
    folder = confined_child(TASK_ROOT, task_id, repository_root=ROOT)
    manifest = read_task_manifest(folder / "task.json")
    if manifest.get("task_id") != task_id:
        raise ValueError("Task Manifest ID mismatch")
    if manifest.get("status") not in {"prepared", "completed"}:
        raise ValueError("task is not prepared or completed")
    return folder, manifest


def _text_items(items: list[str], label: str) -> list[str]:
    if len(items) > MAX_TEXT_ITEMS:
        raise ValueError(f"{label} exceeds {MAX_TEXT_ITEMS} items")
    cleaned: list[str] = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{label} items must be nonblank strings")
        if len(item) > MAX_TEXT_LENGTH or any(
            ord(char) < 32 and char not in "\t" for char in item
        ):
            raise ValueError(f"{label} text is too long or contains control characters")
        cleaned.append(item.strip())
    return cleaned


def _file_sha(path: pathlib.Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"handoff reference is not a regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reference(relative: str, prefix: tuple[str, ...], suffix: str) -> dict:
    if not isinstance(relative, str) or not relative:
        raise ValueError("handoff reference must be a repository-relative path")
    raw = pathlib.PurePosixPath(relative)
    if raw.is_absolute() or ".." in raw.parts or "\\" in relative:
        raise ValueError(f"unsafe handoff reference {relative!r}")
    if tuple(raw.parts[:len(prefix)]) != prefix or not raw.name.endswith(suffix):
        raise ValueError(f"handoff reference outside expected kind: {relative!r}")
    # confined_repository_path resolves aliases; inspect the unreduced path
    # *first* so a symlink to another in-root file does not become trusted
    # merely because its resolved digest matches.
    root = ROOT.resolve()
    candidate = root / raw.as_posix()
    current = candidate
    while current != root:
        if current.is_symlink():
            raise ValueError(f"handoff reference must not traverse a symlink: {relative!r}")
        current = current.parent
    path = confined_repository_path(ROOT, relative, field="handoff reference")
    return {"path": raw.as_posix(), "sha256": _file_sha(path)}


def _validated_checkpoint_refs(task_id: str, args, evidence: dict) -> tuple[list, list, list]:
    decision_paths = args.decision or []
    receipt_paths = args.receipt or []
    claim_ids = args.claim_ids or []
    if max(len(decision_paths), len(receipt_paths), len(claim_ids)) > MAX_REFS:
        raise ValueError("too many handoff references (max eight of each)")
    available_claim_ids = {claim["id"] for claim in evidence["claims"]}
    if any(not CLAIM_ID.fullmatch(claim_id) or claim_id not in available_claim_ids
           for claim_id in claim_ids):
        raise ValueError("handoff Claim ID must exist in current Evidence")
    decision_refs = [
        _reference(path, (".agents", "decisions"), ".md")
        for path in decision_paths
    ]
    run_refs = []
    for relative in receipt_paths:
        info = _reference(relative, (".pact", "runs", task_id), ".json")
        receipt_path = confined_repository_path(ROOT, info["path"], field="run receipt")
        data = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("handoff run receipt is not a JSON object")
        errors = validate_instance(data, load_schema(RUN_SCHEMA))
        if errors:
            raise ValueError("invalid run receipt: " + "; ".join(errors))
        if data["task_id"] != task_id:
            raise ValueError("run receipt belongs to a different task")
        run_refs.append(info)
    return decision_refs, run_refs, list(dict.fromkeys(claim_ids))


def _read_handoff(path: pathlib.Path, task_id: str) -> dict:
    if path.is_symlink():
        raise ValueError("handoff state must not be a symlink")
    if not path.exists():
        return {
            "version": 1, "task_id": task_id,
            "contract_sha256": None, "context_sha256": None, "entries": [],
        }
    if path.stat().st_size > MAX_DOCUMENT_BYTES:
        raise ValueError("handoff file is too large")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1 or data.get("task_id") != task_id:
        raise ValueError("handoff version/identity mismatch")
    entries = data.get("entries")
    if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
        raise ValueError("handoff entries are malformed or oversized")
    expected_keys = {
        "created_at", "done", "todo", "assumptions", "decision_refs",
        "run_refs", "claim_ids",
    }
    for item in entries:
        if not isinstance(item, dict) or set(item) != expected_keys:
            raise ValueError("handoff entry contains malformed fields")
        for key in ("done", "todo", "assumptions"):
            if not isinstance(item[key], list):
                raise ValueError(f"handoff {key} must be a list")
            _text_items(item[key], key)
        for key in ("decision_refs", "run_refs"):
            if (not isinstance(item[key], list) or len(item[key]) > MAX_REFS
                    or any(not isinstance(ref, dict)
                           or set(ref) != {"path", "sha256"}
                           or not isinstance(ref["path"], str)
                           or not isinstance(ref["sha256"], str)
                           or not re.fullmatch("[a-f0-9]{64}", ref["sha256"])
                           for ref in item[key])):
                raise ValueError(f"handoff {key} references malformed")
        if (not isinstance(item["claim_ids"], list)
                or len(item["claim_ids"]) > MAX_REFS
                or any(not isinstance(x, str) or not CLAIM_ID.fullmatch(x)
                       for x in item["claim_ids"])):
            raise ValueError("handoff Claim IDs malformed")
        if not isinstance(item["created_at"], str) or len(item["created_at"]) > 40:
            raise ValueError("handoff timestamp malformed")
    return data


def checkpoint(args) -> int:
    try:
        manifest, _, bundle = _prepared(args.task_id)
        with _exclusive_bundle(bundle):
            manifest, _, _ = _prepared(args.task_id)
            folder, _ = _task_dir_manifest(args.task_id)
            evidence = _existing_evidence(bundle / "evidence.json", manifest)
            decision_refs, run_refs, claim_ids = _validated_checkpoint_refs(
                args.task_id, args, evidence
            )
            entry = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "done": _text_items(args.done or [], "done"),
                "todo": _text_items(args.todo or [], "todo"),
                "assumptions": _text_items(args.assumption or [], "assumptions"),
                "decision_refs": decision_refs,
                "run_refs": run_refs,
                "claim_ids": claim_ids,
            }
            if not any(entry[key] for key in (
                "done", "todo", "assumptions", "decision_refs", "run_refs", "claim_ids"
            )):
                raise ValueError("empty checkpoint is not useful")
            path = folder / "handoff.json"
            handoff = _read_handoff(path, args.task_id)
            if handoff["entries"] and (
                handoff["contract_sha256"] != manifest["contract_sha256"]
                or handoff["context_sha256"] != manifest["context_sha256"]
            ):
                raise ValueError("stale handoff Contract/Context binding")
            if len(handoff["entries"]) >= MAX_ENTRIES:
                raise ValueError("handoff is at its bounded entry limit")
            handoff["contract_sha256"] = manifest["contract_sha256"]
            handoff["context_sha256"] = manifest["context_sha256"]
            handoff["entries"].append(entry)
            write_json(path, handoff)
        result = {
            "task_id": args.task_id, "checkpoint_count": len(handoff["entries"]),
            "untrusted_agent_narrative": True,
            "owner_completed_automatically": False,
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"PACT task checkpoint: {args.task_id} ({result['checkpoint_count']})")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"PACT task checkpoint: {exc}", file=sys.stderr)
        return 2


def resume(args) -> int:
    """Pure read/verify; never invokes commands stored in a handoff."""
    try:
        folder, manifest = _task_dir_manifest(args.task_id)
        handoff = _read_handoff(folder / "handoff.json", args.task_id)
        warnings = list(validate_finish_manifest(manifest, root=ROOT))
        if handoff["entries"] and (
            handoff["contract_sha256"] != manifest.get("contract_sha256")
            or handoff["context_sha256"] != manifest.get("context_sha256")
        ):
            warnings.append("handoff was bound to a different prepared Contract/Context")
        contract = None
        try:
            contract_path = confined_repository_path(
                ROOT, manifest["contract"], field="contract"
            )
            contract = read_status_contract(contract_path)
        except (OSError, ValueError, KeyError) as exc:
            warnings.append(f"cannot read prepared Contract: {exc}")
        try:
            change = task_changed_files(ROOT, manifest["workspace_baseline"])
        except (OSError, ValueError, KeyError) as exc:
            change = {"supported": False, "reason": str(exc), "changed_files": []}
            warnings.append("cannot verify current task delta")
        try:
            current_workspace = workspace_snapshot(ROOT)
        except Exception as exc:
            current_workspace = None
            warnings.append(f"cannot fingerprint current workspace: {exc}")
        all_claims: list[dict] = []
        evidence_errors: list[str] = []
        try:
            from task import completion_bundle_path
            from task_workflow import _existing_evidence
            bundle = completion_bundle_path(manifest, args.task_id)
            evidence = _existing_evidence(bundle / "evidence.json", manifest)
            all_claims = [
                {"id": c["id"], "status": c["status"],
                 "criteria": c.get("criteria", []),
                 "required": bool(c.get("required"))}
                for c in evidence["claims"]
            ]
            ev_errors, gaps, _ = provenance_review(evidence, ROOT)
            evidence_errors = [*ev_errors, *gaps]
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            evidence_errors = [f"Evidence unreadable/unverified: {exc}"]
        checked_refs = []
        for entry in handoff["entries"]:
            for ref in [*entry["run_refs"], *entry["decision_refs"]]:
                state = "stale-or-missing"
                try:
                    relative = ref["path"]
                    prefix = (
                        (".pact", "runs", args.task_id)
                        if ref in entry["run_refs"]
                        else (".agents", "decisions")
                    )
                    checked = _reference(relative, prefix,
                                         ".json" if prefix[0] == ".pact" else ".md")
                    state = "same-file" if checked["sha256"] == ref["sha256"] else "changed"
                    if prefix[0] == ".pact" and current_workspace is not None:
                        candidate = confined_repository_path(ROOT, relative, field="run receipt")
                        record = json.loads(candidate.read_text(encoding="utf-8"))
                        if (record.get("workspace_after", {}).get("sha256")
                                != current_workspace.get("sha256")
                                or record.get("workspace_changed")):
                            state = "stale-reverify"
                except (OSError, ValueError, KeyError, json.JSONDecodeError):
                    pass
                checked_refs.append({"path": ref["path"], "state": state})
        if evidence_errors:
            warnings.append("stale or invalid Evidence must be reverified")
        if not change.get("supported"):
            warnings.append("exact Git changed-file attribution unavailable")
        result = {
            "task_id": args.task_id,
            "prepared_status": manifest["status"],
            "prepared_contract_valid": not warnings or not any(
                "contract" in item.lower() or "context" in item.lower()
                for item in warnings
            ),
            "task_intent": contract.get("intent") if contract else None,
            "acceptance_criteria": contract.get("acceptance_criteria", []) if contract else [],
            "contract_sha256": manifest.get("contract_sha256"),
            "context_sha256": manifest.get("context_sha256"),
            "task_delta": change,
            "evidence_claims": all_claims,
            "evidence_errors": evidence_errors,
            "checkpoint_entries": handoff["entries"],
            "handoff_references": checked_refs,
            "untrusted_agent_narrative": True,
            "reexamine_decision_premises": True,
            "warnings": warnings,
            "recommended_next": (
                "Reverify stale inputs and task Evidence; review assertions and "
                "Decision premises; perform semantic Convergence before finish"
            ),
            "owner_completed_automatically": False,
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"PACT task resume: {args.task_id}")
            print(f"- checkpoints: {len(handoff['entries'])}")
            print(f"- evidence issues: {len(evidence_errors)}")
            print(f"- warnings: {len(warnings)}")
            print("- untrusted narrative; no completion inferred")
        return 0 if not warnings else 1
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"PACT task resume: {exc}", file=sys.stderr)
        return 2
