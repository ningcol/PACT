"""No-model CI validation for a real coding-Agent experiment runner."""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
import github_actions_agent_preflight as runner


class GitHubActionsAgentPreflightTests(unittest.TestCase):
    def test_source_and_status_are_fixed_without_real_agent(self):
        self.assertEqual(runner.UPSTREAM_SHA,
                         "6a03856a6e1819b2eacd3963154ebc7d02923296")
        self.assertEqual(runner.RUNNER_KIND, "github-hosted-disposable-preflight")
        self.assertIn("NOT_RUN", runner.TRIAL_STATUS)
        self.assertIn("github.com/privacyfence/privacyfence.git",
                      runner.UPSTREAM)
        self.assertNotIn("secret", runner.EVALUATION_ORACLE_PATH.lower())

    def test_tracked_manifest_is_content_bound(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            subprocess.run(
                ["git", "init", "--quiet"], cwd=root,
                check=True, capture_output=True, timeout=10,
            )
            f = root / "README.md"
            f.write_text("# Original source\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "--", "README.md"], cwd=root,
                check=True, capture_output=True, timeout=10,
            )
            initial = runner.tracked_source(root)
            digest = runner.manifest_digest(initial)
            self.assertEqual(list(initial), ["README.md"])
            self.assertTrue(runner.original_clean(root))
            f.write_text("# Silent unauthorized change\n", encoding="utf-8")
            current = runner.tracked_source(root)
            self.assertNotEqual(current, initial)
            self.assertNotEqual(runner.manifest_digest(current), digest)
            self.assertFalse(runner.original_clean(root))

    def test_symlink_escape_rejected_without_following_target(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            subprocess.run(["git", "init", "--quiet"], cwd=root,
                           check=True, capture_output=True)
            bad = root / "escape"
            bad.symlink_to("../../private-token-file")
            subprocess.run(["git", "add", "escape"], cwd=root,
                           check=True, capture_output=True)
            with self.assertRaisesRegex(ValueError, "escapes clone"):
                runner.tracked_source(root)

    def test_preflight_failure_is_not_real_agent_success(self):
        with tempfile.TemporaryDirectory() as td:
            report = pathlib.Path(td) / "preflight.json"
            with mock.patch.object(
                runner, "run_preflight",
                side_effect=RuntimeError("source checkout unavailable"),
            ), mock.patch.object(
                sys, "argv",
                ["github_actions_agent_preflight.py",
                 "--output", str(report),
                 "--temp-root", td],
            ), contextlib.redirect_stdout(io.StringIO()):
                exit_code = runner.main()
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 2)
            self.assertEqual(data["preflight_status"], "FAIL")
            self.assertFalse(data["real_agent_executed"])
            self.assertFalse(data["independently_blinded"])
            self.assertEqual(data["release_gate"], "HOLD")
            self.assertEqual(data["error_type"], "RuntimeError")

    def test_missing_scratch_root_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "temporary runner scratch"):
                runner.run_preflight(pathlib.Path(td) / "missing")


if __name__ == "__main__":
    unittest.main()
