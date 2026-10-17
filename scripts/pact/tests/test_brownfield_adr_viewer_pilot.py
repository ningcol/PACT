"""Check frozen real-GitHub-source pilot boundaries without network or Agent claims."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest
import io
import subprocess
from contextlib import redirect_stdout
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
import brownfield_adr_viewer as pilot


class BrownfieldAdrViewerPilotTests(unittest.TestCase):
    @staticmethod
    def fixture():
        return json.loads(pilot.CARDS.read_text(encoding="utf-8"))

    def test_frozen_github_repository_and_oracle_integrity(self):
        cards = self.fixture()
        oracle = json.loads(pilot.ORACLE.read_text(encoding="utf-8"))
        self.assertEqual(pilot.git_blob_sha(pilot.CARDS), pilot.CARDS_BLOB)
        self.assertEqual(pilot.git_blob_sha(pilot.ORACLE), pilot.ORACLE_BLOB)
        self.assertEqual(cards["upstream"], "mrwilson/adr-viewer")
        self.assertEqual(cards["upstream_commit"], pilot.EXPECTED_UPSTREAM_SHA)
        self.assertEqual(cards["pact_parent_sha"], pilot.EXPECTED_BASELINE_SHA)
        self.assertEqual(len(cards["upstream_docs"]), 6)
        self.assertEqual(len(cards["tasks"]), 6)
        self.assertEqual(set(oracle["expected_current"]),
                         {c["id"] for c in cards["tasks"]})
        self.assertEqual(sum(bool(v) for v in oracle["expected_current"].values()), 4)
        for card in cards["tasks"]:
            self.assertNotIn("DEC-ADR-", card["task"])
        self.assertEqual(cards["settings"]["knowledge_limit"], 4)

    def test_copy_original_source_rationale_without_invented_anchors(self):
        cards = self.fixture()
        upstream = (
            "# 4. Distinguish superseded records with colour\n\n"
            "## Status\n\nAccepted\n\n## Context\n\nDifferent states\n\n"
            "## Decision\n\nUse distinct styling.\n"
        )
        md = pilot.render_adapted_original(cards["upstream_docs"][3], upstream)
        self.assertIn('id = "DEC-ADR-0004"', md)
        self.assertIn('status = "implemented"', md)
        self.assertIn('supersedes = ["DEC-ADR-0003"]', md)
        self.assertIn("Use distinct styling.", md)
        self.assertIn("Test-only projection", md)
        self.assertIn("aliases = []", md)
        self.assertIn("paths = []", md)
        self.assertNotIn('status = "confirmed"', md)

    def test_copied_adrs_preserve_text_and_rebase_only_original_sibling_links(self):
        original = (
            "# 4. Distinguish superseded records with colour\n\n"
            "## Status\n\nAccepted\n\n"
            "Supercedes [3. Old header](0003-use-same-colour-for-all-headers.md)\n\n"
            "Amended by [5. Amendments](0005-distinguish-amendments-to-records-with-colour.md)\n"
        )
        untouched = original[:]
        md = pilot.render_adapted_original(self.fixture()["upstream_docs"][3], original)
        self.assertEqual(original, untouched)
        self.assertIn(
            "[3. Old header](../../../doc/adr/0003-use-same-colour-for-all-headers.md)",
            md,
        )
        self.assertIn(
            "[5. Amendments](../../../doc/adr/0005-distinguish-amendments-to-records-with-colour.md)",
            md,
        )
        self.assertIn("Supercedes", md)
        self.assertIn("Amended by", md)
        self.assertNotIn("aliases = [", md.replace("aliases = []", ""))


    def test_reject_invented_or_tampered_source_status(self):
        original = self.fixture()["upstream_docs"][3]
        with self.assertRaisesRegex(ValueError, "upgrade"):
            pilot.render_adapted_original(original, "# ADR\n\n## Status\n\nRejected\n")
        with self.assertRaisesRegex(ValueError, "missing title"):
            pilot.render_adapted_original(original, "## Status\n\nAccepted\n")
        old = self.fixture()["upstream_docs"][2]
        with self.assertRaisesRegex(ValueError, "non-superseded"):
            pilot.render_adapted_original(old, "# Old\n\n## Status\n\nAccepted\n")

    def test_status_lineage_does_not_confuse_amended_with_superseded(self):
        cards = self.fixture()
        decisions = {d["id"]: d for d in cards["upstream_docs"]}
        self.assertEqual(decisions["DEC-ADR-0003"]["status"], "superseded")
        self.assertEqual(decisions["DEC-ADR-0003"]["superseded_by"],
                         "DEC-ADR-0004")
        self.assertEqual(decisions["DEC-ADR-0004"]["supersedes"],
                         ["DEC-ADR-0003"])
        self.assertNotIn("supersedes", decisions["DEC-ADR-0005"])

    def test_document_scope_includes_added_non_markdown_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp)
            folder = target / ".agents" / "decisions" / "implemented"
            folder.mkdir(parents=True)
            (folder / "temp.md").write_text("# fake", encoding="utf-8")
            baseline = pilot.source_snapshot(target)
            (folder / "extra.json").write_text("{}", encoding="utf-8")
            self.assertEqual(len(pilot.source_snapshot(target)), len(baseline) + 1)

    def test_nested_success_records_reject_missing_source_and_type(self):
        self.assertFalse(pilot.valid_discovery_result({}))
        self.assertFalse(pilot.valid_discovery_result({
            "path": "docs/test.md", "artifact_type": "decision",
            "id": None, "status": "implemented",
        }))
        self.assertTrue(pilot.valid_discovery_result({
            "path": "docs/README.md", "artifact_type": "document",
            "id": None, "status": None,
        }))
        self.assertFalse(pilot.valid_context_artifact({"id": "DEC-ADR-0002"}))
        self.assertFalse(pilot.valid_context_artifact({
            "id": "DEC-ADR-0002", "artifact_type": "decision",
            "path": ".agents/decisions/implemented/foo.md", "sha256": "",
        }))

    def test_ab_probe_preserves_finished_cases_when_later_cli_times_out(self):
        cards = self.fixture()
        calls = []
        def scripted(_target, command):
            calls.append(command)
            if len(calls) == 3:
                raise subprocess.TimeoutExpired(command, 1)
            if command[0] == "discover":
                data = {"results": []}
            else:
                data = {
                    "status": "candidate", "artifacts": [],
                    "decisions": [], "applicable_rules": [],
                    "known_unknowns": [], "code_artifacts": [],
                    "context_budget": {"selected_estimated_tokens": 0},
                }
            return {"command": ["pact.py", *command], "returncode": 0,
                    "elapsed_ms": 1, "stderr": "", "data": data}
        progress = []
        with mock.patch.object(pilot.m0, "run_json", side_effect=scripted):
            with self.assertRaises(subprocess.TimeoutExpired):
                pilot.probe(pathlib.Path("/tmp/not-accessed"), cards, progress)
        self.assertEqual(len(progress), 1)
        self.assertEqual(progress[0]["id"], cards["tasks"][0]["id"])
        self.assertEqual(progress[0]["context"]["returncode"], 0)

    def test_main_preserves_partial_probe_data_on_mid_evaluation_failure(self):
        progress_record = {"id": "completed-case", "context": {"returncode": 0}}
        def abort(_target, _cards, progress):
            progress["stage"] = "legacy-probing"
            progress["A_plain_legacy"] = [progress_record]
            raise subprocess.TimeoutExpired(["installed-pact.py"], 3)
        with tempfile.TemporaryDirectory(prefix="pact-partial-evidence-") as td:
            target = pathlib.Path(td) / "public-project"
            target.mkdir()
            with mock.patch.dict("os.environ", {
                "GITHUB_ACTIONS": "true", "RUNNER_TEMP": td,
            }):
                with mock.patch.object(sys, "argv", [
                    "brownfield_adr_viewer.py", "--target", str(target),
                ]):
                    with mock.patch.object(pilot, "evaluate", side_effect=abort):
                        output = io.StringIO()
                        with redirect_stdout(output):
                            rc = pilot.main()
        self.assertEqual(rc, 1)
        report = json.loads(output.getvalue())
        self.assertTrue(report["partial_collection_failed"])
        self.assertTrue(report["completed_probes_preserved"])
        self.assertEqual(report["raw_probes"]["A_plain_legacy"], [progress_record])
        self.assertEqual(report["engineering_safety_gate"], "FAIL")

    def test_installed_archive_must_match_source_rebuilt_bytes(self):
        """Pinned source runtime digest, not merely a present pyz filename."""
        with tempfile.TemporaryDirectory(prefix="pact-brownfield-runtime-") as td:
            installed = pathlib.Path(td) / "pact.pyz"
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "pact" / "runtime_bundle.py"),
                 "--source-root", str(ROOT), "--output", str(installed)],
                check=True, capture_output=True, text=True, timeout=90,
            )
            identity = pilot.verify_installed_runtime_against_source(installed)
            self.assertTrue(identity["installed_source_match"])
            self.assertRegex(identity["installed_archive_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(identity["installed_archive_sha256"],
                             identity["source_rebuilt_archive_sha256"])
            installed.write_bytes(installed.read_bytes() + b"tamper")
            with self.assertRaisesRegex(ValueError, "differs from exact source"):
                pilot.verify_installed_runtime_against_source(installed)

    def test_forged_decision_path_or_sha_cannot_claim_retrieval(self):
        cards = self.fixture()
        known = pilot.projected_decision_paths(cards)
        decision_path = known["DEC-ADR-0002"]
        with tempfile.TemporaryDirectory(prefix="pact-forged-decision-") as td:
            root = pathlib.Path(td)
            file = root / decision_path
            file.parent.mkdir(parents=True)
            file.write_text("# projected\n", encoding="utf-8")
            digest = pilot.m0.digest_file(file)
            good_hit = {
                "id": "DEC-ADR-0002", "path": decision_path,
                "artifact_type": "decision", "status": "implemented",
            }
            good_artifact = {
                "id": "DEC-ADR-0002", "path": decision_path,
                "artifact_type": "decision", "sha256": digest,
            }
            self.assertEqual(
                pilot.verify_installed_probe_sources(root, cards,
                                                     [good_hit], [good_artifact]), []
            )
            for forged in (
                {**good_hit, "path": "README.md"},
                {**good_hit, "id": "DEC-ADR-0003"},
            ):
                self.assertTrue(pilot.verify_installed_probe_sources(
                    root, cards, [forged], []
                ))
            for forged in (
                {**good_artifact, "sha256": "a" * 64},
                {**good_artifact, "path": "README.md"},
            ):
                self.assertTrue(pilot.verify_installed_probe_sources(
                    root, cards, [], [forged]
                ))

    def test_timeout_buffer_is_retained_in_failing_receipt(self):
        with tempfile.TemporaryDirectory(prefix="pact-timeout-buffer-") as td:
            target = pathlib.Path(td) / "upstream"
            target.mkdir()
            error = subprocess.TimeoutExpired(
                ["pact.py", "check"], 4,
                output=b"broken observed stdout", stderr=b"bad stderr"
            )
            with mock.patch.dict("os.environ", {
                "GITHUB_ACTIONS": "true", "RUNNER_TEMP": td
            }):
                with mock.patch.object(sys, "argv", [
                    "brownfield_adr_viewer.py", "--target", str(target)
                ]):
                    with mock.patch.object(pilot, "evaluate", side_effect=error):
                        output = io.StringIO()
                        with redirect_stdout(output):
                            rc = pilot.main()
            self.assertEqual(rc, 1)
            report = json.loads(output.getvalue())
            self.assertEqual(report["engineering_safety_gate"], "FAIL")
            self.assertIn("broken observed stdout",
                          report["interrupted_subprocess"]["stdout_excerpt"])
            self.assertIn("bad stderr",
                          report["interrupted_subprocess"]["stderr_excerpt"])

    def test_installed_successful_context_requires_complete_pact_schema(self):
        cards = self.fixture()
        def scripted(_target, command):
            data = {"results": []} if command[0] == "discover" else {
                "status": "candidate", "artifacts": [], "decisions": [],
                "applicable_rules": [], "known_unknowns": [],
                "code_artifacts": [], "context_budget": {
                    "selected_estimated_tokens": 0,
                },
            }
            return {"command": ["pact.py", *command], "returncode": 0,
                    "elapsed_ms": 1, "stderr": "", "data": data}
        with mock.patch.object(pilot.m0, "run_json", side_effect=scripted):
            report = pilot.probe(pathlib.Path("/tmp/no-real-cli"), cards)
        self.assertEqual(len(report), 6)
        for case in report:
            errors = case["context"]["schema_errors"]
            self.assertTrue(any("missing required property" in err
                                for err in errors), errors)
            self.assertTrue(any("version" in err for err in errors), errors)

    def test_project_check_receipt_survives_adapted_probe_timeout(self):
        import types
        cards = self.fixture()
        progress = {}
        timeout = subprocess.TimeoutExpired(["pact.py", "context"], 2)
        with tempfile.TemporaryDirectory(prefix="pact-check-receipt-") as td:
            target = pathlib.Path(td)
            with mock.patch.object(pilot, "validate_frozen"):
                with mock.patch.object(pilot.m0, "digest_file", return_value="sha"):
                    with mock.patch.object(pilot, "install_pact", return_value={"runtime": "tested"}):
                        with mock.patch.object(pilot, "source_snapshot", return_value={}):
                            with mock.patch.object(pilot, "project_adrs", return_value=[]):
                                with mock.patch.object(
                                    pilot.subprocess, "run",
                                    return_value=types.SimpleNamespace(
                                        returncode=7, stdout="check failed",
                                        stderr="bad Project Truth"
                                    ),
                                ):
                                    with mock.patch.object(
                                        pilot, "probe", side_effect=[[], timeout],
                                    ):
                                        with self.assertRaises(subprocess.TimeoutExpired):
                                            pilot.evaluate(target, cards, progress)
        self.assertEqual(progress["stage"], "adapted-probing")
        self.assertEqual(progress["project_check_returncode"], 7)
        self.assertEqual(progress["project_check_stdout"], "check failed")
        self.assertEqual(progress["project_check_stderr"], "bad Project Truth")

    def test_successful_malformed_discover_payload_cannot_be_scored_as_no_hits(self):
        cards = self.fixture()
        oracle = json.loads(pilot.ORACLE.read_text(encoding="utf-8"))
        def fake_run(_target, command):
            if command[0] == "discover":
                return {"command": ["pact.py", *command], "returncode": 0,
                        "elapsed_ms": 1, "stderr": "", "data": {"results": {}}}
            return {
                "command": ["pact.py", *command], "returncode": 0,
                "elapsed_ms": 1, "stderr": "",
                "data": {
                    "status": "candidate", "artifacts": [], "decisions": [],
                    "applicable_rules": [], "known_unknowns": [],
                    "code_artifacts": [],
                    "context_budget": {"selected_estimated_tokens": 0},
                },
            }
        with mock.patch.object(pilot.m0, "run_json", side_effect=fake_run):
            probes = pilot.probe(pathlib.Path("/tmp/frozen-fixture-not-accessed"), cards)
        self.assertEqual(len(probes), 6)
        self.assertTrue(all(x["discovery"]["schema_errors"] for x in probes))
        evidence = {
            "A_plain_legacy": probes, "B_adapted": probes,
            "unmodified_tracked_sources": True,
            "projected_paths": list(range(6)),
            "project_check_returncode": 0,
            "knowledge_expected": {}, "knowledge_after": {}, "install": {},
        }
        scored = pilot.score(evidence, cards, oracle)
        self.assertEqual(scored["engineering_safety_gate"], "FAIL")
        self.assertTrue(any("malformed successful CLI payload" in failure
                            for failure in scored["safety_gate_failures"]))
        self.assertFalse(scored["agent_semantic_obedience_verified"])

    def test_scoring_exception_retains_completed_a_b_probe_receipts(self):
        """Regression: an invalid sealed oracle cannot erase pre-scored runs."""
        finished = {
            "A_plain_legacy": [{"id": "case-a", "context": {"returncode": 0}}],
            "B_adapted": [{"id": "case-a", "context": {"returncode": 0}}],
            "unmodified_tracked_sources": True,
            "projected_paths": ["test-only-record"],
        }
        with tempfile.TemporaryDirectory(prefix="pact-brownfield-failure-") as td:
            target = pathlib.Path(td) / "copied-public-source"
            target.mkdir()
            with mock.patch.dict("os.environ", {
                "GITHUB_ACTIONS": "true", "RUNNER_TEMP": td,
            }):
                with mock.patch.object(sys, "argv", [
                    "brownfield_adr_viewer.py", "--target", str(target),
                ]):
                    with mock.patch.object(pilot, "evaluate", return_value=finished):
                        with mock.patch.object(
                            pilot, "score",
                            side_effect=ValueError("independent oracle failed validation"),
                        ):
                            output = io.StringIO()
                            with redirect_stdout(output):
                                rc = pilot.main()
        self.assertEqual(rc, 1)
        report = json.loads(output.getvalue())
        self.assertEqual(report["engineering_safety_gate"], "FAIL")
        self.assertTrue(report["completed_probes_preserved"])
        self.assertEqual(report["raw_probes"], finished)
        self.assertIn("oracle failed", report["safety_gate_failures"][0])
        self.assertFalse(report["real_agent_executed"])
        self.assertEqual(report["release_gate"], "HOLD")

    def test_scoring_fails_closed_if_source_or_history_changed(self):
        cards = self.fixture()
        oracle = json.loads(pilot.ORACLE.read_text(encoding="utf-8"))
        def packet(cid, expected):
            return {
                "id": cid,
                "discovery": {"returncode": 0, "hits": []},
                "context": {
                    "returncode": 0, "status": "candidate",
                    "current_decision_ids": list(expected),
                    "selected_ids": list(expected),
                    "applicable_rule_ids": [],
                    "selected_knowledge_files": len(expected),
                    "code_context_selected": 0,
                    "estimated_selected_tokens": 24,
                    "elapsed_ms": 1,
                },
            }
        original = [packet(c["id"], []) for c in cards["tasks"]]
        adapted = [
            packet(c["id"], oracle["expected_current"][c["id"]])
            for c in cards["tasks"]
        ]
        adapted[0]["context"]["current_decision_ids"] = ["DEC-ADR-0003"]
        adapted[0]["context"]["selected_ids"] = ["DEC-ADR-0003"]
        evidence = {
            "A_plain_legacy": original, "B_adapted": adapted,
            "unmodified_tracked_sources": False,
            "projected_paths": list(range(6)),
            "project_check_returncode": 0,
            "knowledge_expected": {"doc": "sha"}, "knowledge_after": {"doc": "sha"},
            "install": {},
        }
        result = pilot.score(evidence, cards, oracle)
        self.assertEqual(result["engineering_safety_gate"], "FAIL")
        self.assertTrue(any("tracked files changed" in err
                            for err in result["safety_gate_failures"]))
        self.assertTrue(any("historical" in err for err in result["safety_gate_failures"]))
        self.assertFalse(result["real_agent_executed"])
        self.assertFalse(result["owner_approval_authenticated"])
        self.assertEqual(result["release_gate"], "HOLD")
        del evidence["B_adapted"][0]
        with self.assertRaisesRegex(ValueError, "missing raw predictions"):
            pilot.score(evidence, cards, oracle)


if __name__ == "__main__":
    unittest.main()
