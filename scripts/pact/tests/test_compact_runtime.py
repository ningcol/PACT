from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
BUNDLE_MODULE = PROJECT_ROOT / "scripts" / "pact" / "runtime_bundle.py"
INIT = PROJECT_ROOT / "scripts" / "pact" / "init.py"

spec = importlib.util.spec_from_file_location("pact_runtime_bundle", BUNDLE_MODULE)
runtime_bundle = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runtime_bundle)


class CompactRuntimeTests(unittest.TestCase):
    def test_bundle_is_deterministic_and_has_runtime_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pact-pyz-") as tmp:
            root = pathlib.Path(tmp)
            first = root / "first.pyz"
            second = root / "second.pyz"

            runtime_bundle.build_runtime_bundle(PROJECT_ROOT, first)
            runtime_bundle.build_runtime_bundle(PROJECT_ROOT, second)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).hexdigest(),
                hashlib.sha256(second.read_bytes()).hexdigest(),
            )

            with zipfile.ZipFile(first) as archive:
                names = set(archive.namelist())

            self.assertIn("__main__.py", names)
            self.assertIn("pact.py", names)
            self.assertIn("runtime_exec.py", names)
            self.assertIn("task.py", names)
            self.assertIn(
                "pact_resources/schema/task-contract.schema.json",
                names,
            )
            self.assertIn(
                "pact_resources/schema/convergence-report.schema.json",
                names,
            )
            self.assertNotIn("tests/test_task_surface.py", names)

    def test_bundle_normalizes_source_line_endings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pact-pyz-newlines-") as tmp:
            root = pathlib.Path(tmp)
            source = root / "source"
            shutil.copytree(
                PROJECT_ROOT,
                source,
                ignore=shutil.ignore_patterns(
                    ".git",
                    "__pycache__",
                    "*.pyc",
                    "cache",
                ),
            )

            baseline = root / "baseline.pyz"
            crlf = root / "crlf.pyz"
            runtime_bundle.build_runtime_bundle(source, baseline)

            target = source / "scripts" / "pact" / "version.py"
            text = target.read_text(encoding="utf-8")
            target.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))

            runtime_bundle.build_runtime_bundle(source, crlf)
            self.assertEqual(baseline.read_bytes(), crlf.read_bytes())

    def test_fresh_init_installs_minimal_runtime_and_executes_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pact-compact-init-") as tmp:
            target = pathlib.Path(tmp) / "target"
            result = subprocess.run(
                [
                    sys.executable,
                    str(INIT),
                    "--target",
                    str(target),
                    "--apply",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            bundle = target / ".pact" / "pact.pyz"
            self.assertTrue(bundle.is_file())
            self.assertFalse((target / "scripts" / "pact").exists())

            manifest = json.loads(
                (target / ".pact" / "install.json").read_text(encoding="utf-8")
            )
            self.assertNotIn("install_profile", manifest)
            self.assertLessEqual(len(manifest["files"]), 8)
            self.assertEqual(
                [
                    path
                    for path, record in manifest["files"].items()
                    if record.get("management") == "framework"
                    and (
                        path == ".pact/pact.pyz"
                        or path.startswith("scripts/pact/")
                    )
                ],
                [".pact/pact.pyz"],
            )

            # Empty knowledge/lifecycle scaffold is intentionally absent.
            for relative in [
                "docs/governance",
                "docs/product",
                "docs/architecture",
                "docs/changes",
                "docs/drift",
                ".agents/decisions",
                ".agents/skills",
            ]:
                self.assertFalse((target / relative).exists(), relative)

            physical_files = [
                path for path in target.rglob("*")
                if path.is_file()
            ]
            self.assertLessEqual(len(physical_files), 9)

            help_result = subprocess.run(
                [sys.executable, str(target / "pact.py"), "--help"],
                cwd=target,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                help_result.returncode,
                0,
                help_result.stdout + help_result.stderr,
            )
            self.assertIn("PACT Project AI Control Plane", help_result.stdout)

            doctor = subprocess.run(
                [
                    sys.executable,
                    str(target / "pact.py"),
                    "doctor",
                    "--strict",
                    "--json",
                ],
                cwd=target,
                capture_output=True,
                text=True,
            )
            self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
            self.assertEqual(json.loads(doctor.stdout)["overall"], "pass")

            status = subprocess.run(
                [
                    sys.executable,
                    str(target / "pact.py"),
                    "status",
                    "--json",
                ],
                cwd=target,
                capture_output=True,
                text=True,
            )
            self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
            data = json.loads(status.stdout)
            self.assertEqual(data["overall"], "pass")
            self.assertIn("baseline-review-pending", data["warnings"])
            self.assertEqual(data["readiness"]["stage"], "foundation-valid")
            self.assertFalse((target / ".pact" / "schema").exists())

            schema_lint = subprocess.run(
                [sys.executable, str(target / "pact.py"), "schema-lint"],
                cwd=target,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                schema_lint.returncode,
                0,
                schema_lint.stdout + schema_lint.stderr,
            )
            self.assertIn("schema file(s) supported", schema_lint.stdout)

            prepared = subprocess.run(
                [
                    sys.executable,
                    str(target / "pact.py"),
                    "task",
                    "prepare",
                    "embedded schema smoke",
                    "--success",
                    "Task Contract and Context validate from embedded schemas",
                    "--risk",
                    "low",
                    "--task-id",
                    "TASK-EMBEDDED-SCHEMA",
                    "--json",
                ],
                cwd=target,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                prepared.returncode,
                0,
                prepared.stdout + prepared.stderr,
            )
            self.assertEqual(
                json.loads(prepared.stdout)["task_id"],
                "TASK-EMBEDDED-SCHEMA",
            )


if __name__ == "__main__":
    unittest.main()
