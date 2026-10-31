#!/usr/bin/env python3
"""PACT RC1 Stage-2 no-model default Context vs experimental Domain-first."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import traceback

import brownfield_adr_viewer as pilot
import community_platform_rc1_stage1 as stage1
import decision_memory_m0 as m0

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOMAIN_FIXTURE = ROOT / "benchmarks/decision-memory/community-platform-stage2-domain-fixture-2026-10-31.json"
DOMAIN_BLOB = "f1a2bb570a98bc0dbfb2285b1340d045bd8f0197"
ARMS = ("B-default", "B-scope-no-domains",
        "C-default-synthetic-domains", "C-scope-synthetic-domains")

def file_sha(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing/symlinked source " + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()

def safe_source(target, relative):
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or pathlib.PurePosixPath(relative).is_absolute()
            or ".." in pathlib.PurePosixPath(relative).parts):
        raise ValueError("invalid source path " + repr(relative))
    return m0.safe_file(target, relative)

def load_frozen():
    cards, oracle = stage1.frozen_inputs()
    if pilot.git_blob_sha(DOMAIN_FIXTURE) != DOMAIN_BLOB:
        raise ValueError("stage2 Domain fixture altered since preregistration")
    config = json.loads(DOMAIN_FIXTURE.read_text(encoding="utf-8"))
    if (config.get("version") != 1 or config.get("pact_sha") != stage1.PACT_SHA
            or config.get("upstream_sha") != stage1.UPSTREAM_SHA
            or config.get("stage1_cards_blob") != stage1.CASES_BLOB
            or config.get("stage1_oracle_blob") != stage1.ORACLE_BLOB
            or [arm["id"] for arm in config["arms"]] != list(ARMS)
            or config.get("extra_safety_cases") != ["C2", "M3"]
            or len(config.get("domains", [])) != 6):
        raise ValueError("stage2 preregistration identity invalid")
    ids = {x["id"] for x in cards["source_decisions"]}
    names = set()
    for item in config["domains"]:
        ident = item.get("id")
        if (not isinstance(ident, str)
                or re.fullmatch(r"DOMAIN-[A-Z0-9]+(?:-[A-Z0-9]+)*", ident) is None
                or ident in names or not set(item.get("related", [])).issubset(ids)
                or len(item["related"]) != len(set(item["related"]))
                or not isinstance(item.get("name"), str)
                or not isinstance(item.get("aliases"), list)
                or any(not isinstance(a, str) or not a.strip() for a in item["aliases"])):
            raise ValueError("invalid hypothetical Domain source")
        names.add(ident)
    return cards, oracle, config

def create_test_domains(target, config):
    domains = {}
    for item in config["domains"]:
        relative = "docs/product/domains/" + item["id"].lower() + ".md"
        path = target / relative
        if path.exists() or path.is_symlink():
            raise ValueError("Domain already exists in original source")
        path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join([
            "+++", "[pact]", 'type = "domain"',
            "id = " + json.dumps(item["id"]),
            'status = "confirmed"',
            "aliases = " + json.dumps(item["aliases"]),
            "related = " + json.dumps(item["related"]),
            "paths = []", "+++", "",
            "# " + item["name"], "",
            "**TEST-ONLY HYPOTHETICAL ROUTER: NOT UPSTREAM OWNER-APPROVED.**",
            "Original ADRs remain authoritative; this test adds no new business rule.",
            "Source rationale: " + item["source_reason"], "",
        ])
        path.write_text(content, encoding="utf-8")
        domains[item["id"]] = {"path": relative, "sha256": file_sha(path)}
    return domains

def verify_envelope(target, packet, projected, domains):
    selected = packet.get("artifacts")
    budget = packet.get("context_budget")
    if not isinstance(selected, list) or not isinstance(budget, dict):
        raise ValueError("Context artifacts or budget malformed")
    paths = set()
    selected_ids = []
    for row in selected:
        if not isinstance(row, dict):
            raise ValueError("non-object Context source")
        path, ident = row.get("path"), row.get("id")
        source = safe_source(target, path)
        if path in paths or file_sha(source) != row.get("sha256"):
            raise ValueError("duplicate or source-SHA-invalid materialized Context")
        paths.add(path)
        kind = row.get("artifact_type")
        if kind == "decision":
            if ident not in projected or projected[ident]["path"] != path:
                raise ValueError("forged selected Decision identity")
            selected_ids.append(ident)
        elif kind == "domain":
            if ident not in domains or domains[ident]["path"] != path:
                raise ValueError("forged selected Domain identity")
        elif kind == "document":
            if ident is not None:
                raise ValueError("raw doc promoted to authority")
        elif kind not in {"rule", "architecture", "change", "drift"}:
            raise ValueError("unknown selected artifact type")
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("duplicate selected Decision ID")
    if set(packet.get("decisions") or []) != set(selected_ids):
        raise ValueError("Decision summary conflicts with selected Context")
    weak = packet.get("weak_decision_hints") or {}
    if (not isinstance(weak, dict)
            or (weak and not isinstance(weak.get("candidates"), list))):
        raise ValueError("weak hint shape invalid")
    weak_ids = []
    for hint in weak.get("candidates", []):
        ident, path = hint.get("id"), hint.get("path")
        if (ident not in projected or projected[ident]["path"] != path
                or file_sha(safe_source(target, path)) != hint.get("sha256")):
            raise ValueError("unverifiable weak Decision hint")
        weak_ids.append(ident)
    if weak and (type(weak.get("total_candidates")) is not int
                 or type(weak.get("truncated_candidates")) is not int
                 or weak["total_candidates"] != len(weak["candidates"]) + weak["truncated_candidates"]):
        raise ValueError("truncated weak Decision hints not accounted for")
    route = packet.get("scope_route")
    scoped_ids = []
    counterfactual_read_cost = 0
    if route is not None:
        if (not isinstance(route, dict)
                or route.get("status") not in {"unique", "unmapped", "ambiguous"}
                or route.get("applicability_verified") is not False
                or not isinstance(route.get("candidates"), list)):
            raise ValueError("invalid scope route or falsely verified applicability")
        for hint in route["candidates"]:
            ident, path = hint.get("id"), hint.get("path")
            source = safe_source(target, path)
            if (ident not in projected or projected[ident]["path"] != path
                    or file_sha(source) != hint.get("sha256")
                    or hint.get("status") != "implemented"):
                raise ValueError("forged/provenance-invalid scope Decision hint")
            scoped_ids.append(ident)
            if path not in paths:
                counterfactual_read_cost += (source.stat().st_size + 3) // 4
        if route["status"] == "unique":
            homes = route.get("domains", [])
            if len(homes) != 1:
                raise ValueError("unique route without one Domain")
            ident, path = homes[0].get("id"), homes[0].get("path")
            if ident not in domains or domains[ident]["path"] != path or path not in paths:
                raise ValueError("unique route Domain absent from selected Context")
        if route["status"] == "unmapped" and route.get("restricted_selection"):
            raise ValueError("unmapped route silently narrowed Context")
    return {
        "selected_current": selected_ids,
        "weak_hint_ids": weak_ids,
        "scope_candidate_ids": scoped_ids,
        "scope_status": route.get("status") if route else None,
        "restricted_selection": bool(route.get("restricted_selection")) if route else False,
        "scope_domains": [x.get("id") for x in route.get("domains", [])] if route else [],
        "scope_candidate_truncated": route.get("truncated_candidates", 0) if route else 0,
        "weak_hint_truncated": weak.get("truncated_candidates", 0),
        "all_hint_read_cost_estimate": counterfactual_read_cost,
        "budget": budget,
    }

def probe(target, cards, projected, domains, arm, rows, risk="low", no_code=False):
    scoped = arm in {"B-scope-no-domains", "C-scope-synthetic-domains", "HIGH-scope-sentinel"}
    for case in cards["cases"]:
        if arm == "HIGH-scope-sentinel" and case["id"] not in {"C2", "M3"}:
            continue
        args = ["context", case["task"], "--success",
                "Preserve established project decisions when applicable", "--risk", risk]
        if no_code:
            args.append("--no-code")
        if scoped:
            args.append("--scope-first")
        row = {"id": case["id"], "category": case["category"],
               "command": ["pact.py", *args]}
        rows.append(row)  # preserve incomplete evidence if later CLI fails
        response = m0.run_json(target, args)
        row["returncode"] = response.get("returncode")
        row["elapsed_ms"] = response.get("elapsed_ms")
        row["stdout_excerpt"] = response.get("stdout_excerpt", "")
        row["stderr"] = response.get("stderr", "")
        row["raw_cli_payload"] = response.get("data")
        if row["returncode"] != 0 or not isinstance(response.get("data"), dict):
            raise RuntimeError(f"{arm} {case['id']} CLI nonzero/malformed: {row['stderr']}")
        row["observed"] = verify_envelope(target, response["data"], projected, domains)

def score(cards, oracle, observed):
    results = {}
    annotated = {}
    for arm in ARMS:
        by_id = {x["id"]: x for x in observed[arm]}
        if len(by_id) != 14 or set(by_id) != set(oracle["expected_current"]):
            raise ValueError("missing/duplicate stage2 arm cases")
        rows = []
        for case in cards["cases"]:
            ident = case["id"]
            actual = by_id[ident]["observed"]
            expected = oracle["expected_current"][ident]
            got = actual["selected_current"]
            hints = set(actual["weak_hint_ids"] + actual["scope_candidate_ids"])
            b = actual["budget"]
            rows.append({
                "id": ident, "category": case["category"], "expected": expected,
                "selected": got, "selected_targets": [x for x in expected if x in got],
                "hint_only_targets": [x for x in expected if x not in got and x in hints],
                "missing_targets": [x for x in expected if x not in got and x not in hints],
                "extra_current": [x for x in got if x not in expected],
                "scope_status": actual["scope_status"],
                "scope_domains": actual["scope_domains"],
                "scope_candidates": actual["scope_candidate_ids"],
                "restricted_selection": actual["restricted_selection"],
                "estimated_tokens": b.get("selected_estimated_tokens"),
                "budget_tokens": b.get("limit_tokens"),
                "dropped_authority": b.get("authority_candidates_dropped"),
                "scope_hint_truncated": actual["scope_candidate_truncated"],
                "weak_hint_truncated": actual["weak_hint_truncated"],
                "read_all_scope_hints_estimate": actual["all_hint_read_cost_estimate"],
            })
        positive = [x for x in rows if x["expected"]]
        negative = [x for x in rows if not x["expected"]]
        results[arm] = {
            "positive_all_expected_materialized": sum(
                len(x["selected_targets"]) == len(x["expected"]) for x in positive
            ),
            "positive_count": len(positive),
            "target_occurrences": sum(len(x["expected"]) for x in positive),
            "target_materialized": sum(len(x["selected_targets"]) for x in positive),
            "target_hint_only": sum(len(x["hint_only_targets"]) for x in positive),
            "target_missing_entirely": sum(len(x["missing_targets"]) for x in positive),
            "routine_clean": sum(not x["selected"] for x in negative),
            "routine_injected": sum(bool(x["selected"]) for x in negative),
            "routine_total": len(negative),
            "oracle_extra_current_slots": sum(len(x["extra_current"]) for x in rows),
            "selected_estimated_tokens_total": sum(x["estimated_tokens"] for x in rows),
            "hypothetical_read_all_scope_hints_tokens": sum(
                x["read_all_scope_hints_estimate"] for x in rows),
            "authority_count_omission_cases": sum(bool(x["dropped_authority"]) for x in rows),
            "weak_hint_truncated_cases": sum(bool(x["weak_hint_truncated"]) for x in rows),
            "scope_hint_truncated_cases": sum(bool(x["scope_hint_truncated"]) for x in rows),
            "scope_route_unique": sum(x["scope_status"] == "unique" for x in rows),
            "scope_route_unmapped": sum(x["scope_status"] == "unmapped" for x in rows),
            "scope_route_ambiguous": sum(x["scope_status"] == "ambiguous" for x in rows),
            "scope_restricted": sum(x["restricted_selection"] for x in rows),
            "cases": rows,
        }
        annotated[arm] = {x["id"]: x for x in rows}
    default = annotated["B-default"]
    fallback = annotated["B-scope-no-domains"]
    high = []
    for row in observed["HIGH-scope-sentinel"]:
        expected = oracle["expected_current"][row["id"]]
        actual = row["observed"]
        high.append({
            "id": row["id"], "expected": expected,
            "selected": actual["selected_current"],
            "missing_materialized": [x for x in expected if x not in actual["selected_current"]],
            "scope_status": actual["scope_status"],
            "restricted_selection": actual["restricted_selection"],
        })
    return {
        "arms": results,
        "unmapped_route_narrowed": [i for i in default if fallback[i]["restricted_selection"]],
        "fallback_selected_ids_differ": [i for i in default if default[i]["selected"] != fallback[i]["selected"]],
        "high_risk_no_code_sentinels": high,
        "independent_blind_evaluation": False,
        "real_agent_execution": False,
        "upstream_owner_domain_confirmation": False,
        "provider_billed_tokens": None,
        "no_default_rollout_authorized": True,
    }

def evaluate(target, report):
    report["stage"] = "validate-frozen-stage1-and-stage2-inputs"
    cards, oracle, config = load_frozen()
    stage1.check_pact_baseline()
    original = stage1.original_sources(target, cards)
    report["source_blobs"] = original
    report["stage"] = "install-exact-rc1"
    report["installed"] = pilot.install_pact(target)
    report["pre_projection_check"] = stage1.pact_check_snapshot(target)
    projected = stage1.project_source_decisions(target, cards)
    report["projection_sources"] = projected
    post = stage1.pact_check_snapshot(target)
    report["post_projection_check"] = post
    stage1.check_only_existing_source_placeholders(report["pre_projection_check"], post)
    expected_projection_sha = {k: file_sha(target / v["path"]) for k, v in projected.items()}
    report["observations"] = {x: [] for x in (*ARMS, "HIGH-scope-sentinel")}
    report["stage"] = "B-default-real-low-risk-budget-no-domains"
    probe(target, cards, projected, {}, "B-default", report["observations"]["B-default"])
    report["stage"] = "B-scope-first-no-real-domains"
    probe(target, cards, projected, {}, "B-scope-no-domains", report["observations"]["B-scope-no-domains"])
    report["stage"] = "create-6-provisional-router-pages-in-disposable-workspace"
    domains = create_test_domains(target, config)
    report["test_only_domains"] = domains
    check_after_domains = stage1.pact_check_snapshot(target)
    report["post_domain_check"] = check_after_domains
    if sorted(check_after_domains["errors"]) != sorted(post["errors"]):
        raise ValueError("Domain experiment added PACT checker errors")
    if "discovered 14 machine-readable artifact(s)" not in check_after_domains["stdout"]:
        raise ValueError("PACT check failed to recognize all 8 Decisions + 6 test Domain records")
    report["stage"] = "C-default-with-hypothetical-domain-source"
    probe(target, cards, projected, domains, "C-default-synthetic-domains",
          report["observations"]["C-default-synthetic-domains"])
    report["stage"] = "C-scope-same-hypothetical-domain-source"
    probe(target, cards, projected, domains, "C-scope-synthetic-domains",
          report["observations"]["C-scope-synthetic-domains"])
    report["stage"] = "high-risk-route-sentinel-no-code"
    probe(target, cards, projected, domains, "HIGH-scope-sentinel",
          report["observations"]["HIGH-scope-sentinel"], risk="high", no_code=True)
    report["stage"] = "postflight-provenance"
    if stage1.original_sources(target, cards) != original:
        raise ValueError("original upstream ADR blobs changed")
    if expected_projection_sha != {k: file_sha(target / v["path"]) for k, v in projected.items()}:
        raise ValueError("PACT source-faithful Decision projections changed")
    if any(file_sha(target / v["path"]) != v["sha256"] for v in domains.values()):
        raise ValueError("hypothetical Domain source mutated")
    if stage1.git(target, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        raise ValueError("upstream tracked source modified")
    report["upstream_tracked_clean"] = True
    report["stage"] = "score-only-after-all-observations"
    report["scores"] = score(cards, oracle, report["observations"])
    report["engineering_collection"] = "PASS"
    report["stage"] = "complete"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=pathlib.Path, required=True)
    args = parser.parse_args()
    report = {
        "pact_tag": "v0.4.0-rc.1", "pact_sha": stage1.PACT_SHA,
        "upstream_sha": stage1.UPSTREAM_SHA, "stage2_fixture_blob": DOMAIN_BLOB,
        "engineering_collection": "FAIL", "stage": "not-started",
        "real_agent_executed": False, "independent_oracle": False,
        "owner_confirmed_domain": False, "external_model_called": False,
        "upstream_remote_writes": False, "release_gate": "HOLD",
    }
    try:
        evaluate(args.target.resolve(), report)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired,
            json.JSONDecodeError) as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        report["traceback_last"] = traceback.format_exc().splitlines()[-12:]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["engineering_collection"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
