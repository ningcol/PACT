from __future__ import annotations

import json
import pathlib
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
PACT_RUNTIME = PROJECT_ROOT / "scripts" / "pact"
sys.path.insert(0, str(PACT_RUNTIME))

from formats import parse_legacy_yaml, parse_markdown_metadata  # noqa: E402
from schema_validate import load_schema, validate_instance  # noqa: E402


class StdlibRuntimeTests(unittest.TestCase):
    def test_runtime_module_names_do_not_shadow_python_stdlib(self) -> None:
        runtime_modules = {
            path.stem
            for path in PACT_RUNTIME.glob("*.py")
            if path.name != "__init__.py"
        }
        collisions = sorted(runtime_modules & set(sys.stdlib_module_names))
        self.assertEqual(
            collisions,
            [],
            f"PACT runtime files shadow Python stdlib modules: {collisions}",
        )

    def test_toml_front_matter(self) -> None:
        data, body, kind = parse_markdown_metadata(
            '+++\n[pact]\ntype = "domain"\nid = "DOMAIN-BATCH"\naliases = ["批次", "examBatch"]\n+++\n# Batch\n'
        )
        self.assertEqual(kind, "toml")
        self.assertEqual(data["pact"]["id"], "DOMAIN-BATCH")
        self.assertEqual(data["pact"]["aliases"], ["批次", "examBatch"])
        self.assertIn("# Batch", body)

    def test_legacy_yaml_front_matter(self) -> None:
        data, _, kind = parse_markdown_metadata(
            "---\npact:\n  type: domain\n  id: DOMAIN-LEGACY\n  owners:\n    - product\n---\n# Legacy\n"
        )
        self.assertEqual(kind, "legacy-yaml")
        self.assertEqual(data["pact"]["id"], "DOMAIN-LEGACY")
        self.assertEqual(data["pact"]["owners"], ["product"])

    def test_legacy_yaml_list_of_mappings(self) -> None:
        data = parse_legacy_yaml(
            """
            version: 1
            checks:
              - id: test-check
                description: Test check.
                command:
                  - python
                  - check.py
                severity: error
            """
        )
        self.assertEqual(data["checks"][0]["id"], "test-check")
        self.assertEqual(data["checks"][0]["command"], ["python", "check.py"])

    def test_schema_if_then_is_enforced(self) -> None:
        schema = load_schema(PROJECT_ROOT / ".pact/schema/convergence-report.schema.json")
        report = json.loads(
            (PROJECT_ROOT / ".pact/examples/convergence-report.example.json").read_text(
                encoding="utf-8"
            )
        )
        report["findings"][0]["classification"] = "owner-decision"
        errors = validate_instance(report, schema)
        self.assertTrue(any("owner_question" in error for error in errors), errors)

    def test_current_example_contracts_validate(self) -> None:
        pairs = [
            ("convergence-report.example.json", "convergence-report.schema.json"),
            ("evidence-receipt.example.json", "evidence-receipt.schema.json"),
            ("owner-report.example.json", "owner-report.schema.json"),
            ("pilot-evaluation.example.json", "pilot-evaluation.schema.json"),
        ]
        for example_name, schema_name in pairs:
            with self.subTest(example=example_name):
                data = json.loads(
                    (PROJECT_ROOT / ".pact/examples" / example_name).read_text(
                        encoding="utf-8"
                    )
                )
                schema = load_schema(PROJECT_ROOT / ".pact/schema" / schema_name)
                self.assertEqual(validate_instance(data, schema), [])


if __name__ == "__main__":
    unittest.main()
