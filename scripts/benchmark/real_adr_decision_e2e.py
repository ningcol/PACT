#!/usr/bin/env python3
"""Three real source-maintenance tasks against pinned adr-viewer, isolated in CI.

No LLM runner or real Owner is invoked. Edits and semantic reviews are
evaluator-authored; PACT's mechanical gates and pytest use the installed runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import brownfield_adr_viewer as pilot

TASKS = [
    dict(id="TASK-E2E-A11Y", title="Preserve readable ADR status in addition to color and icon",
         success="Visible status text regression passes",
         accept="Complete upstream pytest suite passes",
         file="adr_viewer/test_render.py",
         changes=["adr_viewer/templates/index.html", "adr_viewer/test_render.py"],
         queries=["Accessibility will now be a first-class concern",
                  "Distinguish amendments to records with colour"], risk="medium"),
    dict(id="TASK-E2E-ORDERED", title="Parse ordered Status lists without conflating amended and superseded",
         success="Ordered-list status regression passes",
         accept="Complete upstream pytest suite passes",
         file="adr_viewer/test_parse.py",
         changes=["adr_viewer/parse.py", "adr_viewer/test_parse.py"],
         queries=["Distinguish superseded records with colour",
                  "Distinguish amendments to records with colour"], risk="medium"),
    dict(id="TASK-E2E-CLI", title="Protect CLI HTML output of historical record statuses",
         success="Real CLI contract regression passes",
         accept="Complete upstream pytest suite passes",
         file="adr_viewer/test_cli_contract.py",
         changes=["adr_viewer/test_cli_contract.py"],
         queries=["Expose command line interface",
                  "Accessibility will now be a first-class concern"], risk="high"),
]

LABEL_OLD = '                        {% endif %}\n\n                    </h4>'
LABEL_NEW = ('                        {% endif %}\n'
             '                        <span class="adr-status">Status: {{ adr_record.status|capitalize }}</span>\n\n'
             '                    </h4>')
PARSE_OLD = '''    if status_section and status_section.nextSibling:
        current_node = status_section.nextSibling

        while current_node.name != "h2" and current_node.nextSibling:
            current_node = current_node.nextSibling

            if current_node.name == "p":
                yield current_node.text
            elif current_node.name == "ul":
                yield from (li.text for li in current_node.children if li.name == "li")
            else:
                continue'''
PARSE_NEW = '''    if status_section:
        current_node = status_section.next_sibling
        while current_node is not None and current_node.name != "h2":
            if current_node.name == "p":
                yield current_node.get_text()
            elif current_node.name in ("ul", "ol"):
                yield from (li.get_text() for li in current_node.children if li.name == "li")
            current_node = current_node.next_sibling'''

RENDER_TEST = '''

def test_visible_accessible_status_labels_preserve_all_states():
    from bs4 import BeautifulSoup
    states = ["accepted", "superseded", "amended", "pending", "unknown"]
    records = [Adr(f"Record {s}", s, "body", index=i) for i, s in enumerate(states)]
    html = render_html(AdrTemplateConfig(project_title="status", records=records))
    page = BeautifulSoup(html, "html.parser")
    for state in states:
        heading = page.select_one(f".panel-heading.adr-{state}")
        assert heading is not None
        label = heading.select_one(".adr-status")
        assert label is not None
        assert label.get_text(" ", strip=True) == f"Status: {state.capitalize()}"
        assert heading.select_one("i.adr-icon") is not None
'''
PARSE_TEST = '''

def test_ordered_status_list_keeps_amended_and_superseded_distinct():
    for raw, expected in [
        ("Accepted", "accepted"),
        ("Superseded by ADR 4", "superseded"),
        ("Amended by ADR 5", "amended"),
        ("Pending", "pending"),
    ]:
        adr = parse_adr(f"# Minimal ADR\\n\\n## Status\\n\\n1. {raw}\\n")
        assert adr is not None
        assert adr.status == expected
'''
CLI_TEST = '''from bs4 import BeautifulSoup
from click.testing import CliRunner
from adr_viewer import main


def test_cli_generates_real_adr_status_labels(tmp_path):
    output = tmp_path / "output.html"
    result = CliRunner().invoke(main, [
        "--adr-path", "doc/adr", "--output", str(output), "--title", "Architecture History",
    ])
    assert result.exit_code == 0, result.output
    html = BeautifulSoup(output.read_text(encoding="utf-8"), "html.parser")
    assert "Architecture History" in html.title.get_text()
    for status in ("accepted", "superseded", "amended"):
        heading = html.select_one(f".panel-heading.adr-{status}")
        assert heading is not None
        label = heading.select_one(".adr-status")
        assert label is not None
        assert label.get_text(" ", strip=True) == f"Status: {status.capitalize()}"
'''

def sh(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def exec_cmd(target, args, expected=0):
    result = subprocess.run(args, cwd=target, text=True, capture_output=True,
                            check=False, timeout=150)
    if expected is not None and result.returncode != expected:
        raise RuntimeError(f"command {args[:4]} returned {result.returncode}: " +
                           (result.stderr + result.stdout)[-1500:])
    return result

def pact(target, *args, allow_failure=False):
    result = exec_cmd(target, [sys.executable, str(target / "pact.py"), *args],
                      expected=None if allow_failure else 0)
    value = json.loads(result.stdout) if "--json" in args and result.stdout else None
    return result, value

def replace_once(target, relative, old, new):
    path = target / relative
    original = path.read_text("utf-8")
    if original.count(old) != 1:
        raise ValueError(f"missing or ambiguous real-source edit {relative}")
    path.write_text(original.replace(old, new), encoding="utf-8")

def add_tests(target, number):
    if number in (1, 2):
        path = target / ("adr_viewer/test_render.py" if number == 1
                         else "adr_viewer/test_parse.py")
        extra = RENDER_TEST if number == 1 else PARSE_TEST
        path.write_text(path.read_text("utf-8") + extra, encoding="utf-8")
    else:
        path = target / "adr_viewer/test_cli_contract.py"
        if path.exists():
            raise ValueError("unplanned test file already exists")
        path.write_text(CLI_TEST, encoding="utf-8")

def decision_sources(target, context):
    sources = {s["path"]: s for s in context.get("artifacts", [])}
    for key in ("weak_decision_hints", "nonfunctional_decision_hints"):
        group = context.get(key) or {}
        if group.get("truncated_candidates"):
            raise ValueError(f"unreviewed deferred decisions: {key}")
        for s in group.get("candidates", []):
            if s["path"] in sources and sources[s["path"]]["sha256"] != s["sha256"]:
                raise ValueError("conflicting knowledge fingerprint")
            sources[s["path"]] = s
    scope = context.get("scope_route") or {}
    if scope.get("status") == "unique":
        for s in scope.get("candidates", []):
            sources[s["path"]] = s
    review = []
    for relative, s in sorted(sources.items()):
        file = target / relative
        if not file.is_file() or sh(file) != s["sha256"]:
            raise ValueError(f"prepared knowledge changed: {relative}")
        if not file.read_text("utf-8").strip():
            raise ValueError(f"empty context: {relative}")
        review.append(dict(path=relative, disposition="aligned",
                           rationale="Read original source-backed knowledge and checked SHA and relevance; no Product Truth inferred."))
    active = context.get("decisions", [])
    if "DEC-ADR-0003" in active:
        raise ValueError("superseded ADR 0003 promoted as current")
    return review, active

def task_verify(target, task, ac, claim_id, test_path):
    claim = f"pytest -q {test_path} exited successfully in {task['id']}"
    _, payload = pact(target, "task", "verify", task["id"],
                      "--criterion", ac, "--claim-id", claim_id,
                      "--claim", claim, "--kind", "test",
                      "--source", task["file"], "--json", "--",
                      sys.executable, "-m", "pytest", "-q", test_path)
    if payload["status"] != "pass":
        raise ValueError("verification was not passing")
    return dict(claim=claim, id=claim_id, receipt=payload["run_receipt"])

def run_task(target, task, number):
    started = time.monotonic()
    args = ["task", "prepare", task["title"], "--success", task["success"],
            "--accept", task["accept"], "--risk", task["risk"],
            "--task-id", task["id"], "--limit", "20", "--token-budget", "24000",
            "--full-decisions"]
    for phrase in task["queries"]:
        args.extend(["--query", phrase])
    _, manifest = pact(target, *args, "--json")
    contract = json.loads((target / manifest["contract"]).read_text("utf-8"))
    context = json.loads((target / manifest["context"]).read_text("utf-8"))
    coverage, active = decision_sources(target, context)
    if len(contract["acceptance_criteria"]) != 2:
        raise ValueError("expected two explicit criteria")
    pact(target, "task", "draft", task["id"], "--json")
    initial = pilot.source_snapshot(target)

    add_tests(target, number)
    red = None
    if number <= 2:
        red = exec_cmd(target, [sys.executable, "-m", "pytest", "-q", task["file"]],
                       expected=None)
        if red.returncode == 0:
            raise ValueError("new behavior regression did not fail on unmodified code")
        if number == 1:
            replace_once(target, "adr_viewer/templates/index.html", LABEL_OLD, LABEL_NEW)
        else:
            replace_once(target, "adr_viewer/parse.py", PARSE_OLD, PARSE_NEW)
    exec_cmd(target, [sys.executable, "-m", "pytest", "-q", task["file"]])
    if pilot.source_snapshot(target) != initial:
        raise ValueError("new test/code unintentionally changed durable Decisions")

    claims = [
        task_verify(target, task, "AC-1", f"EV-E2E-{number}-SCOPED", task["file"]),
        task_verify(target, task, "AC-2", f"EV-E2E-{number}-FULL", "."),
    ]
    stale = None
    if number == 1:
        previous_tree = pilot.git_output(target, "rev-parse", "HEAD^{tree}")
        exec_cmd(target, ["git", "commit", "--allow-empty", "-qm", "test HEAD-only freshness"])
        if pilot.git_output(target, "rev-parse", "HEAD^{tree}") != previous_tree:
            raise ValueError("empty commit changed source tree")
        bundle = target / ".pact/completions" / task["id"]
        invalid, _ = pact(target, "evidence", str(bundle / "evidence.json"),
                          "--root", str(target), allow_failure=True)
        if invalid.returncode == 0 or not all(
            x in invalid.stderr for x in
            ("stale pact-run receipt", "Git HEAD moved", "committed Git trees are identical")
        ):
            raise ValueError("HEAD-only evidence was not rejected with diagnostic")
        stale = "Rejected HEAD-only stale Evidence; reran both checks for new HEAD"
        # Actually rerun real tests and atomically refresh each run receipt.
        # Do not rewrite the Claim or turn an old failure into passing Evidence.
        for old, test_path in zip(claims, (task["file"], ".")):
            pact(target, "run", "--task-id", task["id"], "--cwd", str(target),
                 "--output", old["receipt"], "--source", task["file"],
                 "--quiet", "--", sys.executable, "-m", "pytest", "-q", test_path)

    evidence_dir = target / ".pact/completions" / task["id"]
    evidence = json.loads((evidence_dir / "evidence.json").read_text("utf-8"))
    if [c["status"] for c in evidence["claims"]] != ["pass", "pass"]:
        raise ValueError("unexpected Evidence statuses")
    convergence = dict(
        version=1, task_id=task["id"], change=task["title"],
        owner_summary="Real code and tests modified in an isolated source clone, source-authored ADRs preserved.",
        context_sha256=manifest["context_sha256"],
        coverage=coverage,
        change_coverage=[dict(path=path, rationale="Reviewed scoped changed code/test file and the explicit regression.")
                         for path in task["changes"]],
        evidence=[c["id"] for c in claims], findings=[],
        knowledge_retention=dict(
            disposition="none", updated=[], created=[],
            rationale="Code/test repair only; no new Owner-approved product rule or non-derivable durable decision; original ADRs unchanged."
        ))
    report = dict(
        version=1, task_id=task["id"], status="completed",
        summary="External source maintenance regression executed and reviewed.",
        before="Original pinned project implementation and existing source ADRs.",
        after="Narrow actual code/test edit verified with both scoped and full pytest.",
        verification=[dict(claim=c["claim"], evidence_ids=[c["id"]]) for c in claims],
        acceptance=[dict(criterion_id=a["id"], summary=a["text"],
                         evidence_ids=[claims[i]["id"]])
                    for i, a in enumerate(contract["acceptance_criteria"])],
        consistency=dict(status="aligned", summary="Source-backed current and historical ADRs unchanged."),
        owner_decisions=[])
    write(evidence_dir / "convergence.json", convergence)
    write(evidence_dir / "owner-report.json", report)
    _, completed = pact(target, "task", "finish", task["id"],
                        "--require-knowledge-retention", "--json")
    if not completed["complete"] or completed["task_change"]["changed_files"] != sorted(task["changes"]):
        raise ValueError("Task Finish or changed-file attribution incorrect")
    if completed["knowledge_retention"]["disposition"] != "none":
        raise ValueError("wrong durable knowledge disposition")
    return dict(id=task["id"], risk=task["risk"], file_changes=sorted(task["changes"]),
                tdd_red=red.returncode != 0 if red is not None else None,
                acceptance=completed["acceptance"],
                reviewed_knowledge=completed["convergence_coverage"],
                current_decisions=active, retention="none", completed=True,
                stale_receipt_check=stale,
                elapsed_seconds=round(time.monotonic()-started, 2))

def negative_accessibility(target):
    template = target / "adr_viewer/templates/index.html"
    before = template.read_bytes()
    label = '                        <span class="adr-status">Status: {{ adr_record.status|capitalize }}</span>'
    if before.decode("utf-8").count(label) != 1:
        raise ValueError("cannot locate one existing status text")
    try:
        template.write_text(before.decode("utf-8").replace(label,
                            "                        <!-- color-only regression -->"), encoding="utf-8")
        rejected = exec_cmd(target, [sys.executable, "-m", "pytest", "-q",
                                    "adr_viewer/test_render.py"], expected=None)
        static, _ = pact(target, "check", allow_failure=True)
        if rejected.returncode == 0:
            raise ValueError("accessibility regression was not detected by real tests")
        return dict(injected="Remove visible status label; keep color/icons",
                    pytest_rejected=True, pact_static_check_returncode=static.returncode,
                    auto_semantic_decision_approval=False)
    finally:
        template.write_bytes(before)

def run(target, progress):
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise ValueError("Only a temporary Actions clone is allowed")
    runner = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    if not target.is_relative_to(runner) or target == runner:
        raise ValueError("Target must be inside RUNNER_TEMP")
    cards = json.loads(pilot.CARDS.read_text(encoding="utf-8"))
    pilot.validate_frozen(cards, target)
    old_adrs = {d["source"]: sh(target / d["source"]) for d in cards["upstream_docs"]}
    exec_cmd(target, [sys.executable, "-m", "pytest", "-q"])
    progress["baseline_upstream_pytest"] = "PASS"
    progress["installed"] = pilot.install_pact(target)
    projected = pilot.project_adrs(target, cards)
    if len(projected) != 6:
        raise ValueError("six source-authored ADRs expected")
    frozen = pilot.source_snapshot(target)

    ignore = target / ".git/info/exclude"
    if ignore.is_symlink() or not ignore.is_file():
        raise ValueError("invalid local test exclude file")
    ignore.write_text(ignore.read_text("utf-8") +
                      "\n# temporary Python test files only\n__pycache__/\n*.pyc\n.pytest_cache/\n",
                      encoding="utf-8")
    baseline_untracked = set(pilot.git_output(target, "ls-files", "--others",
                                               "--exclude-standard").splitlines())
    finds = []
    for phrase, expected in [
        ("Accessibility will now be a first-class concern", "DEC-ADR-0006"),
        ("Distinguish amendments to records with colour", "DEC-ADR-0005"),
        ("Expose command line interface", "DEC-ADR-0002"),
    ]:
        _, found = pact(target, "discover", phrase, "--intent", "decision",
                        "--limit", "15", "--json")
        actual = [x.get("id") for x in found.get("results", [])]
        if expected not in actual:
            raise ValueError(f"{expected} not retrieved for {phrase}: {actual}")
        finds.append(dict(query=phrase, needed=expected, found=True, candidates=len(actual)))
    progress["retrieval"] = finds

    results = []
    for i, task in enumerate(TASKS, 1):
        progress["stage"] = task["id"]
        row = run_task(target, task, i)
        results.append(row)
        progress["tasks"] = results
        if pilot.source_snapshot(target) != frozen:
            raise ValueError("durable Decisions grew/changed across tasks")

    progress["stage"] = "adversarial-accessibility-regression"
    negative = negative_accessibility(target)
    if pilot.source_snapshot(target) != frozen:
        raise ValueError("adversarial case changed durable knowledge")
    if any(sh(target / path) != original for path, original in old_adrs.items()):
        raise ValueError("source ADRs changed")
    exec_cmd(target, [sys.executable, "-m", "pytest", "-q"])
    changed = pilot.git_output(target, "diff", "--name-only").splitlines()
    after_untracked = set(pilot.git_output(target, "ls-files", "--others",
                                           "--exclude-standard").splitlines())
    if not baseline_untracked <= after_untracked:
        raise ValueError("pre-existing source/PACT projection disappeared")
    new_untracked = sorted(after_untracked - baseline_untracked)
    expected_files = sorted(set(p for t in TASKS for p in t["changes"]))
    if sorted(changed + new_untracked) != expected_files:
        raise ValueError(f"unexpected user-source delta {changed + new_untracked}, expected {expected_files}")
    return dict(
        status="PASS", upstream=pilot.EXPECTED_UPSTREAM,
        source_commit=pilot.EXPECTED_UPSTREAM_SHA, task_count=len(results),
        tasks=results, retrieval=finds, negative=negative,
        upstream_pytest_before_and_after="PASS",
        changed_files=expected_files, knowledge_entries_before=len(frozen),
        knowledge_entries_after=len(pilot.source_snapshot(target)),
        decision_bytes_unchanged=True, knowledge_growth=0,
        verified_task_finish=True, source_remote_pushed=False,
        original_public_source_unmodified=True,
        coding_agent_executed=False, independent_owner_observed=False,
        real_agent_decision_obedience_verified=False,
        long_term_benefit_proven=False)

def main():
    arg = argparse.ArgumentParser()
    arg.add_argument("--target", required=True)
    args = arg.parse_args()
    progress = {}
    try:
        result = run(Path(args.target).resolve(strict=True), progress)
    except Exception as exc:
        result = dict(status="FAIL", error=f"{type(exc).__name__}: {exc}",
                      progress=progress, coding_agent_executed=False,
                      real_agent_decision_obedience_verified=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
