"""Frozen M0 decision-memory A/B: correctness of the evaluation instrument.

The integration case executes the actual installed compact PACT runtime;
it does not create an LLM agent and must never claim independent blindness.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "benchmark" / "decision_memory_m0.py"
spec = importlib.util.spec_from_file_location("pact_m0_decision_memory", SCRIPT)
benchmark = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(benchmark)


class DecisionMemoryM0EvaluationTests(unittest.TestCase):
    def test_preregistered_inputs_and_oracle_are_consistent(self):
        inputs = json.loads(benchmark.INPUTS.read_text(encoding="utf-8"))
        oracle = json.loads(benchmark.ORACLE.read_text(encoding="utf-8"))
        benchmark.validate_inputs(inputs)
        self.assertEqual(
            {item["id"] for item in inputs["cases"]},
            set(oracle["expected"]),
        )
        self.assertEqual(
            sum(bool(item["explicit_decision_hint"]) for item in inputs["cases"]),
            6,
        )
        self.assertEqual(inputs["settings"]["knowledge_limit"], 4)
        self.assertEqual(inputs["settings"]["token_budget"], 2048)

    def test_fixture_paths_reject_traversal_and_symlink_escape(self):
        with tempfile.TemporaryDirectory(prefix="pact-m0-traversal-") as td:
            root = pathlib.Path(td)
            for candidate in ("../outside", "/etc/passwd", "src/../../escape",
                              r"src\windows\path", ""):
                with self.subTest(path=candidate):
                    with self.assertRaises(ValueError):
                        benchmark.safe_file(root, candidate)
            outside = root.parent / "outside-file"
            if not outside.exists():
                outside.write_text("fixture", encoding="utf-8")
                self.addCleanup(lambda: outside.unlink(missing_ok=True))
            target = root / "linked"
            try:
                target.symlink_to(outside)
            except (OSError, NotImplementedError):
                pass
            else:
                with self.assertRaises(ValueError):
                    benchmark.safe_file(root, "linked")

    def test_script_does_not_accept_external_fixture_overrides(self):
        output = subprocess.run(
            [sys.executable, str(SCRIPT), "--inputs", "../nonpact"],
            cwd=ROOT, capture_output=True, text=True, timeout=15,
        )
        self.assertNotEqual(output.returncode, 0)
        self.assertIn("no arbitrary fixture paths", output.stderr)

    def test_scoring_rejects_mismatched_oracle_before_claims(self):
        inputs = json.loads(benchmark.INPUTS.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValueError, "frozen oracle"):
            benchmark.score(
                {"predictions": []}, {"version": 1, "expected": {}}, inputs
            )

    def test_actual_installed_runtime_experiment_preserves_boundaries(self):
        report = benchmark.evaluate()
        self.assertEqual(report["case_count"], 7)
        self.assertEqual(report["oracle_target_count"], 6)
        self.assertEqual(report["B_explicit_hint_case_count"], 6)
        self.assertTrue(report["installation"]["compact_archive_present"])
        self.assertTrue(report["installation"]["installed_artifact_check_passed"])
        self.assertFalse(report["independently_withheld_oracle"])
        self.assertFalse(report["real_agent_executed"])
        self.assertFalse(report["real_agent_semantic_obedience_verified"])
        self.assertFalse(report["real_owner_data_observed"])
        self.assertFalse(report["human_approval_authenticated"])
        self.assertIsNone(report["owner_time_minutes"])
        self.assertIsNone(report["owner_clarification_count"])
        self.assertIsNone(report["added_model_tokens"])
        self.assertFalse(report["release_attestation"])
        self.assertEqual(set(report["weighted_decision_recall"]), {"A", "B"})
        self.assertEqual(len(report["case_results"]), 7)
        self.assertTrue(any(
            x["decision_id"] == "DEC-PAYLOAD-ANCHOR"
            and x["path"] == "src/account/legacy_bridge.py"
            for x in report["missing_declared_code_paths"]
        ))
        for case in report["case_results"]:
            for arm in ("A", "B"):
                packet = case[arm]["context"]
                self.assertEqual(packet["returncode"], 0)
                self.assertEqual(case[arm]["discovery"]["returncode"], 0)
                self.assertEqual(packet["code_context_selected"], 0)
                self.assertEqual(packet["status"], "candidate")
                self.assertLessEqual(packet["selected_knowledge_files"], 4)
                self.assertFalse(packet["authority_failures"])
            self.assertIsInstance(case["delta_B_minus_A_elapsed_ms"], float)
        # This diagnostic only reports a failure. It never tunes the corpus
        # or claims a genuine blind/Owner/Agent win from its synthetic oracle.
        self.assertIn(report["synthetic_engineering_gate"], ("PASS", "FAIL"))
        self.assertIsInstance(report["gate_failures"], list)
        print(
            "PACT M0 installed synthetic decision A/B (not Agent/Owner): "
            + json.dumps({
                "weighted_recall": report["weighted_decision_recall"],
                "gate": report["synthetic_engineering_gate"],
                "gate_failures": report["gate_failures"],
            }, sort_keys=True)
        )


if __name__ == "__main__":
    unittest.main()
