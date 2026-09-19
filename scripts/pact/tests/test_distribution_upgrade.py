from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
INIT = PROJECT_ROOT / "scripts" / "pact" / "init.py"
UPGRADE = PROJECT_ROOT / "scripts" / "pact" / "upgrade.py"
SOURCE_VERSION = (PROJECT_ROOT / ".pact" / "VERSION").read_text(
    encoding="utf-8"
).strip()
NEXT_VERSION = "9.9.9-test"


class DistributionUpgradeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-upgrade-test-")
        self.root = pathlib.Path(self.temp.name)
        self.target = self.root / "target"
        self.new_source = self.root / "new-source"
        shutil.copytree(
            PROJECT_ROOT,
            self.new_source,
            ignore=shutil.ignore_patterns(
                ".git",
                "__pycache__",
                "*.pyc",
                "cache",
            ),
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_init(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INIT), "--target", str(self.target), *args],
            capture_output=True,
            text=True,
        )

    def run_upgrade(
        self,
        *args: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
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
            env=env,
        )

    def run_target(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.target / "pact.py"), *args],
            cwd=self.target,
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

    def change_runtime_source(self) -> None:
        self.write_source(".pact/VERSION", NEXT_VERSION + "\n")
        module = self.new_source / "scripts" / "pact" / "version.py"
        module.write_text(
            module.read_text(encoding="utf-8") + "\n# upgrade-test-change\n",
            encoding="utf-8",
        )

    def add_tracked_obsolete_framework(
        self,
        manifest: dict,
        *,
        relative: str = ".pact/obsolete-framework.txt",
        content: str = "obsolete framework content\n",
    ) -> pathlib.Path:
        destination = self.target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        manifest["files"][relative] = {
            "management": "framework",
            "source_path": relative,
            "source_sha256": digest,
            "installed_sha256": digest,
        }
        (self.target / ".pact" / "install.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        return destination

    def test_init_records_current_runtime_and_seed_ownership(self) -> None:
        manifest = self.scaffold()
        self.assertEqual(manifest["runtime_version"], SOURCE_VERSION)
        self.assertNotIn("install_profile", manifest)
        self.assertLessEqual(len(manifest["files"]), 8)
        self.assertEqual(
            manifest["files"][".pact/pact.pyz"]["management"],
            "framework",
        )
        self.assertEqual(
            manifest["files"][".pact/config.toml"]["management"],
            "seed",
        )
        self.assertTrue((self.target / ".pact" / "pact.pyz").is_file())
        self.assertFalse((self.target / "scripts" / "pact").exists())

        version = self.run_target("version", "--json")
        self.assertEqual(version.returncode, 0, version.stdout + version.stderr)

    def test_init_preserves_existing_agents_with_control_plane_bootstrap(self) -> None:
        self.target.mkdir(parents=True)
        agents = self.target / "AGENTS.md"
        agents.write_text("# Existing project agent rules\n", encoding="utf-8")

        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            agents.read_text(encoding="utf-8"),
            "# Existing project agent rules\n",
        )
        self.assertTrue((self.target / ".pact" / "AGENT_BOOTSTRAP.md").is_file())

    def test_reinit_from_different_runtime_is_rejected(self) -> None:
        manifest = self.scaffold()
        manifest["runtime_version"] = "0.0.other"
        (self.target / ".pact" / "install.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Use 'pact upgrade", result.stderr)

    def test_clean_framework_upgrade_updates_compact_runtime_atomically(self) -> None:
        self.scaffold()
        bundle = self.target / ".pact" / "pact.pyz"
        original_bundle = bundle.read_bytes()

        self.change_runtime_source()
        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        self.assertNotEqual(bundle.read_bytes(), original_bundle)
        self.assertEqual(
            (self.target / ".pact" / "VERSION").read_text(encoding="utf-8"),
            NEXT_VERSION + "\n",
        )
        manifest = json.loads(
            (self.target / ".pact" / "install.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["runtime_version"], NEXT_VERSION)
        self.assertNotIn("install_profile", manifest)

    def test_conflicting_compact_runtime_change_blocks_entire_apply(self) -> None:
        manifest = self.scaffold()
        old_version = manifest["runtime_version"]
        runtime_bundle = self.target / ".pact" / "pact.pyz"
        original = runtime_bundle.read_bytes()
        runtime_bundle.write_bytes(original + b"LOCAL-MODIFICATION")

        self.change_runtime_source()
        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(runtime_bundle.read_bytes(), original + b"LOCAL-MODIFICATION")
        after = json.loads(
            (self.target / ".pact" / "install.json").read_text(encoding="utf-8")
        )
        self.assertEqual(after["runtime_version"], old_version)

    def test_mid_apply_failure_rolls_back_files_and_manifest(self) -> None:
        self.scaffold()
        version_path = self.target / ".pact" / "VERSION"
        bundle_path = self.target / ".pact" / "pact.pyz"
        manifest_path = self.target / ".pact" / "install.json"

        original_version = version_path.read_bytes()
        original_bundle = bundle_path.read_bytes()
        original_manifest = manifest_path.read_bytes()

        self.change_runtime_source()
        env = os.environ.copy()
        env["PACT_TEST_FAIL_AFTER_REPLACE"] = "1"
        result = self.run_upgrade("--apply", "--json", env=env)

        self.assertEqual(result.returncode, 2)
        data = json.loads(result.stdout)
        self.assertFalse(data["applied"])
        self.assertTrue(data["rolled_back"])
        self.assertEqual(version_path.read_bytes(), original_version)
        self.assertEqual(bundle_path.read_bytes(), original_bundle)
        self.assertEqual(manifest_path.read_bytes(), original_manifest)

    def test_doctor_detects_modified_compact_runtime(self) -> None:
        self.scaffold()
        runtime_bundle = self.target / ".pact" / "pact.pyz"
        runtime_bundle.write_bytes(runtime_bundle.read_bytes() + b"MODIFIED")

        result = self.run_target("doctor", "--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("framework file modified/corrupt", result.stdout + result.stderr)

    def test_unchanged_obsolete_framework_file_is_removed(self) -> None:
        manifest = self.scaffold()
        obsolete = self.add_tracked_obsolete_framework(manifest)
        self.assertTrue(obsolete.is_file())

        self.change_runtime_source()
        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(obsolete.exists())

        updated = json.loads(
            (self.target / ".pact" / "install.json").read_text(encoding="utf-8")
        )
        self.assertNotIn(".pact/obsolete-framework.txt", updated["files"])

    def test_modified_obsolete_framework_file_is_preserved_and_detached(self) -> None:
        manifest = self.scaffold()
        obsolete = self.add_tracked_obsolete_framework(manifest)
        obsolete.write_text("project modified this old framework file\n", encoding="utf-8")

        self.change_runtime_source()
        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)

        self.assertTrue(obsolete.is_file())
        self.assertIn("project modified", obsolete.read_text(encoding="utf-8"))
        kinds = {notice["kind"] for notice in data["notices"]}
        self.assertIn("obsolete-framework-local-modification", kinds)

        updated = json.loads(
            (self.target / ".pact" / "install.json").read_text(encoding="utf-8")
        )
        self.assertNotIn(".pact/obsolete-framework.txt", updated["files"])

    def test_project_toml_seed_is_never_overwritten(self) -> None:
        self.scaffold()
        config = self.target / ".pact" / "config.toml"
        original = config.read_text(encoding="utf-8")
        config.write_text(original + "\n# PROJECT OWNED\n", encoding="utf-8")

        self.change_runtime_source()
        self.write_source(
            ".pact/config.example.toml",
            'version = 1\n[owner]\nrole = "changed-upstream"\n',
        )

        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("# PROJECT OWNED", config.read_text(encoding="utf-8"))
        kinds = {notice["kind"] for notice in json.loads(result.stdout)["notices"]}
        self.assertIn("seed-update-available", kinds)


if __name__ == "__main__":
    unittest.main()
