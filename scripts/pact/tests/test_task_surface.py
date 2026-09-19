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

    def test_task_id_cannot_escape_pact_state_roots(self) -> None:
        outside = self.root.parent / "escaped-task-state"
        prepared = self.pact(
            "task",
            "prepare",
            "unsafe task id",
            "--success",
            "Must never escape PACT state",
            "--risk",
            "low",
            "--task-id",
            "../../escaped-task-state",
            "--force",
            "--json",
        )
        self.assertEqual(prepared.returncode, 2)
        self.assertIn("invalid task id", prepared.stderr)
        self.assertFalse(outside.exists())

        run = self.pact(
            "run",
            "--task-id",
            "../unsafe",
            "--output",
            ".pact/runs/unsafe.json",
            "--quiet",
            "--",
            sys.executable,
            "-c",
            "print('should not run')",
        )
        self.assertEqual(run.returncode, 2)
        self.assertIn("invalid task id", run.stderr)

    def test_task_prepare_blocks_deterministically_invalid_repository(self) -> None:
        rule_dir = self.root / "docs" / "product" / "rules"
        rule_dir.mkdir(parents=True, exist_ok=True)
        front = (
            "+++\n[pact]\ntype = \"rule\"\n"
            "id = \"RULE-DUPLICATE\"\nstatus = \"confirmed\"\n+++\n"
        )
        (rule_dir / "a.md").write_text(front + "# A\n", encoding="utf-8")
        (rule_dir / "b.md").write_text(front + "# B\n", encoding="utf-8")

        prepared = self.pact(
            "task",
            "prepare",
            "must not prepare invalid knowledge",
            "--success",
            "No ambiguous durable ID reaches Context",
            "--risk",
            "low",
            "--task-id",
            "TASK-PREFLIGHT-INVALID",
            "--json",
        )
        self.assertNotEqual(prepared.returncode, 0)
        self.assertIn("deterministic repository checks failed", prepared.stderr)
        self.assertFalse(
            (
                self.root
                / ".pact"
                / "tasks"
                / "TASK-PREFLIGHT-INVALID"
            ).exists()
        )

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

    def test_inspect_supports_multi_query_code_retrieval(self) -> None:
        source = self.root / "McpServer" / "server.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            "def round_robin_dispatch():\n    return 'ok'\n",
            encoding="utf-8",
        )

        inspected = self.pact(
            "inspect",
            "multiple image clients",
            "--query",
            "round_robin_dispatch",
            "--query",
            "ROUND_ROBIN_DISPATCH",
            "--code-limit",
            "1",
            "--json",
        )
        self.assertEqual(
            inspected.returncode,
            0,
            inspected.stdout + inspected.stderr,
        )
        data = json.loads(inspected.stdout)
        self.assertEqual(
            data["queries"],
            ["multiple image clients", "round_robin_dispatch"],
        )
        self.assertEqual(
            data["explanation"]["queries"],
            data["queries"],
        )
        self.assertLessEqual(
            data["discovery"].get("code_result_count", 0),
            1,
        )
        paths = {
            item["path"]
            for item in data["discovery"].get("code_results", [])
        }
        self.assertIn("McpServer/server.py", paths)

    def test_inspect_propagates_project_index_failure(self) -> None:
        bad = self.root / "docs" / "bad.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_bytes(b"\xff\xfe\x00\x80")

        inspected = self.pact(
            "inspect",
            "password reset",
            "--json",
        )
        self.assertNotEqual(inspected.returncode, 0)
        self.assertIn("PACT inspect:", inspected.stderr)

    def test_generated_control_plane_state_is_git_ignored(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)

        paths = [
            ".pact/cache/example.json",
            ".pact/tasks/TASK-X/task.json",
            ".pact/runs/TASK-X/run.json",
            ".pact/completions/TASK-X/evidence.json",
            ".pact/tmp/staged.json",
        ]
        for relative in paths:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n", encoding="utf-8")
            ignored = subprocess.run(
                ["git", "check-ignore", "-q", relative],
                cwd=self.root,
            )
            self.assertEqual(ignored.returncode, 0, relative)

    def test_failed_prepare_leaves_no_visible_task_directory(self) -> None:
        bad = self.root / "docs" / "bad.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_bytes(b"\xff\xfe\x00\x80")

        task_id = "TASK-PREPARE-FAIL"
        prepared = self.pact(
            "task",
            "prepare",
            "trigger invalid project metadata",
            "--success",
            "Preparation should not publish partial state",
            "--risk",
            "low",
            "--task-id",
            task_id,
            "--json",
        )
        self.assertNotEqual(prepared.returncode, 0)
        self.assertFalse((self.root / ".pact" / "tasks" / task_id).exists())
        self.assertFalse(
            (self.root / ".pact" / "completions" / task_id).exists()
        )

    def test_force_reprepare_replaces_task_and_invalidates_completion(self) -> None:
        task_id = "TASK-FORCE-REPREPARE"
        first = self.pact(
            "task",
            "prepare",
            "first task wording",
            "--success",
            "First success condition",
            "--risk",
            "low",
            "--task-id",
            task_id,
            "--json",
        )
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

        completion = self.root / ".pact" / "completions" / task_id
        completion.mkdir(parents=True, exist_ok=True)
        (completion / "old.json").write_text("{}\n", encoding="utf-8")

        second = self.pact(
            "task",
            "prepare",
            "replacement task wording",
            "--success",
            "Replacement success condition",
            "--risk",
            "low",
            "--task-id",
            task_id,
            "--force",
            "--json",
        )
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertFalse(completion.exists())

        contract = json.loads(
            (
                self.root
                / ".pact"
                / "tasks"
                / task_id
                / "contract.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            contract["acceptance_criteria"][0]["text"],
            "Replacement success condition",
        )

    def test_force_failure_preserves_existing_task_and_completion(self) -> None:
        task_id = "TASK-FORCE-ROLLBACK"
        first = self.pact(
            "task",
            "prepare",
            "stable task",
            "--success",
            "Stable success",
            "--risk",
            "low",
            "--task-id",
            task_id,
            "--json",
        )
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

        task_manifest = (
            self.root / ".pact" / "tasks" / task_id / "task.json"
        )
        original_manifest = task_manifest.read_bytes()
        completion = self.root / ".pact" / "completions" / task_id
        completion.mkdir(parents=True, exist_ok=True)
        marker = completion / "old.json"
        marker.write_text("{}\n", encoding="utf-8")

        bad = self.root / "docs" / "bad.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_bytes(b"\xff\xfe\x00\x80")

        second = self.pact(
            "task",
            "prepare",
            "replacement that must fail",
            "--success",
            "Never published",
            "--risk",
            "low",
            "--task-id",
            task_id,
            "--force",
            "--json",
        )
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(task_manifest.read_bytes(), original_manifest)
        self.assertTrue(marker.is_file())

    def test_task_prepare_forwards_token_budget(self) -> None:
        task_id = "TASK-TOKEN-BUDGET"
        prepared = self.pact(
            "task",
            "prepare",
            "inspect password reset behavior",
            "--success",
            "Relevant context is bounded",
            "--risk",
            "low",
            "--token-budget",
            "1234",
            "--task-id",
            task_id,
            "--json",
        )
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        prep = json.loads(prepared.stdout)
        context = json.loads(
            (self.root / prep["context"]).read_text(encoding="utf-8")
        )
        self.assertEqual(
            context["risk_policy"]["materialization_token_budget"],
            1234,
        )
        self.assertEqual(context["context_budget"]["limit_tokens"], 1234)

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
            "--query",
            "password reset",
            "--query",
            "credentials",
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
        context = json.loads(
            (self.root / prep["context"]).read_text(encoding="utf-8")
        )
        self.assertEqual(
            context["discovery_queries"],
            ["password reset", "credentials"],
        )
        coverage = [
            {
                "path": item["path"],
                "disposition": "aligned",
                "rationale": "Reviewed against the completed task.",
            }
            for item in context["artifacts"]
        ]
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
            "context_sha256": prep["context_sha256"],
            "coverage": coverage,
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
        self.assertEqual(len(finish_data["trust_warnings"]), 1)
        self.assertIn(
            "Exact task changed-file attribution is unavailable",
            finish_data["trust_warnings"][0],
        )

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
        self.assertIsNotNone(
            observed["context"]["selected_estimated_tokens"]
        )

        all_tasks = self.pact("eval", "--all-tasks", "--json")
        self.assertEqual(
            all_tasks.returncode,
            0,
            all_tasks.stdout + all_tasks.stderr,
        )
        machine_summary = json.loads(all_tasks.stdout)
        self.assertEqual(machine_summary["summary"]["task_count"], 1)
        self.assertEqual(
            machine_summary["summary"]["overall"]["completed"],
            1,
        )
        self.assertEqual(len(machine_summary["observations"]), 1)
        self.assertEqual(machine_summary["errors"], [])
        self.assertNotIn("score", machine_summary["summary"])


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
        context = json.loads(
            (self.root / prep["context"]).read_text(encoding="utf-8")
        )
        coverage = [
            {
                "path": item["path"],
                "disposition": "aligned",
                "rationale": "Reviewed against the task.",
            }
            for item in context["artifacts"]
        ]

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
            "context_sha256": prep["context_sha256"],
            "coverage": coverage,
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
        context = json.loads(
            (self.root / prep["context"]).read_text(encoding="utf-8")
        )
        coverage = [
            {
                "path": item["path"],
                "disposition": "aligned",
                "rationale": "Reviewed against the task.",
            }
            for item in context["artifacts"]
        ]

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
            "context_sha256": prep["context_sha256"],
            "coverage": coverage,
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

    def test_task_finish_rejects_missing_convergence_coverage(self) -> None:
        task_id = "TASK-CONVERGENCE-GAP"
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
        context = json.loads(
            (self.root / prep["context"]).read_text(encoding="utf-8")
        )
        self.assertTrue(context["artifacts"])

        evidence = {
            "version": 1,
            "task_id": task_id,
            "task": "change password reset behavior",
            "risk_level": "low",
            "task_contract_sha256": prep["contract_sha256"],
            "claims": [
                {
                    "id": "EV-CONVERGENCE-GAP",
                    "claim": "Behavior is verified.",
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
            "evidence": ["EV-CONVERGENCE-GAP"],
            "context_sha256": prep["context_sha256"],
            "coverage": [],
            "findings": [],
        }
        owner = {
            "version": 1,
            "task_id": task_id,
            "status": "completed",
            "summary": "Task verified.",
            "before": "Before.",
            "after": "After.",
            "verification": [
                {
                    "claim": "Behavior is verified.",
                    "evidence_ids": ["EV-CONVERGENCE-GAP"],
                }
            ],
            "acceptance": [
                {
                    "criterion_id": "AC-1",
                    "summary": "Password reset remains correct",
                    "evidence_ids": ["EV-CONVERGENCE-GAP"],
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
            any(
                "Task Context artifact missing from Convergence coverage" in error
                for error in result["errors"]
            )
        )

    def test_task_finish_rejects_false_updated_convergence_claim(self) -> None:
        task_id = "TASK-FALSE-UPDATED"
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
        context = json.loads(
            (self.root / prep["context"]).read_text(encoding="utf-8")
        )
        self.assertTrue(context["artifacts"])

        coverage = []
        for index, item in enumerate(context["artifacts"]):
            coverage.append(
                {
                    "path": item["path"],
                    "disposition": "updated" if index == 0 else "aligned",
                    "rationale": "Claimed review result.",
                }
            )

        evidence = {
            "version": 1,
            "task_id": task_id,
            "task": "change password reset behavior",
            "risk_level": "low",
            "task_contract_sha256": prep["contract_sha256"],
            "claims": [
                {
                    "id": "EV-FALSE-UPDATED",
                    "claim": "Behavior is verified.",
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
            "owner_summary": "Knowledge was updated.",
            "evidence": ["EV-FALSE-UPDATED"],
            "context_sha256": prep["context_sha256"],
            "coverage": coverage,
            "findings": [],
        }
        owner = {
            "version": 1,
            "task_id": task_id,
            "status": "completed",
            "summary": "Task verified.",
            "before": "Before.",
            "after": "After.",
            "verification": [
                {
                    "claim": "Behavior is verified.",
                    "evidence_ids": ["EV-FALSE-UPDATED"],
                }
            ],
            "acceptance": [
                {
                    "criterion_id": "AC-1",
                    "summary": "Password reset remains correct",
                    "evidence_ids": ["EV-FALSE-UPDATED"],
                }
            ],
            "consistency": {
                "status": "aligned",
                "summary": "Knowledge aligned.",
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
            any(
                "updated but artifact content matches" in error
                for error in result["errors"]
            )
        )

    def test_task_finish_rejects_changed_prepared_context(self) -> None:
        task_id = "TASK-STALE-CONTEXT"
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

        context_path = self.root / prep["context"]
        context = json.loads(context_path.read_text(encoding="utf-8"))
        context["known_unknowns"].append("Changed after preparation.")
        context_path.write_text(
            json.dumps(context, indent=2) + "\n",
            encoding="utf-8",
        )
        import hashlib
        current_context_sha = hashlib.sha256(context_path.read_bytes()).hexdigest()
        coverage = [
            {
                "path": item["path"],
                "disposition": "aligned",
                "rationale": "Reviewed.",
            }
            for item in context["artifacts"]
        ]

        evidence = {
            "version": 1,
            "task_id": task_id,
            "task": "change password reset behavior",
            "risk_level": "low",
            "task_contract_sha256": prep["contract_sha256"],
            "claims": [
                {
                    "id": "EV-STALE-CONTEXT",
                    "claim": "Behavior is verified.",
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
            "evidence": ["EV-STALE-CONTEXT"],
            "context_sha256": current_context_sha,
            "coverage": coverage,
            "findings": [],
        }
        owner = {
            "version": 1,
            "task_id": task_id,
            "status": "completed",
            "summary": "Task verified.",
            "before": "Before.",
            "after": "After.",
            "verification": [
                {
                    "claim": "Behavior is verified.",
                    "evidence_ids": ["EV-STALE-CONTEXT"],
                }
            ],
            "acceptance": [
                {
                    "criterion_id": "AC-1",
                    "summary": "Password reset remains correct",
                    "evidence_ids": ["EV-STALE-CONTEXT"],
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
            any(
                "current Task Context does not match prepared context" in error
                for error in result["errors"]
            )
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
