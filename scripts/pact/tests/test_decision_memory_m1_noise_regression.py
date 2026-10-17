"""M1 RED: generic prose stopwords must not inject unrelated durable Decisions."""
from __future__ import annotations

import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))
from discover import score_document, score_code_file


class ColdStartDocumentNoiseRegressionTests(unittest.TestCase):
    def sample(self) -> dict:
        return {
            "id": "DEC-WIRE-ORDER",
            "title": "Binary wire encoding endianness",
            "artifact_type": "decision", "status": "implemented",
            "aliases": [], "domains": [],
            "text": ("The wire encoding uses network byte order because "
                     "deployed peers require consistent byte layouts."),
        }

    def test_unrelated_documentation_task_cannot_inject_decision_via_stopwords(self):
        score, reasons = score_document(
            self.sample(),
            "Tidy Markdown headings in CHANGELOG and documentation index",
        )
        self.assertEqual((score, reasons), (0, []))

    def test_specific_document_question_still_finds_original_decision(self):
        doc = self.sample()
        matched, _ = score_document(doc, "wire encoding")
        self.assertGreater(matched, 0)
        exact, _ = score_document(doc, "DEC-WIRE-ORDER")
        self.assertGreaterEqual(exact, 200)

    def test_exact_title_still_supported_even_when_title_is_stopword(self):
        doc = self.sample()
        doc["title"] = "in"
        score, reasons = score_document(doc, "in")
        self.assertGreaterEqual(score, 140)
        self.assertIn("exact title", reasons)

    def test_code_queries_unchanged_by_knowledge_only_filter(self):
        item = {"path": "src/cache/index.py", "language": "python",
                "symbols": ["lookup_index"], "identifiers": ["index"],
                "imports": []}
        score, _ = score_code_file(item, "index")
        self.assertGreater(score, 0)


if __name__ == "__main__":
    unittest.main()
