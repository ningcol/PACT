#!/usr/bin/env python3
"""M0: PACT-owned installed-runtime decision retrieval A/B diagnostic.

Inputs and author-written oracle were committed BEFORE this runner existed.
This is neither a real Agent nor an independently held-out or Owner trial.
The oracle is read only after BOTH arms have finished for every case.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time


ROOT = pathlib.Path(__file__).resolve().parents[2]
INPUTS = ROOT / "benchmarks" / "decision-memory" / "m0-inputs.json"
ORACLE = ROOT / "benchmarks" / "decision-memory" / "m0-oracle.json"
CASE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
ALLOWED_DOCS = (".agents/decisions/", "docs/product/rules/")


def digest_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_file(root: pathlib.Path, relative: str) -> pathlib.Path:
    path = pathlib.PurePosixPath(relative)
    if (
        not relative or "\\" in relative or path.is_absolute()
        or ".." in path.parts or not all(part not in {"", "."} for part in path.parts)
    ):
        raise ValueError(f"unsafe M0 path {relative!r}")
    result = root / relative
    if not result.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"M0 path escapes local sandbox: {relative!r}")
    if result.is_symlink():
        raise ValueError(f"M0 path must not be a symlink: {relative!r}")
    return result



def staged_source_read_receipt(
    target: pathlib.Path, selected: list[dict], current_ids: list[str],
) -> dict:
    """Measure source-verified downstream first-only vs all-Decision reads.

    The Context-selected ordering is frozen BEFORE any benchmark oracle is
    consulted. Physically inspect *all* selected sources to authenticate the
    counterfactual costs; do not claim this reduces benchmark-runner disk I/O.
    This is not semantic relevance, agent obedience or actual model tokens.
    """
    if (not isinstance(selected, list) or not isinstance(current_ids, list)
            or any(not isinstance(x, str) or not x.startswith("DEC-")
                   for x in current_ids)
            or len(set(current_ids)) != len(current_ids)):
        raise ValueError("staged read requires distinct current Decision IDs")
    current = set(current_ids)
    records: list[dict] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for item in selected:
        if not isinstance(item, dict):
            raise ValueError("staged read contains malformed Context artifact")
        ident = item.get("id")
        if ident not in current:
            continue
        relative = item.get("path")
        digest = item.get("sha256")
        if (item.get("artifact_type") != "decision"
                or not isinstance(relative, str)
                or not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                or ident in seen_ids or relative in seen_paths):
            raise ValueError("staged Decision source identity or digest invalid")
        path = safe_file(target, relative)
        if not path.is_file():
            raise ValueError("staged Decision source is absent")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("staged Decision source changed after Context")
        # This is the exact same file-size-based estimator as installed Context.
        estimate = max((len(data) + 3) // 4, 1)
        supplied_estimate = item.get("estimated_tokens")
        if (supplied_estimate is not None
                and (type(supplied_estimate) is not int
                     or supplied_estimate != estimate)):
            raise ValueError("staged Decision source estimate differs from actual file")
        seen_ids.add(ident)
        seen_paths.add(relative)
        records.append({
            "id": ident, "path": relative, "sha256": digest,
            "read_source_bytes": len(data),
            "estimated_tokens_utf8_bytes_div4": estimate,
        })
    if seen_ids != current:
        raise ValueError("staged Context omitted a current Decision source")
    first = records[0] if records else None
    return {
        "policy": "first-current-Decision-only-vs-all-current-Decisions",
        "selected_current_ids_in_context_order": [x["id"] for x in records],
        "source_digest_verified": True,
        "all_current_source_bytes": sum(x["read_source_bytes"] for x in records),
        "first_only_source_bytes": first["read_source_bytes"] if first else 0,
        "all_current_estimated_tokens": sum(
            x["estimated_tokens_utf8_bytes_div4"] for x in records
        ),
        "first_only_estimated_tokens": (
            first["estimated_tokens_utf8_bytes_div4"] if first else 0
        ),
        "first_only_id": first["id"] if first else None,
        "unread_in_first_only": [x["id"] for x in records[1:]],
        "source_read_receipts": records,
        "model_calls": 0,
        "counterfactual_downstream_exposure_only": True,
    }


def run_json(target: pathlib.Path, command: list[str]) -> dict:
    """Call the INSTALLED pact.py loader, not source scripts or imported scorers."""
    argv = [sys.executable, str(target / "pact.py"), *command]
    begin = time.perf_counter()
    completed = subprocess.run(
        argv, cwd=target, capture_output=True, text=True, timeout=90,
        check=False,
    )
    milliseconds = round((time.perf_counter() - begin) * 1000, 3)
    record = {
        "command": ["pact.py", *command],
        "returncode": completed.returncode,
        "elapsed_ms": milliseconds,
        "stderr": completed.stderr[:2000] if completed.returncode else "",
        "data": None,
    }
    if completed.returncode == 0:
        try:
            record["data"] = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            record["returncode"] = -1
            record["stderr"] = f"installed CLI returned invalid JSON: {exc}"
    else:
        record["stdout_excerpt"] = completed.stdout[:400]
    return record


def _quoted(value: str) -> str:
    """JSON string escaping is compatible with the subset of TOML we emit."""
    return json.dumps(value, ensure_ascii=False)


def _doc_text(doc: dict) -> str:
    attributes = [
        "+++",
        "[pact]",
        "type = " + _quoted(doc["type"]),
        "id = " + _quoted(doc["id"]),
        "status = " + _quoted(doc["status"]),
        "aliases = [" + ", ".join(_quoted(x) for x in doc.get("aliases", [])) + "]",
        "paths = [" + ", ".join(_quoted(x) for x in doc.get("paths", [])) + "]",
        "domains = []",
        "related = []",
        "supersedes = [" + ", ".join(_quoted(x) for x in doc.get("supersedes", [])) + "]",
    ]
    if doc.get("superseded_by"):
        attributes.append("superseded_by = " + _quoted(doc["superseded_by"]))
    return "\n".join([
        *attributes, "+++", "", "# " + doc["title"], "",
        doc["body"], "",
    ])


def validate_inputs(inputs: dict) -> None:
    if inputs.get("version") != 1:
        raise ValueError("unsupported M0 input format")
    cases = inputs.get("cases")
    ids = [case.get("id") for case in cases] if isinstance(cases, list) else []
    if (
        len(ids) != 7
        or len(set(ids)) != len(ids)
        or not all(isinstance(x, str) and CASE_ID.fullmatch(x) for x in ids)
    ):
        raise ValueError("M0 requires seven uniquely named, safe, frozen cases")
    expected_paths = set()
    expected_ids = set()
    for doc in inputs["documents"]:
        relative = doc["path"]
        if not relative.startswith(ALLOWED_DOCS) or relative in expected_paths:
            raise ValueError(f"unsafe or repeated synthetic document {relative!r}")
        expected_paths.add(relative)
        if doc["id"] in expected_ids:
            raise ValueError(f"duplicate synthetic Decision/Rule ID {doc['id']!r}")
        expected_ids.add(doc["id"])
        if doc["type"] not in {"decision", "rule"}:
            raise ValueError("unsupported synthetic authority type")
    for file in inputs["code_files"]:
        if not file["path"].startswith("src/"):
            raise ValueError("synthetic code must stay under src/")
        if len(file["text"]) > 12000:
            raise ValueError("synthetic source exceeds size limit")
        if file["path"] in expected_paths:
            raise ValueError("duplicate synthetic path")
        expected_paths.add(file["path"])
    for case in cases:
        hint = case.get("explicit_decision_hint")
        if hint is not None and hint not in expected_ids:
            raise ValueError(f"unknown caller-provided Decision hint {hint}")
        if not isinstance(case.get("task"), str) or not case["task"].strip():
            raise ValueError(f"empty M0 task text in {case['id']}")
    setup = inputs.get("settings", {})
    if (
        setup.get("intent") != "work"
        or setup.get("knowledge_limit") != 4
        or setup.get("token_budget") != 2048
        or setup.get("risk") != "low"
        or setup.get("code_context") is not False
    ):
        raise ValueError("M0 frozen runtime and budgets were changed")


def install_fixture(target: pathlib.Path, inputs: dict) -> dict:
    target.mkdir(parents=True, exist_ok=False)
    (target / "README.md").write_text("# Disposable PACT M0 synthetic project\n",
                                    encoding="utf-8")
    applied = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "pact" / "init.py"),
         "--target", str(target), "--apply"],
        cwd=ROOT, capture_output=True, text=True, timeout=90, check=False,
    )
    if applied.returncode != 0 or not (target / "pact.py").is_file():
        raise RuntimeError("PACT installation failed: " + applied.stderr[:1200])
    runtime = target / ".pact" / "runtime" / "pact.pyz"
    if not runtime.is_file():
        # Exact install layout is an observed property, not a guess: the
        # installed pyz must exist somewhere in the target.
        archives = list((target / ".pact").rglob("*.pyz"))
        if not archives:
            raise RuntimeError("PACT installed without the expected compact pyz runtime")
        runtime = archives[0]
    for doc in inputs["documents"]:
        file = safe_file(target, doc["path"])
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(_doc_text(doc), encoding="utf-8")
    for entry in inputs["code_files"]:
        file = safe_file(target, entry["path"])
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(entry["text"], encoding="utf-8")
    validated = subprocess.run(
        [sys.executable, str(target / "pact.py"), "check"],
        cwd=target, capture_output=True, text=True, timeout=90, check=False,
    )
    if validated.returncode != 0:
        raise RuntimeError("installed PACT check rejected frozen fixture: "
                           + validated.stdout[:800] + validated.stderr[:1200])
    return {
        "installed_launcher_present": True,
        "compact_archive_present": True,
        "installed_artifact_check_passed": True,
        "compact_runtime_relative": runtime.relative_to(target).as_posix(),
    }


def _arm(target: pathlib.Path, case: dict, setup: dict, arm: str) -> dict:
    task = case["task"]
    hint = case.get("explicit_decision_hint")
    discover = [
        "discover", task, "--limit", str(setup["knowledge_limit"]),
        "--intent", setup["intent"], "--json",
    ]
    context = [
        "context", task, "--success", setup["success"],
        "--risk", setup["risk"], "--intent", setup["intent"],
        "--no-code", "--limit", str(setup["knowledge_limit"]),
        "--token-budget", str(setup["token_budget"]),
    ]
    if arm == "B" and hint:
        discover.extend(["--query", hint])
        # Preserve original task as PRIMARY in Context; the only additional
        # information is the explicitly supplied caller hint.
        context.extend(["--query", task, "--query", hint])
    discovery = run_json(target, discover)
    envelope = run_json(target, context)
    first = discovery["data"] or {}
    packet = envelope["data"] or {}
    artifacts = packet.get("artifacts", [])
    return {
        "discovery": {
            **{k: discovery[k] for k in ("command", "returncode", "elapsed_ms", "stderr")},
            "hits": [
                {"id": entry.get("id"), "status": entry.get("status"),
                 "type": entry.get("artifact_type"), "path": entry.get("path")}
                for entry in first.get("results", [])
            ],
        },
        "context": {
            **{k: envelope[k] for k in ("command", "returncode", "elapsed_ms", "stderr")},
            "status": packet.get("status"),
            "selected_artifact_ids": [
                entry["id"] for entry in artifacts if entry.get("id")
            ],
            "current_decision_ids": packet.get("decisions", []),
            "applicable_rule_ids": packet.get("applicable_rules", []),
            "selected_knowledge_files": len(artifacts),
            "selected_estimated_tokens": packet.get(
                "context_budget", {}
            ).get("selected_estimated_tokens"),
            "authority_candidates_dropped": packet.get(
                "context_budget", {}
            ).get("authority_candidates_dropped"),
            "known_unknown_count": len(packet.get("known_unknowns", [])),
            "known_unknowns": packet.get("known_unknowns", []),
            "code_context_selected": len(packet.get("code_artifacts", [])),
        },
    }


def evaluate_fixture(inputs: dict) -> dict:
    validate_inputs(inputs)
    with tempfile.TemporaryDirectory(prefix="pact-decision-memory-m0-") as tmp:
        target = pathlib.Path(tmp) / "project"
        installation = install_fixture(target, inputs)
        # Both predictions are captured BEFORE opening the developer oracle.
        predictions = []
        for case in inputs["cases"]:
            predictions.append({
                "id": case["id"],
                "task": case["task"],
                "signal": case["signal"],
                "caller_supplied_hint": case.get("explicit_decision_hint"),
                "A": _arm(target, case, inputs["settings"], "A"),
                "B": _arm(target, case, inputs["settings"], "B"),
            })
        # Anchor diagnostics are deterministic metadata checks, not an
        # assumed implementation guarantee of current PACT.
        existing = {x["path"] for x in inputs["code_files"]}
        missing = [
            {"decision_id": doc["id"], "path": path}
            for doc in inputs["documents"]
            if doc["type"] == "decision"
            for path in doc.get("paths", [])
            if path not in existing
        ]
    return {"predictions": predictions, "installation": installation,
            "missing_declared_code_paths": missing}


def score(evidence: dict, oracle: dict, inputs: dict) -> dict:
    if oracle.get("version") != 1 or set(oracle.get("expected", {})) != {
        x["id"] for x in inputs["cases"]
    }:
        raise ValueError("frozen oracle does not match frozen input set")
    metadata = {doc["id"]: doc for doc in inputs["documents"]}
    results = []
    violations = []
    for item in evidence["predictions"]:
        expected = set(oracle["expected"][item["id"]])
        for arm in ("A", "B"):
            packet = item[arm]["context"]
            found = set(packet["current_decision_ids"])
            missing = sorted(expected - found)
            unexpected = sorted(found - expected)
            packet["oracle_count"] = len(expected)
            packet["matched_ids"] = sorted(found & expected)
            packet["missing_ids"] = missing
            packet["unexpected_current_decisions"] = unexpected
            packet["recall"] = len(found & expected) / len(expected) if expected else None
            bad_current = sorted(
                ident for ident in found
                if ident not in metadata
                or metadata[ident]["type"] != "decision"
                or metadata[ident]["status"] != "implemented"
            )
            bad_rules = sorted(
                ident for ident in packet["applicable_rule_ids"]
                if ident not in metadata
                or metadata[ident]["type"] != "rule"
                or metadata[ident]["status"] != "confirmed"
            )
            packet["authority_failures"] = bad_current + bad_rules
            if packet["returncode"] != 0 or item[arm]["discovery"]["returncode"] != 0:
                violations.append(item["id"] + "/" + arm + ": installed CLI failed")
            if bad_current or bad_rules:
                violations.append(item["id"] + "/" + arm + ": invalid authority promotion")
            if packet["selected_knowledge_files"] > inputs["settings"]["knowledge_limit"]:
                violations.append(item["id"] + "/" + arm + ": knowledge budget exceeded")
            if packet["code_context_selected"]:
                violations.append(item["id"] + "/" + arm + ": no-code boundary violated")
        known = item["caller_supplied_hint"]
        if known and known not in item["B"]["context"]["current_decision_ids"]:
            violations.append(item["id"] + "/B: explicit current Decision ID not selected")
        if not expected:
            for arm in ("A", "B"):
                if item[arm]["context"]["current_decision_ids"]:
                    violations.append(item["id"] + "/" + arm + ": irrelevant Decision selected")
        a = item["A"]["context"]
        b = item["B"]["context"]
        item["delta_B_minus_A_est_tokens"] = (
            b["selected_estimated_tokens"] - a["selected_estimated_tokens"]
            if isinstance(a["selected_estimated_tokens"], int)
            and isinstance(b["selected_estimated_tokens"], int) else None
        )
        item["delta_B_minus_A_elapsed_ms"] = round(
            b["elapsed_ms"] - a["elapsed_ms"], 3
        )
        item["historical_for_review"] = oracle.get(
            "historical_for_review", {}
        ).get(item["id"], [])
        results.append(item)
    total_oracle = sum(len(v) for v in oracle["expected"].values())
    totals = {
        arm: sum(
            len(result[arm]["context"]["matched_ids"]) for result in results
        ) for arm in ("A", "B")
    }
    return {
        "version": 1,
        "evaluation_kind": "PACT-only developer-authored synthetic installed-runtime decision retrieval diagnostic",
        "baseline_source_sha": inputs["baseline_main_sha"],
        "input_sha256": digest_file(INPUTS),
        "oracle_sha256": digest_file(ORACLE),
        "case_count": len(results),
        "oracle_target_count": total_oracle,
        "matched_oracle_decisions": totals,
        "weighted_decision_recall": {
            arm: totals[arm] / total_oracle if total_oracle else None
            for arm in ("A", "B")
        },
        "B_explicit_hint_case_count": sum(
            bool(x["caller_supplied_hint"]) for x in results
        ),
        "synthetic_engineering_gate": "PASS" if not violations else "FAIL",
        "gate_failures": violations,
        "installation": evidence["installation"],
        "missing_declared_code_paths": evidence["missing_declared_code_paths"],
        "case_results": results,
        "developer_wrote_oracle": True,
        "independently_withheld_oracle": False,
        "real_agent_executed": False,
        "real_agent_semantic_obedience_verified": False,
        "real_owner_data_observed": False,
        "owner_clarification_count": None,
        "owner_time_minutes": None,
        "added_model_tokens": None,
        "human_approval_authenticated": False,
        "release_attestation": False,
    }


def evaluate() -> dict:
    inputs = json.loads(INPUTS.read_text(encoding="utf-8"))
    evidence = evaluate_fixture(inputs)
    # The oracle is not placed in the installed target nor read by _arm.
    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    return score(evidence, oracle, inputs)


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit("frozen M0 benchmark accepts no arbitrary fixture paths")
    result = evaluate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # Emit the complete JSON before failing so CI can retain diagnostics.
    # A violated preregistered synthetic correctness gate is a real nonzero
    # exit status, not a "green" benchmark with an internal FAIL message.
    return 0 if result["synthetic_engineering_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
