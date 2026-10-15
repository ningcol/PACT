"""R05: an intentionally removed Context artifact is not a content update."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "pact"))

from convergence_coverage import review as review_coverage
from converge import outcome, validate


class ConvergenceRemovalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-r05-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.artifact = self.root / "docs" / "rule.md"
        self.artifact.parent.mkdir()
        self.artifact.write_text("# Original rule\n", encoding="utf-8")
        self.original_sha = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.context_path = self.root / "context.json"

    def review(self, disposition: str, *, prepared_hash: bool = True,
               findings: list[dict] | None = None) -> tuple[list[str], dict, dict]:
        artifact = {"path": "docs/rule.md"}
        if prepared_hash:
            artifact["sha256"] = self.original_sha
        context = {"risk_level": "low", "artifacts": [artifact]}
        self.context_path.write_text(
            json.dumps(context, sort_keys=True) + "\n", encoding="utf-8"
        )
        context_sha = hashlib.sha256(self.context_path.read_bytes()).hexdigest()
        report = {
            "version": 1,
            "task_id": "TASK-R05",
            "change": "Review the rule",
            "owner_summary": "Review the rule against the task intent.",
            "context_sha256": context_sha,
            "coverage": [{
                "path": "docs/rule.md",
                "disposition": disposition,
                "rationale": "Checked the authoritative task decision for this artifact.",
            }],
            "findings": findings or [],
        }
        self.assertEqual(validate(report), [], report)
        errors, stats = review_coverage(
            context,
            report,
            root=self.root,
            context_path=self.context_path,
            expected_context_sha256=context_sha,
        )
        return errors, stats, report


    def test_schema_runtime_and_skill_dispositions_are_consistent(self) -> None:
        from convergence_coverage import VALID_DISPOSITIONS
        schema = json.loads((
            PROJECT_ROOT / ".pact" / "schema" / "convergence-report.schema.json"
        ).read_text(encoding="utf-8"))
        accepted = set(schema["properties"]["coverage"]["items"]["properties"]
                       ["disposition"]["enum"])
        self.assertEqual(accepted, VALID_DISPOSITIONS)
        guide = (PROJECT_ROOT / ".agents" / "skills" / "convergence-review.md").read_text(
            encoding="utf-8"
        )
        for disposition in sorted(accepted):
            self.assertIn("`" + disposition + "`", guide)
        self.assertIn("A missing artifact is **never** `updated`", guide)

    def test_modified_present_file_is_updated(self) -> None:
        self.artifact.write_text("# Revised rule\n", encoding="utf-8")
        errors, stats, _ = self.review("updated")
        self.assertEqual(errors, [])
        self.assertEqual(stats["updated_verified"], ["docs/rule.md"])
        self.assertEqual(stats["removed_verified"], [])

    def test_deletion_is_never_a_verified_update(self) -> None:
        self.artifact.unlink()
        errors, stats, _ = self.review("updated")
        self.assertTrue(any("updated but artifact no longer exists" in e for e in errors))
        self.assertEqual(stats["updated_verified"], [])
        self.assertEqual(stats["removed_verified"], [])

    def test_intentional_deletion_has_explicit_verified_disposition(self) -> None:
        self.artifact.unlink()
        errors, stats, report = self.review("removed")
        self.assertEqual(errors, [])
        self.assertEqual(stats["updated_verified"], [])
        self.assertEqual(stats["removed_verified"], ["docs/rule.md"])
        self.assertEqual(outcome(report), "converged")

    def test_existing_or_recreated_file_is_not_removed(self) -> None:
        for content in ("# Original rule\n", "# Recreated rule\n"):
            with self.subTest(content=content):
                self.artifact.write_text(content, encoding="utf-8")
                errors, stats, _ = self.review("removed")
                self.assertTrue(any("removed but artifact path still exists" in e for e in errors))
                self.assertEqual(stats["removed_verified"], [])

    def test_directory_replacement_is_not_deletion(self) -> None:
        self.artifact.unlink()
        self.artifact.mkdir()
        errors, stats, _ = self.review("removed")
        self.assertTrue(any("removed but artifact path still exists" in e for e in errors))
        self.assertEqual(stats["removed_verified"], [])

    def test_missing_prepared_hash_cannot_prove_change_or_removal(self) -> None:
        for disposition in ("updated", "removed"):
            with self.subTest(disposition=disposition):
                errors, stats, _ = self.review(disposition, prepared_hash=False)
                self.assertTrue(any("without a prepared content SHA256" in e for e in errors))
                self.assertEqual(stats["updated_verified"], [])
                self.assertEqual(stats["removed_verified"], [])

    def test_missing_file_cannot_be_hidden_as_nonremoval(self) -> None:
        self.artifact.unlink()
        for disposition in ("aligned", "stale", "not-applicable"):
            with self.subTest(disposition=disposition):
                errors, stats, _ = self.review(disposition)
                self.assertTrue(any("artifact no longer exists" in e for e in errors))
                self.assertEqual(stats["removed_verified"], [])

    def test_existing_stale_file_retains_original_semantics(self) -> None:
        errors, stats, report = self.review("stale")
        self.assertEqual(errors, [])
        self.assertEqual(stats["stale_artifacts"], ["docs/rule.md"])
        self.assertEqual(outcome(report), "converged-with-nonblocking-drift")

    def test_unresolved_deletion_remains_owner_blocking(self) -> None:
        self.artifact.unlink()
        finding = {
            "classification": "owner-decision",
            "severity": "high",
            "subject": "docs/rule.md removal",
            "observed": "The document was deleted.",
            "expected": "An authoritative decision on removing the rule.",
            "authority": "Confirmed Product Truth and Task Contract",
            "evidence": ["prepared Context and current file state"],
            "recommended_action": "Ask the owner whether this rule can be retired.",
            "owner_question": "May this rule be removed?",
        }
        errors, stats, report = self.review("owner-decision", findings=[finding])
        self.assertEqual(errors, [])
        self.assertEqual(stats["owner_decision_artifacts"], ["docs/rule.md"])
        self.assertEqual(outcome(report), "needs-owner")

    def test_completion_gate_accepts_removal_but_rejects_deleted_update(self) -> None:
        """The real completion CLI must consume the Schema + coverage decision."""
        self.artifact.unlink()
        errors, _, report = self.review("removed")
        self.assertEqual(errors, [])
        report["evidence"] = ["EV-R05"]
        proof = self.root / "proof.txt"
        proof.write_text("Review evidence fixture\n", encoding="utf-8")
        evidence = {
            "version": 1,
            "task_id": "TASK-R05",
            "task": "Review the rule",
            "risk_level": "low",
            "claims": [{
                "id": "EV-R05",
                "claim": "The rule change was reviewed.",
                "required": True,
                "status": "pass",
                "evidence": [{"kind": "other", "provenance": "file", "ref": "proof.txt"}],
            }],
            "limitations": [],
        }
        owner = {
            "version": 1,
            "task_id": "TASK-R05",
            "status": "completed",
            "summary": "Rule change reviewed",
            "before": "Rule existed",
            "after": "Rule retired",
            "verification": [{
                "claim": "The rule change was reviewed.",
                "evidence_ids": ["EV-R05"],
            }],
            "consistency": {"status": "aligned", "summary": "No blocking drift."},
            "owner_decisions": [],
        }
        bundle = self.root / "bundle"
        bundle.mkdir()
        for name, value in (
            ("convergence.json", report),
            ("evidence.json", evidence),
            ("owner-report.json", owner),
        ):
            (bundle / name).write_text(
                json.dumps(value, indent=2) + "\n", encoding="utf-8"
            )
        command = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "pact" / "complete.py"),
            str(bundle),
            "--root", str(self.root),
            "--context", str(self.context_path),
            "--context-sha256", report["context_sha256"],
            "--json",
        ]
        accepted = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        summary = json.loads(accepted.stdout)
        self.assertTrue(summary["complete"])
        self.assertEqual(
            summary["convergence_coverage"]["removed_verified"], ["docs/rule.md"]
        )

        report["coverage"][0]["disposition"] = "updated"
        (bundle / "convergence.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        rejected = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(rejected.returncode, 1, rejected.stdout + rejected.stderr)
        rejected_result = json.loads(rejected.stdout)
        self.assertFalse(rejected_result["complete"])
        self.assertTrue(any(
            "updated but artifact no longer exists" in error
            for error in rejected_result["errors"]
        ))

    def test_missing_owner_question_is_not_sufficient(self) -> None:
        self.artifact.unlink()
        errors, _, _ = self.review("owner-decision")
        self.assertTrue(any("no owner-decision finding" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
