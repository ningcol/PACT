"""No-model regression tests for the task-close knowledge retention review."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))

from knowledge_retention import review
from schema_validate import load_schema, validate_instance
from converge import outcome as converge_outcome
from report import convergence_outcome as report_outcome


def retention(disposition="none", updated=None, created=None):
    return {
        "disposition": disposition,
        "rationale": "Reviewed task intent and durable knowledge sources.",
        "updated": [] if updated is None else updated,
        "created": [] if created is None else created,
    }


class KnowledgeRetentionTests(unittest.TestCase):
    def test_legacy_is_readable_and_opt_in_requires_review(self):
        self.assertEqual(review({})[0], [])
        self.assertEqual(review({})[1]["status"], "unreviewed")
        self.assertTrue(review({}, require=True)[0])

    def test_no_new_knowledge_for_code_only_change(self):
        errors, result = review(
            {"knowledge_retention": retention()},
            changed_files=["src/order.py", "tests/test_order.py"],
            require=True,
        )
        self.assertEqual(errors, [])
        self.assertEqual(result["disposition"], "none")
        self.assertTrue(result["changed_paths_checked"])
        self.assertFalse(result["semantic_verification"])

    def test_update_create_and_both_require_matching_paths(self):
        old = "docs/product/rules/order.md"
        new = ".agents/decisions/implemented/stock.md"
        for disp, updated, created in [
            ("update", [old], []),
            ("create", [], [new]),
            ("update-and-create", [old], [new]),
        ]:
            with self.subTest(disp=disp):
                problems, summary = review(
                    {"knowledge_retention": retention(disp, updated, created)},
                    changed_files=[old, new],
                    require=True,
                )
                self.assertEqual(problems, [])
                self.assertEqual(summary["status"], "reviewed")

    def test_pending_always_blocks_completion(self):
        data = {"knowledge_retention": retention("pending")}
        self.assertTrue(review(data)[0])
        report = {"findings": [], "coverage": [], **data}
        self.assertEqual(converge_outcome(report), "needs-reconciliation")
        self.assertEqual(report_outcome(report), "needs-reconciliation")

    def test_reject_empty_or_inconsistent_dispositions(self):
        for item in [
            retention("create"),
            retention("none", updated=["docs/product/rules/order.md"]),
            retention("update-and-create", updated=["docs/product/rules/order.md"]),
            retention("update", updated=["docs/product/rules/order.md"], created=["x.md"]),
            retention("create", created=["x.md", "x.md"]),
            retention("update", updated=["../escape.md"]),
            retention("update", updated=["docs\\rule.md"]),
            retention("update", updated=["/etc/passwd"]),
        ]:
            with self.subTest(item=item):
                self.assertTrue(review({"knowledge_retention": item})[0])

    def test_declared_paths_must_be_changed(self):
        doc = "docs/product/rules/order.md"
        errors, _ = review(
            {"knowledge_retention": retention("update", updated=[doc])},
            changed_files=["src/order.py"],
        )
        self.assertIn("not changed by task", " ".join(errors))

    def test_no_changes_claim_conflicts_with_changed_durable_source(self):
        errors, _ = review(
            {"knowledge_retention": retention()},
            changed_files=["docs/product/rules/order.md"],
        )
        self.assertIn("'none' conflicts", " ".join(errors))

    def test_schema_accepts_retention_but_not_unknown_fields(self):
        schema = load_schema(ROOT / ".pact/schema/convergence-report.schema.json")
        example = json.loads(
            (ROOT / ".pact/examples/convergence-report.example.json").read_text("utf-8")
        )
        self.assertEqual(validate_instance(example, schema), [])
        example["knowledge_retention"]["unknown"] = 1
        self.assertTrue(validate_instance(example, schema))

    def test_existing_command_surfaces_expose_opt_in(self):
        for command in [
            [sys.executable, str(ROOT / "scripts/pact/complete.py"), "--help"],
            [sys.executable, str(ROOT / "scripts/pact/pact.py"), "task", "finish", "--help"],
        ]:
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--require-knowledge-retention", result.stdout)


if __name__ == "__main__":
    unittest.main()
