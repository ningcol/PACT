from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
INIT = PROJECT_ROOT / "scripts" / "pact" / "init.py"


class InitReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-init-test-")
        self.target = pathlib.Path(self.temp.name) / "project"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_init(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INIT), "--target", str(self.target), *args],
            capture_output=True,
            text=True,
        )

    def run_target(self, command: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(self.target / "pact.py"),
                command,
                *args,
            ],
            capture_output=True,
            text=True,
        )

    def test_dry_run_writes_nothing(self) -> None:
        result = self.run_init("--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.target.exists())

    def test_apply_creates_toml_foundation_valid_not_ready(self) -> None:
        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.target / ".pact" / "config.toml").exists())
        self.assertTrue((self.target / ".pact" / "baseline.toml").exists())
        self.assertTrue((self.target / ".pact" / "fitness.toml").exists())
        self.assertFalse((self.target / ".pact" / "config.yaml").exists())
        self.assertFalse((self.target / "docs" / "product").exists())
        self.assertFalse((self.target / "docs" / "architecture").exists())
        self.assertFalse((self.target / ".agents" / "decisions").exists())

        readiness = self.run_target("readiness", "--json")
        self.assertEqual(readiness.returncode, 0, readiness.stdout + readiness.stderr)
        data = json.loads(readiness.stdout)
        self.assertEqual(data["stage"], "foundation-valid")
        self.assertIn("agent_bootstrap", data["pending_reviews"])

    def test_init_uses_nested_control_plane_gitignore(self) -> None:
        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        nested = self.target / ".pact" / ".gitignore"
        self.assertTrue(nested.is_file())
        self.assertFalse((self.target / ".gitignore").exists())
        rules = set(nested.read_text(encoding="utf-8").splitlines())
        self.assertTrue({
            "cache/",
            "tasks/",
            "runs/",
            "completions/",
            "tmp/",
        } <= rules)

    def test_existing_root_gitignore_is_untouched(self) -> None:
        self.target.mkdir(parents=True)
        root_ignore = self.target / ".gitignore"
        root_ignore.write_text("KEEP-ME\n", encoding="utf-8")

        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            root_ignore.read_text(encoding="utf-8"),
            "KEEP-ME\n",
        )
        self.assertTrue((self.target / ".pact" / ".gitignore").is_file())

    def test_fresh_status_is_healthy_with_baseline_advisory(self) -> None:
        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        status = self.run_target("status", "--strict", "--json")
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        data = json.loads(status.stdout)
        self.assertEqual(data["overall"], "pass")
        self.assertEqual(data["foundation"]["state"], "pass")
        self.assertEqual(data["readiness"]["stage"], "foundation-valid")
        self.assertIn("baseline-review-pending", data["warnings"])

        gated = self.run_target("readiness", "--require-ready", "--json")
        self.assertEqual(gated.returncode, 1)
        self.assertEqual(json.loads(gated.stdout)["stage"], "foundation-valid")

    def test_invalid_baseline_blocks_status(self) -> None:
        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        baseline = self.target / ".pact" / "baseline.toml"
        baseline.write_text(
            'version = 1\n[reviews]\nagent_bootstrap = "invalid-state"\n',
            encoding="utf-8",
        )

        status = self.run_target("status", "--strict", "--json")
        self.assertEqual(status.returncode, 1)
        data = json.loads(status.stdout)
        self.assertEqual(data["overall"], "fail")
        self.assertTrue(
            any("readiness failed:" in error for error in data["errors"]),
            data,
        )

    def test_all_reviewed_can_become_pact_ready(self) -> None:
        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        baseline = self.target / ".pact" / "baseline.toml"
        text = baseline.read_text(encoding="utf-8").replace('"pending"', '"reviewed"')
        baseline.write_text(text, encoding="utf-8")

        readiness = self.run_target("readiness", "--require-ready", "--json")
        self.assertEqual(readiness.returncode, 0, readiness.stdout + readiness.stderr)
        data = json.loads(readiness.stdout)
        self.assertEqual(data["stage"], "pact-ready")
        self.assertEqual(data["pending_reviews"], [])

    def test_existing_agents_requires_bootstrap_review(self) -> None:
        self.target.mkdir(parents=True)
        agents = self.target / "AGENTS.md"
        agents.write_text("EXISTING RULES\n", encoding="utf-8")

        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(agents.read_text(encoding="utf-8"), "EXISTING RULES\n")
        self.assertTrue(
            (self.target / ".pact" / "AGENT_BOOTSTRAP.md").exists()
        )
        self.assertFalse((self.target / "docs" / "governance").exists())

        baseline = self.target / ".pact" / "baseline.toml"
        text = baseline.read_text(encoding="utf-8")
        self.assertIn('agent_bootstrap = "pending"', text)

    def test_github_actions_is_opt_in(self) -> None:
        result = self.run_init("--apply", "--github-actions")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        workflow = self.target / ".github" / "workflows" / "pact-project-check.yml"
        self.assertTrue(workflow.exists())
        content = workflow.read_text(encoding="utf-8")
        self.assertIn("doctor --strict", content)
        self.assertNotIn("pip install", content)
        manifest = json.loads(
            (self.target / ".pact" / "install.json").read_text(encoding="utf-8")
        )
        self.assertLessEqual(len(manifest["files"]), 10)

    def test_existing_pact_workflow_is_never_overwritten(self) -> None:
        workflow = self.target / ".github" / "workflows" / "pact-project-check.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("KEEP\n", encoding="utf-8")

        result = self.run_init("--apply", "--github-actions")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(workflow.read_text(encoding="utf-8"), "KEEP\n")

    def test_parent_symlink_escape_is_rejected(self) -> None:
        self.target.mkdir(parents=True)
        outside = pathlib.Path(self.temp.name) / "outside"
        outside.mkdir()
        link = self.target / ".pact"
        try:
            os.symlink(outside, link, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")

        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 2)
        self.assertIn("init path escapes target through symlink", result.stderr)
        self.assertTrue(link.is_symlink())
        self.assertEqual(list(outside.iterdir()), [])

    def test_broken_leaf_symlink_is_preserved_as_existing_path(self) -> None:
        self.target.mkdir(parents=True)
        agents = self.target / "AGENTS.md"
        broken_target = self.target / "missing-agents.md"
        try:
            os.symlink(broken_target, agents)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")

        self.assertTrue(agents.is_symlink())
        self.assertFalse(agents.exists())

        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(agents.is_symlink())
        self.assertEqual(os.readlink(agents), str(broken_target))
        self.assertTrue((self.target / ".pact" / "AGENT_BOOTSTRAP.md").is_file())


if __name__ == "__main__":
    unittest.main()
