from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
INIT = PROJECT_ROOT / "scripts" / "pact" / "init.py"


class TaskSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-task-surface-")
        self.root = pathlib.Path(self.temp.name) / "project"
        self.root.mkdir(parents=True)
        (self.root / "README.md").write_text(
            "# Demo Project\n\nPassword reset updates the user's credentials.\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(INIT),
                "--target",
                str(self.root),
                "--apply",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def pact(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(self.root / "pact.py"),
                *args,
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def write_json(self, relative: str, data: dict) -> pathlib.Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return path

    def test_status_and_inspect_are_high_level_entry_points(self) -> None:
        status = self.pact("status", "--json")
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        status_data = json.loads(status.stdout)
        self.assertIn(status_data["overall"], {"pass", "warn"})
        self.assertIn("readiness", status_data)

        inspect = self.pact("inspect", "password reset", "--json")
        self.assertEqual(inspect.returncode, 0, inspect.stdout + inspect.stderr)
        inspect_data = json.loads(inspect.stdout)
        self.assertEqual(inspect_data["query"], "password reset")
        self.assertGreaterEqual(
            inspect_data["discovery"].get("result_count", 0),
            1,
        )

    def test_task_prepare_and_finish_happy_path(self) -> None:
        task_id = "TASK-HAPPY"
        prepared = self.pact(
            "task",
            "prepare",
            "change password reset behavior",
            "--success",
            "Password reset remains correct",
            "--accept",
            "Existing reset links still behave correctly",
            "--constraint",
            "Do not weaken credential security",
            "--risk",
            "medium",
            "--task-id",
            task_id,
            "--json",
        )
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        prep = json.loads(prepared.stdout)
        self.assertEqual(prep["task_id"], task_id)
        self.assertEqual(prep["status"], "prepared")
        self.assertTrue((self.root / prep["context"]).is_file())
        self.assertTrue((self.root / prep["contract"]).is_file())
        contract = json.loads(
            (self.root / prep["contract"]).read_text(encoding="utf-8")
        )
        self.assertEqual(
            [item["id"] for item in contract["acceptance_criteria"]],
            ["AC-1", "AC-2", "AC-3"],
        )
        self.assertEqual(
            [item["kind"] for item in contract["acceptance_criteria"]],
            ["outcome", "outcome", "constraint"],
        )
        self.assertEqual(prep["impact_state"], "deferred")

        task_status = self.pact("task", "status", task_id, "--json")
        self.assertEqual(task_status.returncode, 0, task_status.stdout + task_status.stderr)
        self.assertEqual(json.loads(task_status.stdout)["status"], "prepared")

        run_path = self.root / ".pact" / "runs" / task_id / "tests.json"
        verified = self.pact(
            "run",
            "--task-id",
            task_id,
            "--output",
            str(run_path),
            "--quiet",
            "--",
            sys.executable,
            "-c",
            "print('verified')",
        )
        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)

        bundle = self.root / ".pact" / "completions" / task_id
        evidence = {
            "version": 1,
            "task_id": task_id,
            "task": "change password reset behavior",
            "risk_level": "medium",
            "task_contract_sha256": prep["contract_sha256"],
            "claims": [
                {
                    "id": "EV-TASK-HAPPY",
                    "claim": "Verification command passed.",
                    "required": True,
                    "status": "pass",
                    "criteria": ["AC-1", "AC-2", "AC-3"],
                    "evidence": [
                        {
                            "kind": "test",
                            "provenance": "pact-run",
                            "ref": f".pact/runs/{task_id}/tests.json",
                        }
                    ],
                }
            ],
            "limitations": [],
        }
        convergence = {
            "version": 1,
            "task_id": task_id,
            "change": "change password reset behavior",
            "owner_summary": "Prepared task remains aligned.",
            "evidence": ["EV-TASK-HAPPY"],
            "findings": [],
        }
        owner = {
            "version": 1,
            "task_id": task_id,
            "status": "completed",
            "summary": "Task verified.",
            "before": "Before state.",
            "after": "After state.",
            "verification": [
                {
                    "claim": "Verification command passed.",
                    "evidence_ids": ["EV-TASK-HAPPY"],
                }
            ],
            "acceptance": [
                {
                    "criterion_id": criterion_id,
                    "summary": criterion["text"],
                    "evidence_ids": ["EV-TASK-HAPPY"],
                }
                for criterion_id, criterion in [
                    (item["id"], item)
                    for item in contract["acceptance_criteria"]
                ]
            ],
            "consistency": {
                "status": "aligned",
                "summary": "No blocking drift.",
            },
            "owner_decisions": [],
        }
        self.write_json(
            f".pact/completions/{task_id}/evidence.json",
            evidence,
        )
        self.write_json(
            f".pact/completions/{task_id}/convergence.json",
            convergence,
        )
        self.write_json(
            f".pact/completions/{task_id}/owner-report.json",
            owner,
        )

        finished = self.pact("task", "finish", task_id, "--json")
        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        finish_data = json.loads(finished.stdout)
        self.assertTrue(finish_data["complete"])
        self.assertEqual(finish_data["acceptance"]["total"], 3)
        self.assertEqual(finish_data["acceptance"]["owner_report_covered"], 3)

        final_status = self.pact("task", "status", task_id, "--json")
        self.assertEqual(final_status.returncode, 0, final_status.stdout + final_status.stderr)
        self.assertEqual(json.loads(final_status.stdout)["status"], "completed")

        observation = self.pact("eval", "--task", task_id, "--json")
        self.assertEqual(observation.returncode, 0, observation.stdout + observation.stderr)
        observed = json.loads(observation.stdout)
        self.assertEqual(observed["acceptance"]["total"], 3)
        self.assertEqual(observed["acceptance"]["owner_report_covered"], 3)
        self.assertEqual(observed["completion"]["attempts"], 1)
        self.assertEqual(observed["completion"]["failed_attempts"], 0)
        self.assertTrue(observed["completion"]["final_complete"])
        self.assertIn(
            "owner_interactions.technical_escalations",
            observed["human_required"],
        )


    def test_task_finish_rejects_unverified_acceptance_criterion(self) -> None:
        task_id = "TASK-AC-GAP"
        prepared = self.pact(
            "task",
            "prepare",
            "change password reset behavior",
            "--success",
            "Password reset remains correct",
            "--accept",
            "Existing reset links remain valid",
            "--risk",
            "low",
            "--task-id",
            task_id,
            "--json",
        )
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        prep = json.loads(prepared.stdout)

        evidence = {
            "version": 1,
            "task_id": task_id,
            "task": "change password reset behavior",
            "risk_level": "low",
            "task_contract_sha256": prep["contract_sha256"],
            "claims": [
                {
                    "id": "EV-ONLY-ONE",
                    "claim": "Primary reset behavior is present.",
                    "required": True,
                    "status": "pass",
                    "criteria": ["AC-1"],
                    "evidence": [
                        {
                            "kind": "other",
                            "provenance": "file",
                            "ref": "README.md",
                        }
                    ],
                }
            ],
            "limitations": [],
        }
        convergence = {
            "version": 1,
            "task_id": task_id,
            "change": "change password reset behavior",
            "owner_summary": "No drift found.",
            "evidence": ["EV-ONLY-ONE"],
            "findings": [],
        }
        owner = {
            "version": 1,
            "task_id": task_id,
            "status": "completed",
            "summary": "Primary behavior verified.",
            "before": "Before state.",
            "after": "After state.",
            "verification": [
                {
                    "claim": "Primary reset behavior is present.",
                    "evidence_ids": ["EV-ONLY-ONE"],
                }
            ],
            "acceptance": [
                {
                    "criterion_id": "AC-1",
                    "summary": "Password reset remains correct",
                    "evidence_ids": ["EV-ONLY-ONE"],
                }
            ],
            "consistency": {
                "status": "aligned",
                "summary": "No blocking drift.",
            },
            "owner_decisions": [],
        }
        self.write_json(f".pact/completions/{task_id}/evidence.json", evidence)
        self.write_json(f".pact/completions/{task_id}/convergence.json", convergence)
        self.write_json(f".pact/completions/{task_id}/owner-report.json", owner)

        finished = self.pact("task", "finish", task_id, "--json")
        self.assertEqual(finished.returncode, 1, finished.stdout + finished.stderr)
        result = json.loads(finished.stdout)
        self.assertFalse(result["complete"])
        self.assertIn("AC-2", result["acceptance"]["unverified"])
        self.assertTrue(
            any(
                "acceptance criterion AC-2 has no passing Evidence claim" in error
                for error in result["errors"]
            )
        )

        observation = self.pact("eval", "--task", task_id, "--json")
        self.assertEqual(observation.returncode, 0, observation.stdout + observation.stderr)
        observed = json.loads(observation.stdout)
        self.assertEqual(observed["completion"]["attempts"], 1)
        self.assertEqual(observed["completion"]["failed_attempts"], 1)
        self.assertEqual(observed["completion"]["acceptance_gap_blocks"], 1)
        self.assertFalse(observed["completion"]["final_complete"])



    def test_task_finish_rejects_evidence_for_stale_task_contract(self) -> None:
        task_id = "TASK-STALE-CONTRACT"
        prepared = self.pact(
            "task",
            "prepare",
            "change password reset behavior",
            "--success",
            "Password reset remains correct",
            "--risk",
            "low",
            "--task-id",
            task_id,
            "--json",
        )
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        prep = json.loads(prepared.stdout)

        contract_path = self.root / prep["contract"]
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract["acceptance_criteria"][0]["text"] = "Different acceptance after verification"
        contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

        evidence = {
            "version": 1,
            "task_id": task_id,
            "task": "change password reset behavior",
            "risk_level": "low",
            "task_contract_sha256": prep["contract_sha256"],
            "claims": [
                {
                    "id": "EV-STALE-CONTRACT",
                    "claim": "Old contract was verified.",
                    "required": True,
                    "status": "pass",
                    "criteria": ["AC-1"],
                    "evidence": [
                        {
                            "kind": "other",
                            "provenance": "file",
                            "ref": "README.md",
                        }
                    ],
                }
            ],
            "limitations": [],
        }
        convergence = {
            "version": 1,
            "task_id": task_id,
            "change": "change password reset behavior",
            "owner_summary": "No drift found.",
            "evidence": ["EV-STALE-CONTRACT"],
            "findings": [],
        }
        owner = {
            "version": 1,
            "task_id": task_id,
            "status": "completed",
            "summary": "Old acceptance verified.",
            "before": "Before state.",
            "after": "After state.",
            "verification": [
                {
                    "claim": "Old contract was verified.",
                    "evidence_ids": ["EV-STALE-CONTRACT"],
                }
            ],
            "acceptance": [
                {
                    "criterion_id": "AC-1",
                    "summary": "Different acceptance after verification",
                    "evidence_ids": ["EV-STALE-CONTRACT"],
                }
            ],
            "consistency": {
                "status": "aligned",
                "summary": "No blocking drift.",
            },
            "owner_decisions": [],
        }
        self.write_json(f".pact/completions/{task_id}/evidence.json", evidence)
        self.write_json(f".pact/completions/{task_id}/convergence.json", convergence)
        self.write_json(f".pact/completions/{task_id}/owner-report.json", owner)

        finished = self.pact("task", "finish", task_id, "--json")
        self.assertEqual(finished.returncode, 1, finished.stdout + finished.stderr)
        result = json.loads(finished.stdout)
        self.assertFalse(result["complete"])
        self.assertTrue(
            any("task_contract_sha256" in error for error in result["errors"])
        )

    def test_task_finish_requires_prepared_task(self) -> None:
        finished = self.pact(
            "task",
            "finish",
            "TASK-NOT-PREPARED",
            "--json",
        )
        self.assertEqual(finished.returncode, 2)
        self.assertIn("task was not prepared", finished.stderr)


if __name__ == "__main__":
    unittest.main()
