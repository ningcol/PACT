from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
INIT = PROJECT_ROOT / "scripts" / "pact" / "init.py"
UPGRADE = PROJECT_ROOT / "scripts" / "pact" / "upgrade.py"
SOURCE_VERSION = (PROJECT_ROOT / ".pact" / "VERSION").read_text(encoding="utf-8").strip()
NEXT_VERSION = "9.9.9-test"


class DistributionUpgradeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-upgrade-test-")
        self.root = pathlib.Path(self.temp.name)
        self.target = self.root / "target"
        self.new_source = self.root / "new-source"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_init(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INIT), "--target", str(self.target), *args],
            capture_output=True,
            text=True,
        )

    def run_upgrade(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(UPGRADE),
                "--target",
                str(self.target),
                "--source",
                str(self.new_source),
                *args,
            ],
            capture_output=True,
            text=True,
        )

    def write_source(self, relative: str, content: str) -> None:
        path = self.new_source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def scaffold(self) -> dict:
        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest_path = self.target / ".pact" / "install.json"
        self.assertTrue(manifest_path.exists())
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def test_init_records_framework_and_seed_ownership(self) -> None:
        manifest = self.scaffold()
        self.assertEqual(manifest["runtime_version"], SOURCE_VERSION)
        self.assertEqual(
            manifest["files"]["scripts/pact/README.md"]["management"],
            "framework",
        )
        self.assertEqual(
            manifest["files"][".pact/config.yaml"]["management"],
            "seed",
        )

    def test_clean_framework_upgrade_updates_atomically(self) -> None:
        self.scaffold()

        self.write_source(".pact/VERSION", NEXT_VERSION + "\n")
        self.write_source("scripts/pact/README.md", "# New Runtime Docs\n")

        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        self.assertEqual(
            (self.target / "scripts" / "pact" / "README.md").read_text(encoding="utf-8"),
            "# New Runtime Docs\n",
        )
        self.assertEqual(
            (self.target / ".pact" / "VERSION").read_text(encoding="utf-8"),
            NEXT_VERSION + "\n",
        )

        manifest = json.loads(
            (self.target / ".pact" / "install.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["runtime_version"], NEXT_VERSION)

    def test_conflicting_framework_change_blocks_entire_apply(self) -> None:
        manifest = self.scaffold()
        old_version = manifest["runtime_version"]

        runtime_readme = self.target / "scripts" / "pact" / "README.md"
        runtime_readme.write_text("# Local Project Modification\n", encoding="utf-8")

        self.write_source(".pact/VERSION", NEXT_VERSION + "\n")
        self.write_source("scripts/pact/README.md", "# Upstream Runtime Change\n")

        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 1)

        self.assertEqual(
            runtime_readme.read_text(encoding="utf-8"),
            "# Local Project Modification\n",
        )
        self.assertEqual(
            (self.target / ".pact" / "VERSION").read_text(encoding="utf-8"),
            SOURCE_VERSION + "\n",
        )

        after = json.loads(
            (self.target / ".pact" / "install.json").read_text(encoding="utf-8")
        )
        self.assertEqual(after["runtime_version"], old_version)

    def test_project_seed_is_never_overwritten(self) -> None:
        self.scaffold()

        config = self.target / ".pact" / "config.yaml"
        config.write_text("# PROJECT OWNED CONFIG\n", encoding="utf-8")

        self.write_source(".pact/VERSION", NEXT_VERSION + "\n")
        (self.new_source / "scripts" / "pact").mkdir(parents=True, exist_ok=True)
        self.write_source(
            ".pact/config.example.yaml",
            "# NEW FRAMEWORK CONFIG TEMPLATE\n",
        )

        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        self.assertEqual(
            config.read_text(encoding="utf-8"),
            "# PROJECT OWNED CONFIG\n",
        )

        data = json.loads(result.stdout)
        kinds = {notice["kind"] for notice in data["notices"]}
        self.assertIn("seed-update-available", kinds)


if __name__ == "__main__":
    unittest.main()
