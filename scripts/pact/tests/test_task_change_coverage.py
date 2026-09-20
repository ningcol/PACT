from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
RUNTIME = PROJECT_ROOT / "scripts" / "pact"
INIT = RUNTIME / "init.py"
sys.path.insert(0, str(RUNTIME))

spec = importlib.util.spec_from_file_location(
    "pact_workspace_task_changes",
    RUNTIME / "workspace.py",
)
workspace = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(workspace)


class TaskChangedFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-task-change-")
        self.root = pathlib.Path(self.temp.name) / "project"
        self.root.mkdir(parents=True)
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

    def tearDown(self) -> None:
        self.temp.cleanup()

    def commit_all(self, message: str) -> None:
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", message],
            cwd=self.root,
            check=True,
        )

    def pact(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.root / "pact.py"), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def write_json(self, relative: str, data: dict) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_git_baseline_does_not_attribute_untouched_predirty_file(self) -> None:
        (self.root / "tracked.txt").write_text("base\n", encoding="utf-8")
        (self.root / "predirty.txt").write_text("base\n", encoding="utf-8")
        self.commit_all("baseline")

        (self.root / "predirty.txt").write_text(
            "already dirty before task\n",
            encoding="utf-8",
        )
        baseline = workspace.task_workspace_baseline(self.root)
        self.assertIn("predirty.txt", baseline["dirty_files"])

        unchanged = workspace.task_changed_files(self.root, baseline)
        self.assertEqual(unchanged["changed_files"], [])

        (self.root / "predirty.txt").write_text(
            "changed during task\n",
            encoding="utf-8",
        )
        changed = workspace.task_changed_files(self.root, baseline)
        self.assertEqual(changed["changed_files"], ["predirty.txt"])

    def test_new_deleted_committed_and_generated_paths_are_attributed_correctly(self) -> None:
        (self.root / "tracked.txt").write_text("base\n", encoding="utf-8")
        (self.root / "delete-me.txt").write_text("delete\n", encoding="utf-8")
        self.commit_all("baseline")
        baseline = workspace.task_workspace_baseline(self.root)

        (self.root / "tracked.txt").write_text("committed change\n", encoding="utf-8")
        self.commit_all("task commit")
        (self.root / "delete-me.txt").unlink()
        (self.root / "new.txt").write_text("new\n", encoding="utf-8")
        generated = self.root / ".pact" / "tasks" / "TASK-X" / "task.json"
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text("{}\n", encoding="utf-8")

        delta = workspace.task_changed_files(self.root, baseline)
        self.assertEqual(
            delta["changed_files"],
            ["delete-me.txt", "new.txt", "tracked.txt"],
        )
        self.assertNotIn(".pact/tasks/TASK-X/task.json", delta["changed_files"])

    def test_fresh_adoption_control_plane_is_not_project_workspace_dirty(self) -> None:
        (self.root / "README.md").write_text("# Demo\n", encoding="utf-8")
        self.commit_all("baseline")

        init = subprocess.run(
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
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)

        # Git still exposes the uncommitted PACT scaffold to the owner, but
        # PACT's filtered project workspace must not call its own pristine
        # control-plane installation a product change.
        native_status = subprocess.run(
            ["git", "status", "--short"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("?? .pact/", native_status.stdout)

        snapshot = workspace.git_workspace_snapshot(self.root)
        self.assertIsNotNone(snapshot)
        self.assertFalse(snapshot["dirty"])
        self.assertEqual(snapshot["untracked_count"], 0)

        baseline = workspace.task_workspace_baseline(self.root)
        self.assertEqual(baseline["dirty_files"], {})

        manifest_path = self.root / ".pact" / "install.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        # Re-render valid install provenance so its bytes change without
        # changing the project's product/source state.
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8",
        )
        control_plane_only = workspace.task_changed_files(self.root, baseline)
        self.assertEqual(control_plane_only["changed_files"], [])
        self.assertEqual(control_plane_only["candidate_count"], 0)

        # Project-owned seeds remain part of project state once customized.
        config = self.root / ".pact" / "config.toml"
        config.write_text(
            config.read_text(encoding="utf-8") + "\n# project-owned customization\n",
            encoding="utf-8",
        )
        project_change = workspace.task_changed_files(self.root, baseline)
        self.assertEqual(project_change["changed_files"], [".pact/config.toml"])

    def test_corrupt_install_provenance_still_fails_workspace_closed(self) -> None:
        (self.root / "README.md").write_text("# Demo\n", encoding="utf-8")
        self.commit_all("baseline")

        init = subprocess.run(
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
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)

        manifest_path = self.root / ".pact" / "install.json"
        manifest_path.write_text("{ not valid json\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "invalid .pact/install.json"):
            workspace.git_workspace_snapshot(self.root)

    def test_filesystem_fallback_excludes_install_provenance_only(self) -> None:
        nongit = pathlib.Path(self.temp.name) / "nongit-project"
        nongit.mkdir()
        (nongit / "README.md").write_text("# Demo\n", encoding="utf-8")

        init = subprocess.run(
            [
                sys.executable,
                str(INIT),
                "--target",
                str(nongit),
                "--apply",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)

        snapshot = workspace.filesystem_workspace_snapshot(nongit)
        self.assertEqual(snapshot["file_count"], 1)

        manifest_path = nongit / ".pact" / "install.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8",
        )
        after_manifest_change = workspace.filesystem_workspace_snapshot(nongit)
        self.assertEqual(
            after_manifest_change["sha256"],
            snapshot["sha256"],
        )
        self.assertEqual(after_manifest_change["file_count"], 1)

        config = nongit / ".pact" / "config.toml"
        config.write_text(
            config.read_text(encoding="utf-8") + "\n# project-owned customization\n",
            encoding="utf-8",
        )
        customized = workspace.filesystem_workspace_snapshot(nongit)
        self.assertNotEqual(customized["sha256"], snapshot["sha256"])
        self.assertEqual(customized["file_count"], 2)

    def test_high_level_finish_requires_changed_file_convergence_coverage(self) -> None:
        (self.root / "README.md").write_text(
            "# Demo\n\nFeature behavior.\n",
            encoding="utf-8",
        )
        init = subprocess.run(
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
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.commit_all("adopt PACT")

        task_id = "TASK-CHANGE-COVERAGE"
        prepared = self.pact(
            "task",
            "prepare",
            "implement feature helper",
            "--success",
            "Feature helper exists",
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

        source = self.root / "src" / "feature.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("def feature():\n    return True\n", encoding="utf-8")

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
            "task": "implement feature helper",
            "risk_level": "low",
            "task_contract_sha256": prep["contract_sha256"],
            "claims": [
                {
                    "id": "EV-CHANGE",
                    "claim": "Feature helper exists.",
                    "required": True,
                    "status": "pass",
                    "criteria": ["AC-1"],
                    "evidence": [
                        {
                            "kind": "other",
                            "provenance": "file",
                            "ref": "src/feature.py",
                        }
                    ],
                }
            ],
            "limitations": [],
        }
        convergence = {
            "version": 1,
            "task_id": task_id,
            "change": "implement feature helper",
            "owner_summary": "Implementation reviewed.",
            "evidence": ["EV-CHANGE"],
            "context_sha256": prep["context_sha256"],
            "coverage": coverage,
            "findings": [],
        }
        owner = {
            "version": 1,
            "task_id": task_id,
            "status": "completed",
            "summary": "Feature helper implemented.",
            "before": "Helper absent.",
            "after": "Helper present.",
            "verification": [
                {
                    "claim": "Feature helper exists.",
                    "evidence_ids": ["EV-CHANGE"],
                }
            ],
            "acceptance": [
                {
                    "criterion_id": "AC-1",
                    "summary": "Feature helper exists",
                    "evidence_ids": ["EV-CHANGE"],
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

        blocked = self.pact("task", "finish", task_id, "--json")
        self.assertEqual(blocked.returncode, 1, blocked.stdout + blocked.stderr)
        blocked_data = json.loads(blocked.stdout)
        self.assertIn("src/feature.py", blocked_data["task_change"]["changed_files"])
        self.assertTrue(
            any(
                "Task changed file missing from Convergence change coverage"
                in error
                for error in blocked_data["errors"]
            )
        )
        final_impact = self.root / blocked_data["final_impact"]
        self.assertTrue(final_impact.is_file())
        impact = json.loads(final_impact.read_text(encoding="utf-8"))
        self.assertEqual(impact["changed_files"], ["src/feature.py"])

        convergence["change_coverage"] = [
            {
                "path": "src/feature.py",
                "rationale": "Intended implementation file for the accepted behavior.",
            }
        ]
        self.write_json(
            f".pact/completions/{task_id}/convergence.json",
            convergence,
        )

        finished = self.pact("task", "finish", task_id, "--json")
        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        result = json.loads(finished.stdout)
        self.assertTrue(result["complete"])
        self.assertEqual(
            result["change_coverage"]["covered_changed_files"],
            1,
        )
        self.assertEqual(
            result["task_change"]["changed_files"],
            ["src/feature.py"],
        )


if __name__ == "__main__":
    unittest.main()
