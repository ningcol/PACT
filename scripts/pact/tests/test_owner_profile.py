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


VALID_CONFIG = """
version: 1

owner:
  role: product_project_owner
  language: zh-CN
  technical_depth: product
  communication:
    prefer:
      - user_behavior
    hide_by_default:
      - implementation_patterns
    explain_consequence_before_technical_term: true
    progressive_disclosure: true
    decision_translation: consequence_first

paths:
  product_truth: docs/product
  architecture: docs/architecture
  decisions: .agents/decisions
  changes: docs/changes
  drift: docs/drift
  skills: .agents/skills

risk:
  levels:
    - low
    - medium
    - high

discovery:
  use_canonical_vocabulary: true
  derived_cache: .pact/cache

convergence:
  code_wins_product_truth: false
  deterministic_fact_mismatch: fail
  heuristic_drift: warn
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

    def test_valid_project_profile(self) -> None:
        self.write(".pact/config.yaml", VALID_CONFIG)
        result = self.run_owner("--strict", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"language": "zh-CN"', result.stdout)
        self.assertIn('"technical_depth": "product"', result.stdout)

    def test_invalid_code_wins_policy_is_rejected(self) -> None:
        invalid = VALID_CONFIG.replace(
            "code_wins_product_truth: false",
            "code_wins_product_truth: true",
        )
        self.write(".pact/config.yaml", invalid)
        result = self.run_owner("--strict")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid configuration", result.stderr)

    def test_example_fallback_is_not_project_config(self) -> None:
        self.write(".pact/config.example.yaml", VALID_CONFIG)
        result = self.run_owner("--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"configured": false', result.stdout)

    def test_strict_requires_project_config(self) -> None:
        self.write(".pact/config.example.yaml", VALID_CONFIG)
        result = self.run_owner("--strict")
        self.assertEqual(result.returncode, 2)
        self.assertIn(".pact/config.yaml is missing", result.stderr)


if __name__ == "__main__":
    unittest.main()
