"""Review-only detection for explicitly mixed-confirmation Product Rules."""

from __future__ import annotations

import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))

import audit
import context
import discover


def rule(status: str, content: str, *, ident: str = "RULE-HOME-001") -> dict:
    return {
        "artifact_type": "rule",
        "id": ident,
        "status": status,
        "title": "Home and operations questions",
        "path": f"docs/product/rules/{ident.lower()}.md",
        "text": content,
        "aliases": [],
        "domains": [],
        "related": [],
        "verification": [],
        "links": [],
    }


class MixedAuthorityTests(unittest.TestCase):
    def test_explicit_pending_headings_are_detected(self) -> None:
        for heading in (
            "## 待确认",
            "### 2. 待确认：运营范围",
            "## 未确认 - 下一步",
            "## 尚未确认（第三方需求）",
            "## TBD: outstanding behavior",
            "# Unconfirmed: business meaning",
            "### Pending confirmation",
        ):
            with self.subTest(heading=heading):
                self.assertTrue(
                    discover.mixed_rule_authority(rule("confirmed", "# Good\n" + heading))
                )

    def test_fenced_example_and_prose_are_not_authoritative_warnings(self) -> None:
        cases = (
            "## Confirmed\nDo not treat the word 待确认 as a heading.",
            "# Confirmed\n\n```markdown\n## 待确认\n```",
            "# Confirmed\n\n~~~markdown\n## Unconfirmed\n~~~",
            "## Confirmed\n### Candidate ideas (not a pending heading)",
            "  ## 待确认",  # four spaces: indented code, not an ATX heading
        )
        for text in cases:
            with self.subTest(text=text):
                self.assertFalse(discover.mixed_rule_authority(rule("confirmed", text)))

    def test_candidate_document_is_not_promoted_or_reclassified(self) -> None:
        doc = rule("candidate", "# Draft\n## 待确认")
        self.assertFalse(discover.mixed_rule_authority(doc))
        self.assertEqual(context.applicable_rule_ids([doc]), [])

    def test_generic_discovery_preserves_mixed_warning_without_hiding_candidate(self) -> None:
        current = rule("confirmed", "# Home\nConfirmed subsection.\n## 待确认\nUncertain.", ident="RULE-HOME-MIXED")
        clean = rule("confirmed", "# Home\nOnly confirmed behavior.", ident="RULE-HOME-VALID")
        ranked = discover.ranked_knowledge_results(
            {"documents": [current, clean]}, "Home", limit=2,
        )
        self.assertEqual({item["id"] for item in ranked}, {current["id"], clean["id"]})
        mixed = next(item for item in ranked if item["id"] == current["id"])
        self.assertTrue(mixed["mixed_authority"])
        self.assertFalse(next(item for item in ranked if item["id"] == clean["id"])["mixed_authority"])
        self.assertEqual(context.applicable_rule_ids(ranked), [clean["id"]])
        self.assertEqual(context.knowledge_priority(mixed)[1], False)
        self.assertEqual(context.knowledge_priority(
            next(item for item in ranked if item["id"] == clean["id"])
        )[1], True)

    def test_audit_surfaces_semantic_candidate_not_hard_failure(self) -> None:
        mixed = rule("confirmed", "# Valid\n## 未确认\nUnreviewed.")
        clean = rule("confirmed", "# Valid\nNo pending sections.")
        report = audit.evaluate(
            {"documents": [mixed, clean]}, deterministic_check="pass"
        )
        self.assertEqual(report["deterministic_check"], "pass")
        self.assertEqual(len(report["mixed_rule_candidates"]), 1)
        self.assertEqual(report["mixed_rule_candidates"][0]["id"], mixed["id"])
        self.assertTrue(any(
            item.get("path") == mixed["path"]
            for item in report["semantic_review_targets"]
        ))


if __name__ == "__main__":
    unittest.main()
