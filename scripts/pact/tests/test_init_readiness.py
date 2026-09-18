from __future__ import annotations

import json
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
                str(self.target / "scripts" / "pact" / "pact.py"),
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

    def test_apply_creates_foundation_valid_not_ready(self) -> None:
        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.target / ".pact" / "baseline.yaml").exists())
        self.assertFalse(
            (self.target / ".github" / "workflows" / "pact-project-check.yml").exists()
        )

        readiness = self.run_target("readiness", "--json")
        self.assertEqual(readiness.returncode, 0, readiness.stdout + readiness.stderr)
        data = json.loads(readiness.stdout)
        self.assertEqual(data["stage"], "foundation-valid")
        self.assertTrue(data["pending_reviews"])

    def test_all_reviewed_can_become_pact_ready(self) -> None:
        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        baseline = self.target / ".pact" / "baseline.yaml"
        text = baseline.read_text(encoding="utf-8").replace(": pending", ": reviewed")
        baseline.write_text(text, encoding="utf-8")

        readiness = self.run_target("readiness", "--require-ready", "--json")
        self.assertEqual(readiness.returncode, 0, readiness.stdout + readiness.stderr)
        data = json.loads(readiness.stdout)
        self.assertEqual(data["stage"], "pact-ready")
        self.assertEqual(data["pending_reviews"], [])

    def test_github_actions_is_opt_in(self) -> None:
        result = self.run_init("--apply", "--github-actions")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        workflow = self.target / ".github" / "workflows" / "pact-project-check.yml"
        self.assertTrue(workflow.exists())
        content = workflow.read_text(encoding="utf-8")
        self.assertIn("doctor --strict", content)
        self.assertIn("pact.py readiness", content)
        self.assertNotIn(".pact/examples", content)

    def test_existing_pact_workflow_is_never_overwritten(self) -> None:
        workflow = self.target / ".github" / "workflows" / "pact-project-check.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("KEEP\n", encoding="utf-8")

        result = self.run_init("--apply", "--github-actions")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(workflow.read_text(encoding="utf-8"), "KEEP\n")

    def test_existing_agents_is_preserved(self) -> None:
        self.target.mkdir(parents=True)
        agents = self.target / "AGENTS.md"
        agents.write_text("EXISTING RULES\n", encoding="utf-8")

        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(agents.read_text(encoding="utf-8"), "EXISTING RULES\n")
        self.assertTrue(
            (self.target / "docs" / "governance" / "PACT_AGENT_BOOTSTRAP.md").exists()
        )


if __name__ == "__main__":
    unittest.main()
