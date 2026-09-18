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
            "claims": [
                {
                    "id": "EV-TASK-HAPPY",
                    "claim": "Verification command passed.",
                    "required": True,
                    "status": "pass",
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

        final_status = self.pact("task", "status", task_id, "--json")
        self.assertEqual(final_status.returncode, 0, final_status.stdout + final_status.stderr)
        self.assertEqual(json.loads(final_status.stdout)["status"], "completed")


if __name__ == "__main__":
    unittest.main()
