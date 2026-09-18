from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
RUN = PROJECT_ROOT / "scripts" / "pact" / "run.py"
EVIDENCE = PROJECT_ROOT / "scripts" / "pact" / "evidence.py"
REPORT = PROJECT_ROOT / "scripts" / "pact" / "report.py"
COMPLETE = PROJECT_ROOT / "scripts" / "pact" / "complete.py"


class TrustedCompletionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-complete-test-")
        self.root = pathlib.Path(self.temp.name)
        self.bundle = self.root / "bundle"
        self.bundle.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_json(self, path: pathlib.Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def create_passing_run(self, task_id: str = "TASK-1") -> pathlib.Path:
        receipt = self.root / "run.json"
        result = subprocess.run(
            [
                sys.executable,
                str(RUN),
                "--task-id",
                task_id,
                "--output",
                str(receipt),
                "--quiet",
                "--",
                sys.executable,
                "-c",
                "print('ok')",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(receipt.exists())
        return receipt

    def base_bundle(self, risk: str = "medium") -> tuple[dict, dict, dict]:
        run = self.create_passing_run()
        evidence = {
            "version": 1,
            "task_id": "TASK-1",
            "task": "Test task",
            "risk_level": risk,
            "claims": [
                {
                    "id": "EV-TEST-PASS",
                    "claim": "The verification command passes.",
                    "required": True,
                    "status": "pass",
                    "evidence": [
                        {
                            "kind": "test",
                            "provenance": "pact-run",
                            "ref": str(run),
                        }
                    ],
                }
            ],
            "limitations": [],
        }
        convergence = {
            "version": 1,
            "task_id": "TASK-1",
            "change": "Test task",
            "owner_summary": "Everything is aligned.",
            "evidence": ["EV-TEST-PASS"],
            "findings": [],
        }
        owner = {
            "version": 1,
            "task_id": "TASK-1",
            "status": "completed",
            "summary": "The task is complete.",
            "before": "Before state.",
            "after": "After state.",
            "verification": [
                {
                    "claim": "Verification passed.",
                    "evidence_ids": ["EV-TEST-PASS"],
                }
            ],
            "consistency": {
                "status": "aligned",
                "summary": "Project state is aligned.",
            },
            "owner_decisions": [],
        }
        return evidence, convergence, owner

    def save_bundle(self, evidence: dict, convergence: dict, owner: dict) -> None:
        self.write_json(self.bundle / "evidence.json", evidence)
        self.write_json(self.bundle / "convergence.json", convergence)
        self.write_json(self.bundle / "owner-report.json", owner)

    def run_complete(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(COMPLETE),
                str(self.bundle),
                "--root",
                str(self.root),
                "--json",
            ],
            capture_output=True,
            text=True,
        )

    def test_medium_machine_backed_bundle_passes(self) -> None:
        evidence, convergence, owner = self.base_bundle("medium")
        self.save_bundle(evidence, convergence, owner)

        result = self.run_complete()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["complete"])

    def test_missing_evidence_ref_is_rejected(self) -> None:
        evidence, convergence, owner = self.base_bundle("medium")
        evidence["claims"][0]["evidence"][0]["ref"] = str(self.root / "missing.json")
        self.save_bundle(evidence, convergence, owner)

        result = self.run_complete()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not exist", result.stdout + result.stderr)

    def test_medium_manual_only_required_claim_is_incomplete(self) -> None:
        evidence, convergence, owner = self.base_bundle("medium")
        evidence["claims"][0]["evidence"] = [
            {
                "kind": "manual",
                "provenance": "manual",
                "ref": "human said it looked correct",
            }
        ]
        self.save_bundle(evidence, convergence, owner)

        result = self.run_complete()
        self.assertEqual(result.returncode, 1)
        self.assertIn("machine-backed", result.stdout)

    def test_owner_cannot_call_unverified_claim_verified(self) -> None:
        evidence, convergence, owner = self.base_bundle("low")
        evidence["claims"][0]["status"] = "unverified"
        evidence["claims"][0]["evidence"] = []
        self.save_bundle(evidence, convergence, owner)

        result = subprocess.run(
            [
                sys.executable,
                str(REPORT),
                str(self.bundle / "owner-report.json"),
                "--evidence",
                str(self.bundle / "evidence.json"),
                "--convergence",
                str(self.bundle / "convergence.json"),
                "--root",
                str(self.root),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("non-passing evidence id", result.stderr)

    def test_task_id_mismatch_blocks_completion(self) -> None:
        evidence, convergence, owner = self.base_bundle("medium")
        owner["task_id"] = "OTHER"
        self.save_bundle(evidence, convergence, owner)

        result = self.run_complete()
        self.assertEqual(result.returncode, 1)
        self.assertIn("task_id mismatch", result.stdout)

    def test_high_risk_limitations_block_completion(self) -> None:
        evidence, convergence, owner = self.base_bundle("high")
        evidence["limitations"] = ["Production migration was not exercised."]
        self.save_bundle(evidence, convergence, owner)

        result = self.run_complete()
        self.assertEqual(result.returncode, 1)
        self.assertIn("high-risk completion cannot carry", result.stdout)


if __name__ == "__main__":
    unittest.main()
