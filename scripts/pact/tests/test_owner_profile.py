from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNER = PROJECT_ROOT / "scripts" / "pact" / "owner.py"
SCHEMA = PROJECT_ROOT / ".pact" / "schema" / "config.schema.json"

VALID_TOML = """
version = 1

[owner]
role = "product_project_owner"
language = "zh-CN"
technical_depth = "product"

[owner.communication]
prefer = ["user_behavior"]
hide_by_default = ["implementation_patterns"]
explain_consequence_before_technical_term = true
progressive_disclosure = true
decision_translation = "consequence_first"
"""



class OwnerProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-owner-test-")
        self.root = pathlib.Path(self.temp.name)
        schema_dir = self.root / ".pact" / "schema"
        schema_dir.mkdir(parents=True)
        shutil.copy2(SCHEMA, schema_dir / "config.schema.json")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")

    def run_owner(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(OWNER), "--root", str(self.root), *args],
            capture_output=True,
            text=True,
        )

    def test_valid_toml_project_profile(self) -> None:
        self.write(".pact/config.toml", VALID_TOML)
        result = self.run_owner("--strict", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"language": "zh-CN"', result.stdout)
        self.assertIn('"technical_depth": "product"', result.stdout)
        self.assertIn('"source_format": "toml"', result.stdout)

    def test_invalid_toml_profile_is_rejected(self) -> None:
        invalid = VALID_TOML.replace('technical_depth = "product"', 'technical_depth = "magic"')
        self.write(".pact/config.toml", invalid)
        result = self.run_owner("--strict")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid configuration", result.stderr)

    def test_example_fallback_is_not_project_config(self) -> None:
        self.write(".pact/config.example.toml", VALID_TOML)
        result = self.run_owner("--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"configured": false', result.stdout)

    def test_strict_requires_project_config(self) -> None:
        self.write(".pact/config.example.toml", VALID_TOML)
        result = self.run_owner("--strict")
        self.assertEqual(result.returncode, 2)
        self.assertIn(".pact/config.toml is missing", result.stderr)


if __name__ == "__main__":
    unittest.main()
