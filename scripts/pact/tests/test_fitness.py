from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
FITNESS = PROJECT_ROOT / "scripts" / "pact" / "fitness.py"
SCHEMA = PROJECT_ROOT / ".pact" / "schema" / "fitness.schema.json"


class FitnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-fitness-test-")
        self.root = pathlib.Path(self.temp.name)
        schema_dir = self.root / ".pact" / "schema"
        schema_dir.mkdir(parents=True)
        shutil.copy2(SCHEMA, schema_dir / "fitness.schema.json")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, relative: str, content: str) -> pathlib.Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
        return path

    def run_fitness(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(FITNESS), "--root", str(self.root), *args],
            capture_output=True,
            text=True,
        )

    def test_empty_toml_project_config_passes(self) -> None:
        self.write(".pact/fitness.toml", "version = 1\nchecks = []\n")
        result = self.run_fitness("--strict", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"configured": true', result.stdout)
        self.assertIn('"config_format": "toml"', result.stdout)

    def test_error_check_blocks(self) -> None:
        checker = self.write("checks/fail.py", "raise SystemExit(1)\n")
        self.write(
            ".pact/fitness.toml",
            f"""
            version = 1

            [[checks]]
            id = "must-pass"
            description = "This invariant must pass."
            command = [{json.dumps(str(sys.executable))}, {json.dumps(str(checker))}]
            severity = "error"
            """,
        )
        result = self.run_fitness("--strict", "--json")
        self.assertEqual(result.returncode, 1)
        self.assertIn('"blocking_failures": 1', result.stdout)

    def test_warn_check_does_not_block(self) -> None:
        checker = self.write("checks/warn.py", "raise SystemExit(1)\n")
        self.write(
            ".pact/fitness.toml",
            f"""
            version = 1

            [[checks]]
            id = "migration-warning"
            description = "Migration still has a known cycle."
            command = ["{sys.executable}", "{checker}"]
            severity = "warn"
            """,
        )
        result = self.run_fitness("--strict", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"overall": "warn"', result.stdout)

    def test_legacy_yaml_list_of_checks_remains_readable(self) -> None:
        checker = self.write("checks/ok.py", "raise SystemExit(0)\n")
        self.write(
            ".pact/fitness.yaml",
            f"""
            version: 1
            checks:
              - id: legacy-check
                description: Legacy config stays readable.
                command:
                  - {sys.executable}
                  - {checker}
                severity: error
            """,
        )
        result = self.run_fitness("--strict", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"config_format": "legacy-yaml"', result.stdout)

    def test_strict_requires_project_config(self) -> None:
        self.write(".pact/fitness.example.toml", "version = 1\nchecks = []\n")
        result = self.run_fitness("--strict")
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing config", result.stderr)

    def test_nonstrict_can_use_example_fallback(self) -> None:
        self.write(".pact/fitness.example.toml", "version = 1\nchecks = []\n")
        result = self.run_fitness("--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"configured": false', result.stdout)


if __name__ == "__main__":
    unittest.main()
