#!/usr/bin/env python3
"""PACT-only diagnostic of installed Context on a pinned PUBLIC source checkout.

Developer-labelled and nonblind. No real coding Agent, Owner observations,
external write or claim that status-faithful projections are Owner authority.
The original PrivacyFence tracked files remain unchanged.
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
import time
import traceback

import brownfield_adr_viewer as pilot
import decision_memory_m0 as m0

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))
from schema_validate import validate_instance

CASES = ROOT / "benchmarks" / "privacyfence" / "pilot-cases-v1.json"
ORACLE = ROOT / "benchmarks" / "privacyfence" / "pilot-developer-oracle-v1.json"
CASES_BLOB = "d0397c34bbed537b5a91a5d9340d52d21bc9460b"
ORACLE_BLOB = "1f6cb98e38a529fb8012c49cbda7b19c9c4e59d0"
UPSTREAM_SHA = "6a03856a6e1819b2eacd3963154ebc7d02923296"
UPSTREAM = "privacyfence/privacyfence"
PACT_BASE = "09e78ed995fb7cedb5b21851833346274f5aec33"
SCHEMA = json.loads(
    (ROOT / ".pact/schema/context-envelope.schema.json").read_text(encoding="utf-8")
)
DEC_ID = re.compile(r"^DEC-PF-\d{4}$")
EXPECTED_COUNT = 12


def safe_source(target: pathlib.Path, relative: str) -> pathlib.Path:
    path = m0.safe_file(target, relative)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"pinned source missing or symlinked: {relative}")
    return path


def verify_freeze(target: pathlib.Path) -> dict:
    if pilot.git_blob_sha(CASES) != CASES_BLOB:
        raise ValueError("precommitted PrivacyFence tasks/source manifest mutated")
    if pilot.git_blob_sha(ORACLE) != ORACLE_BLOB:
        raise ValueError("precommitted developer oracle mutated")
    cards = json.loads(CASES.read_text(encoding="utf-8"))
    if (cards.get("upstream") != UPSTREAM
            or cards.get("upstream_commit") != UPSTREAM_SHA
            or cards.get("pact_baseline") != PACT_BASE
            or cards.get("version") != 1):
        raise ValueError("wrong fixed PrivacyFence/Pact revision")
    if cards.get("settings") != {
        "risk": "low", "intent": "work", "knowledge_limit": 6,
        "estimated_token_budget": 4096, "code_context": False,
    }:
        raise ValueError("frozen budget or retrieval settings changed")
    docs = cards.get("source_docs", [])
    cases = cards.get("tasks", [])
    if len(docs) != EXPECTED_COUNT or len(cases) != EXPECTED_COUNT:
        raise ValueError("expected 12 pinned ADRs and 12 distinct tasks")
    ids, sources = [d["id"] for d in docs], [d["source"] for d in docs]
    if (len(set(ids)) != len(ids) or len(set(sources)) != len(sources)
            or any(not DEC_ID.fullmatch(x) for x in ids)):
        raise ValueError("invalid or duplicate projection IDs")
    for d in docs:
        if (not re.fullmatch(r"docs/adr/\d{4}-[a-z0-9-]+\.md", d["source"])
                or d["id"] != "DEC-PF-" + d["source"].split("/")[-1][:4]
                or d["status"] not in {"implemented", "proposed"}):
            raise ValueError("unsupported ADR identity or source status")
        if pilot.git_blob_sha(safe_source(target, d["source"])) != d["git_blob"]:
            raise ValueError(f"original ADR blob changed: {d['source']}")
        raw = safe_source(target, d["source"]).read_text(encoding="utf-8")
        status_text = re.search(r"(?m)^## Status\s*\n+([\s\S]*?)(?=\n## |\Z)", raw)
        if not status_text:
            raise ValueError(f"no original Status section: {d['source']}")
        first = status_text.group(1).strip().splitlines()[0]
        if d["status"] == "implemented" and not first.startswith("Accepted"):
            raise ValueError(f"ADR not source-accepted: {d['source']}")
        if d["status"] == "proposed" and "Proposed" not in first:
            raise ValueError(f"ADR not source-proposed: {d['source']}")
    if sum(d["status"] == "proposed" for d in docs) != 1:
        raise ValueError("must preserve exactly one Proposed guard ADR")
    cids = [x["id"] for x in cases]
    if (len(set(cids)) != EXPECTED_COUNT
            or sum(x["kind"] == "conflict" for x in cases) != 10
            or sum(x["kind"] == "routine-negative" for x in cases) != 2
            or any(
                not re.fullmatch(r"[a-z][a-z0-9-]{1,63}", x["id"])
                or not isinstance(x["task"], str) or not x["task"].strip()
                or "DEC-PF-" in x["task"] or "docs/adr/" in x["task"]
                for x in cases
            )):
        raise ValueError("unfrozen/unsafe task wording or case structure")
    if pilot.git_output(target, "rev-parse", "HEAD") != UPSTREAM_SHA:
        raise ValueError("not on exact pinned real upstream revision")
    remote = pilot.git_output(target, "remote", "get-url", "origin")
    if remote not in {
        "https://github.com/privacyfence/privacyfence.git",
        "https://github.com/privacyfence/privacyfence",
    }:
        raise ValueError(f"unrecognized read-only upstream URL: {remote}")
    if pilot.git_output(target, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("pinned upstream was already locally modified")
    count = len(list((target / "docs/adr").glob("*.md")))
    if count != cards["source_adr_markdown_count"] or count != 184:
        raise ValueError(f"upstream ADR inventory drift: {count}")
    return cards


def target_path(doc: dict) -> str:
    return (
        ".agents/decisions/" +
        ("proposed" if doc["status"] == "proposed" else "implemented") +
        "/" + doc["id"].lower() + ".md"
    )


def rebase_links(source: str, source_path: str, projected_path: str) -> str:
    """Change local Markdown link DESTINATIONS only, never the source words."""
    from_dir = posixpath.dirname(source_path)
    to_dir = posixpath.dirname(projected_path)

    def replace(match: re.Match[str]) -> str:
        href = match.group(2)
        if href.startswith(("#", "/", "http://", "https://", "mailto:", "data:")):
            return match.group(0)
        if "://" in href or href.startswith("<"):
            return match.group(0)
        pure, sep, fragment = href.partition("#")
        if not pure:
            return match.group(0)
        absolute = posixpath.normpath(posixpath.join(from_dir, pure))
        if absolute == ".." or absolute.startswith("../"):
            raise ValueError(f"original ADR link exits upstream checkout: {href}")
        output = posixpath.relpath(absolute, to_dir)
        return match.group(1) + output + (sep + fragment if sep else "") + match.group(3)

    return re.sub(r"(\]\()([^)]+)(\))", replace, source)


def project_sources(target: pathlib.Path, cards: dict) -> dict[str, str]:
    result: dict[str, str] = {}
    for doc in cards["source_docs"]:
        origin = safe_source(target, doc["source"])
        dest_rel = target_path(doc)
        destination = m0.safe_file(target, dest_rel)
        if destination.exists() or destination.is_symlink():
            raise ValueError(f"projection destination already exists: {dest_rel}")
        content = origin.read_text(encoding="utf-8")
        body = rebase_links(content, doc["source"], dest_rel)
        prefix = "\n".join([
            "+++", "[pact]", 'type = "decision"',
            'id = ' + json.dumps(doc["id"]),
            'status = ' + json.dumps(doc["status"]),
            "aliases = []", "paths = []", "domains = []",
            "related = []", "supersedes = []", "+++", "",
        ])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(prefix + body.rstrip() + "\n", encoding="utf-8")
        result[dest_rel] = m0.digest_file(destination)
    return dict(sorted(result.items()))


def run_arm(target: pathlib.Path, cards: dict, label: str) -> list[dict]:
    s = cards["settings"]
    output = []
    for case in cards["tasks"]:
        task = case["task"]
        d_args = [
            "discover", task, "--json", "--intent", s["intent"],
            "--limit", str(s["knowledge_limit"]),
        ]
        c_args = [
            "context", task, "--success", "Preserve existing, applicable project decisions",
            "--intent", s["intent"], "--risk", s["risk"],
            "--no-code", "--limit", str(s["knowledge_limit"]),
            "--token-budget", str(s["estimated_token_budget"]),
        ]
        discover = m0.run_json(target, d_args)
        context = m0.run_json(target, c_args)
        d = discover.get("data") if isinstance(discover.get("data"), dict) else {}
        e = context.get("data") if isinstance(context.get("data"), dict) else {}
        items = e.get("artifacts", []) if isinstance(e.get("artifacts"), list) else []
        raw_hits = d.get("results")
        hits = raw_hits if isinstance(raw_hits, list) else []
        errs = []
        if discover["returncode"] != 0 or context["returncode"] != 0:
            errs.append("installed CLI failed")
        if discover["returncode"] == 0:
            if not isinstance(discover.get("data"), dict):
                errs.append("successful Discover returned a non-object packet")
            if not isinstance(raw_hits, list):
                errs.append("successful Discover returned missing/non-array results")
            elif any(not pilot.valid_discovery_result(item) for item in raw_hits):
                errs.append("successful Discover returned malformed/unknown source hits")
        if context["returncode"] == 0:
            if not isinstance(context.get("data"), dict):
                errs.append("successful Context returned a non-object packet")
            errs.extend(validate_instance(e, SCHEMA))
        by_id = {x["id"]: x for x in cards["source_docs"]}
        # Discover emits a status for each result. Context deliberately
        # omits it: source-verify the selected artifact digest and its
        # original ADR status instead of inventing a missing Context field.
        for origin, records in (("Discover", hits), ("Context", items)):
            for x in records:
                if not isinstance(x, dict):
                    errs.append(f"non-object {origin} hit")
                    continue
                relative = x.get("path")
                if not isinstance(relative, str):
                    errs.append(f"{origin} hit lacks source path")
                    continue
                try:
                    file = safe_source(target, relative)
                    if origin == "Context" and x.get("sha256") != m0.digest_file(file):
                        errs.append(f"invalid selected content digest: {relative}")
                except (ValueError, OSError) as exc:
                    errs.append(f"missing/unsafe {origin} source {relative}: {exc}")
                ident = x.get("id")
                if ident is not None and (
                    ident not in by_id
                    or target_path(by_id[ident]) != relative
                    or x.get("artifact_type") != "decision"
                    or (origin == "Discover"
                        and x.get("status") != by_id[ident]["status"])
                ):
                    errs.append(f"forged or non-source {origin} authority: {ident}")
        selected = [
            {"id":x.get("id"), "path":x.get("path"),
             "reported_status":x.get("status"),
             "source_expected_status": (
                 by_id[x["id"]]["status"] if x.get("id") in by_id else None
             ),
             "artifact_type":x.get("artifact_type"), "sha256":x.get("sha256"),
             "estimated_tokens":x.get("estimated_tokens")}
            for x in items if isinstance(x, dict)
        ]
        trusted_current_ids: set[str] = set()
        for item in selected:
            ident, relative = item.get("id"), item.get("path")
            source = by_id.get(ident)
            if (not isinstance(ident, str) or source is None
                    or source["status"] != "implemented"
                    or item.get("artifact_type") != "decision"
                    or target_path(source) != relative):
                continue
            try:
                if item.get("sha256") == m0.digest_file(safe_source(target, relative)):
                    trusted_current_ids.add(ident)
            except (ValueError, OSError):
                pass
        claimed = e.get("decisions")
        if context["returncode"] == 0 and (
            not isinstance(claimed, list)
            or any(not isinstance(x, str) for x in claimed)
        ):
            errs.append("successful Context returned malformed decisions")
        claimed_ids = claimed if isinstance(claimed, list) else []
        for ident in claimed_ids:
            if ident not in trusted_current_ids:
                errs.append(
                    f"Decision ID lacks a matching selected, source-verified "
                    f"implemented artifact: {ident!r}"
                )
        verified_decisions = [
            ident for ident in claimed_ids if ident in trusted_current_ids
        ]
        output.append({
            "id":case["id"], "kind":case["kind"], "task":task, "arm":label,
            "discover_command": discover["command"],
            "discover_returncode": discover["returncode"],
            "discover_stderr": discover["stderr"], "discover_ms": discover["elapsed_ms"],
            "discover_hits": [
                {"id":x.get("id"), "path":x.get("path"),
                 "status":x.get("status"), "type":x.get("artifact_type")}
                for x in hits if isinstance(x, dict)
            ],
            "context_command":context["command"],
            "context_returncode":context["returncode"],
            "context_stderr":context["stderr"], "context_ms":context["elapsed_ms"],
            "selected":selected,
            "decisions":e.get("decisions", []),
            "source_verified_decisions":verified_decisions,
            "applicable_rules":e.get("applicable_rules", []),
            "budget":e.get("context_budget", {}),
            "schema_and_source_errors":errs,
        })
    return output


def score(report: dict, cases: dict) -> dict:
    # Oracle was frozen before the runner, and deliberately loaded only here
    # after BOTH installed-PACT arms have produced their entire raw outputs.
    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    tasks = cases["tasks"]
    expected = oracle.get("expected_current", {})
    if set(expected) != {x["id"] for x in tasks}:
        raise ValueError("frozen oracle case IDs do not match cards")
    target_count = sum(len(expected[x["id"]]) for x in tasks)
    by_id = {d["id"]: d for d in cases["source_docs"]}
    if target_count != 10 or any(
        not isinstance(ids, list)
        or any(ident not in by_id or by_id[ident]["status"] != "implemented"
               for ident in ids)
        for ids in expected.values()
    ):
        raise ValueError("invalid author-labelled reference targets")
    a = report["arms"]["A_unadapted"]
    b = report["arms"]["B_source_projection"]
    if [x["id"] for x in a] != [x["id"] for x in b]:
        raise ValueError("A/B cases were not executed in identical order")
    hits, extra, routine_noise = 0, 0, 0
    a_raw_target_hits = 0
    for x,y in zip(a,b):
        wanted = set(expected[y["id"]])
        got = set(y.get("source_verified_decisions", []))
        hits += len(wanted & got)
        extra += len(got - wanted)
        if y["kind"] == "routine-negative" and got:
            routine_noise += 1
        paths = {d["source"] for d in cases["source_docs"] if d["id"] in wanted}
        a_raw_target_hits += len(paths & {z["path"] for z in x["selected"]})
    return {
        "developer_target_count":target_count,
        "A_original_adr_document_target_hits":a_raw_target_hits,
        "B_current_decision_target_hits":hits,
        "B_extra_current_decision_slots":extra,
        "B_routine_cases_with_selected_decisions":routine_noise,
        "routine_case_count":2,
        "total_estimated_context_tokens":{
            "A":sum(x["budget"].get("selected_estimated_tokens", 0) for x in a),
            "B":sum(x["budget"].get("selected_estimated_tokens", 0) for x in b),
        },
        "total_context_wall_ms":{
            "A":sum(x["context_ms"] for x in a),
            "B":sum(x["context_ms"] for x in b),
        },
        "per_case":[
            {"id":y["id"], "developer_expected":expected[y["id"]],
             "A_original_doc_paths":[x["path"] for x in a[i]["selected"]
                                     if x["path"].startswith("docs/adr/")],
             "B_claimed_decisions":y["decisions"],
             "B_source_verified_decisions":y["source_verified_decisions"],
             "target_hit":bool(set(expected[y["id"]]) & set(y["source_verified_decisions"])),
             "B_extraneous":[id for id in y["source_verified_decisions"]
                              if id not in expected[y["id"]]]}
            for i,y in enumerate(b)
        ],
    }



def inspect_proposed_context(
    target: pathlib.Path, cards: dict, receipt: dict,
) -> dict:
    """Prove the standalone status guard received a valid source-bound Context.

    A bare `{"decisions":[]}` is NOT evidence that an unconfirmed ADR was
    handled safely. The response must pass the same envelope/source checks
    required of regular task Context, including all selected file digests.
    """
    errors: list[str] = []
    envelope = receipt.get("data")
    if receipt.get("returncode") != 0:
        errors.append("proposed-ADR Context lookup failed")
    if not isinstance(envelope, dict):
        errors.append("proposed-ADR Context returned non-object packet")
        envelope = {}
    else:
        errors.extend(validate_instance(envelope, SCHEMA))

    by_id = {doc["id"]: doc for doc in cards["source_docs"]}
    artifacts = envelope.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("proposed-ADR Context missing selected artifact array")
    else:
        for item in artifacts:
            if not isinstance(item, dict):
                errors.append("proposed-ADR Context selected malformed artifact")
                continue
            path, ident = item.get("path"), item.get("id")
            if not isinstance(path, str):
                errors.append("proposed-ADR Context artifact lacks source path")
                continue
            try:
                source = safe_source(target, path)
                if item.get("sha256") != m0.digest_file(source):
                    errors.append(f"proposed-ADR Context source digest invalid: {path}")
            except (ValueError, OSError) as exc:
                errors.append(f"proposed-ADR Context source invalid: {path}: {exc}")
            if ident is not None:
                pinned = by_id.get(ident)
                if (pinned is None or target_path(pinned) != path
                        or item.get("artifact_type") != "decision"):
                    errors.append(
                        f"proposed-ADR Context has unbound Decision source: {ident!r}"
                    )
    if envelope.get("decisions") != []:
        errors.append(
            "proposed-ADR lookup promoted a non-implemented Decision "
            "or returned a malformed Decision list"
        )
    return {
        "returncode": receipt.get("returncode"),
        "stderr": receipt.get("stderr"),
        "decisions": envelope.get("decisions"),
        "schema_and_source_errors": errors,
    }


def trial(target: pathlib.Path) -> dict:
    report: dict = {
        "kind":"developer-authored-not-blind-real-repository-installed-PACT",
        "source_repo":UPSTREAM,"source_sha":UPSTREAM_SHA,
        "pact_base":PACT_BASE,
        "independent_holdout":False,
        "real_agent_executed":False,"owner_approval_authenticated":False,
        "real_model_token_usage":None, "release_gate":"HOLD",
        "case_manifest_blob":CASES_BLOB,"developer_oracle_blob":ORACLE_BLOB,
        "stage":"initial","arms":{},"integrity_failures":[],
    }
    try:
        cards = verify_freeze(target)
        report["stage"] = "install-source-identical-PACT"
        report["install"] = pilot.install_pact(target)
        report["stage"] = "A-unadapted-source"
        report["arms"]["A_unadapted"] = run_arm(target, cards, "A_unadapted")
        report["stage"] = "B-project-source-projections"
        report["projected_source_sha256"] = project_sources(target,cards)
        report["stage"] = "verify-pact-check"
        check = subprocess.run(
            [sys.executable, str(target/"pact.py"), "check"],
            cwd=target, capture_output=True, text=True, timeout=120, check=False,
        )
        report["pact_check"] = {
            "returncode":check.returncode,
            "stdout":check.stdout[:2500], "stderr":check.stderr[:2500],
        }
        report["stage"] = "B-projected-source"
        report["arms"]["B_source_projection"] = run_arm(target,cards,"B_source_projection")
        report["stage"] = "verify-proposed-status"
        proposed = m0.run_json(target,[
            "context", "DEC-PF-0005", "--success",
            "Do not promote a proposed source ADR into a current decision",
            "--risk","low","--intent","history","--no-code","--limit","6",
        ])
        report["proposed_lookup"] = inspect_proposed_context(
            target, cards, proposed,
        )
        report["stage"] = "verify-original-source-unmodified"
        report["tracked_upstream_clean"] = not pilot.git_output(
            target, "status", "--porcelain", "--untracked-files=no"
        )
        report["source_blobs_unchanged"] = all(
            pilot.git_blob_sha(safe_source(target,d["source"])) == d["git_blob"]
            for d in cards["source_docs"]
        )
        expected_paths = {target_path(d) for d in cards["source_docs"]}
        actual_paths = {
            p.relative_to(target).as_posix()
            for p in (target/".agents/decisions").rglob("*.md")
        }
        report["only_frozen_projections_added"] = actual_paths == expected_paths
        report["projection_digests_unchanged"] = all(
            m0.digest_file(safe_source(target, path)) == digest
            for path,digest in report["projected_source_sha256"].items()
        )
        report["stage"] = "score-after-both-arms"
        report["developer_scoring"] = score(report,cards)
        failures = report["integrity_failures"]
        if check.returncode != 0:
            failures.append("source projection failed installed pact check")
        for label,records in report["arms"].items():
            if len(records)!=EXPECTED_COUNT:
                failures.append(f"{label} missing case output")
            for row in records:
                failures.extend(f"{label}/{row['id']}: {error}" for error in row["schema_and_source_errors"])
        failures.extend(
            "proposed-ADR standalone lookup: " + error
            for error in report["proposed_lookup"]["schema_and_source_errors"]
        )
        for key in ("tracked_upstream_clean","source_blobs_unchanged",
                    "only_frozen_projections_added","projection_digests_unchanged"):
            if not report[key]:
                failures.append(f"source/projection invariant violated: {key}")
        report["engineering_gate"]="PASS" if not failures else "FAIL"
        report["stage"]="done"
    except Exception as exc:
        report["integrity_failures"].append(f"{type(exc).__name__}: {exc}")
        report["exception_traceback"] = traceback.format_exc(limit=8)
        report["engineering_gate"]="FAIL"
    return report


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--target",required=True)
    args=ap.parse_args()
    target=pathlib.Path(args.target).resolve()
    report=trial(target)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report["engineering_gate"]=="PASS" else 2


if __name__=="__main__":
    raise SystemExit(main())
