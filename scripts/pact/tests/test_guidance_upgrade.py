"""Guidance upgrades preserve project authority and expose legacy entry gaps."""
from __future__ import annotations

import hashlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib
from contextlib import redirect_stdout
from unittest import mock


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "pact"))
import guidance
import upgrade
from runtime_bundle import ensure_runtime_bundle


class GuidanceUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory(prefix="pact-guidance-upgrade-"))
        self.root = pathlib.Path(self.temp)
        self.target = self.root / "project"
        self.source = self.root / "source"
        # Only the real distribution inputs are needed; no copied Git history,
        # project evidence, release downloads, or test suite in the fixture.
        runtime = self.source / "scripts" / "pact"
        runtime.mkdir(parents=True)
        for path in (PROJECT_ROOT / "scripts" / "pact").glob("*.py"):
            shutil.copy2(path, runtime / path.name)
        for relative in ("pact.py", "LICENSE", ".pact/VERSION",
                         ".pact/config.example.toml", ".pact/baseline.example.toml",
                         ".pact/fitness.example.toml"):
            destination = self.source / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJECT_ROOT / relative, destination)
        for relative in (".pact/schema", ".pact/templates"):
            shutil.copytree(PROJECT_ROOT / relative, self.source / relative)
        self.bundle = ensure_runtime_bundle(self.source)

    def command(self, script, *args, cwd=None):
        result = subprocess.run(
            [sys.executable, str(script), *args], cwd=cwd,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def init(self):
        return self.command(PROJECT_ROOT / "scripts/pact/init.py",
                            "--target", str(self.target), "--apply", "--json")

    def plan(self, *, apply=False):
        args = ["--target", str(self.target), "--source", str(self.source), "--json"]
        if apply:
            args.append("--apply")
        result = self.command(PROJECT_ROOT / "scripts/pact/upgrade.py", *args)
        return json.loads(result.stdout)

    def test_fresh_entry_stays_short_and_reinit_does_not_create_bootstrap(self):
        self.init()
        entry = self.target / "AGENTS.md"
        original = entry.read_bytes()
        self.assertEqual(original.decode("utf-8"), guidance.minimal_project_entry())
        self.assertLess(len(original), len(guidance.STANDARD_GUIDANCE.encode("utf-8")))
        self.assertTrue(guidance.entry_reference_present(original.decode("utf-8")))
        self.init()
        self.assertEqual(entry.read_bytes(), original)
        self.assertFalse((self.target / ".pact/AGENT_BOOTSTRAP.md").exists())
        self.assertFalse(any(n["kind"] == "agent-guidance-review" for n in self.plan()["notices"]))

    def test_existing_project_and_bootstrap_survive_repeat_init(self):
        self.target.mkdir()
        entry = self.target / "AGENTS.md"
        entry.write_text("# 项目规定\nUse our existing business manual.\n", encoding="utf-8")
        original = entry.read_bytes()
        self.init()
        bootstrap = self.target / ".pact/AGENT_BOOTSTRAP.md"
        initial_bootstrap = bootstrap.read_bytes()
        self.assertIn("pact.py guidance", initial_bootstrap.decode("utf-8"))
        self.init()
        self.assertEqual(entry.read_bytes(), original)
        self.assertEqual(bootstrap.read_bytes(), initial_bootstrap)
        notices = [n for n in self.plan()["notices"] if n["kind"] == "agent-guidance-review"]
        self.assertEqual(len(notices), 1)
        self.assertIn("indirect routing may already be valid", notices[0]["reason"])

    def test_legacy_generated_seeds_get_review_without_rewriting_project_files(self):
        self.init()
        entry = self.target / "AGENTS.md"
        # Legacy generated entries have no source hash, just as in real installs.
        manifest = json.loads((self.target / ".pact/install.json").read_text(encoding="utf-8"))
        self.assertIsNone(manifest["files"]["AGENTS.md"]["source_sha256"])
        files = {
            entry: "# Old generated guide\nPreserve confirmed Product Truth.\n",
            self.target / ".pact/AGENT_BOOTSTRAP.md": "# Old bootstrap\nKeep custom routing.\n",
            self.target / ".pact/README.md": "# 项目操作\nUse backend/venv/bin/python.\n",
        }
        for path, text in files.items():
            path.write_text(text, encoding="utf-8")
        original = {path: path.read_bytes() for path in files}
        self._change_source_guidance()
        result = self.plan(apply=True)
        self.assertTrue(result["applied"])
        self.assertEqual(len([n for n in result["notices"] if n["kind"] == "agent-guidance-review"]), 1)
        for path, content in original.items():
            self.assertEqual(path.read_bytes(), content)
        # Still-unresolved routing remains visible rather than being silently
        # acknowledged in an editable registry or an invented acceptance state.
        self.assertTrue(any(n["kind"] == "agent-guidance-review" for n in self.plan()["notices"]))

    def _change_source_guidance(self):
        path = self.source / "scripts/pact/guidance.py"
        path.write_text(path.read_text(encoding="utf-8")
                        + '\nSTANDARD_GUIDANCE += "\\nVersion-matched upgrade marker.\\n"\n',
                        encoding="utf-8")
        (self.source / ".pact/VERSION").write_text("9.9.9-guidance-test\n", encoding="utf-8")

    def test_upgraded_runtime_supplies_new_guidance_without_entry_changes(self):
        self.init()
        entry = self.target / "AGENTS.md"
        original = entry.read_bytes()
        self._change_source_guidance()
        first = self.plan(apply=True)
        self.assertFalse(any(n["kind"] == "agent-guidance-review" for n in first["notices"]))
        self.assertEqual(entry.read_bytes(), original)
        # A leftover Markdown copy cannot override the runtime's standard text.
        (self.target / ".pact/guidance.md").write_text("Stale copied guide", encoding="utf-8")
        read = self.command(self.target / "pact.py", "guidance", "--json", cwd=self.target)
        data = json.loads(read.stdout)
        self.assertIn("Version-matched upgrade marker.", data["content"])
        self.assertNotIn("Stale copied guide", data["content"])
        self.assertEqual(data["runtime"]["version"], "9.9.9-guidance-test")
        self.assertEqual(data["content_sha256"], hashlib.sha256(data["content"].encode("utf-8")).hexdigest())
        second = self.plan(apply=True)
        self.assertEqual(second["replaced_files"], 0)
        self.assertEqual(second["created_files"], 0)
        self.assertEqual(entry.read_bytes(), original)
        self.assertFalse((self.target / ".pact/AGENT_BOOTSTRAP.md").exists())

    def test_custom_interpreter_reference_does_not_require_a_new_overlay(self):
        self.target.mkdir()
        entry = self.target / "AGENTS.md"
        entry.write_text("Read this once per new session:\n`backend/venv/bin/python pact.py guidance`\n",
                         encoding="utf-8")
        self.init()
        self.assertFalse((self.target / ".pact/AGENT_BOOTSTRAP.md").exists())
        self.assertFalse(any(n["kind"] == "agent-guidance-review" for n in self.plan()["notices"]))

    def test_old_source_without_registered_command_does_not_recommend_guidance(self):
        self.init()
        (self.target / "AGENTS.md").write_text("Old project entry\n", encoding="utf-8")
        dispatcher = self.source / "scripts/pact/pact.py"
        dispatcher.write_text(dispatcher.read_text(encoding="utf-8").replace(
            '    "guidance": "guidance",\n', ""), encoding="utf-8")
        self.assertFalse(upgrade._runtime_has_guidance(ensure_runtime_bundle(self.source)))
        self.assertFalse(any(n["kind"] == "agent-guidance-review" for n in self.plan()["notices"]))

    def test_concurrent_project_entry_edit_is_preserved_without_blocking_upgrade(self):
        self.init()
        self._change_source_guidance()
        manifest = upgrade.load_manifest(self.target)
        plan = upgrade.plan_upgrade(self.source, self.target, manifest)
        self.assertFalse(any(n["kind"] == "agent-guidance-review" for n in plan["notices"]))
        entry = self.target / "AGENTS.md"
        concurrent = "# Concurrent project policy\nUse the existing indirect router.\n"
        entry.write_text(concurrent, encoding="utf-8")
        self.assertTrue(any(n["kind"] == "agent-guidance-review"
                            for n in upgrade.plan_upgrade(self.source, self.target, manifest)["notices"]))
        result = upgrade.apply_upgrade(self.source, self.target, manifest, plan)
        self.assertGreater(result["replaced_files"], 0)
        self.assertEqual(entry.read_text(encoding="utf-8"), concurrent)

    def test_successful_apply_reports_current_advisory_after_concurrent_entry_edit(self):
        self._change_source_guidance()
        real_apply = upgrade.apply_upgrade
        for was_present in (False, True):
            with self.subTest(initial_reference=was_present):
                self.target = self.root / f"concurrent-main-{was_present}"
                self.init()
                entry = self.target / "AGENTS.md"
                if not was_present:
                    entry.write_text("# Existing indirect project router\n", encoding="utf-8")
                replacement = ("# Concurrent project router\n" if was_present
                               else guidance.minimal_project_entry())

                def edit_while_applying(*args, **kwargs):
                    entry.write_text(replacement, encoding="utf-8")
                    return real_apply(*args, **kwargs)

                output = io.StringIO()
                with mock.patch.object(sys, "argv", [
                    "upgrade", "--target", str(self.target), "--source", str(self.source),
                    "--apply", "--json",
                ]), mock.patch.object(upgrade, "apply_upgrade", side_effect=edit_while_applying), \
                        redirect_stdout(output):
                    self.assertEqual(upgrade.main(), 0)
                data = json.loads(output.getvalue())
                self.assertTrue(data["applied"])
                self.assertEqual(any(n["kind"] == "agent-guidance-review" for n in data["notices"]),
                                 was_present)
                self.assertEqual(entry.read_text(encoding="utf-8"), replacement)

    def test_compact_source_uses_actual_archive_not_leftover_scripts(self):
        for supports_guidance in (True, False):
            with self.subTest(supports_guidance=supports_guidance):
                self.target = self.root / f"compact-target-{supports_guidance}"
                self.init()
                (self.target / "AGENTS.md").write_text("# Legacy project router\n", encoding="utf-8")
                compact = self.root / f"compact-source-{supports_guidance}"
                shutil.copytree(self.source, compact)
                shutil.rmtree(compact / "scripts")
                selected_bundle = compact / ".pact/pact.pyz"
                if supports_guidance:
                    shutil.copy2(self.bundle, selected_bundle)
                else:
                    # This archive deliberately lacks the command declaration,
                    # even though stray new source files below advertise it.
                    with zipfile.ZipFile(self.bundle) as old, zipfile.ZipFile(selected_bundle, "w") as new:
                        for name in old.namelist():
                            content = old.read(name)
                            if name == "pact.py":
                                content = content.replace(b'    "guidance": "guidance",\n', b"")
                            new.writestr(name, content)
                    stray = compact / "scripts/pact"
                    stray.mkdir(parents=True)
                    for name in ("pact.py", "guidance.py"):
                        shutil.copy2(PROJECT_ROOT / "scripts/pact" / name, stray / name)
                manifest = upgrade.load_manifest(self.target)
                with mock.patch.object(upgrade, "agent_guidance_notices",
                                       wraps=upgrade.agent_guidance_notices) as notice:
                    plan = upgrade.plan_upgrade(compact, self.target, manifest)
                self.assertEqual(pathlib.Path(notice.call_args.args[0]).resolve(), selected_bundle.resolve())
                self.assertEqual(any(n["kind"] == "agent-guidance-review" for n in plan["notices"]),
                                 supports_guidance)

    def test_runtime_capability_read_is_bounded_and_never_executes_code(self):
        path = self.root / "capabilities.pyz"
        dispatcher = 'raise RuntimeError("must never execute")\nCOMMANDS = {"guidance": "guidance"}\n'
        for module in (b"pass\n", b"x" * (upgrade.GUIDANCE_READ_LIMIT + 1)):
            with self.subTest(size=len(module)):
                with zipfile.ZipFile(path, "w") as archive:
                    archive.writestr("pact.py", dispatcher)
                    archive.writestr("guidance.py", module)
                self.assertEqual(upgrade._runtime_has_guidance(path), len(module) < upgrade.GUIDANCE_READ_LIMIT)
        path.write_bytes(b"not a ZIP archive")
        self.assertFalse(upgrade._runtime_has_guidance(path))

    def test_corrupt_compressed_dispatcher_only_disables_advisory(self):
        path = self.root / "corrupt-compressed.pyz"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("guidance.py", "pass\n")
            archive.writestr("pact.py", 'COMMANDS = {"guidance": "guidance"}\n')
            header = archive.getinfo("pact.py").header_offset
        data = bytearray(path.read_bytes())
        name_size = int.from_bytes(data[header + 26:header + 28], "little")
        extra_size = int.from_bytes(data[header + 28:header + 30], "little")
        payload = header + 30 + name_size + extra_size
        # DEFLATE BTYPE=3 is invalid. Corrupt the stream itself rather than the
        # ZIP directory, so this exercises decompression's distinct exception.
        data[payload] = (data[payload] & ~7) | 7
        path.write_bytes(data)
        with zipfile.ZipFile(path) as archive:
            with self.assertRaises(zlib.error):
                archive.read("pact.py")
        self.assertFalse(upgrade._runtime_has_guidance(path))

    def test_unreadable_non_regular_or_large_entry_only_requires_review(self):
        self.target.mkdir()
        entry = self.target / "AGENTS.md"
        for data in (b"\xff", b"x" * (upgrade.GUIDANCE_READ_LIMIT + 1)):
            with self.subTest(size=len(data)):
                entry.write_bytes(data)
                notices = upgrade.agent_guidance_notices(self.bundle, self.target)
                self.assertEqual(len(notices), 1)
                self.assertEqual(notices[0]["kind"], "agent-guidance-review")
        entry.unlink()
        entry.mkdir()
        self.assertEqual(len(upgrade.agent_guidance_notices(self.bundle, self.target)), 1)
        entry.rmdir()
        entry.write_text("Restricted project entry\n", encoding="utf-8")
        with mock.patch.object(pathlib.Path, "open", side_effect=PermissionError("restricted")):
            text, problem = upgrade._guidance_entry_text(self.target)
            self.assertIsNone(text)
            self.assertIsNotNone(problem)

    def test_symlinked_entry_is_not_followed_or_rewritten(self):
        self.target.mkdir()
        outside = self.root / "outside.md"
        outside.write_text(guidance.minimal_project_entry(), encoding="utf-8")
        entry = self.target / "AGENTS.md"
        try:
            entry.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        text, problem = upgrade._guidance_entry_text(self.target)
        self.assertIsNone(text)
        self.assertIn("symbolic", problem)
        self.init()
        self.assertTrue(entry.is_symlink())
        self.assertEqual(outside.read_text(encoding="utf-8"), guidance.minimal_project_entry())
        self.assertEqual(len(upgrade.agent_guidance_notices(self.bundle, self.target)), 1)


if __name__ == "__main__":
    unittest.main()
