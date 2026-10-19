#!/usr/bin/env python3
"""Reproducible ASSISTANT-AUTHORED real-source coding task, not a live model-Agent A/B.

Only PACT owns this runner. Public PrivacyFence is copied into disposable
worktrees and changed locally. Actual code edits, pre-RED/post-GREEN source
probes, original offline tests, Decision retrieval and an ADR-conflict negative
control are preserved even when a stage fails.

Task/oracle authorship and deterministic replay are public: no claim of blind
Agent obedience, comparative model benefit or Owner acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import traceback
from typing import Any

import github_actions_agent_preflight as isolation
import privacyfence_pilot as pf

ROOT = pathlib.Path(__file__).resolve().parents[2]
UPSTREAM_SHA = "6a03856a6e1819b2eacd3963154ebc7d02923296"
SOURCE_FILE = "src/privacyfence/export_files.py"
SOURCE_BLOB = "20cf3e73902221f4e308f0586c840ab3122d017c"
TEST_FILE = "tests/unit/test_export_files.py"
TEST_BLOB = "61471e28fe1c907e958a13666e2507185b238ac5"
ADR_BLOBS = {
    "docs/adr/0180-jira-and-salesforce-csv-exports-neutralise-formula-cells.md":
        "cf7c47ff6276905f244c2194348466a4aa1e02e2",
    "docs/adr/0155-exports-write-a-file-and-return-only-counts-and-a-hash.md":
        "3aff5b308d87978e694330e14b8c74253300d9f7",
}
TARGET_DECISION_ID = "DEC-PF-0180"
TASK = (
    "Refactor CSV export rendering to process spreadsheet-safe rows incrementally "
    "instead of making an eager copy of all input rows. Preserve byte-for-byte "
    "CSV/JSON behavior, Jira and Salesforce spreadsheet formula safety, and "
    "Grist round-trip semantics. Do not change the export security policy "
    "or its historical architecture decisions. Provide a real source diff "
    "and pass the project's original offline tests."
)
SOURCE_PATTERN = '''    if fmt == "csv":
        if spreadsheet_safe:
            rows = [[_neutralise(v) for v in row] for row in rows]
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([csv_cell(v) for v in row])
        return buf.getvalue().encode("utf-8")
'''
PATCH_PATTERN = '''    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([
                csv_cell(_neutralise(v) if spreadsheet_safe else v)
                for v in row
            ])
        return buf.getvalue().encode("utf-8")
'''
# Runtime probe belongs to the evaluator, never into the upstream checkout.
# The original source consumes ALL source rows before csv.writer is constructed.
# The patch must emit the first record before requesting the second source row.
STREAM_PROBE = r'''
import pathlib
import os
from privacyfence import export_files

expected = (pathlib.Path(os.environ["PACT_CODING_ARM"]) /
            "src/privacyfence/export_files.py").resolve()
assert pathlib.Path(export_files.__file__).resolve() == expected, (
    "WRONG_IMPORT_SOURCE", export_files.__file__, expected
)
original_writer = export_files.csv.writer
writes = []
def tracked_writer(*args, **kwargs):
    delegate = original_writer(*args, **kwargs)
    class Writer:
        def writerow(self, values):
            writes.append(tuple(values))
            return delegate.writerow(values)
    return Writer()
class GuardedRows(list):
    def __iter__(self):
        for index, row in enumerate(super().__iter__()):
            if index == 1 and len(writes) < 2:
                raise AssertionError("EAGER_COPY_BEFORE_FIRST_WRITE")
            yield row
export_files.csv.writer = tracked_writer
output = export_files.render(
    ["a"], GuardedRows([["=1+1"], ["@SUM(A1)"]]),
    "csv", spreadsheet_safe=True,
)
assert output == b"a\n'=1+1\n'@SUM(A1)\n", repr(output)
assert len(writes) == 3, writes
# ADR 0180: Grist retains raw text and JSON ignores spreadsheet_safe.
assert export_files.render(["a"], [["=1+1"]], "csv") == b"a\n=1+1\n"
assert export_files.render(["a"], [["=1+1"]], "json", spreadsheet_safe=True) == (
    b'[{"a":"=1+1"}]\n'
)
print("STREAMING_CSV_OK")
'''

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(arm: pathlib.Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(arm), *args],
        capture_output=True, text=True, timeout=45, check=False,
    )
    if result.returncode:
        raise ValueError(f"git {args[0]} failed ({result.returncode}): {result.stderr[-500:]}")
    return result.stdout.strip()


def source_pins(arm: pathlib.Path) -> None:
    if git(arm, "rev-parse", "HEAD") != UPSTREAM_SHA:
        raise ValueError("unrecognized upstream source HEAD")
    if git(arm, "remote", "get-url", "origin") != isolation.UPSTREAM:
        raise ValueError("unrecognized public upstream origin")
    pins = {SOURCE_FILE: SOURCE_BLOB, TEST_FILE: TEST_BLOB, **ADR_BLOBS}
    for path, expected in pins.items():
        file = arm / path
        if not file.is_file() or file.is_symlink():
            raise ValueError(f"pinned source unavailable/symlinked: {path}")
        if git(arm, "hash-object", path) != expected:
            raise ValueError(f"pinned upstream source blob changed: {path}")
    if len(list((arm / "docs/adr").glob("*.md"))) != 184:
        raise ValueError("source ADR inventory was changed")


def fixture_patch(content: str) -> str:
    """Single, exact source edit. Refuse source drift or a second occurrence."""
    if content.count(SOURCE_PATTERN) != 1:
        raise ValueError("source patch anchor missing/ambiguous, refuse unsafe edit")
    return content.replace(SOURCE_PATTERN, PATCH_PATTERN)


def change_only_agreed_file(arm: pathlib.Path, before: dict[str, str]) -> str:
    after = isolation.tracked_source(arm)
    if set(after) != set(before):
        raise ValueError("tracked file inventory changed unexpectedly")
    changed = sorted(x for x in before if before[x] != after[x])
    if changed != [SOURCE_FILE]:
        raise ValueError(f"code patch changed non-authorized tracked paths: {changed!r}")
    if git(arm, "diff", "--name-only") != SOURCE_FILE:
        raise ValueError("Git diff does not match exactly the approved source file")
    check = subprocess.run(
        ["git", "-C", str(arm), "diff", "--check"],
        capture_output=True, text=True, check=False, timeout=15,
    )
    if check.returncode:
        raise ValueError("patch whitespace check failed: " + check.stdout[-500:])
    for path in ADR_BLOBS:
        if git(arm, "hash-object", path) != ADR_BLOBS[path]:
            raise ValueError("original operative ADR was modified")
    return git(arm, "diff", "--", SOURCE_FILE)


def run_step(args: list[str], *, cwd: pathlib.Path, timeout: int = 160,
             env: dict[str, str] | None = None) -> dict[str, Any]:
    proc = subprocess.run(
        args, cwd=cwd, env=env, capture_output=True, text=True,
        timeout=timeout, check=False,
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout[-6500:],
        "stderr": proc.stderr[-3500:],
    }


def python_env(arm: pathlib.Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(arm / "src")
    env["PACT_CODING_ARM"] = str(arm)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def stream_check(arm: pathlib.Path, *, expected_red: bool) -> dict:
    observed = run_step(
        [sys.executable, "-c", STREAM_PROBE], cwd=arm, timeout=65,
        env=python_env(arm),
    )
    red = (
        observed["returncode"] == 1
        and "AssertionError: EAGER_COPY_BEFORE_FIRST_WRITE" in observed["stderr"]
        and "WRONG_IMPORT_SOURCE" not in observed["stderr"]
    )
    green = (
        observed["returncode"] == 0
        and "STREAMING_CSV_OK" in observed["stdout"]
        and not observed["stderr"].strip()
    )
    observed["expected_result_observed"] = red if expected_red else green
    if not observed["expected_result_observed"]:
        raise ValueError(
            "stream observer did not produce the exact "
            + ("baseline RED" if expected_red else "post-change GREEN")
            + " signature: " + str(observed)[:1250]
        )
    return observed


def original_offline_tests(arm: pathlib.Path) -> dict[str, dict]:
    # No live connector/service tests. The existing pure source regression suite
    # must still validate CSV bytes, signed formula rules, history and Grist.
    suites = [
        [
            "tests/unit/test_export_files.py",
            "tests/unit/test_code_no_history.py",
            "tests/unit/test_docs_no_history.py",
        ],
        [
            "tests/unit/connectors/test_jira_connector.py",
            "tests/unit/connectors/test_salesforce_connector.py",
            "tests/unit/connectors/test_grist_connector.py",
            "-k", "Export",
        ],
    ]
    receipts = {}
    for index, suite in enumerate(suites, start=1):
        receipt = run_step(
            [sys.executable, "-m", "pytest", "-q", *suite],
            cwd=arm, env=python_env(arm), timeout=240,
        )
        if receipt["returncode"] != 0:
            raise ValueError(f"original offline source suite {index} failed: {receipt!r}")
        receipts[f"suite_{index}"] = receipt
    return receipts


def conflict_negative_control(control: pathlib.Path, scratch: pathlib.Path) -> dict:
    """Prove accepted Grist decision is a real executable limitation."""
    # The conflict fixture is an independent local checkout, never an A/B edit.
    c = scratch / "C-unauthorized-Grist-formula-change"
    shutil.copytree(control, c, symlinks=True)
    source_pins(c)
    target = c / SOURCE_FILE
    content = target.read_text(encoding="utf-8")
    prior = "*, spreadsheet_safe: bool = False,"
    if content.count(prior) != 1:
        raise ValueError("unsafe Grist negative mutation anchor")
    target.write_text(content.replace(prior, "*, spreadsheet_safe: bool = True,"), encoding="utf-8")
    receipt = run_step(
        [sys.executable, "-m", "pytest", "-q",
         "tests/unit/test_export_files.py::TestRender::test_cells_are_left_alone_by_default"],
        cwd=c, env=python_env(c), timeout=110,
    )
    # A mismatched return code or a pytest collection/import error must not pass.
    expected = (
        receipt["returncode"] == 1
        and "test_cells_are_left_alone_by_default" in receipt["stdout"]
        and "AssertionError" in receipt["stdout"]
        and "1 failed" in receipt["stdout"]
        and "ERROR collecting" not in receipt["stdout"]
        and "ModuleNotFoundError" not in receipt["stderr"]
    )
    receipt["expected_adr_conflict_red"] = expected
    if not expected:
        raise ValueError("original Grist round-trip guard did not reject forbidden change: "
                         + str(receipt)[:1000])
    return receipt


def source_verified_context(arm: pathlib.Path) -> dict:
    """Observe ACTUAL installed PACT Context from no-ID natural task text."""
    cards = pf.verify_freeze(arm)
    install = pf.pilot.install_pact(arm)
    if not install["installed_source_match"]:
        raise ValueError("installed PACT runtime differs from checkout")
    projected = pf.project_sources(arm, cards)
    check = run_step(
        [sys.executable, str(arm / "pact.py"), "check"],
        cwd=arm, timeout=160,
    )
    if check["returncode"] != 0:
        raise ValueError("installed project PACT Check rejected source projections: "
                         + str(check)[:1000])

    arguments = [
        sys.executable, str(arm / "pact.py"), "context", TASK,
        "--success", "CSV output, authority and source tests unchanged",
        "--risk", "medium", "--intent", "work", "--no-code",
        "--limit", "8", "--token-budget", "8192",
    ]
    query = run_step(arguments, cwd=arm, timeout=200)
    if query["returncode"] != 0:
        raise ValueError("installed PACT Context failed: " + str(query)[:1400])
    envelope = json.loads(query["stdout"])
    artifacts = envelope.get("artifacts")
    if not isinstance(artifacts, list) or not isinstance(envelope.get("decisions"), list):
        raise ValueError("installed Context lacks valid artifact/Decision arrays")
    trusted = set()
    for item in artifacts:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("Context contains malformed selected artifact")
        file = pf.safe_source(arm, item["path"])
        if item.get("sha256") != pf.m0.digest_file(file):
            raise ValueError("Context source hash mismatch: " + item["path"])
        for original in cards["source_docs"]:
            if (original["id"] == item.get("id")
                    and original["status"] == "implemented"
                    and pf.target_path(original) == item["path"]):
                trusted.add(original["id"])
    claimed = set(envelope["decisions"])
    if claimed - trusted:
        raise ValueError("Context asserted implemented Decision without source-bound selection")
    if len(projected) != 12:
        raise ValueError("unexpected source-projection count")
    return {
        "command_kind": "installed-PACT-context-no-ID",
        "status": envelope.get("status"),
        "source_verified_target_decision_recalled": TARGET_DECISION_ID in claimed,
        "selected_implemented_decisions": sorted(claimed),
        "selected_knowledge_paths": [x["path"] for x in artifacts],
        "selected_estimated_tokens": envelope.get("context_budget", {}).get("selected_estimated_tokens"),
        "selected_knowledge_count": len(artifacts),
        "additional_decision_candidates": sorted(claimed - {TARGET_DECISION_ID}),
        "projected_source_count": len(projected),
        "runtime_sha256": install.get("installed_archive_sha256"),
        "real_owner_confirmed_decisions": False,
        "quality_warning": (
            "TARGET_MISSED: further original ADR inspection needed"
            if TARGET_DECISION_ID not in claimed
            else None
        ),
    }


def execute(source: pathlib.Path, scratch: pathlib.Path) -> dict:
    result: dict[str, Any] = {
        "kind": "assistant-authored-public-source-real-code-edit-not-agent-ab",
        "upstream": "privacyfence/privacyfence",
        "upstream_sha": UPSTREAM_SHA,
        "task_text": TASK,
        "live_coding_agent_executed": False,
        "preauthored_code_change_replayed": True,
        "independent_blind_holdout": False,
        "owner_authenticated_observation": False,
        "model_billed_tokens": None,
        "release_gate": "HOLD",
        "stage": "source-preflight",
        "safety_failures": [],
    }
    try:
        if not scratch.is_dir() or scratch.is_symlink():
            raise ValueError("private runner scratch missing or unsafe")
        source_pins(source)
        if not isolation.original_clean(source):
            raise ValueError("original source checkout not clean")
        pinned = isolation.tracked_source(source)
        result["original_tracked_count"] = len(pinned)
        result["original_tracked_tree_digest"] = isolation.manifest_digest(pinned)
        if len(pinned) != 971:
            raise ValueError(f"original tracked file count differs from pinned 971: {len(pinned)}")

        with tempfile.TemporaryDirectory(prefix="pact-real-code-", dir=scratch) as td:
            root = pathlib.Path(td)
            a, b = root / "A-original-ADRs", root / "B-PACT-source-adapted"
            shutil.copytree(source, a, symlinks=True)
            shutil.copytree(source, b, symlinks=True)
            for arm in (a, b):
                source_pins(arm)
                if isolation.tracked_source(arm) != pinned:
                    raise ValueError("source differed between original and treatment")
                if not isolation.original_clean(arm):
                    raise ValueError("pre-edit control/treatment clone has tracked edits")
            if (a / "pact.py").exists() or (a / ".pact").exists():
                raise ValueError("A was contaminated with PACT runtime")
            for name, arm in (("A", a), ("B", b)):
                if (arm / pf.ORACLE.relative_to(ROOT)).exists():
                    raise ValueError(f"answer key leaked into {name} workspace")

            result["stage"] = "B-context-before-code"
            result["B_pact_context"] = source_verified_context(b)
            if isolation.tracked_source(b) != pinned:
                raise ValueError("PACT Context/materialization changed original tracked files")
            result["A_direct_original_adr_access"] = (
                "docs/adr/0180-jira-and-salesforce-csv-exports-neutralise-formula-cells.md"
            )
            result["stage"] = "pre-edit-expected-RED"
            result["pre_edit_red"] = {
                "A": stream_check(a, expected_red=True),
                "B": stream_check(b, expected_red=True),
            }

            result["stage"] = "actual-application-code-edit"
            diffs = {}
            for name, arm in (("A", a), ("B", b)):
                file = arm / SOURCE_FILE
                original = file.read_text(encoding="utf-8")
                updated = fixture_patch(original)
                file.write_text(updated, encoding="utf-8")
                diff = change_only_agreed_file(arm, pinned)
                diffs[name] = diff
            if diffs["A"] != diffs["B"]:
                raise ValueError("A/B original application code diff differs")
            result["application_diff_sha256"] = sha256(diffs["A"].encode())
            result["application_diff"] = diffs["A"][:8000]
            result["modified_application_paths"] = [SOURCE_FILE]

            result["stage"] = "post-edit-expected-GREEN"
            result["post_edit_green"] = {
                "A": stream_check(a, expected_red=False),
                "B": stream_check(b, expected_red=False),
            }

            result["stage"] = "original-offline-tests-on-both-edited-arms"
            result["application_tests"] = {
                "A": original_offline_tests(a),
                "B": original_offline_tests(b),
            }

            result["stage"] = "source-bound-conflict-negative"
            result["Grist_conflict_guard"] = conflict_negative_control(source, root)

            result["stage"] = "final-integrity"
            if not isolation.original_clean(source) or isolation.tracked_source(source) != pinned:
                raise ValueError("original upstream source was modified")
            for arm in (a, b):
                if git(arm, "rev-parse", "HEAD") != UPSTREAM_SHA:
                    raise ValueError("application code patch changed Git HEAD")
                if change_only_agreed_file(arm, pinned) != diffs["A"]:
                    raise ValueError("final one-file source diff does not match reviewed patch")
            if len(list((b / ".agents/decisions").rglob("*.md"))) != 12:
                raise ValueError("unexpected growth of durable Decision projections")
            result["original_source_unchanged"] = True
            result["B_only_twelve_test_projections"] = True
            result["stage"] = "complete"
            result["engineering_gate"] = "PASS"
            result["retrieval_quality_gate"] = (
                "OBSERVED_TARGET_HIT"
                if result["B_pact_context"]["source_verified_target_decision_recalled"]
                else "HOLD_TARGET_MISSED"
            )
    except Exception as exc:
        result["safety_failures"].append(f"{type(exc).__name__}: {exc}"[:1800])
        result["traceback"] = traceback.format_exc(limit=7)[-3500:]
        result["engineering_gate"] = "FAIL"
        result["retrieval_quality_gate"] = "UNVERIFIED"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--temp-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    destination = pathlib.Path(args.output)
    if not destination.parent.is_dir():
        parser.error("output parent must already exist")
    report = execute(pathlib.Path(args.source).resolve(), pathlib.Path(args.temp_root).resolve())
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(f"Real source code task: {report['engineering_gate']}; "
          f"retrieval: {report['retrieval_quality_gate']}; model calls: 0")
    return 0 if report["engineering_gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
