#!/usr/bin/env python3
"""Frozen RC1 no-model Decision-memory probe on an unmodified real upstream.

The author-labelled cases/oracle were committed before this runner. They are
not independently blind and never represent coding-Agent obedience.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import posixpath
import re
import subprocess
import sys
import traceback

import brownfield_adr_viewer as pilot
import decision_memory_m0 as m0

ROOT = pathlib.Path(__file__).resolve().parents[2]
CASES = ROOT / "benchmarks/decision-memory/community-platform-stage1-cases-2026-10-31.json"
ORACLE = ROOT / "benchmarks/decision-memory/community-platform-stage1-oracle-2026-10-31.json"
CASES_BLOB = "7398962212a21bb00a44fb1b6750a4d96ee59868"
ORACLE_BLOB = "56c8c37bf841adf0b18697ab50c271f9a45fe598"
PACT_SHA = "7592efd3393ff568758400ff06d7e2e5b3315a2f"
UPSTREAM = "What-We-Will/community-platform"
UPSTREAM_SHA = "52ca3e7cecab0a1568158921359cc743fdd0954a"
PROBE_CLASSES = {
    "decision-conflict": 4,
    "pathless-no-id": 3,
    "partial-amendment": 3,
    "routine-negative": 4,
}
LINK = re.compile(r"(\]\()([^\s)]+)(\))")


def git(root: pathlib.Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True, capture_output=True, timeout=35, check=False,
    )
    if check and result.returncode:
        raise RuntimeError("git " + " ".join(args) + ": " + result.stderr[:500])
    return result


def frozen_inputs() -> tuple[dict, dict]:
    if pilot.git_blob_sha(CASES) != CASES_BLOB:
        raise ValueError("frozen case blob differs from precommitted SHA")
    if pilot.git_blob_sha(ORACLE) != ORACLE_BLOB:
        raise ValueError("frozen oracle blob differs from precommitted SHA")
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    if (cases.get("version") != 1
            or cases.get("pact_tag") != "v0.4.0-rc.1"
            or cases.get("pact_commit") != PACT_SHA
            or cases.get("upstream") != UPSTREAM
            or cases.get("upstream_commit") != UPSTREAM_SHA
            or cases.get("settings") != {
                "query_mode": "single-task-default-no-intent",
                "risk": "low", "knowledge_limit": 12,
                "estimated_token_budget": 45000, "code_context": False
            }):
        raise ValueError("frozen trial source/settings changed")
    tasks = cases.get("cases")
    if not isinstance(tasks, list) or len(tasks) != 14:
        raise ValueError("14 preregistered cases required")
    if {k: sum(c["category"] == k for c in tasks) for k in PROBE_CLASSES} != PROBE_CLASSES:
        raise ValueError("changed preregistered category count")
    ids = [item["id"] for item in tasks]
    if len(ids) != len(set(ids)) or set(oracle.get("expected_current", {})) != set(ids):
        raise ValueError("missing/duplicate case or oracle entries")
    source = cases.get("source_decisions")
    if not isinstance(source, list) or len(source) != 8:
        raise ValueError("eight pinned original ADRs required")
    source_ids = {doc["id"] for doc in source}
    if len(source_ids) != len(source):
        raise ValueError("duplicate source ADR")
    for entry in source:
        if (not re.fullmatch(r"DEC-CPL-\d{4}", entry["id"])
                or not re.fullmatch(r"docs/adr/\d{4}-[a-z0-9-]+\.md", entry["path"])
                or entry["id"][-4:] != pathlib.Path(entry["path"]).name[:4]
                or not re.fullmatch(r"[a-f0-9]{40}", entry["git_blob"])
                or entry["source_status"] != "Accepted"
                or entry["projection_status"] != "implemented"):
            raise ValueError("malformed/adversarial source fixture")
    for item in tasks:
        if (not isinstance(item["task"], str) or not item["task"].strip()
                or "DEC-CPL-" in item["task"]
                or "ADR-00" in item["task"]
                or "docs/adr/" in item["task"]):
            raise ValueError("task leaks source ID/path or is empty")
        expected = oracle["expected_current"][item["id"]]
        if (not isinstance(expected, list) or len(expected) != len(set(expected))
                or any(x not in source_ids for x in expected)
                or (item["category"] == "routine-negative") != (not expected)):
            raise ValueError("oracle source IDs or routine controls malformed")
    return cases, oracle


def check_pact_baseline() -> None:
    # Experiment-only additions cannot change the PACT runtime under test.
    args = [
        "diff", "--quiet", PACT_SHA, "HEAD", "--",
        "bootstrap.py", "pact.py", "scripts/pact", ".pact",
        "AGENTS.md", ".agents/decisions", "docs/governance",
        "docs/product", "docs/design",
    ]
    result = git(ROOT, *args, check=False)
    if result.returncode:
        raise ValueError("evaluated PACT runtime/truth does not match exact RC1")
    if git(ROOT, "cat-file", "-t", PACT_SHA).stdout.strip() != "commit":
        raise ValueError("RC1 commit not in checkout")


def original_sources(target: pathlib.Path, cases: dict) -> dict[str, str]:
    if git(target, "rev-parse", "HEAD").stdout.strip() != UPSTREAM_SHA:
        raise ValueError("upstream checkout is not the frozen commit")
    origin = git(target, "remote", "get-url", "origin").stdout.strip()
    if origin not in {
        "https://github.com/What-We-Will/community-platform",
        "https://github.com/What-We-Will/community-platform.git",
    }:
        raise ValueError("upstream checkout remote is not allowlisted")
    if git(target, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        raise ValueError("upstream tracked files already changed")
    hashes = {}
    for entry in cases["source_decisions"]:
        path = target / entry["path"]
        if path.is_symlink() or not path.is_file():
            raise ValueError("original ADR source missing or symlinked: " + entry["path"])
        blob = pilot.git_blob_sha(path)
        if blob != entry["git_blob"]:
            raise ValueError("original Git blob mismatch: " + entry["path"])
        if not re.search(
            r"^\*\*Status:\*\*\s+Accepted\b",
            path.read_text(encoding="utf-8"), re.MULTILINE,
        ):
            raise ValueError("source not accepted: " + entry["path"])
        hashes[entry["path"]] = blob
    return hashes


def adapt_links(original: str, source_path: str, destination: str) -> str:
    # Modify relative Markdown targets only in the ephemeral copy. The source
    # Markdown and its substantive prose remain immutable.
    def convert(match: re.Match) -> str:
        value = match.group(2)
        if value.startswith(("#", "/", "//")) or "://" in value or re.match(
            r"^[a-zA-Z][a-zA-Z0-9+.-]*:", value
        ):
            return match.group(0)
        pathname, separator, fragment = value.partition("#")
        if not pathname:
            return match.group(0)
        target_path = posixpath.normpath(
            posixpath.join(posixpath.dirname(source_path), pathname)
        )
        if target_path == ".." or target_path.startswith("../"):
            raise ValueError("source Markdown link outside checkout: " + value)
        rebased = posixpath.relpath(target_path, posixpath.dirname(destination))
        if separator:
            rebased += "#" + fragment
        return match.group(1) + rebased + match.group(3)
    return LINK.sub(convert, original)


def projected_cards(cases: dict) -> dict:
    return {"upstream_docs": [
        {"id": entry["id"], "source": entry["path"], "status": entry["projection_status"]}
        for entry in cases["source_decisions"]
    ]}


def project_source_decisions(target: pathlib.Path, cases: dict) -> dict:
    result = {}
    for doc in cases["source_decisions"]:
        original = (target / doc["path"]).read_text(encoding="utf-8")
        relative = ".agents/decisions/implemented/" + doc["id"].lower() + ".md"
        file = target / relative
        if file.exists() or file.is_symlink():
            raise ValueError("projection target pre-existed: " + relative)
        file.parent.mkdir(parents=True, exist_ok=True)
        metadata = [
            "+++", "[pact]", 'type = "decision"',
            "id = " + json.dumps(doc["id"]),
            'status = "implemented"',
            "aliases = []", "paths = []", "domains = []", "related = []",
            "supersedes = []", "+++",
            "",
            "Source-faithful experimental projection, NOT Owner-approved PACT truth.",
            "Upstream original: " + doc["path"],
            "Git blob SHA: " + doc["git_blob"],
            "",
        ]
        adapted = adapt_links(original, doc["path"], relative)
        file.write_text("\n".join(metadata) + adapted.rstrip() + "\n", encoding="utf-8")
        result[doc["id"]] = {
            "path": relative,
            "source_blob": doc["git_blob"],
            "projection_sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
        }
    return result


def run_installed_cli(target: pathlib.Path, args: list[str], store: dict, field: str) -> dict:
    response = m0.run_json(target, args)
    store[field] = {
        "command": response.get("command", ["pact.py", *args]),
        "returncode": response.get("returncode"),
        "elapsed_ms": response.get("elapsed_ms"),
        "stderr": response.get("stderr", ""),
        "stdout_excerpt": response.get("stdout_excerpt", ""),
        "raw_cli_payload": response.get("data"),
    }
    if response.get("returncode") != 0 or not isinstance(response.get("data"), dict):
        raise RuntimeError("installed PACT CLI failed: " + field + " " + str(args[:2]))
    return response["data"]


def probe(target: pathlib.Path, cases: dict, phase: str, records: list) -> None:
    settings = cases["settings"]
    adapted = projected_cards(cases)
    for card in cases["cases"]:
        receipt: dict = {"id": card["id"], "category": card["category"], "task": card["task"]}
        records.append(receipt)  # preserve partial failures
        query = card["task"]
        discover_args = [
            "discover", query, "--json", "--limit",
            str(settings["knowledge_limit"]),
        ]
        discover = run_installed_cli(target, discover_args, receipt, "discover")
        context_args = [
            "context", query, "--success", "Preserve established project behavior",
            "--risk", "low", "--no-code", "--limit",
            str(settings["knowledge_limit"]), "--token-budget",
            str(settings["estimated_token_budget"]),
        ]
        envelope = run_installed_cli(target, context_args, receipt, "context")
        results = discover.get("results")
        selected = envelope.get("artifacts")
        if not isinstance(results, list) or not isinstance(selected, list):
            raise ValueError("discovery/context missing result lists")
        if any(not pilot.valid_discovery_result(item) for item in results):
            raise ValueError("malformed installed discover result")
        if any(not pilot.valid_context_artifact(item) for item in selected):
            raise ValueError("malformed installed context source")
        errors = pilot.verify_installed_probe_sources(target, adapted, results, selected)
        errors.extend(pilot.verify_weak_decision_hints(target, adapted, envelope))
        if errors:
            raise ValueError("untrusted output/source: " + "; ".join(errors[:5]))
        chosen = [item["id"] for item in selected
                  if item.get("artifact_type") == "decision"]
        if len(chosen) != len(set(chosen)):
            raise ValueError("duplicate selected Decision IDs")
        candidates = ((envelope.get("weak_decision_hints") or {}).get("candidates") or [])
        hinted = [item["id"] for item in candidates]
        budget = envelope.get("context_budget") or {}
        receipt["observed"] = {
            "source_phase": phase,
            "selected_current_decision_ids": chosen,
            "deferred_weak_decision_ids": hinted,
            "discovery_typed_ids": [item.get("id") for item in results if item.get("id")],
            "source_bound_selections": [
                {"id": item["id"], "path": item["path"], "sha256": item["sha256"]}
                for item in selected if item.get("artifact_type") == "decision"
            ],
            "estimated_context_tokens": budget.get("selected_estimated_tokens"),
            "authority_candidates_dropped": budget.get("authority_candidates_dropped"),
            "weak_hint_truncated": (envelope.get("weak_decision_hints") or {}).get("truncated_candidates", 0),
        }


def score(cases: dict, oracle: dict, record_b: list[dict]) -> dict:
    by_id = {record["id"]: record for record in record_b}
    rows = []
    for card in cases["cases"]:
        ident = card["id"]
        observed = by_id[ident]["observed"]
        expected = oracle["expected_current"][ident]
        selected = observed["selected_current_decision_ids"]
        hinted = observed["deferred_weak_decision_ids"]
        rows.append({
            "id": ident, "category": card["category"],
            "expected_current": expected,
            "selected_current": selected,
            "target_selected": [x for x in expected if x in selected],
            "target_hint_only": [x for x in expected if x not in selected and x in hinted],
            "target_missing_entirely": [x for x in expected if x not in selected and x not in hinted],
            "extra_current": [x for x in selected if x not in expected],
            "negative_injected": bool(selected) if not expected else None,
            "estimated_context_tokens": observed["estimated_context_tokens"],
            "authority_candidates_dropped": observed["authority_candidates_dropped"],
        })
    positives = [r for r in rows if r["expected_current"]]
    negatives = [r for r in rows if not r["expected_current"]]
    passed = (
        all(len(r["target_selected"]) == len(r["expected_current"]) for r in positives)
        and all(not r["selected_current"] for r in negatives)
        and all(not r["authority_candidates_dropped"] for r in rows)
        and all((by_id[r["id"]]["observed"]["weak_hint_truncated"] or 0) == 0 for r in rows)
    )
    return {
        "retrieval_gate": "PASS_DEVELOPER_ORACLE_PROXY" if passed else "NO-GO",
        "target_positive_tasks": len(positives),
        "positive_all_targets_selected": sum(
            len(r["target_selected"]) == len(r["expected_current"]) for r in positives
        ),
        "target_source_occurrences": sum(len(r["expected_current"]) for r in positives),
        "target_source_selected": sum(len(r["target_selected"]) for r in positives),
        "target_source_hint_only": sum(len(r["target_hint_only"]) for r in positives),
        "target_source_missing": sum(len(r["target_missing_entirely"]) for r in positives),
        "routine_negative_tasks": len(negatives),
        "routine_negative_clean": sum(not r["selected_current"] for r in negatives),
        "routine_negative_injected": sum(bool(r["selected_current"]) for r in negatives),
        "oracle_extraneous_selected_slots": sum(len(r["extra_current"]) for r in rows),
        "context_token_estimate_total_B": sum(
            r["estimated_context_tokens"] for r in rows
            if type(r["estimated_context_tokens"]) is int
        ),
        "source_rows": rows,
        "extra_candidates_are_not_semantically_proven_irrelevant": True,
        "independent_blind_trial": False,
        "real_coding_agent_executed": False,
        "owner_validation": False,
        "model_tokens_billed": None,
        "release_authorization": False,
    }


def pact_check_snapshot(target: pathlib.Path) -> dict:
    """Keep all known original upstream check errors, not a fabricated pass."""
    result = subprocess.run(
        [sys.executable, str(target / "pact.py"), "check"],
        cwd=target, capture_output=True, text=True, timeout=120, check=False,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout[:3000],
        "stderr": result.stderr[:3000],
        "errors": [
            line.strip()[2:].strip()
            for line in result.stderr.splitlines()
            if line.strip().startswith("- ")
        ],
    }


def check_only_existing_source_placeholders(before: dict, after: dict) -> None:
    """Treat original-only broken examples as a documented baseline, not success."""
    known = {
        "docs/adr/README.md: broken internal link './NNNN-...'",
        "docs/adr/template.md: broken internal link './NNNN-...'",
    }
    if (before["returncode"] != 1 or len(before["errors"]) != 4
            or set(before["errors"]) != known):
        raise ValueError("unexpected preexisting source check errors; no waiver")
    if (after["returncode"] != 1
            or sorted(after["errors"]) != sorted(before["errors"])):
        raise ValueError("PACT projection introduced or changed check errors")
    if "discovered 8 machine-readable artifact(s)" not in after["stdout"]:
        raise ValueError("pact check did not discover exactly eight projected Decisions")


def evaluate(target: pathlib.Path, report: dict) -> None:
    report["stage"] = "validate-frozen-fixtures"
    cases, oracle = frozen_inputs()
    report["cases_blob_sha"] = CASES_BLOB
    report["oracle_blob_sha"] = ORACLE_BLOB
    report["stage"] = "validate-exact-pact-tag-runtime"
    check_pact_baseline()
    report["stage"] = "verify-unmodified-original-ADRs"
    report["upstream_blobs_before"] = original_sources(target, cases)
    report["stage"] = "install-rc1"
    report["installed"] = pilot.install_pact(target)
    report["stage"] = "record-unadapted-upstream-pact-check-baseline"
    report["pact_check_baseline"] = pact_check_snapshot(target)
    report["stage"] = "probe-A-unadapted-source"
    report["A"] = []
    probe(target, cases, "A-original-ADR-no-Pact-projection", report["A"])
    report["stage"] = "project-pinned-ADRs-into-disposable-clone"
    report["projected"] = project_source_decisions(target, cases)
    report["pact_check"] = pact_check_snapshot(target)
    check_only_existing_source_placeholders(
        report["pact_check_baseline"], report["pact_check"]
    )
    report["upstream_preexisting_broken_template_links"] = 4
    report["pact_check_new_errors"] = 0
    report["stage"] = "probe-B-source-faithful-test-projection"
    report["B"] = []
    probe(target, cases, "B-projected-original-ADRs", report["B"])
    report["stage"] = "source-safety-postflight"
    if report["upstream_blobs_before"] != original_sources(target, cases):
        raise ValueError("original upstream ADR changed during evaluation")
    report["upstream_tracked_clean"] = not bool(
        git(target, "status", "--porcelain", "--untracked-files=no").stdout.strip()
    )
    if not report["upstream_tracked_clean"]:
        raise ValueError("original upstream tracked code changed")
    report["stage"] = "read-developer-oracle-after-complete-probes"
    report["scores"] = score(cases, oracle, report["B"])
    report["engineering_safety_gate"] = "PASS"
    report["stage"] = "complete"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=pathlib.Path, required=True)
    args = parser.parse_args()
    report = {
        "pact_ref": "v0.4.0-rc.1", "pact_sha": PACT_SHA,
        "upstream": UPSTREAM, "upstream_sha": UPSTREAM_SHA,
        "engineering_safety_gate": "FAIL", "stage": "not-started",
        "independent_blind_trial": False, "real_coding_agent_executed": False,
        "owner_validation": False, "external_model_called": False,
        "upstream_remote_writes": False, "release_gate": "HOLD",
    }
    try:
        evaluate(args.target.resolve(), report)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired,
            json.JSONDecodeError) as exc:
        report["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        report["traceback_last"] = traceback.format_exc().splitlines()[-8:]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["engineering_safety_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
