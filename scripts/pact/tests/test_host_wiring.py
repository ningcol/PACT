"""S6: non-destructive host integration preflight never guesses Agent compliance."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


SOURCE = pathlib.Path(__file__).resolve().parents[3]
RUNTIME = SOURCE / "scripts" / "pact"
sys.path.insert(0, str(RUNTIME))
import doctor


class HostWiringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pact-host-wiring-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name) / "project"
        self.root.mkdir()

    def write(self, relative, body):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def test_pact_guide_routes_without_claiming_agent_executed(self):
        self.write("AGENTS.md", "# Host\nUse PACT for task preparation.\n")
        checks = doctor.host_wiring_checks(self.root)
        found = [x for x in checks if x["check"] == "host:AGENTS.md"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["state"], "pass")
        self.assertIn("actual Agent loading still unverified", found[0]["detail"])

    def test_missing_host_route_is_manual_review_not_false_pass(self):
        self.write("AGENTS.md", "# Instructions\nKeep things short.\n")
        checks = doctor.host_wiring_checks(self.root)
        self.assertTrue(any(x["state"] == "needs-manual-review" and
                            "do not explicitly route" in x["detail"]
                            for x in checks), checks)

    def test_direct_markdown_include_cycle_is_rejected(self):
        self.write("AGENTS.md", "# Agent\nSee [Claude](CLAUDE.md)\n")
        self.write("CLAUDE.md", "# Claude\nSee [Agents](AGENTS.md)\n")
        checks = doctor.host_wiring_checks(self.root)
        self.assertTrue(any(x["state"] == "fail" and
                            x["check"] == "host-include-cycle"
                            for x in checks), checks)

    def test_filtering_host_ci_is_not_automatically_declared_compatible(self):
        self.write("AGENTS.md", "# PACT\n")
        self.write(".github/workflows/build.yml",
                   "name: Build\non:\n  push:\n    paths:\n      - 'src/**'\n")
        checks = doctor.host_wiring_checks(self.root)
        self.assertTrue(any(x["check"].startswith("host-ci:") and
                            x["state"] == "needs-manual-review"
                            for x in checks), checks)

    def test_symlinked_host_config_is_not_opened(self):
        outside = pathlib.Path(self.temp.name) / "private-guide"
        outside.write_text("DO NOT READ MY SECRET", encoding="utf-8")
        try:
            os.symlink(outside, self.root / "CLAUDE.md")
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        checks = doctor.host_wiring_checks(self.root)
        self.assertTrue(any(x["check"] == "host:CLAUDE.md" and
                            x["state"] == "needs-manual-review"
                            for x in checks), checks)
        self.assertNotIn("DO NOT READ MY SECRET", json.dumps(checks))

    def test_installed_host_wiring_only_does_not_generate_map_or_execute_ci(self):
        target = self.root
        init = subprocess.run(
            [sys.executable, str(SOURCE / "scripts" / "pact" / "init.py"),
             "--target", str(target), "--apply"],
            capture_output=True, text=True,
        )
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        cache_map = target / ".pact" / "cache" / "project-map.json"
        self.assertFalse(cache_map.exists())
        result = subprocess.run(
            [sys.executable, str(target / "pact.py"), "doctor",
             "--host-wiring-only", "--json"],
            cwd=target, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertFalse(data["host_ci_executed"])
        self.assertNotEqual(data["overall"], "fail")
        self.assertFalse(cache_map.exists())


if __name__ == "__main__":
    unittest.main()
