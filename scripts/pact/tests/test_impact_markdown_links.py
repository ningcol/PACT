"""Impact Analysis regression cases for Markdown links resolved from source docs.

All documentation and changed files are created in isolated temporary projects.
The public Project Map parser supplies the raw Markdown links to Impact.
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
RUNTIME = PROJECT_ROOT / "scripts" / "pact"
sys.path.insert(0, str(RUNTIME))

import impact
import map as project_map


class MarkdownImpactLinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-impact-doc-links-")
        self.root = pathlib.Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def analyze(
        self,
        *,
        document_path: str,
        markdown: str,
        changed_path: str,
        verification: list[str] | None = None,
    ) -> dict:
        document = self.root / document_path
        document.parent.mkdir(parents=True, exist_ok=True)
        document.write_text(markdown, encoding="utf-8")

        source = self.root / changed_path
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("# file under review\n", encoding="utf-8")

        parsed = project_map.parse_document(document, self.root)
        if verification is not None:
            parsed["verification"] = verification
        output = io.StringIO()
        errors = io.StringIO()
        with (
            mock.patch.object(impact, "ROOT", self.root),
            mock.patch.object(impact, "build_map", return_value={"documents": [parsed]}),
            mock.patch.object(
                sys,
                "argv",
                ["impact.py", "--files", changed_path, "--risk", "low",
                 "--no-code", "--json"],
            ),
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(errors),
        ):
            status = impact.main()
        self.assertEqual(status, 0, errors.getvalue() + output.getvalue())
        return json.loads(output.getvalue())

    def test_nested_relative_markdown_link_maps_actual_code_path(self) -> None:
        report = self.analyze(
            document_path="docs/product/rules/password-reset.md",
            markdown="# Password reset\n\n[Implementation](../../../src/api/reset.py)\n",
            changed_path="src/api/reset.py",
        )
        self.assertEqual(
            [(hit["relation"], hit["target"]["path"])
             for hit in report["deterministic_impacts"]],
            [("explicit-doc-link", "docs/product/rules/password-reset.md")],
        )
        self.assertEqual(report["unmapped_files"], [])

    def test_nested_anchor_and_percent_encoded_spaces_resolve_from_doc(self) -> None:
        report = self.analyze(
            document_path="docs/product/rules/password-reset.md",
            markdown="# Reset\n\n[worker](../../../src/api/reset%20worker.py#L20)\n",
            changed_path="src/api/reset worker.py",
        )
        self.assertEqual(
            [hit["relation"] for hit in report["deterministic_impacts"]],
            ["explicit-doc-link"],
        )
        self.assertEqual(report["unmapped_files"], [])

    def test_root_readme_relative_link_retains_existing_behavior(self) -> None:
        report = self.analyze(
            document_path="README.md",
            markdown="# Welcome\n\n[Docs](docs/architecture.md)\n",
            changed_path="docs/architecture.md",
        )
        self.assertEqual(
            [hit["relation"] for hit in report["deterministic_impacts"]],
            ["explicit-doc-link"],
        )

    def test_repo_root_link_resolves_without_document_directory(self) -> None:
        report = self.analyze(
            document_path="docs/product/rules/checkout.md",
            markdown="# Checkout\n\n[Source](/src/api/checkout.py)\n",
            changed_path="src/api/checkout.py",
        )
        self.assertEqual(
            [hit["relation"] for hit in report["deterministic_impacts"]],
            ["explicit-doc-link"],
        )

    def test_escaping_parent_path_does_not_alias_repository_file(self) -> None:
        report = self.analyze(
            document_path="docs/product/rules/checkout.md",
            markdown="# Checkout\n\n[Outside](../../../../src/api/checkout.py)\n",
            changed_path="src/api/checkout.py",
        )
        self.assertEqual(report["deterministic_impacts"], [])
        self.assertEqual(report["unmapped_files"], ["src/api/checkout.py"])

    def test_external_url_is_not_treated_as_repository_link(self) -> None:
        report = self.analyze(
            document_path="docs/product/rules/checkout.md",
            markdown="# Checkout\n\n[External](https://example.org/src/api/checkout.py)\n",
            changed_path="src/api/checkout.py",
        )
        self.assertEqual(report["deterministic_impacts"], [])

    def test_verification_paths_stay_repository_relative(self) -> None:
        report = self.analyze(
            document_path="docs/product/rules/checkout.md",
            markdown="# Checkout\n\nNo direct Markdown code links.\n",
            changed_path="src/api/checkout.py",
            verification=["src/api/checkout.py"],
        )
        self.assertEqual(
            [hit["relation"] for hit in report["deterministic_impacts"]],
            ["verification-reference"],
        )


if __name__ == "__main__":
    unittest.main()
