from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
RUN = PROJECT_ROOT / "scripts" / "pact" / "run.py"
REPORT = PROJECT_ROOT / "scripts" / "pact" / "report.py"
COMPLETE = PROJECT_ROOT / "scripts" / "pact" / "complete.py"


class TrustedCompletionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-complete-test-")
        self.root = pathlib.Path(self.temp.name)
        self.bundle = self.root / ".pact" / "completions" / "TASK-1"
        self.bundle.mkdir(parents=True)

        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "pact-test@example.invalid"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "PACT Test"],
            cwd=self.root,
            check=True,
        )
        (self.root / "app.txt").write_text("baseline\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.txt"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "baseline"],
            cwd=self.root,
            check=True,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_json(self, path: pathlib.Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def create_passing_run(
        self,
        task_id: str = "TASK-1",
        *,
        env: dict[str, str] | None = None,
        extra_args: list[str] | None = None,
    ) -> pathlib.Path:
        receipt = self.root / ".pact" / "runs" / task_id / "run.json"
        receipt.parent.mkdir(parents=True, exist_ok=True)

        command = [
            sys.executable,
            str(RUN),
            "--task-id",
            task_id,
            "--output",
            str(receipt),
            "--cwd",
            str(self.root),
            "--quiet",
        ]
        if extra_args:
            command.extend(extra_args)
        command.extend([
            "--",
            sys.executable,
            "-c",
            "import sys; print('ok')",
        ])

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(receipt.exists())
        return receipt

    def base_bundle(
        self,
        risk: str = "medium",
        *,
        run: pathlib.Path | None = None,
    ) -> tuple[dict, dict, dict]:
        run = run or self.create_passing_run()
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

    def run_complete(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(COMPLETE),
                str(self.bundle),
                "--root",
                str(self.root),
                "--json",
                *extra,
            ],
            capture_output=True,
            text=True,
        )

    def test_medium_machine_backed_bundle_passes_on_same_workspace(self) -> None:
        evidence, convergence, owner = self.base_bundle("medium")
        self.save_bundle(evidence, convergence, owner)

        result = self.run_complete()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data["complete"])
        self.assertEqual(data["workspace_bound_claims"], 1)

    def test_tracked_change_after_verification_blocks_completion(self) -> None:
        evidence, convergence, owner = self.base_bundle("medium")
        self.save_bundle(evidence, convergence, owner)
        (self.root / "app.txt").write_text("changed after verification\n", encoding="utf-8")

        result = self.run_complete()
        self.assertEqual(result.returncode, 1)
        self.assertIn("stale pact-run receipt", result.stdout)

    def test_untracked_change_after_verification_blocks_completion(self) -> None:
        evidence, convergence, owner = self.base_bundle("medium")
        self.save_bundle(evidence, convergence, owner)
        (self.root / "new_source.py").write_text("print('new')\n", encoding="utf-8")

        result = self.run_complete()
        self.assertEqual(result.returncode, 1)
        self.assertIn("stale pact-run receipt", result.stdout)

    def test_generated_pact_bundle_does_not_stale_workspace(self) -> None:
        evidence, convergence, owner = self.base_bundle("medium")
        self.save_bundle(evidence, convergence, owner)

        # evidence/convergence/owner-report live under .pact/completions and are
        # deliberately outside the verified product workspace fingerprint.
        result = self.run_complete()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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

    def test_secret_arguments_are_redacted_in_receipt(self) -> None:
        env = os.environ.copy()
        env["MY_API_KEY"] = "env-secret-12345"
        receipt = self.root / ".pact" / "runs" / "TASK-1" / "secret.json"
        receipt.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                sys.executable,
                str(RUN),
                "--task-id",
                "TASK-1",
                "--output",
                str(receipt),
                "--cwd",
                str(self.root),
                "--quiet",
                "--",
                sys.executable,
                "-c",
                "import sys; print('ok')",
                "--token",
                "literal-secret",
                "header=env-secret-12345",
                "Authorization: Bearer abc123",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        data = json.loads(receipt.read_text(encoding="utf-8"))
        persisted = json.dumps(data["argv"])
        self.assertNotIn("literal-secret", persisted)
        self.assertNotIn("env-secret-12345", persisted)
        self.assertNotIn("Bearer abc123", persisted)
        self.assertGreaterEqual(data["redacted_argument_count"], 3)

    def test_github_actions_provenance_is_captured(self) -> None:
        env = os.environ.copy()
        env.update({
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": "ningcol/PACT",
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "2",
            "GITHUB_JOB": "test",
            "GITHUB_WORKFLOW": "PACT Check",
            "GITHUB_SHA": "deadbeef",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SERVER_URL": "https://github.com",
        })
        run = self.create_passing_run(env=env)
        data = json.loads(run.read_text(encoding="utf-8"))
        self.assertEqual(data["ci"]["provider"], "github-actions")
        self.assertEqual(data["ci"]["run_id"], "123")

        evidence, convergence, owner = self.base_bundle("medium", run=run)
        self.save_bundle(evidence, convergence, owner)
        result = self.run_complete("--require-ci")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["ci_backed_claims"], 1)

    def test_require_ci_blocks_local_only_completion(self) -> None:
        evidence, convergence, owner = self.base_bundle("medium")
        self.save_bundle(evidence, convergence, owner)

        result = self.run_complete("--require-ci")
        self.assertEqual(result.returncode, 1)
        self.assertIn("requires CI-backed Evidence", result.stdout)


if __name__ == "__main__":
    unittest.main()
