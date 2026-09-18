from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
CHECK = PROJECT_ROOT / "scripts" / "pact" / "check.py"
SCHEMA = PROJECT_ROOT / ".pact" / "schema" / "artifact.schema.json"


class PactCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-check-test-")
        self.root = pathlib.Path(self.temp.name)
        schema_dir = self.root / ".pact" / "schema"
        schema_dir.mkdir(parents=True)
        shutil.copy2(SCHEMA, schema_dir / "artifact.schema.json")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")

    def run_check(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CHECK), "--root", str(self.root)],
            capture_output=True,
            text=True,
        )

    def add_domain(self) -> None:
        self.write(
            "docs/product/domains/batch.md",
            """
            ---
            pact:
              type: domain
              id: DOMAIN-BATCH
              status: confirmed
              owners:
                - product
            ---
            # Batch
            """,
        )

    def test_valid_references_and_internal_link_pass(self) -> None:
        self.add_domain()
        self.write(
            "docs/product/rules/batch.md",
            """
            ---
            pact:
              type: rule
              id: RULE-BATCH-001
              status: confirmed
              owners:
                - product
              domains:
                - DOMAIN-BATCH
            ---
            # Batch Rule
            """,
        )
        self.write(
            "README.md",
            "[Batch rule](docs/product/rules/batch.md)\n",
        )

        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_domain_reference_fails(self) -> None:
        self.write(
            "docs/product/rules/batch.md",
            """
            ---
            pact:
              type: rule
              id: RULE-BATCH-001
              status: confirmed
              domains:
                - DOMAIN-MISSING
            ---
            # Batch Rule
            """,
        )

        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("domains references missing id 'DOMAIN-MISSING'", result.stderr)

    def test_missing_related_reference_fails(self) -> None:
        self.add_domain()
        self.write(
            "docs/product/rules/batch.md",
            """
            ---
            pact:
              type: rule
              id: RULE-BATCH-001
              status: confirmed
              domains:
                - DOMAIN-BATCH
              related:
                - DEC-BATCH-999
            ---
            # Batch Rule
            """,
        )

        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("related references missing id 'DEC-BATCH-999'", result.stderr)

    def test_wrong_change_lifecycle_directory_fails(self) -> None:
        self.write(
            "docs/changes/completed/example.md",
            """
            ---
            pact:
              type: change
              status: active
              domains: []
            ---
            # Example Change
            """,
        )

        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("completed change path requires status 'completed'", result.stderr)

    def test_broken_internal_link_fails(self) -> None:
        self.write("README.md", "[Missing](docs/does-not-exist.md)\n")

        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("broken internal link", result.stderr)


if __name__ == "__main__":
    unittest.main()
