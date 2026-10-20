#!/usr/bin/env python3
"""PACT-only real-repository onboarding probe against a PINNED public clone.

The repo is real; task wording/oracle are developer-authored, NOT independently
withheld, and NO real LLM Agent changes or obeys a decision in this runner.
All PACT-generated source lives in the disposable cloned checkout only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

import decision_memory_m0 as m0


ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))
from schema_validate import validate_instance  # stdlib PACT schema validator

CONTEXT_SCHEMA = json.loads(
    (ROOT / ".pact" / "schema" / "context-envelope.schema.json").read_text(
        encoding="utf-8"
    )
)
CARDS = ROOT / "benchmarks" / "brownfield-adr-viewer" / "pilot-cards.json"
ORACLE = ROOT / "benchmarks" / "brownfield-adr-viewer" / "pilot-oracle.json"
CARDS_BLOB = "b4bc6e790b6b3777db1cb2983e476673280cc242"
ORACLE_BLOB = "896676e4ba74bd84a54c511f82b8a9d639593ff0"
EXPECTED_UPSTREAM = "mrwilson/adr-viewer"
EXPECTED_UPSTREAM_SHA = "a25f1c71e031bdaa63fe3175f969f197139f2044"
EXPECTED_BASELINE_SHA = "4c7416f2c24375fa61929e80b135a66036cf1320"
SOURCE_REL = (".agents/decisions", "docs/product/rules")
ID = re.compile(r"^DEC-ADR-\d{4}$")


def git_blob_sha(path: pathlib.Path) -> str:
    # Commit SHA is over canonical LF bytes even on Windows CRLF worktrees.
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\x00" + data
    ).hexdigest()


def git_output(target: pathlib.Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(target), *args],
        text=True, capture_output=True, check=False, timeout=30,
    )
    if result.returncode:
        raise RuntimeError(f"git {args[0]} failed: {result.stderr[:300]}")
    return result.stdout.strip()


def source_snapshot(target: pathlib.Path) -> dict[str, str]:
    files: list[pathlib.Path] = []
    for prefix in SOURCE_REL:
        folder = target / prefix
        if folder.is_dir():
            files.extend(path for path in folder.rglob("*")
                         if path.is_file() or path.is_symlink())
    result: dict[str, str] = {}
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(target.resolve()):
            raise ValueError("knowledge path escaped temporary checkout")
        result[path.relative_to(target).as_posix()] = m0.digest_file(path)
    return dict(sorted(result.items()))


def validate_frozen(cards: dict, target: pathlib.Path) -> None:
    if git_blob_sha(CARDS) != CARDS_BLOB:
        raise ValueError("frozen public-repository cards changed")
    if cards.get("version") != 1 or cards.get("upstream") != EXPECTED_UPSTREAM:
        raise ValueError("unexpected brownfield fixture")
    if (cards.get("upstream_commit") != EXPECTED_UPSTREAM_SHA
            or cards.get("pact_parent_sha") != EXPECTED_BASELINE_SHA):
        raise ValueError("pinned GitHub/Pact SHA mismatch")
    if len(cards.get("upstream_docs", [])) != 6 or len(cards.get("tasks", [])) != 6:
        raise ValueError("expected six original source ADRs and six frozen tasks")
    if cards.get("settings") != {
        "intent": "work", "knowledge_limit": 4, "estimated_token_budget": 2048,
        "risk": "low", "code_context": False
    }:
        raise ValueError("frozen discovery and materialization budget changed")
    tids = [x["id"] for x in cards["tasks"]]
    if len(set(tids)) != len(tids):
        raise ValueError("duplicate case")
    identities = [d["id"] for d in cards["upstream_docs"]]
    if len(set(identities)) != 6 or not all(ID.fullmatch(v) for v in identities):
        raise ValueError("duplicate or invalid projected Decision IDs")
    if any("DEC-ADR-" in x["task"] or not x["task"].strip() for x in cards["tasks"]):
        raise ValueError("frozen task leaks a Decision ID")
    if any(d.get("status") not in {"implemented", "superseded"}
           for d in cards["upstream_docs"]):
        raise ValueError("invalid original decision status")
    if git_output(target, "rev-parse", "HEAD") != EXPECTED_UPSTREAM_SHA:
        raise ValueError("GitHub clone not at pinned external commit")
    remote = git_output(target, "remote", "get-url", "origin")
    if remote not in {
        "https://github.com/mrwilson/adr-viewer.git",
        "https://github.com/mrwilson/adr-viewer",
    }:
        raise ValueError(f"incorrect source remote: {remote}")
    if git_output(target, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("external repository tracked files already modified")
    for doc in cards["upstream_docs"]:
        relative = doc["source"]
        if (
            not isinstance(relative, str)
            or not re.fullmatch(r"doc/adr/000[1-6]-[a-z0-9-]+\.md", relative)
            or doc["id"] != "DEC-ADR-" + relative.split("/")[-1][:4]
        ):
            raise ValueError(f"unsafe frozen ADR source path: {relative!r}")
        source = target / relative
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"source ADR absent {relative}")
        if git_blob_sha(source) != doc["git_blob"]:
            raise ValueError(f"source ADR content no longer matches pin: {relative}")


def rebase_legacy_adr_links(original: str) -> str:
    """Keep original ADR text/labels, adjust ONLY relative Markdown link targets.

    Original doc/adr/ siblings are relative to that directory. The test-only
    PACT copy lives three directories deep under .agents/decisions/{status}/.
    Leaving URLs unchanged makes the installed PACT link-integrity check fail.
    We do not edit any original ADR, change heading text, or add task aliases.
    """
    return re.sub(
        r"(\]\()(000[1-6]-[a-z0-9-]+\.md)(\))",
        lambda match: match.group(1) + "../../../doc/adr/" +
        match.group(2) + match.group(3),
        original,
    )


def render_adapted_original(doc: dict, source_text: str) -> str:
    """No new aliases, paths, domain hypotheses or invented Owner approval."""
    match = re.search(r"^#\s+(.+)$", source_text, flags=re.MULTILINE)
    if not match:
        raise ValueError("original ADR missing title")
    status = doc["status"]
    if "\n## Status\n\n" not in source_text:
        raise ValueError("original ADR missing explicit status")
    source_status = source_text.split("\n## Status\n\n", 1)[1].split("\n", 1)[0].strip()
    if status == "implemented" and source_status != "Accepted":
        raise ValueError("attempted to upgrade source-unaccepted ADR")
    if status == "superseded" and not source_status.startswith("Superseded by"):
        raise ValueError("attempted to reinterpret non-superseded ADR")
    lines = [
        "+++", "[pact]", 'type = "decision"',
        "id = " + json.dumps(doc["id"]),
        "status = " + json.dumps(status),
        'aliases = []', 'paths = []', 'domains = []', 'related = []',
        "supersedes = [" + ", ".join(json.dumps(x) for x in doc.get("supersedes", [])) + "]",
    ]
    if "superseded_by" in doc:
        lines.append("superseded_by = " + json.dumps(doc["superseded_by"]))
    return "\n".join([
        *lines, "+++", "", "# " + match.group(1), "",
        "Source (unchanged, project-authored): " + doc["source"],
        "Test-only projection of source ADR; not authenticated PACT Owner approval.",
        "Original prose retained; relative Markdown link targets are rebased in this copy.",
        "", rebase_legacy_adr_links(source_text.rstrip()), "",
    ])


def verify_installed_runtime_against_source(installed_archive: pathlib.Path) -> dict:
    """Rebuild from *this checkout* in a fresh scratch dir and compare exact bytes."""
    if not installed_archive.is_file() or installed_archive.is_symlink():
        raise ValueError("installed compact PACT archive is missing or symlinked")
    with tempfile.TemporaryDirectory(prefix="pact-brownfield-source-bundle-") as td:
        expected = pathlib.Path(td) / "source-rebuilt.pyz"
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "pact" / "runtime_bundle.py"),
             "--source-root", str(ROOT), "--output", str(expected)],
            cwd=ROOT, capture_output=True, text=True, check=False, timeout=90,
        )
        if completed.returncode or not expected.is_file():
            raise RuntimeError("cannot build trusted source PACT runtime: " +
                               completed.stderr[:500])
        expected_sha = m0.digest_file(expected)
    actual_sha = m0.digest_file(installed_archive)
    if actual_sha != expected_sha:
        raise ValueError(
            "installed PACT compact runtime differs from exact source checkout "
            f"(installed={actual_sha}, expected={expected_sha})"
        )
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT,
        capture_output=True, text=True, check=False, timeout=15,
    )
    return {
        "source_checkout_git_sha": revision.stdout.strip() if revision.returncode == 0 else None,
        "installed_archive_sha256": actual_sha,
        "source_rebuilt_archive_sha256": expected_sha,
        "installed_source_match": True,
    }


def install_pact(target: pathlib.Path) -> dict:
    call = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "pact" / "init.py"),
         "--target", str(target), "--apply"],
        cwd=ROOT, text=True, capture_output=True, timeout=120, check=False,
    )
    installed = target / "pact.py"
    archives = list((target / ".pact").rglob("*.pyz"))
    if call.returncode != 0 or not installed.is_file() or len(archives) != 1:
        raise RuntimeError(
            "PACT installation failed or installed runtime is not unique: " +
            (call.stderr + call.stdout)[:1000]
        )
    identity = verify_installed_runtime_against_source(archives[0])
    return {"pact_loader": True, "installed_pyz_count": len(archives),
            "installed_pyz_relative": archives[0].relative_to(target).as_posix(),
            "init_returncode": call.returncode, **identity}


def project_adrs(target: pathlib.Path, cards: dict) -> list[str]:
    paths = []
    for doc in cards["upstream_docs"]:
        source = target / doc["source"]
        subdir = "superseded" if doc["status"] == "superseded" else "implemented"
        destination = target / ".agents" / "decisions" / subdir / (
            doc["id"].lower() + ".md"
        )
        if destination.exists() or destination.is_symlink():
            raise ValueError("target Decision path already exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            render_adapted_original(doc, source.read_text(encoding="utf-8")),
            encoding="utf-8",
        )
        paths.append(destination.relative_to(target).as_posix())
    return paths


def valid_discovery_result(record: object) -> bool:
    if not isinstance(record, dict):
        return False
    path = record.get("path")
    if (not isinstance(path, str) or not path or chr(92) in path
            or pathlib.PurePosixPath(path).is_absolute()
            or ".." in pathlib.PurePosixPath(path).parts):
        return False
    kind = record.get("artifact_type")
    if kind == "document":
        return record.get("id") is None and record.get("status") is None
    if kind in {"decision", "rule"}:
        ident, status = record.get("id"), record.get("status")
        return (isinstance(ident, str)
                and ident.startswith("DEC-" if kind == "decision" else "RULE-")
                and isinstance(status, str) and bool(status))
    return False


def valid_context_artifact(record: object) -> bool:
    if not isinstance(record, dict):
        return False
    path, sha = record.get("path"), record.get("sha256")
    if (not isinstance(path, str) or not path or chr(92) in path
            or pathlib.PurePosixPath(path).is_absolute()
            or ".." in pathlib.PurePosixPath(path).parts
            or not isinstance(sha, str) or
            re.fullmatch(r"[0-9a-f]{64}", sha) is None):
        return False
    kind, ident = record.get("artifact_type"), record.get("id")
    if kind == "document":
        return ident is None
    if kind in {"decision", "rule"}:
        return isinstance(ident, str) and ident.startswith(
            "DEC-" if kind == "decision" else "RULE-"
        )
    return False


def projected_decision_paths(cards: dict) -> dict[str, str]:
    return {
        doc["id"]: (
            ".agents/decisions/" +
            ("superseded" if doc["status"] == "superseded" else "implemented") +
            "/" + doc["id"].lower() + ".md"
        )
        for doc in cards["upstream_docs"]
    }


def verify_installed_probe_sources(
    target: pathlib.Path, cards: dict, hits: list, selected: list,
) -> list[str]:
    """All returned sources must exist; typed IDs must refer to exact projections."""
    failures = []
    by_id = projected_decision_paths(cards)
    by_status = {doc["id"]: doc["status"] for doc in cards["upstream_docs"]}
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        path, ident = hit.get("path"), hit.get("id")
        if ident is not None and (
            by_id.get(ident) != path
            or hit.get("artifact_type") != "decision"
            or hit.get("status") != by_status.get(ident)
        ):
            failures.append(
                f"Discover has forged Decision ID/source/status: {ident!r} {path!r}"
            )
        if isinstance(path, str):
            try:
                source = m0.safe_file(target, path)
                if not source.is_file():
                    raise ValueError("missing source")
            except (OSError, ValueError) as exc:
                failures.append(f"Discover hit has missing source: {path!r}: {exc}")
    for item in selected:
        if not isinstance(item, dict):
            continue
        path, ident = item.get("path"), item.get("id")
        if ident is not None and by_id.get(ident) != path:
            failures.append(f"Context has forged Decision ID/source: {ident!r} {path!r}")
        if isinstance(path, str):
            try:
                source = m0.safe_file(target, path)
                if (not source.is_file() or
                        m0.digest_file(source) != item.get("sha256")):
                    raise ValueError("source SHA mismatch")
            except (OSError, ValueError) as exc:
                failures.append(f"Context source invalid: {path!r}: {exc}")
    return failures


def verify_weak_decision_hints(
    target: pathlib.Path, cards: dict, envelope: dict,
) -> list[str]:
    """Authenticate deferred navigation metadata against original source."""
    group = envelope.get("weak_decision_hints")
    if group is None:
        return []
    errs: list[str] = []
    if not isinstance(group, dict):
        return ["Weak Context hint metadata is not an object"]
    candidates = group.get("candidates")
    total, truncated = group.get("total_candidates"), group.get("truncated_candidates")
    if (not isinstance(candidates, list)
            or type(total) is not int or type(truncated) is not int
            or total < 0 or truncated < 0 or total != len(candidates) + truncated
            or len(candidates) > 5):
        return ["Weak Context hint count and truncation are inconsistent"]
    known = {doc["id"]: doc for doc in cards["upstream_docs"]}
    paths = projected_decision_paths(cards)
    seen = set()
    for item in candidates:
        if not isinstance(item, dict):
            errs.append("Weak Context hint is not an object")
            continue
        ident, relative = item.get("id"), item.get("path")
        doc = known.get(ident)
        if (doc is None or paths.get(ident) != relative
                or item.get("status") != doc["status"]
                or relative in seen):
            errs.append("Weak Context hint lacks original Decision source identity")
            continue
        seen.add(relative)
        try:
            file = m0.safe_file(target, relative)
            if (file.is_symlink() or not file.is_file()
                    or m0.digest_file(file) != item.get("sha256")):
                raise ValueError("source hash mismatch")
        except (ValueError, OSError) as exc:
            errs.append(f"Weak Context hint source invalid: {relative!r}: {exc}")
    return errs


def probe(
    target: pathlib.Path, cards: dict, result: list[dict] | None = None,
    *, in_flight: dict | None = None,
) -> list[dict]:
    """Collect installed CLI evidence; optional sink preserves an interrupted case."""
    settings = cards["settings"]
    if result is None:
        result = []
    for case in cards["tasks"]:
        task = case["task"]
        d_args = [
            "discover", task, "--intent", settings["intent"], "--json",
            "--limit", str(settings["knowledge_limit"]),
        ]
        if in_flight is not None:
            in_flight.clear()
            in_flight.update({"id": case["id"], "stage": "discover",
                              "command": ["pact.py", *d_args]})
        discovery = m0.run_json(target, d_args)
        if in_flight is not None:
            in_flight.update({"stage": "context", "discovery": discovery})
        c_args = [
            "context", task,
            "--success", "Preserve documented project decisions when applicable",
            "--intent", settings["intent"], "--risk", settings["risk"],
            "--no-code", "--limit", str(settings["knowledge_limit"]),
            "--token-budget", str(settings["estimated_token_budget"]),
        ]
        if in_flight is not None:
            in_flight["command"] = ["pact.py", *c_args]
        context = m0.run_json(target, c_args)
        if in_flight is not None:
            in_flight.update({"stage": "normalize", "context": context})
        disc = discovery["data"] if isinstance(discovery["data"], dict) else {}
        envelope = context["data"] if isinstance(context["data"], dict) else {}
        discovery_schema_errors = []
        context_schema_errors = []
        if discovery["returncode"] == 0:
            if not isinstance(discovery["data"], dict):
                discovery_schema_errors.append("successful discovery response is not an object")
            if not isinstance(disc.get("results"), list) or any(
                not valid_discovery_result(v) for v in disc.get("results", [])
            ):
                discovery_schema_errors.append("successful discovery results contain malformed entries")
        if context["returncode"] == 0:
            if not isinstance(context["data"], dict):
                context_schema_errors.append("successful Context response is not an object")
            for key in ("artifacts", "decisions", "applicable_rules", "code_artifacts", "known_unknowns"):
                if not isinstance(envelope.get(key), list):
                    context_schema_errors.append(f"Context {key} not a list")
            if not isinstance(envelope.get("context_budget"), dict):
                context_schema_errors.append("Context budget not an object")
            context_schema_errors.extend(validate_instance(envelope, CONTEXT_SCHEMA))
        budget = envelope.get("context_budget")
        if not isinstance(budget, dict):
            budget = {}
        selected = envelope.get("artifacts")
        if not isinstance(selected, list):
            selected = []
        if any(not valid_context_artifact(v) for v in selected):
            context_schema_errors.append("Context artifacts have malformed source/path/type/digest")
            selected = [v for v in selected if isinstance(v, dict)]
        source_errors = verify_installed_probe_sources(
            target, cards,
            disc.get("results", []) if isinstance(disc.get("results"), list) else [],
            selected,
        )
        discovery_schema_errors.extend(
            x for x in source_errors if x.startswith("Discover ")
        )
        context_schema_errors.extend(
            x for x in source_errors if x.startswith("Context ")
        )
        context_schema_errors.extend(
            verify_weak_decision_hints(target, cards, envelope)
        )
        result.append({
            "id": case["id"], "task": task, "kind": case["kind"],
            "discovery": {
                "command": discovery["command"],
                "returncode": discovery["returncode"],
                "elapsed_ms": discovery["elapsed_ms"],
                "stderr": discovery["stderr"],
                "stdout_excerpt": discovery.get("stdout_excerpt", ""),
                "schema_errors": discovery_schema_errors,
                "hits": [
                    {"id": x.get("id"), "status": x.get("status"),
                     "type": x.get("artifact_type"), "path": x.get("path")}
                    for x in disc.get("results", []) if isinstance(x, dict)
                ],
            },
            "context": {
                "command": context["command"],
                "returncode": context["returncode"],
                "elapsed_ms": context["elapsed_ms"],
                "stderr": context["stderr"],
                "stdout_excerpt": context.get("stdout_excerpt", ""),
                "schema_errors": context_schema_errors,
                "status": envelope.get("status"),
                "selected_ids": [x.get("id") for x in selected if isinstance(x, dict)],
                "selected_artifacts": [
                    {"id": x.get("id"), "path": x.get("path"),
                     "artifact_type": x.get("artifact_type"),
                     "sha256": x.get("sha256")}
                    for x in selected if isinstance(x, dict)
                ],
                "current_decision_ids": envelope.get("decisions") or [],
                **({"weak_decision_hints": envelope["weak_decision_hints"]}
                   if "weak_decision_hints" in envelope else {}),
                "applicable_rule_ids": envelope.get("applicable_rules") or [],
                "selected_knowledge_files": len(selected),
                "estimated_selected_tokens": budget.get("selected_estimated_tokens"),
                "code_context_selected": len(envelope.get("code_artifacts") or []),
                "known_unknowns": envelope.get("known_unknowns") or [],
            },
        })
        if in_flight is not None:
            in_flight.clear()
    return result


def score(predictions: dict, cards: dict, oracle: dict) -> dict:
    if git_blob_sha(ORACLE) != ORACLE_BLOB:
        raise ValueError("frozen pilot oracle hash changed")
    case_ids = [case["id"] for case in cards["tasks"]]
    if set(oracle.get("expected_current", {})) != set(case_ids) or set(
        oracle.get("history_for_review", {})
    ) != set(case_ids):
        raise ValueError("frozen oracle case denominator mismatch")
    known_status = {doc["id"]: doc["status"] for doc in cards["upstream_docs"]}
    if len(predictions["A_plain_legacy"]) != len(case_ids) or len(
        predictions["B_adapted"]
    ) != len(case_ids):
        raise ValueError("missing raw predictions")
    failures = []
    if not predictions["unmodified_tracked_sources"]:
        failures.append("original upstream tracked files changed")
    if len(predictions["projected_paths"]) != 6:
        failures.append("projected ADR source count incorrect")
    if predictions["knowledge_after"] != predictions["knowledge_expected"]:
        failures.append("long-term memory changed during probe")
    if predictions["project_check_returncode"] != 0:
        failures.append("installed project check failed")
    targets = 0
    b_hits = 0
    extras = 0
    b_current_candidates = 0
    cards_output = []
    for i, cid in enumerate(case_ids):
        a = predictions["A_plain_legacy"][i]
        b = predictions["B_adapted"][i]
        if a["id"] != cid or b["id"] != cid:
            raise ValueError("predictions reordered; denominator contaminated")
        expected = set(oracle["expected_current"][cid])
        targets += len(expected)
        found = set(b["context"]["current_decision_ids"])
        b_hits += len(expected & found)
        b_current_candidates += len(found)
        unexpected = sorted(found - expected)
        extras += len(unexpected)
        for phase, rec in (("A", a), ("B", b)):
            context = rec["context"]
            if rec["discovery"]["returncode"] or context["returncode"]:
                failures.append(f"{cid}/{phase}: CLI failure")
            if rec["discovery"].get("schema_errors") or context.get("schema_errors"):
                failures.append(f"{cid}/{phase}: malformed successful CLI payload")
            if context["status"] != "candidate":
                failures.append(f"{cid}/{phase}: unexpected authority envelope")
            if context["selected_knowledge_files"] > cards["settings"]["knowledge_limit"]:
                failures.append(f"{cid}/{phase}: knowledge count exceeded")
            if context["code_context_selected"]:
                failures.append(f"{cid}/{phase}: no-code boundary violated")
            decisions = context["current_decision_ids"]
            if not isinstance(decisions, list) or any(
                known_status.get(ident) != "implemented" for ident in decisions
            ):
                failures.append(f"{cid}/{phase}: historical or unknown Decision promoted")
            if any(ident not in set(context["selected_ids"]) for ident in decisions):
                failures.append(f"{cid}/{phase}: unmaterialized Decision claimed")
            if context["applicable_rule_ids"]:
                failures.append(f"{cid}/{phase}: unexpected applicable Product Rules")
            tokens = context["estimated_selected_tokens"]
            if not isinstance(tokens, int) or tokens > cards["settings"]["estimated_token_budget"]:
                failures.append(f"{cid}/{phase}: invalid/over-budget Context estimate")
        cards_output.append({
            "id": cid,
            "A_current_decisions": a["context"]["current_decision_ids"],
            "B_target_hits": sorted(found & expected),
            "B_target_missing": sorted(expected - found),
            "B_unexpected_current": unexpected,
            "B_related_history_discovery": sorted(
                set(oracle["history_for_review"][cid]) &
                {v["id"] for v in b["discovery"]["hits"]}
            ),
            "A_estimated_tokens": a["context"]["estimated_selected_tokens"],
            "B_estimated_tokens": b["context"]["estimated_selected_tokens"],
            "A_context_elapsed_ms": a["context"]["elapsed_ms"],
            "B_context_elapsed_ms": b["context"]["elapsed_ms"],
            "decision_obedience": "unverified",
        })
    if any(r["context"]["current_decision_ids"] for r in predictions["A_plain_legacy"]):
        failures.append("unadapted legacy files unexpectedly promoted into Decisions")
    routine_bad = [
        r["id"] for r in cards_output
        if not oracle["expected_current"][r["id"]] and r["B_unexpected_current"]
    ]
    return {
        "version": 1,
        "kind": "real GitHub repo / synthetic task / installed PACT engineering evaluation",
        "upstream": cards["upstream"], "upstream_sha": cards["upstream_commit"],
        "frozen_card_blob": CARDS_BLOB, "frozen_oracle_blob": ORACLE_BLOB,
        "case_count": len(case_ids), "target_decision_count": targets,
        "A_unadapted_current_hits": sum(
            len(x["context"]["current_decision_ids"]) for x in
            predictions["A_plain_legacy"]
        ),
        "B_adapted_matched": b_hits,
        "B_adapted_target_recall_proxy": b_hits / targets if targets else None,
        "B_total_selected_current_candidates": b_current_candidates,
        "B_oracle_extraneous_current_candidates": extras,
        "B_candidate_precision_proxy": b_hits / b_current_candidates
        if b_current_candidates else None,
        "B_routine_false_injection_case_ids": routine_bad,
        "projection_added_long_term_files": len(predictions["projected_paths"]),
        "projected_decisions_are_test_interpretations_not_owner_approvals": True,
        "upstream_tracked_files_modified": not predictions["unmodified_tracked_sources"],
        "engineering_safety_gate": "PASS" if not failures else "FAIL",
        "safety_gate_failures": failures,
        "retrieval_effectiveness": "DIAGNOSTIC_ONLY" if (
            b_hits == targets and not routine_bad
        ) else "HOLD",
        "real_agent_executed": False,
        "independently_withheld_oracle": False,
        "owner_approval_authenticated": False,
        "agent_semantic_obedience_verified": False,
        "real_model_tokens": None, "owner_clarification_count": None,
        "owner_time_minutes": None, "release_gate": "HOLD",
        "install": predictions["install"],
        "evaluated_source_checkout_git_sha": predictions["install"].get("source_checkout_git_sha"),
        "evaluated_installed_runtime_sha256": predictions["install"].get("installed_archive_sha256"),
        "pact_project_check_returncode": predictions["project_check_returncode"],
        "cases": cards_output,
        "raw_probes": predictions,
    }


def evaluate(target: pathlib.Path, cards: dict, progress: dict | None = None) -> dict:
    if progress is None:
        progress = {}
    progress["stage"] = "source-validation"
    validate_frozen(cards, target)
    original_hashes = {
        doc["source"]: m0.digest_file(target / doc["source"])
        for doc in cards["upstream_docs"]
    }
    install = install_pact(target)
    progress["install"] = install
    progress["stage"] = "legacy-probing"
    knowledge_baseline = source_snapshot(target)
    if knowledge_baseline:
        raise ValueError("unexpected initial long-term Decision files in target")
    # Collect all original-ADR behavior before adapting any note or reading oracle.
    progress["A_plain_legacy"] = []
    a = probe(target, cards, progress["A_plain_legacy"])
    progress["stage"] = "projection"
    projected = project_adrs(target, cards)
    progress["projected_paths"] = projected
    snapshot = source_snapshot(target)
    progress["stage"] = "installed-project-check"
    check = subprocess.run(
        [sys.executable, str(target / "pact.py"), "check"],
        cwd=target, capture_output=True, text=True, timeout=120, check=False,
    )
    progress["project_check_returncode"] = check.returncode
    progress["project_check_stdout"] = check.stdout[:1200]
    progress["project_check_stderr"] = check.stderr[:1200]
    progress["knowledge_expected"] = snapshot
    progress["stage"] = "adapted-probing"
    progress["B_adapted"] = []
    b = probe(target, cards, progress["B_adapted"])
    progress["stage"] = "source-verification"
    final_snapshot = source_snapshot(target)
    still_original = (
        not git_output(target, "status", "--porcelain", "--untracked-files=no")
        and all(m0.digest_file(target / p) == h for p, h in original_hashes.items())
    )
    return {
        "install": install, "A_plain_legacy": a, "B_adapted": b,
        "projected_paths": projected,
        "knowledge_expected": snapshot,
        "knowledge_after": final_snapshot,
        "knowledge_before": knowledge_baseline,
        "unmodified_tracked_sources": still_original,
        "project_check_returncode": check.returncode,
        "project_check_stdout": check.stdout[:1200] if check.returncode else "",
        "project_check_stderr": check.stderr[:1200] if check.returncode else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    evidence = None  # Keep completed installed-CLI probes even if scoring fails.
    progress: dict = {}
    try:
        if os.environ.get("GITHUB_ACTIONS") != "true":
            raise ValueError("run only on isolated GitHub Actions temp runner")
        target = pathlib.Path(args.target).resolve(strict=True)
        runner_temp = pathlib.Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
        if target == runner_temp or not target.is_relative_to(runner_temp):
            raise ValueError("must use a disposable checkout inside RUNNER_TEMP")
        cards = json.loads(CARDS.read_text(encoding="utf-8"))
        evidence = evaluate(target, cards, progress)
        # Public developer-authored oracle read only AFTER all calls and inputs.
        oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
        report = score(evidence, cards, oracle)
    except Exception as exc:
        interrupted = None
        if isinstance(exc, subprocess.TimeoutExpired):
            def decode_buffer(value):
                if isinstance(value, bytes):
                    return value.decode("utf-8", errors="replace")[:2000]
                return str(value or "")[:2000]
            interrupted = {
                "command": exc.cmd if isinstance(exc.cmd, (str, list, tuple))
                else str(exc.cmd),
                "timeout_seconds": exc.timeout,
                "stdout_excerpt": decode_buffer(exc.stdout),
                "stderr_excerpt": decode_buffer(exc.stderr),
            }
        report = {
            "version": 1,
            "kind": "real GitHub clone installed PACT engineering probe",
            "engineering_safety_gate": "FAIL",
            "safety_gate_failures": [f"{type(exc).__name__}: {exc}"],
            "interrupted_subprocess": interrupted,
            "raw_probes": evidence if evidence is not None else (progress or None),
            "completed_probes_preserved": bool(evidence is not None or progress.get("A_plain_legacy") or progress.get("B_adapted")),
            "partial_collection_failed": evidence is None,
            "real_agent_executed": False,
            "owner_approval_authenticated": False,
            "release_gate": "HOLD",
        }
    # Print the entire JSON BEFORE a nonzero exit so GitHub CI retains evidence.
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["engineering_safety_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
