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
from unittest import mock


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
INIT = PROJECT_ROOT / "scripts" / "pact" / "init.py"
UPGRADE = PROJECT_ROOT / "scripts" / "pact" / "upgrade.py"
SOURCE_VERSION = (PROJECT_ROOT / ".pact" / "VERSION").read_text(
    encoding="utf-8"
).strip()
NEXT_VERSION = "9.9.9-test"

sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "pact"))
import upgrade as upgrade_runtime


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

    def run_init(
        self,
        *args: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INIT), "--target", str(self.target), *args],
            capture_output=True,
            text=True,
            env=env,
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

    def test_mid_init_failure_rolls_back_created_files_and_manifest(self) -> None:
        self.target.mkdir(parents=True)
        existing = self.target / "README.md"
        existing.write_text("# Existing project\n", encoding="utf-8")

        env = os.environ.copy()
        env["PACT_TEST_FAIL_INIT_AFTER_CREATE"] = "3"
        result = self.run_init("--apply", env=env)

        self.assertEqual(result.returncode, 2)
        self.assertIn("rollback was attempted", result.stderr)
        self.assertEqual(
            existing.read_text(encoding="utf-8"),
            "# Existing project\n",
        )
        self.assertFalse((self.target / "pact.py").exists())
        self.assertFalse((self.target / ".pact" / "install.json").exists())
        self.assertFalse((self.target / ".pact" / "pact.pyz").exists())
        self.assertFalse((self.target / "AGENTS.md").exists())

        remaining = sorted(
            path.relative_to(self.target).as_posix()
            for path in self.target.rglob("*")
            if path.is_file()
        )
        self.assertEqual(remaining, ["README.md"])

    def test_reinit_failure_restores_existing_manifest_and_files(self) -> None:
        manifest = self.scaffold()
        original_manifest = (
            self.target / ".pact" / "install.json"
        ).read_bytes()
        existing_agents = self.target / "AGENTS.md"
        original_agents = existing_agents.read_bytes()

        # Create one missing optional framework target to exercise a same-version
        # re-init transaction without changing existing managed files.
        workflow = self.target / ".github" / "workflows" / "pact-project-check.yml"
        env = os.environ.copy()
        env["PACT_TEST_FAIL_INIT_AFTER_CREATE"] = "1"
        result = self.run_init("--apply", "--github-actions", env=env)

        self.assertEqual(result.returncode, 2)
        self.assertFalse(workflow.exists())
        self.assertEqual(
            (self.target / ".pact" / "install.json").read_bytes(),
            original_manifest,
        )
        self.assertEqual(existing_agents.read_bytes(), original_agents)
        after = json.loads(original_manifest)
        self.assertEqual(after, manifest)

    def test_init_records_current_runtime_and_seed_ownership(self) -> None:
        manifest = self.scaffold()
        self.assertEqual(manifest["runtime_version"], SOURCE_VERSION)
        self.assertNotIn("install_profile", manifest)
        self.assertLessEqual(len(manifest["files"]), 9)
        self.assertEqual(
            manifest["files"][".pact/pact.pyz"]["management"],
            "framework",
        )
        self.assertEqual(
            manifest["files"][".pact/LICENSE"]["management"],
            "framework",
        )
        self.assertEqual(
            manifest["files"][".pact/config.toml"]["management"],
            "seed",
        )
        self.assertTrue((self.target / ".pact" / "pact.pyz").is_file())
        self.assertEqual(
            (self.target / ".pact" / "LICENSE").read_bytes(),
            (PROJECT_ROOT / "LICENSE").read_bytes(),
        )
        self.assertFalse((self.target / "LICENSE").exists())
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

    def test_corrupt_install_manifest_blocks_all_surfaces(self) -> None:
        self.scaffold()
        manifest_path = self.target / ".pact" / "install.json"
        manifest_path.write_text("{ not valid json\n", encoding="utf-8")

        reinit = self.run_init("--apply")
        self.assertEqual(reinit.returncode, 2)
        self.assertIn("invalid .pact/install.json", reinit.stderr)

        doctor = self.run_target("doctor", "--strict", "--json")
        self.assertEqual(doctor.returncode, 1)
        self.assertIn("invalid .pact/install.json", doctor.stdout + doctor.stderr)

        status = self.run_target("status", "--strict", "--json")
        self.assertEqual(status.returncode, 1)
        self.assertIn("invalid .pact/install.json", status.stdout + status.stderr)

        version = self.run_target(
            "version",
            "--target",
            str(self.target),
            "--json",
        )
        self.assertEqual(version.returncode, 2)
        self.assertIn("invalid .pact/install.json", version.stderr)

        upgrade = self.run_upgrade("--apply")
        self.assertEqual(upgrade.returncode, 2)
        self.assertIn("invalid .pact/install.json", upgrade.stderr)

    def test_invalid_install_manifest_hash_blocks_all_surfaces(self) -> None:
        manifest = self.scaffold()
        manifest["files"]["pact.py"]["installed_sha256"] = "not-a-sha"
        (self.target / ".pact" / "install.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

        reinit = self.run_init("--apply")
        self.assertEqual(reinit.returncode, 2)
        self.assertIn("invalid installed_sha256", reinit.stderr)

        doctor = self.run_target("doctor", "--strict", "--json")
        self.assertEqual(doctor.returncode, 1)
        self.assertIn("invalid installed_sha256", doctor.stdout + doctor.stderr)

        version = self.run_target(
            "version",
            "--target",
            str(self.target),
            "--json",
        )
        self.assertEqual(version.returncode, 2)
        self.assertIn("invalid installed_sha256", version.stderr)

        upgrade = self.run_upgrade("--apply")
        self.assertEqual(upgrade.returncode, 2)
        self.assertIn("invalid installed_sha256", upgrade.stderr)

    def test_local_framework_modification_conflicts_even_when_upstream_file_is_unchanged(self) -> None:
        self.scaffold()
        root_entry = self.target / "pact.py"
        root_entry.write_text(
            root_entry.read_text(encoding="utf-8")
            + "\n# local framework modification\n",
            encoding="utf-8",
        )

        self.change_runtime_source()
        result = self.run_upgrade("--apply", "--json")

        self.assertEqual(result.returncode, 1)
        data = json.loads(result.stdout)
        conflict_paths = {item["path"] for item in data["conflicts"]}
        self.assertIn("pact.py", conflict_paths)
        self.assertIn(
            "local framework modification",
            root_entry.read_text(encoding="utf-8"),
        )

    def test_unsafe_install_manifest_path_is_rejected(self) -> None:
        manifest = self.scaffold()
        manifest["files"]["../../outside"] = {
            "management": "framework",
            "source_path": "pact.py",
            "source_sha256": "0" * 64,
            "installed_sha256": "0" * 64,
        }
        (self.target / ".pact" / "install.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        reinit = self.run_init("--apply")
        self.assertEqual(reinit.returncode, 2)
        self.assertIn("unsafe tracked path", reinit.stderr)

        doctor = self.run_target("doctor", "--strict", "--json")
        self.assertEqual(doctor.returncode, 1)
        self.assertIn("unsafe tracked path", doctor.stdout + doctor.stderr)

        status = self.run_target("status", "--strict", "--json")
        self.assertEqual(status.returncode, 1)
        self.assertIn("unsafe tracked path", status.stdout + status.stderr)

        version = self.run_target(
            "version",
            "--target",
            str(self.target),
            "--json",
        )
        self.assertEqual(version.returncode, 2)
        self.assertIn("unsafe tracked path", version.stderr)

        upgrade = self.run_upgrade("--apply")
        self.assertEqual(upgrade.returncode, 2)
        self.assertIn("unsafe tracked path", upgrade.stderr)

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

    def test_stale_upgrade_plan_refuses_changed_framework_target(self) -> None:
        manifest = self.scaffold()
        self.change_runtime_source()
        plan = upgrade_runtime.plan_upgrade(self.new_source, self.target, manifest)
        target_file = self.target / ".pact" / "pact.pyz"
        self.assertTrue(any(
            item["action"] == "update-framework"
            and item["path"] == ".pact/pact.pyz"
            for item in plan["operations"]
        ))
        user_content = target_file.read_bytes() + b"\nUSER-WORKTREE-EDIT\n"
        target_file.write_bytes(user_content)
        manifest_file = self.target / ".pact" / "install.json"
        original_manifest = manifest_file.read_bytes()

        with self.assertRaises(upgrade_runtime.UpgradeApplyError):
            upgrade_runtime.apply_upgrade(
                self.new_source, self.target, manifest, plan
            )

        self.assertEqual(target_file.read_bytes(), user_content)
        self.assertEqual(manifest_file.read_bytes(), original_manifest)

    def test_stale_upgrade_plan_refuses_create_over_new_user_file(self) -> None:
        manifest = self.scaffold()
        target_file = self.target / ".pact" / "LICENSE"
        target_file.unlink()
        self.change_runtime_source()
        plan = upgrade_runtime.plan_upgrade(self.new_source, self.target, manifest)
        self.assertTrue(any(
            item["action"] == "create-framework"
            and item["path"] == ".pact/LICENSE"
            for item in plan["operations"]
        ))
        target_file.write_text("NEW USER FILE - MUST NOT OVERWRITE\n", encoding="utf-8")
        manifest_file = self.target / ".pact" / "install.json"
        original_manifest = manifest_file.read_bytes()

        with self.assertRaises(upgrade_runtime.UpgradeApplyError):
            upgrade_runtime.apply_upgrade(
                self.new_source, self.target, manifest, plan
            )

        self.assertEqual(target_file.read_text(encoding="utf-8"), "NEW USER FILE - MUST NOT OVERWRITE\n")
        self.assertEqual(manifest_file.read_bytes(), original_manifest)

    def test_stale_upgrade_plan_refuses_remove_after_local_edit(self) -> None:
        manifest = self.scaffold()
        obsolete = self.add_tracked_obsolete_framework(manifest)
        plan = upgrade_runtime.plan_upgrade(self.new_source, self.target, manifest)
        self.assertTrue(any(
            item["action"] == "remove-framework"
            and item["path"] == ".pact/obsolete-framework.txt"
            and not item.get("already_absent")
            for item in plan["operations"]
        ))
        original_manifest = (self.target / ".pact" / "install.json").read_bytes()
        obsolete.write_text("AN OWNER EDIT AFTER PLAN\n", encoding="utf-8")
        with self.assertRaises(upgrade_runtime.UpgradeApplyError):
            upgrade_runtime.apply_upgrade(
                self.new_source, self.target, manifest, plan
            )
        self.assertEqual(obsolete.read_text(encoding="utf-8"), "AN OWNER EDIT AFTER PLAN\n")
        self.assertEqual(
            (self.target / ".pact" / "install.json").read_bytes(),
            original_manifest,
        )

    def test_stale_refresh_plan_refuses_adopting_modified_target(self) -> None:
        manifest = self.scaffold()
        plan = upgrade_runtime.plan_upgrade(self.new_source, self.target, manifest)
        self.assertTrue(any(
            item["action"] == "refresh-manifest"
            and item["path"] == ".pact/LICENSE"
            for item in plan["operations"]
        ))
        target_file = self.target / ".pact" / "LICENSE"
        target_file.write_text("UNTRACKED OWNER CONTENT\n", encoding="utf-8")
        manifest_file = self.target / ".pact" / "install.json"
        before = manifest_file.read_bytes()
        with self.assertRaises(upgrade_runtime.UpgradeApplyError):
            upgrade_runtime.apply_upgrade(
                self.new_source, self.target, manifest, plan
            )
        self.assertEqual(target_file.read_text(encoding="utf-8"), "UNTRACKED OWNER CONTENT\n")
        self.assertEqual(manifest_file.read_bytes(), before)

    def test_stale_apply_refuses_modified_install_manifest(self) -> None:
        manifest = self.scaffold()
        self.change_runtime_source()
        plan = upgrade_runtime.plan_upgrade(self.new_source, self.target, manifest)
        disk_path = self.target / ".pact" / "install.json"
        edited = json.loads(disk_path.read_text(encoding="utf-8"))
        edited["runtime_version"] = "OWNER-EDITED-RUNTIME"
        disk_path.write_text(json.dumps(edited, indent=2) + "\n", encoding="utf-8")
        before = disk_path.read_bytes()
        version_before = (self.target / ".pact" / "VERSION").read_bytes()
        with self.assertRaises(upgrade_runtime.UpgradeApplyError):
            upgrade_runtime.apply_upgrade(
                self.new_source, self.target, manifest, plan
            )
        self.assertEqual(disk_path.read_bytes(), before)
        self.assertEqual((self.target / ".pact" / "VERSION").read_bytes(), version_before)

    def test_stale_plan_does_not_overwrite_new_seed(self) -> None:
        manifest = self.scaffold()
        config = self.target / ".pact" / "config.toml"
        self.assertTrue(config.is_file())
        config.unlink()
        plan = upgrade_runtime.plan_upgrade(self.new_source, self.target, manifest)
        self.assertTrue(any(
            item["action"] == "create-seed"
            and item["path"] == ".pact/config.toml"
            for item in plan["operations"]
        ))
        config.write_text("owner created this file after planning\n", encoding="utf-8")
        before = (self.target / ".pact" / "install.json").read_bytes()
        with self.assertRaises(upgrade_runtime.UpgradeApplyError):
            upgrade_runtime.apply_upgrade(
                self.new_source, self.target, manifest, plan
            )
        self.assertEqual(
            config.read_text(encoding="utf-8"),
            "owner created this file after planning\n",
        )
        self.assertEqual((self.target / ".pact" / "install.json").read_bytes(), before)

    def test_stale_already_absent_obsolete_path_does_not_delete_new_file(self) -> None:
        manifest = self.scaffold()
        old = self.add_tracked_obsolete_framework(manifest)
        old.unlink()
        plan = upgrade_runtime.plan_upgrade(self.new_source, self.target, manifest)
        self.assertTrue(any(
            item["action"] == "remove-framework"
            and item["path"] == ".pact/obsolete-framework.txt"
            and item.get("already_absent")
            for item in plan["operations"]
        ))
        old.write_text("OWNER RECREATED THIS FILE\n", encoding="utf-8")
        before = (self.target / ".pact" / "install.json").read_bytes()
        with self.assertRaises(upgrade_runtime.UpgradeApplyError):
            upgrade_runtime.apply_upgrade(
                self.new_source, self.target, manifest, plan
            )
        self.assertEqual(old.read_text(encoding="utf-8"), "OWNER RECREATED THIS FILE\n")
        self.assertEqual((self.target / ".pact" / "install.json").read_bytes(), before)

    def test_install_manifest_edit_after_backup_is_not_rolled_back_over_owner(self) -> None:
        manifest = self.scaffold()
        self.change_runtime_source()
        plan = upgrade_runtime.plan_upgrade(self.new_source, self.target, manifest)
        manifest_path = self.target / ".pact" / "install.json"
        original_copy = upgrade_runtime.shutil.copy2
        injected = {"done": False}

        def backup_then_edit(source, destination, *args, **kwargs):
            result = original_copy(source, destination, *args, **kwargs)
            if (
                not injected["done"]
                and pathlib.Path(source) == manifest_path
                and "backup" in pathlib.Path(destination).parts
            ):
                changed = json.loads(manifest_path.read_text(encoding="utf-8"))
                changed["runtime_version"] = "OWNER-CHANGED-DURING-BACKUP"
                manifest_path.write_text(
                    json.dumps(changed, indent=2) + "\n", encoding="utf-8"
                )
                injected["done"] = True
            return result

        with mock.patch.object(
            upgrade_runtime.shutil, "copy2", side_effect=backup_then_edit
        ):
            with self.assertRaises(upgrade_runtime.UpgradeApplyError):
                upgrade_runtime.apply_upgrade(
                    self.new_source, self.target, manifest, plan
                )
        self.assertTrue(injected["done"])
        self.assertEqual(
            json.loads(manifest_path.read_text(encoding="utf-8"))["runtime_version"],
            "OWNER-CHANGED-DURING-BACKUP",
        )
        self.assertNotEqual(
            (self.target / ".pact" / "VERSION").read_text(encoding="utf-8").strip(),
            NEXT_VERSION,
        )

    def test_stale_source_change_stays_rejected_before_target_mutation(self) -> None:
        manifest = self.scaffold()
        self.change_runtime_source()
        plan = upgrade_runtime.plan_upgrade(self.new_source, self.target, manifest)
        version_source = self.new_source / ".pact" / "VERSION"
        version_source.write_text("9.9.8-CHANGED-AFTER-PLAN\n", encoding="utf-8")
        version_before = (self.target / ".pact" / "VERSION").read_bytes()
        manifest_before = (self.target / ".pact" / "install.json").read_bytes()
        with self.assertRaises(upgrade_runtime.UpgradeApplyError):
            upgrade_runtime.apply_upgrade(
                self.new_source, self.target, manifest, plan
            )
        self.assertEqual((self.target / ".pact" / "VERSION").read_bytes(), version_before)
        self.assertEqual((self.target / ".pact" / "install.json").read_bytes(), manifest_before)

    def test_rollback_does_not_overwrite_file_edited_after_replacement(self) -> None:
        manifest = self.scaffold()
        self.change_runtime_source()
        plan = upgrade_runtime.plan_upgrade(self.new_source, self.target, manifest)
        changed_path = self.target / ".pact" / "VERSION"
        user_edit = b"USER EDIT AFTER UPGRADE REPLACEMENT\n"
        original_manifest = (self.target / ".pact" / "install.json").read_bytes()
        original_replace = upgrade_runtime.os.replace
        modified = {"done": False}

        def replace_then_external_edit(source, destination, *args, **kwargs):
            result = original_replace(source, destination, *args, **kwargs)
            if (
                not modified["done"]
                and pathlib.Path(destination) == changed_path
                and pathlib.Path(source).name.startswith(".VERSION.pact-upgrade-")
                and pathlib.Path(source).name.endswith(".tmp")
            ):
                changed_path.write_bytes(user_edit)
                modified["done"] = True
            return result

        with mock.patch.dict(
            os.environ, {"PACT_TEST_FAIL_AFTER_REPLACE": "1"}
        ), mock.patch.object(
            upgrade_runtime.os, "replace", side_effect=replace_then_external_edit
        ):
            with self.assertRaises(upgrade_runtime.UpgradeApplyError) as raised:
                upgrade_runtime.apply_upgrade(
                    self.new_source, self.target, manifest, plan
                )
        self.assertTrue(modified["done"], "post-replace edit injection did not fire")
        self.assertFalse(
            raised.exception.rolled_back,
            "concurrent user edit must prevent claiming successful full rollback",
        )
        self.assertEqual(changed_path.read_bytes(), user_edit)
        self.assertEqual(
            (self.target / ".pact" / "install.json").read_bytes(),
            original_manifest,
        )

    def test_source_removed_during_staging_fails_without_unhandled_error(self) -> None:
        manifest = self.scaffold()
        self.change_runtime_source()
        plan = upgrade_runtime.plan_upgrade(self.new_source, self.target, manifest)
        source = self.new_source / ".pact" / "VERSION"
        old_version = (self.target / ".pact" / "VERSION").read_bytes()
        old_manifest = (self.target / ".pact" / "install.json").read_bytes()
        original_copy = upgrade_runtime.shutil.copy2
        injected = {"done": False}

        def disappear_during_stage(src, dst, *args, **kwargs):
            if (
                not injected["done"]
                and pathlib.Path(src) == source
                and "stage" in pathlib.Path(dst).parts
            ):
                source.unlink()
                injected["done"] = True
            return original_copy(src, dst, *args, **kwargs)

        with mock.patch.object(
            upgrade_runtime.shutil, "copy2", side_effect=disappear_during_stage
        ):
            with self.assertRaises(upgrade_runtime.UpgradeApplyError) as raised:
                upgrade_runtime.apply_upgrade(
                    self.new_source, self.target, manifest, plan
                )
        self.assertTrue(injected["done"])
        self.assertFalse(raised.exception.rolled_back)
        self.assertEqual((self.target / ".pact" / "VERSION").read_bytes(), old_version)
        self.assertEqual(
            (self.target / ".pact" / "install.json").read_bytes(), old_manifest
        )

    def test_target_removed_during_backup_fails_without_unhandled_error(self) -> None:
        manifest = self.scaffold()
        self.change_runtime_source()
        plan = upgrade_runtime.plan_upgrade(self.new_source, self.target, manifest)
        destination = self.target / ".pact" / "VERSION"
        old_manifest = (self.target / ".pact" / "install.json").read_bytes()
        original_copy = upgrade_runtime.shutil.copy2
        injected = {"done": False}

        def disappear_during_backup(src, dst, *args, **kwargs):
            if (
                not injected["done"]
                and pathlib.Path(src) == destination
                and "backup" in pathlib.Path(dst).parts
            ):
                destination.unlink()
                injected["done"] = True
            return original_copy(src, dst, *args, **kwargs)

        with mock.patch.object(
            upgrade_runtime.shutil, "copy2", side_effect=disappear_during_backup
        ):
            with self.assertRaises(upgrade_runtime.UpgradeApplyError) as raised:
                upgrade_runtime.apply_upgrade(
                    self.new_source, self.target, manifest, plan
                )
        self.assertTrue(injected["done"])
        self.assertFalse(raised.exception.rolled_back)
        self.assertFalse(destination.exists(), "foreign removal must be preserved")
        self.assertEqual(
            (self.target / ".pact" / "install.json").read_bytes(), old_manifest
        )

    def test_late_target_edit_after_backup_is_not_overwritten(self) -> None:
        manifest = self.scaffold()
        self.change_runtime_source()
        plan = upgrade_runtime.plan_upgrade(self.new_source, self.target, manifest)
        victim = self.target / ".pact" / "VERSION"
        original_manifest = (self.target / ".pact" / "install.json").read_bytes()
        concurrent = b"EDITED-BETWEEN-BACKUP-AND-REPLACE\n"
        original_copy = upgrade_runtime.shutil.copy2
        injected = {"done": False}

        def copy_and_inject(source, destination, *args, **kwargs):
            result = original_copy(source, destination, *args, **kwargs)
            if (
                not injected["done"]
                and pathlib.Path(source) == victim
                and "backup" in pathlib.Path(destination).parts
            ):
                victim.write_bytes(concurrent)
                injected["done"] = True
            return result

        with mock.patch.object(upgrade_runtime.shutil, "copy2", side_effect=copy_and_inject):
            with self.assertRaises(upgrade_runtime.UpgradeApplyError):
                upgrade_runtime.apply_upgrade(
                    self.new_source, self.target, manifest, plan
                )

        self.assertTrue(injected["done"], "race injection did not fire")
        self.assertEqual(victim.read_bytes(), concurrent)
        self.assertEqual(
            (self.target / ".pact" / "install.json").read_bytes(),
            original_manifest,
        )

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

    def test_init_preserves_host_license_and_installs_pact_license(self) -> None:
        self.target.mkdir(parents=True)
        host_license = self.target / "LICENSE"
        host_license.write_text("Host project license\n", encoding="utf-8")

        manifest = self.scaffold()

        self.assertEqual(
            host_license.read_text(encoding="utf-8"),
            "Host project license\n",
        )
        pact_license = self.target / ".pact" / "LICENSE"
        self.assertEqual(
            pact_license.read_bytes(),
            (PROJECT_ROOT / "LICENSE").read_bytes(),
        )
        record = manifest["files"][".pact/LICENSE"]
        self.assertEqual(record["management"], "framework")
        self.assertEqual(record["source_path"], "LICENSE")
        self.assertEqual(
            record["installed_sha256"],
            hashlib.sha256(pact_license.read_bytes()).hexdigest(),
        )

    def test_upgrade_updates_framework_managed_pact_license(self) -> None:
        self.scaffold()
        original = (self.target / ".pact" / "LICENSE").read_text(encoding="utf-8")

        self.change_runtime_source()
        changed = original + "\n# test-only upstream license payload change\n"
        self.write_source("LICENSE", changed)

        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            (self.target / ".pact" / "LICENSE").read_text(encoding="utf-8"),
            changed,
        )
        manifest = json.loads(
            (self.target / ".pact" / "install.json").read_text(encoding="utf-8")
        )
        # A source file's bytes, not text re-encoded from read_text(), are
        # the package/manifest authority. On Windows write_text() can emit
        # CRLF, so hashing changed.encode() can incorrectly expect LF bytes.
        source_bytes = (self.new_source / "LICENSE").read_bytes()
        installed_bytes = (self.target / ".pact" / "LICENSE").read_bytes()
        self.assertEqual(installed_bytes, source_bytes)
        self.assertEqual(
            manifest["files"][".pact/LICENSE"]["installed_sha256"],
            hashlib.sha256(source_bytes).hexdigest(),
        )
        self.assertEqual(
            manifest["files"][".pact/LICENSE"]["source_sha256"],
            hashlib.sha256(source_bytes).hexdigest(),
        )

    def test_upgrade_license_preserves_explicit_crlf_source_bytes(self) -> None:
        self.scaffold()
        self.change_runtime_source()
        crlf_bytes = b"PACT test-only license fixture\r\nSecond line\r\n"

        (self.new_source / "LICENSE").write_bytes(crlf_bytes)

        result = self.run_upgrade("--apply", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        installed = (self.target / ".pact" / "LICENSE").read_bytes()
        self.assertEqual(installed, crlf_bytes)
        manifest = json.loads(
            (self.target / ".pact" / "install.json").read_text(encoding="utf-8")
        )
        digest = hashlib.sha256(crlf_bytes).hexdigest()
        self.assertEqual(
            manifest["files"][".pact/LICENSE"]["installed_sha256"], digest
        )
        self.assertEqual(
            manifest["files"][".pact/LICENSE"]["source_sha256"], digest
        )

    def test_manifest_parent_symlink_escape_is_rejected_everywhere(self) -> None:
        manifest = self.scaffold()
        outside_dir = self.root / "outside-framework"
        outside_dir.mkdir()
        outside_file = outside_dir / "framework.txt"
        outside_file.write_text("outside framework\n", encoding="utf-8")
        digest = hashlib.sha256(outside_file.read_bytes()).hexdigest()

        linked = self.target / "linked-framework"
        try:
            os.symlink(outside_dir, linked, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")

        manifest["files"]["linked-framework/framework.txt"] = {
            "management": "framework",
            "source_path": "pact.py",
            "source_sha256": digest,
            "installed_sha256": digest,
        }
        (self.target / ".pact" / "install.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

        doctor = self.run_target("doctor", "--strict", "--json")
        self.assertEqual(doctor.returncode, 1)
        self.assertIn("escapes repository through symlink", doctor.stdout + doctor.stderr)

        version = self.run_target(
            "version",
            "--target",
            str(self.target),
            "--json",
        )
        self.assertEqual(version.returncode, 2)
        self.assertIn("escapes repository through symlink", version.stderr)

        upgrade = self.run_upgrade("--apply")
        self.assertEqual(upgrade.returncode, 2)
        self.assertIn("escapes repository through symlink", upgrade.stderr)

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

    def test_symlinked_install_manifest_is_rejected_by_reinit_and_upgrade(self) -> None:
        self.scaffold()
        manifest_path = self.target / ".pact" / "install.json"
        outside = self.root / "outside-install.json"
        outside.write_bytes(manifest_path.read_bytes())
        manifest_path.unlink()
        try:
            os.symlink(outside, manifest_path)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")

        original = outside.read_bytes()

        reinit = self.run_init("--apply")
        self.assertEqual(reinit.returncode, 2)
        self.assertIn(".pact/install.json", reinit.stderr)
        self.assertIn("must not be a symlink", reinit.stderr)
        self.assertTrue(manifest_path.is_symlink())
        self.assertEqual(outside.read_bytes(), original)

        doctor = self.run_target("doctor", "--strict", "--json")
        self.assertEqual(doctor.returncode, 1)
        self.assertIn("install.json", doctor.stdout + doctor.stderr)
        self.assertIn("symlink", doctor.stdout + doctor.stderr)

        version = self.run_target(
            "version",
            "--target",
            str(self.target),
            "--json",
        )
        self.assertEqual(version.returncode, 2)
        self.assertIn("install.json", version.stderr)
        self.assertIn("symlink", version.stderr)

        upgrade = self.run_upgrade("--apply")
        self.assertEqual(upgrade.returncode, 2)
        self.assertIn("install.json", upgrade.stderr)
        self.assertIn("symlink", upgrade.stderr)
        self.assertTrue(manifest_path.is_symlink())
        self.assertEqual(outside.read_bytes(), original)

    def test_upgrade_plan_rejects_framework_leaf_symlink(self) -> None:
        self.scaffold()
        framework = self.target / "pact.py"
        outside = self.root / "outside-pact.py"
        outside.write_bytes(framework.read_bytes())
        framework.unlink()
        try:
            os.symlink(outside, framework)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")

        original = outside.read_bytes()
        result = self.run_upgrade("--apply")

        self.assertEqual(result.returncode, 2)
        self.assertIn("tracked path is a symlink: 'pact.py'", result.stderr)
        self.assertTrue(framework.is_symlink())
        self.assertEqual(outside.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
