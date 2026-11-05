"""Current-behavior reproductions for PACT completion and evidence freshness.

These tests document strict v1 behavior; they do NOT prescribe a bypass or
claim that unrelated changes are safe when verifier inputs are unknown.
Every test uses its own disposable Git repository and PACT's actual CLI.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
RUN = PROJECT_ROOT / "scripts" / "pact" / "run.py"
COMPLETE = PROJECT_ROOT / "scripts" / "pact" / "complete.py"


class CompletionFrictionReproTests(unittest.TestCase):
    TASK_ID = "TASK-FRICTION-001"
    CLAIM = "The narrow smoke command succeeds"
    CRITERION = "The smoke command succeeds"

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-completion-friction-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name) / "project"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "pact-test@example.invalid")
        self.git("config", "user.name", "PACT diagnostic")
        (self.root / "app.py").write_text("ANSWER = 42\n", encoding="utf-8")
        (self.root / "README.md").write_text("# Fixture\n", encoding="utf-8")
        self.git("add", "app.py", "README.md")
        self.git("commit", "-qm", "baseline")

        self.bundle = self.root / ".pact" / "completions" / self.TASK_ID
        self.bundle.mkdir(parents=True)
        self.run_ref = self.root / ".pact" / "runs" / self.TASK_ID / "smoke.json"
        self.contract_path = self.root / "contract.json"
        # The contract is deliberately kept outside of the tracked source tree
        # and is written before verification. This is only a disposable fixture.
        self.contract = {
            "version": 1,
            "task_id": self.TASK_ID,
            "intent": "exercise current completion policy",
            "acceptance_criteria": [
                {"id": "AC-1", "kind": "outcome", "text": self.CRITERION},
            ],
        }
        self.write_json(self.contract_path, self.contract)
        self.evidence = {
            "version": 1,
            "task_id": self.TASK_ID,
            "task": "exercise current completion policy",
            "risk_level": "high",
            "task_contract_sha256": hashlib.sha256(self.contract_path.read_bytes()).hexdigest(),
            "claims": [
                {"id": "EV-SMOKE", "claim": self.CLAIM, "required": True,
                 "status": "pass", "criteria": ["AC-1"],
                 "evidence": [{"kind": "test", "provenance": "pact-run",
                               "ref": str(self.run_ref)}]},
            ],
            "limitations": [],
        }
        self.convergence = {
            "version": 1,
            "task_id": self.TASK_ID,
            "change": "Diagnostic task",
            "owner_summary": "No unresolved knowledge finding",
            "evidence": ["EV-SMOKE"],
            "findings": [],
        }
        self.owner = {
            "version": 1,
            "task_id": self.TASK_ID,
            "status": "completed",
            "summary": "Diagnostic smoke result",
            "before": "Previously unverified",
            "after": "The smoke command was run",
            "verification": [{"claim": self.CLAIM, "evidence_ids": ["EV-SMOKE"]}],
            "acceptance": [
                {"criterion_id": "AC-1", "summary": self.CRITERION,
                 "evidence_ids": ["EV-SMOKE"]},
            ],
            "consistency": {"status": "aligned", "summary": "No drift found"},
            "owner_decisions": [],
        }

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=self.root,
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    @staticmethod
    def write_json(path: pathlib.Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    def verify(self, *, sources: tuple[str, ...] = ()) -> None:
        args = [
            sys.executable, str(RUN), "--task-id", self.TASK_ID,
            "--output", str(self.run_ref), "--cwd", str(self.root), "--quiet",
        ]
        for source in sources:
            args.extend(["--source", source])
        args.extend(["--", sys.executable, "-c", "print('smoke passed')"])
        result = subprocess.run(args, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def complete(self) -> tuple[subprocess.CompletedProcess[str], dict]:
        self.write_json(self.bundle / "evidence.json", self.evidence)
        self.write_json(self.bundle / "convergence.json", self.convergence)
        self.write_json(self.bundle / "owner-report.json", self.owner)
        result = subprocess.run(
            [sys.executable, str(COMPLETE), str(self.bundle), "--root",
             str(self.root), "--contract", str(self.contract_path),
             "--expected-risk", "high", "--json"],
            capture_output=True, text=True, cwd=self.root,
        )
        self.assertTrue(result.stdout.strip(), result.stderr)
        return result, json.loads(result.stdout)

    def assert_verified(self) -> None:
        result, outcome = self.complete()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(outcome["complete"])
        self.assertEqual(outcome["acceptance"]["evidence_verified"], 1)

    def assert_stale(self) -> None:
        result, outcome = self.complete()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertFalse(outcome["complete"])
        self.assertIn("stale pact-run receipt", "\n".join(outcome["errors"]))

    def test_baseline_valid_completion(self) -> None:
        self.verify()
        self.assert_verified()

    def test_empty_commit_changes_no_files_but_invalidates_run_receipt(self) -> None:
        self.verify()
        self.assert_verified()
        old_tree = self.git("rev-parse", "HEAD^{tree}")
        self.git("commit", "--allow-empty", "-qm", "no content change")
        self.assertEqual(old_tree, self.git("rev-parse", "HEAD^{tree}"))
        self.assert_stale()

    def test_unrelated_document_commit_invalidates_run_receipt(self) -> None:
        self.verify()
        self.assert_verified()
        (self.root / "README.md").write_text("# Fixture\nExtra note\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-qm", "change unrelated README")
        self.assert_stale()

    def test_relevant_source_change_correctly_invalidates_receipt(self) -> None:
        self.verify()
        self.assert_verified()
        (self.root / "app.py").write_text("ANSWER = 43\n", encoding="utf-8")
        self.assert_stale()

    def test_changed_declared_verification_source_correctly_rejects_receipt(self) -> None:
        (self.root / "verify.py").write_text("print('first')\n", encoding="utf-8")
        self.verify(sources=("verify.py",))
        self.assert_verified()
        (self.root / "verify.py").write_text("print('changed')\n", encoding="utf-8")
        result, outcome = self.complete()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertFalse(outcome["complete"])
        self.assertIn("declared source digest has changed", "\n".join(outcome["errors"]))

    def test_owner_acceptance_in_prose_cannot_mask_missing_verification(self) -> None:
        self.verify()
        self.assert_verified()
        self.owner["status"] = "partial"
        self.owner["summary"] = (
            "Owner explicitly accepted this delivery scope, with E2E unverified"
        )
        self.owner["verification"] = []
        self.owner["acceptance"] = []
        self.evidence["limitations"] = ["E2E not run"]
        self.evidence["claims"][0]["status"] = "unverified"
        self.evidence["claims"][0]["evidence"] = []
        result, outcome = self.complete()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertFalse(outcome["complete"])
        self.assertIn("acceptance criterion AC-1 has no passing Evidence claim",
                      "\n".join(outcome["errors"]))


if __name__ == "__main__":
    unittest.main()
