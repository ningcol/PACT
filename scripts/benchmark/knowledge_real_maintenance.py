#!/usr/bin/env python3
"""No-model three-task PACT completion replay against a pinned public codebase.

This edits REAL upstream code/docs only in a disposable Actions clone. The
tasks and review judgments are PACT-evaluator-authored, not an independent
cold-start Agent/Owner trial. Each round exercises installed task prepare,
draft, verified pytest receipt, semantic-review bundle and task finish.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys

import brownfield_adr_viewer as pilot

ROOT = pathlib.Path(__file__).resolve().parents[2]
TASKS = (
    (
        "TASK-REAL-MAINT-001", "adr_viewer/parse.py",
        "from typing import Iterator, Optional, List",
        "from typing import Iterator, List, Optional",
        "Keep parser typing imports consistently ordered",
    ),
    (
        "TASK-REAL-MAINT-002", "adr_viewer/parse.py",
        'if any([line.startswith("Amended by") for line in statuses]):',
        'if any(line.startswith("Amended by") for line in statuses):',
        "Avoid a temporary list for the amended status predicate",
    ),
    (
        "TASK-REAL-MAINT-003", "README.md",
        "adr-viewer requires Python 3.7 or higher (with Pip)",
        "adr-viewer requires Python 3.7 or higher (with pip)",
        "Normalize Python package manager spelling in README",
    ),
)


def cli(target: pathlib.Path, *args: str) -> dict:
    process = subprocess.run(
        [sys.executable, str(target / "pact.py"), *args],
        cwd=target,
        capture_output=True, text=True, timeout=150, check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"pact {args[0]} failed {process.returncode}: "
            + (process.stderr or process.stdout)[-1800:]
        )
    if "--json" in args:
        try:
            return json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("PACT success response was not valid JSON") from exc
    return {"returncode": process.returncode}


def write_json(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", "utf-8")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def do_round(target: pathlib.Path, task: tuple, round_index: int) -> dict:
    task_id, source, before, after, title = task
    success = f"All upstream pytest tests pass after: {title}"
    prepared = cli(
        target, "task", "prepare", title,
        "--success", success,
        "--risk", "low", "--task-id", task_id, "--json",
    )
    if prepared.get("status") != "prepared":
        raise ValueError("task did not enter prepared state")
    contract = json.loads((target / prepared["contract"]).read_text("utf-8"))
    context = json.loads((target / prepared["context"]).read_text("utf-8"))
    acceptance_ids = [x["id"] for x in contract["acceptance_criteria"]]
    if acceptance_ids != ["AC-1"]:
        raise ValueError(f"unexpected acceptance contract {acceptance_ids}")
    cli(target, "task", "draft", task_id, "--json")

    file_path = target / source
    source_before = file_path.read_text("utf-8")
    if source_before.count(before) != 1:
        raise ValueError(f"source anchor changed or ambiguous: {source}")
    file_path.write_text(source_before.replace(before, after), "utf-8")
    if file_path.read_text("utf-8") == source_before:
        raise ValueError("maintenance task made no real source change")

    claim_id = f"EV-REAL-{round_index:03d}"
    claim = f"Upstream pytest suite exited successfully in {task_id}"
    cli(target, "task", "verify", task_id,
        "--criterion", "AC-1", "--claim-id", claim_id,
        "--claim", claim, "--kind", "test",
        "--source", "adr_viewer/test_parse.py",
        "--json", "--", sys.executable, "-m", "pytest", "-q")
    bundle = target / ".pact/completions" / task_id
    evidence = json.loads((bundle / "evidence.json").read_text("utf-8"))
    claims = [x for x in evidence["claims"] if x["id"] == claim_id]
    if len(claims) != 1 or claims[0]["status"] != "pass":
        raise ValueError("missing passing execution-backed pytest receipt")

    # In addition to selected Context artifacts, PACT can expose
    # source-bound but not materialized Decision hints. They are NOT
    # automatically applicable authority; however Task Finish requires the
    # Agent to inspect and disposition every one, even for routine edits.
    sources = {item["path"]: item for item in context["artifacts"]}
    for field in ("weak_decision_hints", "nonfunctional_decision_hints"):
        packet = context.get(field)
        if packet is None:
            continue
        if packet.get("truncated_candidates"):
            raise ValueError(f"{field} omitted sources; reprepare with more context")
        for item in packet.get("candidates", []):
            earlier = sources.get(item["path"])
            if earlier is not None and earlier["sha256"] != item["sha256"]:
                raise ValueError(f"conflicting fingerprint for {item['path']}")
            sources[item["path"]] = item

    scope = context.get("scope_route") or {}
    if scope.get("status") == "unique":
        for item in scope.get("candidates", []):
            earlier = sources.get(item["path"])
            if earlier is not None and earlier["sha256"] != item["sha256"]:
                raise ValueError(f"conflicting routed source: {item['path']}")
            sources[item["path"]] = item

    coverage = []
    for source_path, item in sorted(sources.items()):
        current_file = target / source_path
        if not current_file.is_file():
            raise ValueError(f"knowledge source vanished before review: {source_path}")
        changed = sha256(current_file) != item["sha256"]
        # The script physically reads and hashes the exact source; it cannot
        # independently establish semantic correctness or owner approval.
        body = current_file.read_text("utf-8")
        if not body.strip():
            raise ValueError("empty knowledge source cannot be certified as reviewed")
        coverage.append({
            "path": source_path,
            "disposition": "updated" if changed else "aligned",
            "rationale": (
                "Read the original source and checked the changed content against "
                "this narrow task; no new product authority was inferred"
                if changed else
                "Read source-bound current/historical knowledge; its original "
                "prepared source hash remains unchanged"
            ),
        })

    convergence = {
        "version": 1,
        "task_id": task_id, "change": title,
        "owner_summary": (
            "A small real-source maintenance edit was performed; the upstream "
            "test suite was executed and no normative PACT knowledge changed."
        ),
        "context_sha256": prepared["context_sha256"],
        "coverage": coverage,
        "change_coverage": [{
            "path": source,
            "rationale": "One targeted source/document wording edit; upstream pytest verified.",
        }],
        "evidence": [claim_id],
        "findings": [],
        "knowledge_retention": {
            "disposition": "none",
            "rationale": (
                "The source edit introduces no new product rule or non-derivable "
                "durable architectural trade-off. Existing Decisions stay intact."
            ),
            "updated": [], "created": [],
        },
    }
    report = {
        "version": 1, "task_id": task_id,
        "status": "completed",
        "summary": "Existing upstream tests passed after a small maintenance edit.",
        "before": "Original pinned implementation/documentation wording.",
        "after": "Narrowly changed wording/import expression, with test results recorded.",
        "verification": [{"claim": claim, "evidence_ids": [claim_id]}],
        "acceptance": [{
            "criterion_id": "AC-1",
            "summary": success,
            "evidence_ids": [claim_id],
        }],
        "consistency": {
            "status": "aligned",
            "summary": "Confirmed PACT Rule and Decision sources remain unchanged.",
        },
        "owner_decisions": [],
    }
    write_json(bundle / "convergence.json", convergence)
    write_json(bundle / "owner-report.json", report)
    finished = cli(
        target, "task", "finish", task_id,
        "--require-knowledge-retention", "--json",
    )
    if not finished.get("complete"):
        raise ValueError("task finish did not establish full completion")
    changed_files = finished["task_change"]["changed_files"]
    if changed_files != [source]:
        raise ValueError(f"task delta attributed unexpected files: {changed_files!r}")
    if finished["knowledge_retention"]["disposition"] != "none":
        raise ValueError("task finish changed the reviewed retention disposition")

    return {
        "task": task_id, "modified_source": source,
        "acceptance_verified": finished["acceptance"]["owner_report_covered"],
        "context_coverage": finished["convergence_coverage"]["covered_artifacts"],
        "context_required": finished["convergence_coverage"]["required_artifacts"],
        "changed_files": changed_files,
        "knowledge_retention": finished["knowledge_retention"]["disposition"],
        "test_receipt_count": len(claims[0]["evidence"]),
        "task_finished": finished["complete"],
    }


def run(target: pathlib.Path, progress: dict) -> dict:
    if pilot.git_output(target, "rev-parse", "HEAD") != pilot.EXPECTED_UPSTREAM_SHA:
        raise ValueError("external project is not pinned to the expected SHA")
    cards = json.loads(pilot.CARDS.read_text("utf-8"))
    if pilot.git_output(target, "remote", "get-url", "origin") not in {
        "https://github.com/mrwilson/adr-viewer.git",
        "https://github.com/mrwilson/adr-viewer",
    }:
        raise ValueError("unexpected upstream origin")
    if pilot.git_output(target, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("upstream code was already edited before the task replay")

    # The real source has no Git rules for generated Python/pytest caches.
    # Keep transient test output out of the task change envelope using a
    # TEST-WORKTREE-LOCAL exclude file. Never change the upstream .gitignore.
    exclude = target / ".git/info/exclude"
    if not exclude.is_file() or exclude.is_symlink():
        raise ValueError("expected a plain Git info/exclude file")
    current_exclude = exclude.read_text("utf-8")
    test_ignores = "\n# PACT disposable pilot: Python test caches only\n__pycache__/\n*.pyc\n.pytest_cache/\n"
    exclude.write_text(current_exclude + test_ignores, encoding="utf-8")

    # Earlier read-only knowledge replay has installed PACT and projected
    # source-authored ADRs; capture their content to detect any unrequested
    # long-term Decision change during REAL code maintenance.
    original = pilot.source_snapshot(target)
    if len([p for p in original if p.startswith(".agents/decisions/")]) != 6:
        raise ValueError("six projected existing Decisions required")
    if not (target / "pact.py").is_file():
        raise ValueError("installed PACT runtime missing")

    tasks = []
    for index, task in enumerate(TASKS, 1):
        progress["stage"] = task[0]
        observation = do_round(target, task, index)
        if pilot.source_snapshot(target) != original:
            raise ValueError(f"durable PACT knowledge changed in {task[0]}")
        tasks.append(observation)

    observed_paths = set(
        pilot.git_output(target, "diff", "--name-only").splitlines()
    )
    expected_paths = {"adr_viewer/parse.py", "README.md"}
    if observed_paths != expected_paths:
        raise ValueError(f"unexpected external tracked paths: {sorted(observed_paths)}")

    return {
        "version": 1,
        "kind": "real-source edits / installed PACT Task Contract and Finish / no-model",
        "source_repo": pilot.EXPECTED_UPSTREAM,
        "source_sha": pilot.EXPECTED_UPSTREAM_SHA,
        "round_count": len(tasks),
        "tasks": tasks,
        "modified_source_paths": sorted(observed_paths),
        "durable_decision_count_before": 6,
        "durable_decision_count_after": 6,
        "durable_decisions_unchanged": True,
        "new_confirmed_rules": 0,
        "replayed_real_tests": True,
        "real_coding_agent_executed": False,
        "independent_owner_oracle": False,
        "agent_decision_obedience_verified": False,
        "long_term_effectiveness_proven": False,
        "engineering_gate": "PASS",
        "gate_failures": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    progress = {}
    try:
        if os.environ.get("GITHUB_ACTIONS") != "true":
            raise ValueError("real-project code replay is restricted to CI runner")
        target = pathlib.Path(args.target).resolve(strict=True)
        runner = pathlib.Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
        if target == runner or not target.is_relative_to(runner):
            raise ValueError("target must be a disposable CI worktree")
        result = run(target, progress)
    except Exception as exc:
        result = {
            "version": 1,
            "engineering_gate": "FAIL",
            "gate_failures": [f"{type(exc).__name__}: {exc}"],
            "progress": progress,
            "real_coding_agent_executed": False,
            "agent_decision_obedience_verified": False,
        }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["engineering_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
