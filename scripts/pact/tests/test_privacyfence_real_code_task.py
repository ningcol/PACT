"""Test the public-source replay machinery without downloading or editing upstream.

These use *local synthetic fixture modules* only. The separate GitHub Actions
job must prove the same signatures against the pinned real PrivacyFence source.
"""
from __future__ import annotations

import ast
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
import privacyfence_real_code_task as task


MINIMAL_EXPORT = '''"""Local test-only fake of the real export rendering boundary."""
import csv
import io
import json
FORMULA_TRIGGER_CHARS = ("=", "+", "-", "@", "\\t", "\\r")
def csv_cell(value):
    return str(value)
def _neutralise(value):
    return "'" + value if isinstance(value, str) and value.startswith(FORMULA_TRIGGER_CHARS) else value
def render(columns, rows, fmt, *, spreadsheet_safe=False):
''' + task.SOURCE_PATTERN + '''    return (json.dumps([dict(zip(columns, r)) for r in rows],
                       separators=(",", ":")) + "\\n").encode("utf-8")
'''


class SourceBoundCodeTaskUnitTests(unittest.TestCase):
    def test_precise_source_patch_refuses_missing_and_duplicate_anchor(self):
        self.assertEqual(MINIMAL_EXPORT.count(task.SOURCE_PATTERN), 1)
        transformed = task.fixture_patch(MINIMAL_EXPORT)
        self.assertNotIn("rows = [[_neutralise(v)", transformed)
        self.assertIn("for row in rows:", transformed)
        self.assertEqual(transformed.count(task.PATCH_PATTERN), 1)
        with self.assertRaisesRegex(ValueError, "missing/ambiguous"):
            task.fixture_patch(MINIMAL_EXPORT.replace("if spreadsheet_safe:", "if True:"))
        with self.assertRaisesRegex(ValueError, "missing/ambiguous"):
            task.fixture_patch(MINIMAL_EXPORT + task.SOURCE_PATTERN)

    def test_pinned_source_and_probe_are_parseable_python(self):
        ast.parse(MINIMAL_EXPORT)
        ast.parse(task.fixture_patch(MINIMAL_EXPORT))
        ast.parse(task.STREAM_PROBE)
        self.assertNotIn("DEC-PF-", task.TASK)
        self.assertNotIn("docs/adr/", task.TASK)
        self.assertEqual(
            task.ADR_BLOBS[
                "docs/adr/0180-jira-and-salesforce-csv-exports-neutralise-formula-cells.md"
            ], "cf7c47ff6276905f244c2194348466a4aa1e02e2",
        )

    def test_baseline_realistic_fixture_is_exact_red_then_streaming_green(self):
        with tempfile.TemporaryDirectory(prefix="pact-public-code-local-") as td:
            arm = pathlib.Path(td) / "A"
            package = arm / "src" / "privacyfence"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("", encoding="utf-8")
            module = package / "export_files.py"
            module.write_text(MINIMAL_EXPORT, encoding="utf-8")
            before = task.stream_check(arm, expected_red=True)
            self.assertTrue(before["expected_result_observed"])
            self.assertIn("EAGER_COPY_BEFORE_FIRST_WRITE", before["stderr"])
            module.write_text(task.fixture_patch(MINIMAL_EXPORT), encoding="utf-8")
            after = task.stream_check(arm, expected_red=False)
            self.assertTrue(after["expected_result_observed"])
            self.assertIn("STREAMING_CSV_OK", after["stdout"])

    def test_context_json_execution_does_not_truncate_middle(self):
        with tempfile.TemporaryDirectory(prefix="pact-code-context-json-") as td:
            root = pathlib.Path(td)
            data = "x" * 9000
            receipt = task.run_step(
                [sys.executable, "-c", f"print({data!r})"],
                cwd=root, stdout_limit=250000,
            )
            self.assertEqual(receipt["returncode"], 0)
            self.assertEqual(receipt["stdout"].strip(), data)

    def test_unavailable_real_source_fails_closed_without_success_claim(self):
        with tempfile.TemporaryDirectory(prefix="pact-code-no-upstream-") as td:
            root = pathlib.Path(td)
            report = task.execute(root / "missing", root)
            self.assertEqual(report["engineering_gate"], "FAIL")
            self.assertTrue(report["safety_failures"])
            self.assertFalse(report["live_coding_agent_executed"])
            self.assertEqual(report["release_gate"], "HOLD")


if __name__ == "__main__":
    unittest.main()
