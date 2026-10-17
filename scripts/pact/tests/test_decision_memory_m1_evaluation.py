"""M1 instrument regressions. Passing here is not real Agent or Owner evidence."""
from __future__ import annotations

import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
import decision_memory_m0 as m0
import decision_memory_m1 as benchmark


class ColdStartM1Tests(unittest.TestCase):
    @staticmethod
    def inputs():
        cards = json.loads(benchmark.CARDS.read_text(encoding="utf-8"))
        corpus = json.loads(m0.INPUTS.read_text(encoding="utf-8"))
        oracle = json.loads(benchmark.ORACLE.read_text(encoding="utf-8"))
        return cards, corpus, oracle

    def test_precommitted_cards_corpus_oracle_and_no_id_hint(self):
        cards, corpus, oracle = self.inputs()
        benchmark.validate_cards(cards, corpus)
        benchmark.validate_oracle(oracle, cards, corpus)
        self.assertEqual(cards["baseline_main_sha"],
                         "b96a64485e1c855c5caeedb2a2addcd766f6398b")
        self.assertEqual(len(cards["cases"]), 8)
        self.assertEqual(sum(bool(x) for x in oracle["expected_current"].values()), 7)
        for case in cards["cases"]:
            self.assertNotIn("DEC-", case["task"].upper())
            self.assertNotIn("explicit_decision_hint", case)
        self.assertEqual(cards["settings"]["max_path_hints"], 4)

    def test_memory_snapshot_detects_non_markdown_long_term_notes(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix="pact-m1-notes-") as temp:
            root = pathlib.Path(temp)
            folder = root / ".agents" / "decisions" / "implemented"
            folder.mkdir(parents=True)
            (folder / "original.md").write_text("# original", encoding="utf-8")
            before = benchmark.source_snapshot(root)
            (folder / "new-note.json").write_text('{"note":"unnecessary"}', encoding="utf-8")
            after = benchmark.source_snapshot(root)
            self.assertEqual(len(after), len(before) + 1)
            self.assertIn(".agents/decisions/implemented/new-note.json", after)

    def test_git_blob_pin_ignores_checkout_crlf_but_not_content_changes(self):
        import tempfile
        original = benchmark.CARDS.read_bytes().replace(b"\r\n", b"\n")
        with tempfile.TemporaryDirectory(prefix="pact-m1-hash-") as tmp:
            target = pathlib.Path(tmp) / "cards.json"
            target.write_bytes(original.replace(b"\n", b"\r\n"))
            self.assertEqual(benchmark.blob_sha(target), benchmark.CARDS_BLOB)
            target.write_bytes(original.replace(b"\n", b"\r\n") + b"x")
            self.assertNotEqual(benchmark.blob_sha(target), benchmark.CARDS_BLOB)

    def test_caller_cannot_override_frozen_fixture(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "benchmark" /
                                 "decision_memory_m1.py"), "--cards", "/tmp/override"],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no external fixture arguments", result.stderr)

    def test_only_exact_public_paths_and_bounded_history(self):
        index = {"documents": [
            {"id": "DEC-A", "artifact_type": "decision", "status": "implemented",
             "path": "decision/A.md", "paths": ["src/x/a.py"]},
            {"id": "DEC-B", "artifact_type": "decision", "status": "superseded",
             "path": "decision/B.md", "paths": ["src/x/a.py"]},
            {"id": "DEC-C", "artifact_type": "decision", "status": "rejected",
             "path": "decision/C.md", "paths": ["src/x/b.py"]},
            {"id": "DEC-D", "artifact_type": "decision", "status": "implemented",
             "path": "decision/D.md", "paths": []},
        ]}
        nav = benchmark.path_diagnostic(index, ["src/x/a.py"], 4)
        self.assertEqual([x["id"] for x in nav["current_candidates"]], ["DEC-A"])
        self.assertEqual([x["id"] for x in nav["historical_candidates"]], ["DEC-B"])
        self.assertFalse(nav["injected_into_context"])
        self.assertFalse(nav["retrieval_treatment"])
        self.assertEqual(
            benchmark.path_diagnostic(index, ["src/x/new-name.py"], 4)["total_raw_matches"], 0,
        )
        small = benchmark.path_diagnostic(index, ["src/x/a.py", "src/x/b.py"], 1)
        self.assertEqual(
            len(small["current_candidates"]) + len(small["historical_candidates"]), 1
        )
        self.assertEqual(small["omitted_candidates"], 2)

    def test_no_unknown_discover_id_or_forged_unclaimed_document(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix="pact-m1-tamper-") as td:
            project = pathlib.Path(td)
            real_doc = project / "docs" / "project.md"
            real_doc.parent.mkdir()
            real_doc.write_text("# Real doc\n", encoding="utf-8")
            genuine = benchmark.m0.digest_file(real_doc)
            index = {"documents": [{
                "path": "docs/project.md", "id": None,
                "artifact_type": "document", "status": None
            }]}
            item = {
                "A": {
                    "discovery": {
                        "hits": [{"path": "docs/project.md",
                                  "id": "DEC-NOT-IN-FIXTURE",
                                  "type": "decision", "status": "implemented"}],
                        "schema_errors": [],
                    },
                    "context": {
                        "selected_artifacts": [
                            {"path": "docs/project.md", "id": None,
                             "artifact_type": "document", "sha256": "a" * 64}
                        ],
                        "schema_errors": [],
                    },
                }
            }
            benchmark.verify_probe_source_evidence(project, item, index)
            self.assertTrue(item["A"]["discovery"]["schema_errors"])
            self.assertTrue(item["A"]["context"]["schema_errors"])
            item["A"]["discovery"]["hits"] = [{
                "path": "docs/project.md", "id": None,
                "type": "document", "status": None
            }]
            item["A"]["context"]["selected_artifacts"][0]["sha256"] = genuine
            item["A"]["discovery"]["schema_errors"] = []
            item["A"]["context"]["schema_errors"] = []
            benchmark.verify_probe_source_evidence(project, item, index)
            self.assertEqual(item["A"]["discovery"]["schema_errors"], [])
            self.assertEqual(item["A"]["context"]["schema_errors"], [])

    def test_mutated_frozen_source_is_detected_by_independent_expected_bytes(self):
        cards, corpus, _ = self.inputs()
        expected = benchmark.fixture_expected_source_hashes(corpus)
        self.assertEqual(len(expected), 9)
        with tempfile.TemporaryDirectory(prefix="pact-m1-frozen-") as td:
            root = pathlib.Path(td)
            for entry in corpus["documents"]:
                path = root / entry["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(m0._doc_text(entry), encoding="utf-8")
            self.assertEqual(benchmark.normalized_installed_source_hashes(root, list(expected)), expected)
            first = root / corpus["documents"][0]["path"]
            first.write_text(first.read_text(encoding="utf-8") + "altered\n",
                             encoding="utf-8")
            self.assertNotEqual(benchmark.normalized_installed_source_hashes(root, list(expected)), expected)

    def test_installer_nonzero_and_timeout_receipts_are_not_erased(self):
        import types
        progress = {}
        failed = types.SimpleNamespace(returncode=19, stdout="invalid fixture",
                                       stderr="authorities conflict")
        with mock.patch.object(benchmark.subprocess, "run", return_value=failed):
            outcome = benchmark.run_fixture_step(
                [sys.executable, "pact.py", "check"], cwd=benchmark.ROOT,
                stage="check", progress=progress
            )
        self.assertEqual(outcome.returncode, 19)
        self.assertEqual(progress["fixture_process_receipts"][0]["returncode"], 19)
        self.assertIn("authorities", progress["fixture_process_receipts"][0]["stderr"])
        exc = subprocess.TimeoutExpired(
            ["pact.py", "check"], 3, output=b"partial output", stderr=b"timeout stderr"
        )
        with mock.patch.object(benchmark.subprocess, "run", side_effect=exc):
            with self.assertRaises(subprocess.TimeoutExpired):
                benchmark.run_fixture_step(
                    ["pact.py", "check"], cwd=benchmark.ROOT,
                    stage="check-timeout", progress=progress
                )
        receipt = progress["fixture_process_receipts"][-1]
        self.assertTrue(receipt["timed_out"])
        self.assertIn("partial output", receipt["stdout"])
        self.assertIn("timeout stderr", receipt["stderr"])

    def test_malformed_context_list_cannot_erase_completed_envelope(self):
        cards, _, _ = self.inputs()
        success = {
            "command": ["pact.py", "discover"], "returncode": 0,
            "elapsed_ms": 1, "stderr": "", "data": {"results": []}
        }
        malformed = {
            "command": ["pact.py", "context"], "returncode": 0,
            "elapsed_ms": 1, "stderr": "",
            "data": {
                "artifacts": [], "decisions": [], "applicable_rules": [],
                "code_artifacts": 7, "known_unknowns": 3,
                "context_budget": {"selected_estimated_tokens": 0},
                "status": "candidate",
            },
        }
        progress = {}
        with mock.patch.object(m0, "run_json", side_effect=[success, malformed]):
            outcome = benchmark.context_probe(
                pathlib.Path("/tmp/pact-no-files"), cards["cases"][0],
                cards["settings"], progress
            )
        self.assertEqual(outcome["context"]["code_files"], 0)
        self.assertEqual(outcome["context"]["known_unknown_count"], 0)
        self.assertTrue(outcome["context"]["schema_errors"])
        self.assertEqual(progress["context"]["schema_errors"],
                         outcome["context"]["schema_errors"])

    def test_completed_discover_receipt_survives_context_timeout(self):
        cards, _, _ = self.inputs()
        discovery = {
            "command": ["pact.py", "discover"], "returncode": 0,
            "elapsed_ms": 2, "stderr": "", "data": {"results": []},
        }
        partial = {}
        with mock.patch.object(
            m0, "run_json",
            side_effect=[discovery, subprocess.TimeoutExpired(["context"], 2)],
        ):
            with self.assertRaises(subprocess.TimeoutExpired):
                benchmark.context_probe(
                    pathlib.Path("/tmp/fake-m1"), cards["cases"][0],
                    cards["settings"], partial,
                )
        self.assertEqual(partial["discovery_before_context"], discovery)
        self.assertTrue(partial["context_failure"]["timed_out"])
        self.assertIn("context", partial["context_failure"]["command"])

    def test_malformed_unclaimed_context_artifact_is_not_safe(self):
        self.assertFalse(benchmark.valid_context_artifact({}))
        self.assertFalse(benchmark.valid_context_artifact({
            "id": None, "artifact_type": "document", "path": "README.md",
            "sha256": "not-a-digest",
        }))
        self.assertTrue(benchmark.valid_context_artifact({
            "id": None, "artifact_type": "document", "path": "README.md",
            "sha256": "a" * 64,
        }))
        cards, corpus, oracle = self.inputs()
        predictions = []
        for card in cards["cases"]:
            discovery = {
                "command": ["pact.py", "discover", card["task"]],
                "returncode": 0, "elapsed_ms": 1, "stderr": "",
                "data": {"results": []},
            }
            packet = {
                "command": ["pact.py", "context", card["task"]],
                "returncode": 0, "elapsed_ms": 1, "stderr": "",
                "data": {
                    "status": "candidate", "artifacts": [{}],
                    "decisions": [], "applicable_rules": [],
                    "code_artifacts": [], "known_unknowns": [],
                    "context_budget": {"selected_estimated_tokens": 0},
                },
            }
            with mock.patch.object(m0, "run_json", side_effect=[discovery, packet]):
                a = benchmark.context_probe(pathlib.Path("/tmp/unused"), card,
                                            cards["settings"])
            self.assertTrue(a["context"]["schema_errors"])
            predictions.append({
                "id": card["id"], "task": card["task"],
                "type": card["type"], "changed_paths": card["changed_paths"],
                "A": a,
                "B_path_navigation_only": {
                    "current_candidates": [], "historical_candidates": [],
                    "injected_into_context": False,
                    "retrieval_treatment": False,
                },
            })
        evidence = {
            "predictions": predictions,
            "installation": {"compact_archive_present": True},
            "knowledge_source_mutations": [],
            "knowledge_files_before": 9, "knowledge_files_after": 9,
            "stale_declared_code_anchors": [],
        }
        scored = benchmark.score(evidence, oracle, cards, corpus)
        self.assertEqual(scored["synthetic_safety_gate"], "FAIL")
        self.assertTrue(any("malformed discovery/context" in issue
                            for issue in scored["gate_failures"]))

    def test_main_preserves_completed_a_probes_on_map_failure(self):
        import subprocess
        previous = {"id": "pre-failure", "A": {"context": {"returncode": 0}},
                    "B_path_navigation_only": None}
        def interrupted(progress):
            progress["stage"] = "collect-predictions"
            progress["predictions"] = [previous]
            raise ValueError("installed Project Map malformed")
        output = io.StringIO()
        with mock.patch.object(benchmark, "evaluate", side_effect=interrupted):
            with mock.patch.object(sys, "argv", ["decision_memory_m1.py"]):
                with redirect_stdout(output):
                    result = benchmark.main()
        self.assertEqual(result, 1)
        report = json.loads(output.getvalue())
        self.assertEqual(report["synthetic_safety_gate"], "FAIL")
        self.assertTrue(report["completed_probes_preserved"])
        self.assertEqual(report["partial_probe_evidence"]["predictions"], [previous])
        self.assertIn("Project Map malformed", report["gate_failures"][0])
        self.assertEqual(report["release_gate"], "HOLD")

    def test_malformed_discovery_record_is_not_a_valid_empty_hit(self):
        self.assertFalse(benchmark.valid_discovery_hit({}))
        self.assertFalse(benchmark.valid_discovery_hit({
            "artifact_type": "decision", "id": None,
            "status": "implemented", "path": ".agents/decisions/a.md",
        }))
        self.assertFalse(benchmark.valid_discovery_hit({
            "artifact_type": "decision", "id": "DEC-TEST",
            "status": "implemented", "path": "../escape.md",
        }))
        self.assertTrue(benchmark.valid_discovery_hit({
            "artifact_type": "document", "id": None,
            "status": None, "path": "docs/readme.md",
        }))

    def test_invalid_project_map_cannot_hide_frozen_decisions(self):
        cards, corpus, _ = self.inputs()
        docs = [
            {"id": row["id"], "path": row["path"],
             "artifact_type": row["type"], "status": row["status"],
             "paths": row.get("paths", [])}
            for row in corpus["documents"]
        ]
        lookup = {x["id"]: x["path"] for x in corpus["documents"]}
        index = {
            "repository_root": ".", "documents": docs, "id_to_path": lookup,
        }
        benchmark.validate_installed_project_map(index, corpus)
        with self.assertRaisesRegex(ValueError, "omits"):
            benchmark.validate_installed_project_map(
                {**index, "documents": docs[:-1],
                 "id_to_path": dict(list(lookup.items())[:-1])}, corpus
            )
        with self.assertRaisesRegex(ValueError, "malformed document"):
            benchmark.validate_installed_project_map(
                {**index, "documents": docs[:-1] + [{}]}, corpus
            )
        with self.assertRaisesRegex(ValueError, "top-level"):
            benchmark.validate_installed_project_map(
                {"repository_root": ".", "id_to_path": {}, "documents": "corrupt"}, corpus
            )

    def test_claimed_current_decision_needs_real_path_type_and_digest(self):
        cards, corpus, oracle = self.inputs()
        doc = next(x for x in corpus["documents"]
                   if x["id"] == "DEC-CACHE-OWNERSHIP")
        digest = "d" * 64
        predictions = []
        for case in cards["cases"]:
            current = ["DEC-CACHE-OWNERSHIP"] if case["id"] == "cache-owner-conflict" else []
            predictions.append({
                "id": case["id"], "task": case["task"],
                "type": case["type"], "changed_paths": case["changed_paths"],
                "A": {
                    "discovery": {"returncode": 0, "schema_errors": []},
                    "context": {
                        "returncode": 0, "status": "candidate",
                        "current_decision_ids": current,
                        "applicable_rule_ids": [],
                        "selected_ids": current,
                        "selected_artifacts": (
                            [{"id": current[0]}] if current else []
                        ),
                        "schema_errors": [],
                        "selected_knowledge_files": len(current),
                        "estimated_selected_tokens": 100,
                        "code_files": 0,
                    },
                },
                "B_path_navigation_only": {
                    "current_candidates": [], "historical_candidates": [],
                    "injected_into_context": False, "retrieval_treatment": False,
                },
            })
        evidence = {
            "predictions": predictions,
            "installation": {"compact_archive_present": True},
            "knowledge_source_mutations": [],
            "knowledge_source_sha256": {doc["path"]: digest},
            "knowledge_files_before": 9, "knowledge_files_after": 9,
            "stale_declared_code_anchors": [],
        }
        rejected = benchmark.score(evidence, oracle, cards, corpus)
        self.assertEqual(rejected["synthetic_safety_gate"], "FAIL")
        self.assertTrue(any("missing valid materialized source record" in x
                            for x in rejected["gate_failures"]))
        predictions[0]["A"]["context"]["selected_artifacts"][0].update({
            "path": doc["path"], "artifact_type": "decision", "sha256": digest,
        })
        accepted = benchmark.score(evidence, oracle, cards, corpus)
        self.assertEqual(accepted["synthetic_safety_gate"], "PASS")
        self.assertEqual(accepted["cold_start_effectiveness"], "HOLD")

    def test_successful_malformed_discover_is_not_silently_treated_as_no_hits(self):
        cards, corpus, oracle = self.inputs()
        predictions = []
        for case in cards["cases"]:
            discovery = {
                "command": ["pact.py", "discover", case["task"]],
                "returncode": 0, "elapsed_ms": 1, "stderr": "",
                "data": {"results": "unexpected-object-not-array"},
            }
            context = {
                "command": ["pact.py", "context", case["task"]],
                "returncode": 0, "elapsed_ms": 1, "stderr": "",
                "data": {
                    "status": "candidate", "artifacts": [],
                    "decisions": [], "applicable_rules": [],
                    "context_budget": {"selected_estimated_tokens": 0},
                    "code_artifacts": [], "known_unknowns": [],
                },
            }
            with mock.patch.object(m0, "run_json", side_effect=[discovery, context]):
                probed = benchmark.context_probe(
                    pathlib.Path("/tmp/synthetic-no-cli"), case, cards["settings"]
                )
            self.assertTrue(probed["discovery"]["schema_errors"])
            predictions.append({
                "id": case["id"], "task": case["task"],
                "type": case["type"], "changed_paths": case["changed_paths"],
                "A": probed,
                "B_path_navigation_only": {
                    "current_candidates": [], "historical_candidates": [],
                    "injected_into_context": False, "retrieval_treatment": False,
                    "total_raw_matches": 0, "omitted_candidates": 0,
                },
            })
        evidence = {
            "predictions": predictions,
            "installation": {"compact_archive_present": True},
            "knowledge_source_mutations": [],
            "knowledge_files_before": 9, "knowledge_files_after": 9,
            "stale_declared_code_anchors": [],
        }
        result = benchmark.score(evidence, oracle, cards, corpus)
        self.assertEqual(result["synthetic_safety_gate"], "FAIL")
        self.assertTrue(any("malformed discovery/context" in x
                            for x in result["gate_failures"]))

    def test_installed_commands_never_receive_scoring_oracle_or_decision_id(self):
        cards, _, _ = self.inputs()
        calls = []
        def capture(_target, command):
            calls.append(command)
            if command[0] == "discover":
                return {"command": ["pact.py", *command], "returncode": 0,
                        "elapsed_ms": 1, "stderr": "",
                        "data": {"results": []}}
            return {"command": ["pact.py", *command], "returncode": 0,
                    "elapsed_ms": 1, "stderr": "",
                    "data": {"status": "candidate", "artifacts": [],
                             "decisions": [], "applicable_rules": [],
                             "context_budget": {"selected_estimated_tokens": 0}}}
        with mock.patch.object(m0, "run_json", side_effect=capture):
            for case in cards["cases"]:
                benchmark.context_probe(pathlib.Path("/tmp/pact-m1-fake"), case,
                                        cards["settings"])
        self.assertEqual(len(calls), 16)
        for call in calls:
            self.assertNotIn("--query", call)
            self.assertNotIn("--require-rule", call)
            self.assertFalse(any("DEC-" in value for value in call))

    def test_scoring_does_not_approve_historical_promotion(self):
        cards, corpus, oracle = self.inputs()
        predictions = []
        for case in cards["cases"]:
            cid = case["id"]
            selected = list(oracle["expected_current"][cid])
            if cid == "routine-docs":
                selected = ["DEC-REPLAY-OLD"]  # invalid and unrelated
            predictions.append({
                "id": cid, "type": case["type"], "task": case["task"],
                "changed_paths": case["changed_paths"],
                "A": {"context": {
                    "returncode": 0, "status": "candidate",
                    "current_decision_ids": selected,
                    "selected_ids": [] if cid == "broker-local-counter" else selected,
                    "applicable_rule_ids": ["RULE-CACHE-RETENTION"] if cid == "cache-owner-conflict" else [],
                    "selected_knowledge_files": 1, "estimated_selected_tokens": 10,
                    "code_files": 0},
                    "discovery": {"returncode": 0}},
                "B_path_navigation_only": {
                    "current_candidates": [], "historical_candidates": [],
                    "injected_into_context": False, "retrieval_treatment": False,
                    "total_raw_matches": 0, "omitted_candidates": 0},
            })
        evidence = {
            "predictions": predictions,
            "installation": {"compact_archive_present": True},
            "knowledge_source_mutations": [],
            "knowledge_files_before": 9, "knowledge_files_after": 9,
            "stale_declared_code_anchors": [],
        }
        report = benchmark.score(evidence, oracle, cards, corpus)
        self.assertEqual(report["synthetic_safety_gate"], "FAIL")
        self.assertTrue(any("promoted" in failure for failure in report["gate_failures"]))
        self.assertTrue(any("unrelated" in failure for failure in report["gate_failures"]))
        self.assertTrue(any("not materialized" in failure for failure in report["gate_failures"]))
        self.assertTrue(any("applicable Rule not materialized" in failure for failure in report["gate_failures"]))
        self.assertEqual(report["target_decision_count"], 7)
        self.assertFalse(report["agent_obedience_verified"])
        self.assertEqual(report["release_gate"], "HOLD")
        evidence["predictions"] = predictions[:-1]
        with self.assertRaisesRegex(ValueError, "denominator"):
            benchmark.score(evidence, oracle, cards, corpus)

    def test_main_emits_full_failing_json_and_nonzero_exit(self):
        failure = {"synthetic_safety_gate": "FAIL",
                   "gate_failures": ["explicit unknown Decision promoted"],
                   "real_agent_executed": False, "release_gate": "HOLD"}
        stream = io.StringIO()
        with mock.patch.object(benchmark, "evaluate", return_value=failure):
            with mock.patch.object(sys, "argv", ["decision_memory_m1.py"]):
                with redirect_stdout(stream):
                    exit_code = benchmark.main()
        self.assertEqual(exit_code, 1)
        self.assertEqual(json.loads(stream.getvalue()), failure)

    def test_installed_m1_evidence_preserves_frozen_boundaries(self):
        result = benchmark.evaluate()
        self.assertEqual(result["case_count"], 8)
        self.assertEqual(result["target_decision_count"], 7)
        self.assertRegex(result["evaluated_installed_compact_runtime_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(result["evaluated_source_checkout_git_sha"], r"^[0-9a-f]{40}$")
        self.assertGreaterEqual(result["A_oracle_extraneous_current_candidates"], 0)
        self.assertGreaterEqual(result["A_total_current_decision_candidates"],
                                result["A_matched_decisions"])
        self.assertTrue(result["precision_proxy_is_not_verified_semantic_precision"])
        self.assertEqual(result["knowledge_files_before"], 9)
        self.assertEqual(result["knowledge_source_mutations"], [])
        self.assertEqual(result["knowledge_files_after"], 9)
        self.assertEqual(result["synthetic_safety_gate"], "PASS",
                         result["gate_failures"])
        self.assertEqual(result["independent_real_agent_gate"],
                         "BLOCKED_NO_AUTHORIZED_RUNNER")
        self.assertEqual(result["release_gate"], "HOLD")
        self.assertFalse(result["B_is_actual_context_or_agent_recall"])
        self.assertFalse(result["real_agent_executed"])
        self.assertFalse(result["independent_holdout"])
        self.assertFalse(result["agent_obedience_verified"])
        self.assertFalse(result["owner_approval_authenticated"])
        self.assertFalse(result["release_attestation"])
        self.assertIsNone(result["owner_time_minutes"])
        self.assertIsNone(result["added_model_tokens"])
        self.assertEqual(result["cold_start_effectiveness"],
                         "HOLD" if result["A_matched_decisions"] != 7
                         else "DIAGNOSTIC_ONLY")
        rows = {x["id"]: x for x in result["case_results"]}
        self.assertIn("DEC-BROKER-EDGE", [
            x["id"] for x in rows["broker-local-counter"]
            ["B_path_navigation_only"]["current_candidates"]
        ])
        for cid in ("pathless-counter", "renamed-ingress"):
            self.assertEqual(
                rows[cid]["B_path_navigation_only"]["current_candidates"], []
            )
        self.assertEqual(
            rows["routine-docs"]["B_path_navigation_only"]["current_candidates"], []
        )
        print(
            "PACT M1 NO-ID installed synthetic only: " +
            json.dumps({"A_recall": result["A_weighted_recall"],
                        "path_navigation_candidate_coverage":
                        result["B_diagnostic_union_candidate_coverage"],
                        "hard_safety": result["synthetic_safety_gate"],
                        "real_agent_gate": result["independent_real_agent_gate"]})
        )


if __name__ == "__main__":
    unittest.main()
