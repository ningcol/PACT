"""Integration regression for PR-01 Contract + PR-02 Git workspace semantics.

Exercises the installed compact runtime in a real, temporary Git worktree.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


SOURCE_ROOT = pathlib.Path(__file__).resolve().parents[3]
INIT = SOURCE_ROOT / "scripts" / "pact" / "init.py"


class MergedTrustRoundtripTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-merged-trust-")
        self.root = pathlib.Path(self.temp.name) / "project"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "pact-test@example.invalid"],
            cwd=self.root, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "PACT Test"],
            cwd=self.root, check=True,
        )

        (self.root / "README.md").write_text(
            "# Git-backed project\n\nA service flag is verified through PACT.\n",
            encoding="utf-8",
        )
        source = self.root / "src" / "service.py"
        source.parent.mkdir()
        source.write_text("FLAG = 'old'\n", encoding="utf-8")

        init = subprocess.run(
            [sys.executable, str(INIT), "--target", str(self.root), "--apply"],
            cwd=self.root, capture_output=True, text=True,
        )
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "adopt PACT"], cwd=self.root, check=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def pact(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.root / "pact.py"), *arguments],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def write_bundle_file(self, task_id: str, name: str, record: dict) -> None:
        folder = self.root / ".pact" / "completions" / task_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def prepared_verification(self, task_id: str) -> tuple[dict, dict, dict, dict]:
        prepared = self.pact(
            "task", "prepare", "Update service flag",
            "--success", "Service flag is updated",
            "--risk", "medium", "--task-id", task_id, "--json",
        )
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        task = json.loads(prepared.stdout)
        contract = json.loads((self.root / task["contract"]).read_text(encoding="utf-8"))
        context = json.loads((self.root / task["context"]).read_text(encoding="utf-8"))
        (self.root / "src" / "service.py").write_text(
            "FLAG = 'new'\n", encoding="utf-8",
        )

        run_relative = f".pact/runs/{task_id}/verified.json"
        executed = self.pact(
            "run", "--task-id", task_id, "--output", run_relative,
            "--cwd", str(self.root), "--quiet", "--",
            sys.executable, "-c",
            "from pathlib import Path; assert Path('src/service.py').read_text() == \"FLAG = 'new'\\n\"",
        )
        self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)

        claim = "The service flag verification command passed."
        evidence = {
            "version": 1, "task_id": task_id, "task": "Update service flag",
            "risk_level": "medium", "task_contract_sha256": task["contract_sha256"],
            "claims": [{
                "id": "EV-SERVICE", "claim": claim, "required": True, "status": "pass",
                "criteria": [item["id"] for item in contract["acceptance_criteria"]],
                "evidence": [{"kind": "test", "provenance": "pact-run", "ref": run_relative}],
            }],
            "limitations": [],
        }
        convergence = {
            "version": 1, "task_id": task_id, "change": "Update service flag",
            "owner_summary": "All context reviewed", "evidence": ["EV-SERVICE"],
            "context_sha256": task["context_sha256"],
            "coverage": [{
                "path": item["path"], "disposition": "aligned",
                "rationale": "Reviewed the existing project truth.",
            } for item in context["artifacts"]],
            "change_coverage": [{
                "path": "src/service.py", "rationale": "Verified intentional implementation change.",
            }],
            "findings": [],
        }
        owner = {
            "version": 1, "task_id": task_id, "status": "completed",
            "summary": "Service flag updated", "before": "Old flag", "after": "New flag",
            "verification": [{"claim": claim, "evidence_ids": ["EV-SERVICE"]}],
            "acceptance": [{
                "criterion_id": item["id"], "summary": item["text"],
                "evidence_ids": ["EV-SERVICE"],
            } for item in contract["acceptance_criteria"]],
            "consistency": {"status": "aligned", "summary": "No blocking drift"},
            "owner_decisions": [],
        }
        for name, payload in (
            ("evidence.json", evidence),
            ("convergence.json", convergence),
            ("owner-report.json", owner),
        ):
            self.write_bundle_file(task_id, name, payload)
        return task, contract, evidence, owner

    def test_custom_relative_bundle_remains_default_on_finish_retry(self) -> None:
        task_id = "TASK-CUSTOM-RETRY"
        self.prepared_verification(task_id)
        original = self.root / ".pact" / "completions" / task_id
        custom_relative = f".pact/completions/{task_id}-custom"
        original.rename(self.root / custom_relative)

        first = self.pact(
            "task", "finish", task_id, "--bundle", custom_relative, "--json"
        )
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        first_data = json.loads(first.stdout)
        self.assertTrue(first_data["complete"])

        manifest_path = self.root / ".pact" / "tasks" / task_id / "task.json"
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["completion_bundle"], custom_relative)
        self.assertFalse(original.exists(), "default bundle was never populated")

        status = self.pact("task", "status", task_id, "--json")
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        self.assertTrue(all(json.loads(status.stdout)["completion_files"].values()))

        second = self.pact("task", "finish", task_id, "--json")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertTrue(json.loads(second.stdout)["complete"])
        saved_again = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(saved_again["completion_bundle"], custom_relative)

        history = self.root / ".pact" / "tasks" / task_id / "completion-attempts.jsonl"
        attempts = [
            json.loads(line) for line in history.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(len(attempts), 2)
        self.assertTrue(all(item["complete"] for item in attempts))
        observed = self.pact("eval", "--task", task_id, "--json")
        self.assertEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertTrue(json.loads(observed.stdout)["completion"]["final_complete"])

    def test_custom_absolute_bundle_remains_default_on_finish_retry(self) -> None:
        task_id = "TASK-ABS-RETRY"
        self.prepared_verification(task_id)
        original = self.root / ".pact" / "completions" / task_id
        outside = pathlib.Path(self.temp.name) / "external-completion"
        original.rename(outside)
        first = self.pact(
            "task", "finish", task_id, "--bundle", str(outside), "--json"
        )
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertTrue(json.loads(first.stdout)["complete"])

        manifest_path = self.root / ".pact" / "tasks" / task_id / "task.json"
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["completion_bundle"], str(outside))
        self.assertFalse(original.exists())

        second = self.pact("task", "finish", task_id, "--json")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertTrue(json.loads(second.stdout)["complete"])
        self.assertEqual(
            json.loads(manifest_path.read_text(encoding="utf-8"))["completion_bundle"],
            str(outside),
        )

    def test_finish_rejects_invalid_manifest_completion_bundle_before_side_effects(self) -> None:
        task_id = "TASK-BUNDLE-INVALID"
        self.prepared_verification(task_id)
        task_dir = self.root / ".pact" / "tasks" / task_id
        manifest_path = task_dir / "task.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["completion_bundle"] = {"unsafe": "path"}
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        original = manifest_path.read_bytes()

        finished = self.pact("task", "finish", task_id, "--json")
        self.assertEqual(finished.returncode, 2, finished.stdout + finished.stderr)
        self.assertIn("completion_bundle", finished.stderr)
        self.assertEqual(manifest_path.read_bytes(), original)
        self.assertFalse((task_dir / "final-impact.json").exists())
        self.assertFalse((task_dir / "completion-attempts.jsonl").exists())

    def test_null_manifest_bundle_path_is_rejected_without_traceback(self) -> None:
        task_id = "TASK-BUNDLE-NULL"
        self.prepared_verification(task_id)
        task_dir = self.root / ".pact" / "tasks" / task_id
        manifest_path = task_dir / "task.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["completion_bundle"] = None
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        original = manifest_path.read_bytes()

        for args in (
            ("task", "finish", task_id, "--json"),
            ("task", "status", task_id, "--json"),
        ):
            with self.subTest(args=args):
                observed = self.pact(*args)
                self.assertEqual(observed.returncode, 2, observed.stdout + observed.stderr)
                self.assertIn("completion_bundle", observed.stderr)
                self.assertNotIn("Traceback", observed.stderr)
        self.assertEqual(manifest_path.read_bytes(), original)
        self.assertFalse((task_dir / "completion-attempts.jsonl").exists())
        self.assertFalse((task_dir / "final-impact.json").exists())

    def test_medium_risk_git_prepare_run_finish_eval_roundtrip(self) -> None:
        task_id = "TASK-MERGED-ROUNDTRIP"
        self.prepared_verification(task_id)

        finished = self.pact("task", "finish", task_id, "--json")
        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        outcome = json.loads(finished.stdout)
        self.assertTrue(outcome["complete"])
        self.assertEqual(outcome["workspace_bound_claims"], 1)
        self.assertEqual(outcome["changed_files"], ["src/service.py"])
        self.assertEqual(outcome["change_coverage"]["covered_changed_files"], 1)
        self.assertEqual(outcome["acceptance"]["owner_report_covered"], 1)

        evaluated = self.pact("eval", "--task", task_id, "--json")
        self.assertEqual(evaluated.returncode, 0, evaluated.stdout + evaluated.stderr)
        result = json.loads(evaluated.stdout)
        self.assertTrue(result["completion"]["final_complete"])
        self.assertEqual(result["task_change"]["paths"], ["src/service.py"])

    def test_mutated_contract_and_updated_evidence_cannot_bypass_original_sha(self) -> None:
        task_id = "TASK-MERGED-MUTATION"
        task, contract, evidence, owner = self.prepared_verification(task_id)
        contract["acceptance_criteria"][0]["text"] = "Weakened acceptance after preparation"
        path = self.root / task["contract"]
        path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
        evidence["task_contract_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        owner["acceptance"][0]["summary"] = contract["acceptance_criteria"][0]["text"]
        self.write_bundle_file(task_id, "evidence.json", evidence)
        self.write_bundle_file(task_id, "owner-report.json", owner)

        finished = self.pact("task", "finish", task_id, "--json")
        self.assertEqual(finished.returncode, 2, finished.stdout + finished.stderr)
        self.assertIn("contract_sha256 does not match prepared", finished.stderr)
        task_dir = self.root / ".pact" / "tasks" / task_id
        self.assertFalse((task_dir / "completion-attempts.jsonl").exists())
        self.assertFalse((task_dir / "final-impact.json").exists())


if __name__ == "__main__":
    unittest.main()
