"""S7 PACT-only synthetic evaluation—no external repo or real-Agent claims."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
MODULE = ROOT / "scripts" / "benchmark" / "eight_stage_synthetic.py"
spec = importlib.util.spec_from_file_location("pact_eight_stage_synthetic", MODULE)
harness = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(harness)


class SyntheticEightStageTests(unittest.TestCase):
    def test_scoring_is_oracle_based_and_reports_missing_files(self):
        metrics = {
            "paths": ["src/a.py", "src/b.py"],
            "code_file_count": 2,
            "selected_estimated_tokens": 120,
            "known_unknown_count": 1,
            "elapsed_ms": 50,
        }
        result = harness.score(metrics, ["src/a.py", "src/missing.py"])
        self.assertEqual(result["matched_oracle_files"], ["src/a.py"])
        self.assertEqual(result["missing_oracle_files"], ["src/missing.py"])
        self.assertEqual(result["recall"], 0.5)
        self.assertEqual(result["precision_proxy"], 0.5)

    def test_input_rejects_traversal(self):
        with tempfile.TemporaryDirectory(prefix="pact-s7-unsafe-") as td:
            root = pathlib.Path(td)
            for relative in ("../outside", "/absolute", "src/../../escape"):
                with self.subTest(relative=relative):
                    with self.assertRaises(ValueError):
                        harness._safe_file(root, relative)

    def test_case_id_cannot_escape_disposable_parent(self):
        inputs = json.loads(harness.CASES.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="pact-s7-id-") as td:
            root = pathlib.Path(td)
            escape_name = root.name + "-outside"
            bad = dict(inputs["cases"][0], id="../" + escape_name)
            escaped_path = root.parent / escape_name
            self.assertFalse(escaped_path.exists())
            with self.assertRaisesRegex(ValueError, "unsafe synthetic case id"):
                harness.evaluate_case(bad, parent=root)
            self.assertFalse(escaped_path.exists())

    def test_frozen_command_line_has_no_external_input_or_output(self):
        source = MODULE.read_text(encoding="utf-8")
        self.assertIn("frozen PACT-owned inputs", source)
        self.assertNotIn('parser.add_argument("--inputs"', source)
        self.assertNotIn('parser.add_argument("--oracle"', source)
        self.assertNotIn('parser.add_argument("--output"', source)

    def test_oracle_is_not_materialized_in_disposable_runtime(self):
        inputs = json.loads(harness.CASES.read_text(encoding="utf-8"))
        self.assertEqual(inputs["version"], 1)
        with tempfile.TemporaryDirectory(prefix="pact-s7-fixture-") as td:
            result = harness.evaluate_case(inputs["cases"][0], parent=pathlib.Path(td))
            target = pathlib.Path(td) / inputs["cases"][0]["id"]
            self.assertFalse((target / harness.ORACLE.name).exists())
            self.assertFalse(result["real_agent_executed"])
            self.assertFalse(result["owner_data_observed"])
            self.assertIn("default", result)
            self.assertIn("work", result)
            self.assertIn("code_file_count", result["default"])

    def test_evaluation_keeps_human_data_null(self):
        inputs = json.loads(harness.CASES.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="pact-s7-report-") as td:
            case = inputs["cases"][0]
            small = {"version": 1, "cases": [case]}
            oracle = json.loads(harness.ORACLE.read_text(encoding="utf-8"))
            only = {"version": 1, "cases": {case["id"]: oracle["cases"][case["id"]]}}
            path = pathlib.Path(td) / "oracle.json"
            path.write_text(json.dumps(only), encoding="utf-8")
            result = harness.evaluate(small, path)
        self.assertEqual(result["case_count"], 1)
        self.assertIsNone(result["owner_time_minutes"])
        self.assertIsNone(result["owner_clarification_count"])
        self.assertFalse(result["real_agent_compatibility_verified"])
        self.assertFalse(result["release_attestation"])
        self.assertIn(result["case_results"][0]["default"]["recall"], (0, 0.5, 1.0))


if __name__ == "__main__":
    unittest.main()
