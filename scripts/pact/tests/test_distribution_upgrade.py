from __future__ import annotations

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
SOURCE_VERSION = (PROJECT_ROOT / ".pact" / "VERSION").read_text(encoding="utf-8").strip()
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
            [
                sys.executable,
                str(self.target / "pact.py"),
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

    def test_init_records_minimal_profile_and_toml_seed_ownership(self) -> None:
        manifest = self.scaffold()
        self.assertEqual(manifest["runtime_version"], SOURCE_VERSION)
        self.assertEqual(manifest.get("install_profile"), "minimal")
        self.assertLessEqual(len(manifest["files"]), 8)
        self.assertEqual(
            manifest["files"][".pact/pact.pyz"]["management"],
            "framework",
        )
        self.assertTrue((self.target / ".pact" / "pact.pyz").is_file())
        self.assertFalse((self.target / "scripts" / "pact").exists())
        self.assertFalse((self.target / "docs" / "product").exists())
        self.assertFalse((self.target / ".agents" / "decisions").exists())

        version = self.run_target("version", "--json")
        self.assertEqual(version.returncode, 0, version.stdout + version.stderr)
        self.assertEqual(
            manifest["files"][".pact/config.toml"]["management"],
            "seed",
        )

        doctor = self.run_target("doctor", "--strict")
        self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)

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

        bootstrap = self.target / ".pact" / "AGENT_BOOTSTRAP.md"
        self.assertTrue(bootstrap.is_file())
        self.assertFalse((self.target / "docs" / "governance").exists())

        manifest = json.loads(
            (self.target / ".pact" / "install.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["files"][".pact/AGENT_BOOTSTRAP.md"]["management"],
            "seed",
        )

    def test_reinit_from_different_runtime_is_rejected(self) -> None:
        manifest = self.scaffold()
        manifest["runtime_version"] = "0.0.legacy"
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

        self.write_source(".pact/VERSION", NEXT_VERSION + "\n")
        version_module = self.new_source / "scripts" / "pact" / "version.py"
        version_module.write_text(
            version_module.read_text(encoding="utf-8") + "\n# compact-upgrade-test\n",
            encoding="utf-8",
        )

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
        self.assertIn(".pact/pact.pyz", manifest["files"])
        self.assertEqual(manifest.get("install_profile"), "minimal")
        self.assertFalse((self.target / "docs" / "product").exists())
        self.assertFalse((self.target / "scripts" / "pact").exists())

    def test_conflicting_compact_runtime_change_blocks_entire_apply(self) -> None:
        manifest = self.scaffold()
        old_version = manifest["runtime_version"]

        runtime_bundle = self.target / ".pact" / "pact.pyz"
        original = runtime_bundle.read_bytes()
        runtime_bundle.write_bytes(original + b"LOCAL-MODIFICATION")

        self.write_source(".pact/VERSION", NEXT_VERSION + "\n")
        version_module = self.new_source / "scripts" / "pact" / "version.py"
        version_module.write_text(
            version_module.read_text(encoding="utf-8") + "\n# upstream-change\n",
            encoding="utf-8",
        )

        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(runtime_bundle.read_bytes(), original + b"LOCAL-MODIFICATION")
        self.assertEqual(
            (self.target / ".pact" / "VERSION").read_text(encoding="utf-8"),
            SOURCE_VERSION + "\n",
        )

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

        self.write_source(".pact/VERSION", NEXT_VERSION + "\n")
        version_module = self.new_source / "scripts" / "pact" / "version.py"
        version_module.write_text(
            version_module.read_text(encoding="utf-8") + "\n# transaction-test\n",
            encoding="utf-8",
        )

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

    def make_legacy_runtime_install(self, *, modify_one: bool = False) -> dict:
        manifest = self.scaffold()
        # Simulate an older/full-profile installation. Legacy manifests predate
        # install_profile and must retain the historical compatibility surface.
        manifest.pop("install_profile", None)
        compact = self.target / ".pact" / "pact.pyz"
        compact.unlink()
        manifest["files"].pop(".pact/pact.pyz", None)

        legacy_paths = [
            "scripts/pact/pact.py",
            "scripts/pact/runtime_exec.py",
            "scripts/pact/README.md",
        ]
        for relative in legacy_paths:
            source = PROJECT_ROOT / relative
            destination = self.target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            import hashlib
            digest = hashlib.sha256(destination.read_bytes()).hexdigest()
            manifest["files"][relative] = {
                "management": "framework",
                "source_path": relative,
                "source_sha256": digest,
                "installed_sha256": digest,
            }

        if modify_one:
            local = self.target / "scripts/pact/README.md"
            local.write_text("# locally customized old runtime docs\n", encoding="utf-8")

        (self.target / ".pact" / "install.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        return manifest

    def test_legacy_source_runtime_migrates_to_single_compact_bundle(self) -> None:
        self.make_legacy_runtime_install()
        self.write_source(".pact/VERSION", NEXT_VERSION + "\n")

        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)

        self.assertTrue((self.target / ".pact" / "pact.pyz").is_file())
        legacy_entry = self.target / "scripts" / "pact" / "pact.py"
        self.assertTrue(legacy_entry.is_file())
        self.assertFalse((self.target / "scripts" / "pact" / "runtime_exec.py").exists())
        self.assertFalse((self.target / "scripts" / "pact" / "README.md").exists())
        self.assertGreaterEqual(data.get("removed_files", 0), 2)

        manifest = json.loads(
            (self.target / ".pact" / "install.json").read_text(encoding="utf-8")
        )
        self.assertIn(".pact/pact.pyz", manifest["files"])
        self.assertIn("scripts/pact/pact.py", manifest["files"])
        self.assertIn("scripts/pact/converge.py", manifest["files"])
        self.assertIn("scripts/pact/report.py", manifest["files"])

        legacy_status = subprocess.run(
            [sys.executable, str(legacy_entry), "status", "--json"],
            cwd=self.target,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            legacy_status.returncode,
            0,
            legacy_status.stdout + legacy_status.stderr,
        )

    def test_legacy_runtime_removal_is_rolled_back_on_late_failure(self) -> None:
        original_manifest = self.make_legacy_runtime_install()
        legacy_runtime = self.target / "scripts" / "pact" / "runtime_exec.py"
        original_runtime = legacy_runtime.read_bytes()
        original_manifest_bytes = (
            self.target / ".pact" / "install.json"
        ).read_bytes()

        self.write_source(".pact/VERSION", NEXT_VERSION + "\n")

        planned = self.run_upgrade("--json")
        self.assertEqual(planned.returncode, 0, planned.stdout + planned.stderr)
        plan = json.loads(planned.stdout)
        mutating = [
            item
            for item in plan["operations"]
            if item["action"]
            in {
                "create-framework",
                "update-framework",
                "create-seed",
                "remove-framework",
            }
        ]
        first_removal = next(
            index
            for index, item in enumerate(mutating, start=1)
            if item["action"] == "remove-framework"
            and item["path"] == "scripts/pact/runtime_exec.py"
        )

        env = os.environ.copy()
        env["PACT_TEST_FAIL_AFTER_REPLACE"] = str(first_removal)
        result = self.run_upgrade("--apply", "--json", env=env)

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertFalse(data["applied"])
        self.assertTrue(data["rolled_back"])
        self.assertTrue(legacy_runtime.is_file())
        self.assertEqual(legacy_runtime.read_bytes(), original_runtime)
        self.assertEqual(
            (self.target / ".pact" / "install.json").read_bytes(),
            original_manifest_bytes,
        )
        self.assertFalse((self.target / ".pact" / "pact.pyz").exists())

    def test_modified_obsolete_runtime_file_is_preserved(self) -> None:
        self.make_legacy_runtime_install(modify_one=True)
        self.write_source(".pact/VERSION", NEXT_VERSION + "\n")

        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)

        local = self.target / "scripts" / "pact" / "README.md"
        self.assertTrue(local.is_file())
        self.assertIn("locally customized", local.read_text(encoding="utf-8"))
        kinds = {notice["kind"] for notice in data["notices"]}
        self.assertIn("obsolete-framework-local-modification", kinds)

        manifest = json.loads(
            (self.target / ".pact" / "install.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("scripts/pact/README.md", manifest["files"])

        doctor = self.run_target("doctor", "--strict")
        self.assertNotIn(
            "framework file modified/corrupt: scripts/pact/README.md",
            doctor.stdout + doctor.stderr,
        )

    def test_locally_modified_legacy_dispatcher_blocks_compact_migration(self) -> None:
        self.make_legacy_runtime_install()
        dispatcher = self.target / "scripts" / "pact" / "pact.py"
        dispatcher.write_text(
            dispatcher.read_text(encoding="utf-8") + "\n# LOCAL DISPATCHER CHANGE\n",
            encoding="utf-8",
        )
        self.write_source(".pact/VERSION", NEXT_VERSION + "\n")

        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertFalse(data["applied"])
        self.assertTrue(
            any(
                conflict["path"] == "scripts/pact/pact.py"
                for conflict in data["conflicts"]
            )
        )
        self.assertFalse((self.target / ".pact" / "pact.pyz").exists())
        self.assertIn(
            "LOCAL DISPATCHER CHANGE",
            dispatcher.read_text(encoding="utf-8"),
        )

    def test_referenced_old_schema_becomes_compatibility_seed(self) -> None:
        manifest = self.scaffold()

        seed_path = self.target / ".agents" / "skills" / "convergence-review.md"
        seed_path.parent.mkdir(parents=True, exist_ok=True)
        seed_path.write_text(
            "# Project convergence guidance\n"
            "Legacy schema reference: .pact/schema/convergence-report.schema.json\n",
            encoding="utf-8",
        )
        import hashlib
        seed_sha = hashlib.sha256(seed_path.read_bytes()).hexdigest()
        manifest["files"][".agents/skills/convergence-review.md"] = {
            "management": "seed",
            "source_path": None,
            "source_sha256": None,
            "installed_sha256": seed_sha,
        }

        relative = ".pact/schema/convergence-report.schema.json"
        source = PROJECT_ROOT / relative
        destination = self.target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

        installed_sha = hashlib.sha256(destination.read_bytes()).hexdigest()
        manifest["files"][relative] = {
            "management": "framework",
            "source_path": relative,
            "source_sha256": installed_sha,
            "installed_sha256": installed_sha,
        }
        (self.target / ".pact" / "install.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

        self.write_source(".pact/VERSION", NEXT_VERSION + "\n")
        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        kinds = {notice["kind"] for notice in data["notices"]}
        self.assertIn("obsolete-schema-referenced-by-project-seed", kinds)

        self.assertTrue(destination.is_file())
        updated_manifest = json.loads(
            (self.target / ".pact" / "install.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            updated_manifest["files"][relative]["management"],
            "seed",
        )

        linted = self.run_target("schema-lint")
        self.assertEqual(linted.returncode, 0, linted.stdout + linted.stderr)

    def test_modified_obsolete_schema_is_preserved_but_embedded_protocol_wins(self) -> None:
        manifest = self.scaffold()

        relative = ".pact/schema/task-contract.schema.json"
        source = PROJECT_ROOT / relative
        destination = self.target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

        import hashlib
        installed_sha = hashlib.sha256(destination.read_bytes()).hexdigest()
        manifest["files"][relative] = {
            "management": "framework",
            "source_path": relative,
            "source_sha256": installed_sha,
            "installed_sha256": installed_sha,
        }
        (self.target / ".pact" / "install.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

        # Simulate a local customization/corruption of an old framework schema.
        destination.write_text("{ definitely-not-valid-json", encoding="utf-8")
        self.write_source(".pact/VERSION", NEXT_VERSION + "\n")

        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        kinds = {notice["kind"] for notice in data["notices"]}
        self.assertIn("obsolete-framework-local-modification", kinds)

        self.assertTrue(destination.is_file())
        updated_manifest = json.loads(
            (self.target / ".pact" / "install.json").read_text(encoding="utf-8")
        )
        self.assertNotIn(relative, updated_manifest["files"])

        # Compact runtime must use its embedded official schema set rather than
        # the preserved obsolete local file.
        linted = self.run_target("schema-lint")
        self.assertEqual(linted.returncode, 0, linted.stdout + linted.stderr)
        self.assertIn("schema file(s) supported", linted.stdout)

        prepared = self.run_target(
            "task",
            "prepare",
            "embedded schema remains authoritative",
            "--success",
            "Task Contract validates",
            "--risk",
            "low",
            "--task-id",
            "TASK-EMBEDDED-AUTHORITY",
            "--json",
        )
        self.assertEqual(
            prepared.returncode,
            0,
            prepared.stdout + prepared.stderr,
        )

    def test_project_toml_seed_is_never_overwritten(self) -> None:
        self.scaffold()

        config = self.target / ".pact" / "config.toml"
        original = config.read_text(encoding="utf-8")
        config.write_text(original + "\n# PROJECT OWNED\n", encoding="utf-8")

        self.write_source(".pact/VERSION", NEXT_VERSION + "\n")
        self.write_source(
            ".pact/config.example.toml",
            'version = 1\n[owner]\nrole = "changed-upstream"\n',
        )

        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("# PROJECT OWNED", config.read_text(encoding="utf-8"))

        data = json.loads(result.stdout)
        kinds = {notice["kind"] for notice in data["notices"]}
        self.assertIn("seed-update-available", kinds)

    def test_legacy_yaml_seed_is_preserved_instead_of_replaced_by_default_toml(self) -> None:
        self.target.mkdir(parents=True)
        legacy = self.target / ".pact" / "config.yaml"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(
            "version: 1\nowner:\n  role: product_project_owner\n",
            encoding="utf-8",
        )

        result = self.run_init("--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(legacy.exists())
        self.assertFalse((self.target / ".pact" / "config.toml").exists())


if __name__ == "__main__":
    unittest.main()
