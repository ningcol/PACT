"""Standard guidance follows the serving runtime without project writes/scans."""
from __future__ import annotations

from contextlib import redirect_stdout
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
from unittest.mock import patch


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "scripts/pact"))
import guidance
from runtime_bundle import build_runtime_bundle


def snapshot(root: pathlib.Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*") if path.is_file()
    }


class StandardGuidanceTests(unittest.TestCase):
    def make_root(self) -> pathlib.Path:
        root = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory(prefix="pact-standard-guide-")))
        (root / ".pact").mkdir()
        (root / ".pact/VERSION").write_text("guidance-test-version\n", encoding="utf-8")
        shutil.copyfile(PROJECT_ROOT / "pact.py", root / "pact.py")
        # Old/custom project documents cannot substitute for runtime guidance.
        (root / ".pact/README.md").write_text("PROJECT-OWNED CUSTOM GUIDE\n", encoding="utf-8")
        return root

    def invoke(self, root: pathlib.Path, *args: str, direct: bool = False):
        script = root / "scripts/pact/guidance.py" if direct else root / "pact.py"
        env = dict(os.environ)
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        env.pop("PYTHONPYCACHEPREFIX", None)
        # Python may otherwise be configured to write its cache outside the
        # fixture. Explicitly enable bytecode so the command must prevent it.
        return subprocess.run(
            [sys.executable, str(script), *args], cwd=root,
            capture_output=True, text=True, encoding="utf-8", env=env,
        )

    def install_bundle(self, root: pathlib.Path) -> str:
        bundle = root / ".pact/pact.pyz"
        build_runtime_bundle(PROJECT_ROOT, bundle)
        digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
        (root / ".pact/install.json").write_text(json.dumps({
            "format_version": 1, "runtime_version": "guidance-test-version",
            "files": {".pact/pact.pyz": {
                "management": "framework", "source_path": ".pact/pact.pyz",
                "source_sha256": digest, "installed_sha256": digest,
            }},
        }), encoding="utf-8")
        return digest

    def assert_json(self, result, *, source_kind: str) -> dict:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["content"], guidance.STANDARD_GUIDANCE)
        self.assertEqual(
            data["content_sha256"],
            hashlib.sha256(data["content"].encode("utf-8")).hexdigest(),
        )
        self.assertEqual(data["runtime"]["version"], "guidance-test-version")
        self.assertEqual(data["source"]["kind"], source_kind)
        self.assertEqual(set(data["verification"].values()), {"unverified"})
        return data

    def test_fresh_source_and_direct_read_do_not_create_bytecode_or_state(self):
        root = self.make_root()
        shutil.copytree(
            PROJECT_ROOT / "scripts/pact", root / "scripts/pact",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"),
        )
        before = snapshot(root)
        self.assert_json(self.invoke(root, "guidance", "--json"), source_kind="source")
        self.assertEqual(snapshot(root), before)
        self.assert_json(self.invoke(root, "--json", direct=True), source_kind="source")
        self.assertEqual(snapshot(root), before)
        self.assertEqual(list(root.rglob("__pycache__")), [])

    def test_installed_runtime_supplies_guidance_and_ignores_old_project_copy(self):
        root = self.make_root()
        digest = self.install_bundle(root)
        before = snapshot(root)
        data = self.assert_json(self.invoke(root, "guidance", "--json"), source_kind="embedded-runtime")
        self.assertEqual(data["runtime"]["sha256"], digest)
        self.assertEqual(data["runtime"]["integrity"], "matched")
        self.assertEqual(snapshot(root), before)

    def test_plain_installed_read_exposes_version_mismatch_and_manifest_error(self):
        root = self.make_root()
        self.install_bundle(root)
        (root / ".pact/VERSION").write_text("another-version\n", encoding="utf-8")
        result = self.invoke(root, "guidance")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("integrity=mismatch", result.stdout)
        self.assertIn("Warning: runtime identity is mismatch", result.stdout)
        self.assertTrue(result.stdout.endswith(guidance.STANDARD_GUIDANCE))
        (root / ".pact/install.json").write_text("{invalid json", encoding="utf-8")
        result = self.invoke(root, "guidance")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("integrity=error", result.stdout)
        self.assertIn("runtime identity error: invalid .pact/install.json", result.stdout)
        self.assertTrue(result.stdout.endswith(guidance.STANDARD_GUIDANCE))

    def test_plain_output_identifies_content_without_claiming_host_activation(self):
        out = io.StringIO()
        with patch.object(sys, "argv", ["guidance"]), \
                patch.object(guidance, "runtime_identity", return_value={"version": "test"}), \
                redirect_stdout(out):
            self.assertEqual(guidance.main(), 0)
        text = out.getvalue()
        self.assertIn("runtime=test", text)
        self.assertIn(hashlib.sha256(guidance.STANDARD_GUIDANCE.encode("utf-8")).hexdigest(), text)
        self.assertIn("remain unverified", text)
        self.assertTrue(text.endswith(guidance.STANDARD_GUIDANCE))

    def test_reading_guidance_never_runs_commands_or_writes_project_state(self):
        root = self.make_root()
        before = snapshot(root)
        out = io.StringIO()
        with patch.object(sys, "argv", ["guidance", "--json"]), \
                patch.object(guidance, "ROOT", root), \
                patch.object(subprocess, "Popen", side_effect=AssertionError("project command/Git scan")), \
                patch.object(pathlib.Path, "write_text", side_effect=AssertionError("project write")), \
                patch.object(pathlib.Path, "write_bytes", side_effect=AssertionError("project write")), \
                redirect_stdout(out):
            self.assertEqual(guidance.main(), 0)
        self.assertEqual(snapshot(root), before)
        self.assert_json(subprocess.CompletedProcess([], 0, out.getvalue(), ""), source_kind="source")

    def test_json_remains_lossless_on_legacy_console_encoding(self):
        raw = io.BytesIO()
        console = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
        content = "项目规则与证据 🧭\n"
        with patch.object(sys, "argv", ["guidance", "--json"]), \
                patch.object(guidance, "STANDARD_GUIDANCE", content), \
                patch.object(guidance, "runtime_identity", return_value={"version": "版本 🧭"}), \
                redirect_stdout(console):
            self.assertEqual(guidance.main(), 0)
        console.flush()
        data = json.loads(raw.getvalue().decode("ascii"))
        self.assertEqual(data["content"], content)
        self.assertEqual(data["runtime"]["version"], "版本 🧭")

    def test_entry_is_a_small_reference_and_recognition_is_only_static(self):
        self.assertTrue(guidance.entry_reference_present(guidance.minimal_project_entry()))
        self.assertTrue(guidance.entry_reference_present(guidance.bootstrap_snippet()))
        self.assertLess(len(guidance.PROJECT_ENTRY), len(guidance.STANDARD_GUIDANCE) // 4)
        self.assertNotIn(guidance.STANDARD_GUIDANCE, guidance.bootstrap_snippet())
        for text in ("`backend/venv/bin/python ./pact.py guidance --json`", "python3 pact.py guidance"):
            self.assertTrue(guidance.entry_reference_present(text), text)
        for text in ("pact.py guidance-extra", "pact.py guidance.py", "evilpact.py guidance", "pact.py status"):
            self.assertFalse(guidance.entry_reference_present(text), text)


if __name__ == "__main__":
    unittest.main()
