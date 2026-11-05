"""No-model tests: domain knowledge overlap is review-only, never authority."""

from __future__ import annotations

import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))
import audit


def doc(kind: str, ident: str, domain: str | None = None, **extra) -> dict:
    item = {
        "id": ident,
        "artifact_type": kind,
        "status": "confirmed" if kind in {"domain", "rule"} else "implemented",
        "title": ident,
        "path": f"docs/{ident.lower()}.md",
        "text": "An unrelated body.",
        "domains": [] if domain is None else [domain],
        "related": [],
        "supersedes": [],
        "aliases": [],
    }
    item.update(extra)
    return item


class DomainKnowledgeAuditTests(unittest.TestCase):
    def setUp(self):
        self.order = doc(
            "domain", "DOMAIN-ORDER", aliases=["orders", "订单"],
            text="# Orders\n\n- RULE-ORDER-9\n- DEC-ORDER-9",
        )
        self.payment = doc(
            "domain", "DOMAIN-PAYMENT", aliases=["payment", "订单"],
        )

    def test_same_topic_different_rules_are_only_review_candidates(self):
        a = doc(
            "rule", "RULE-ORDER-1", "DOMAIN-ORDER",
            title="RULE-ORDER-1 — 退款条件",
            text="Refunds are allowed for unsettled orders.",
        )
        b = doc(
            "rule", "RULE-ORDER-2", "DOMAIN-ORDER",
            title="RULE-ORDER-2 — 退款条件",
            text="Refunds are forbidden after settlement.",
        )
        result = audit.evaluate(
            {"documents": [self.order, self.payment, a, b]},
            deterministic_check="pass",
        )
        self.assertEqual(result["deterministic_check"], "pass")
        candidates = result["possible_knowledge_overlaps"]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["signal"], "same-title")
        self.assertEqual(candidates[0]["domain"], "DOMAIN-ORDER")
        self.assertIn("no semantic verdict", candidates[0]["reason"])
        self.assertIn("订单", [x["alias"] for x in result["domain_alias_collisions"]])

    def test_different_topics_in_same_domain_are_not_declared_conflicting(self):
        a = doc("rule", "RULE-ORDER-1", "DOMAIN-ORDER", title="Stock recovery")
        b = doc("rule", "RULE-ORDER-2", "DOMAIN-ORDER", title="Refund eligibility")
        result = audit.evaluate(
            {"documents": [self.order, a, b]}, deterministic_check="pass"
        )
        self.assertEqual(result["possible_knowledge_overlaps"], [])

    def test_explicit_successor_is_not_a_duplicate_decision(self):
        old = doc("decision", "DEC-ORDER-1", "DOMAIN-ORDER",
                  title="Stock ownership", status="superseded")
        new = doc("decision", "DEC-ORDER-2", "DOMAIN-ORDER",
                  title="Stock ownership", supersedes=["DEC-ORDER-1"])
        result = audit.evaluate(
            {"documents": [self.order, old, new]}, deterministic_check="pass"
        )
        self.assertEqual(result["possible_knowledge_overlaps"], [])
        self.assertEqual(len(result["decision_retention_candidates"]), 1)

    def test_scoped_domain_review_includes_explicit_router_ids(self):
        linked = doc(
            "decision", "DEC-ORDER-9", None, title="Stock ownership",
            path=".agents/decisions/implemented/stock.md",
        )
        rule = doc("rule", "RULE-ORDER-9", None,
                   title="Refund rule",
                   path="docs/product/rules/refund.md")
        unrelated = doc("rule", "RULE-PAY-1", "DOMAIN-PAYMENT")
        result = audit.evaluate(
            {"documents": [self.order, self.payment, linked, rule, unrelated]},
            deterministic_check="pass", domain="DOMAIN-ORDER",
        )
        self.assertEqual(
            {row["id"] for row in result["scoped_sources"]},
            {"DEC-ORDER-9", "RULE-ORDER-9"},
        )
        self.assertTrue(all(
            row["routing_evidence"] == "explicit-router-id"
            for row in result["scoped_sources"]
        ))
        self.assertEqual(result["possible_knowledge_overlaps"], [])

    def test_router_links_without_domains_are_compared_for_review_only(self):
        router = doc(
            "domain", "DOMAIN-RETURNS", status="candidate",
            related=["RULE-RETURNS-1", "RULE-RETURNS-2"],
        )
        left = doc("rule", "RULE-RETURNS-1", title="退款规则",
                   text="Refund before settlement.")
        right = doc("rule", "RULE-RETURNS-2", title="退款规则",
                    text="Refund after settlement.")
        result = audit.evaluate(
            {"documents": [router, left, right]}, deterministic_check="pass",
            domain="DOMAIN-RETURNS",
        )
        self.assertEqual(result["domain_status"], "candidate")
        self.assertEqual(len(result["possible_knowledge_overlaps"]), 1)
        self.assertEqual(result["possible_knowledge_overlaps"][0]["signal"], "same-title")
        self.assertEqual(result["scoped_sources_count"], 2)

    def test_unknown_domain_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unknown Domain"):
            audit.evaluate({"documents": []}, deterministic_check="pass",
                           domain="DOMAIN-MISSING")

    def test_no_clue_does_not_fabricate_semantic_conflict(self):
        misleading = doc("document", "DOC-1", "DOMAIN-ORDER",
                         title="Refund eligibility",
                         text="A historical note about unrelated UI changes")
        result = audit.evaluate(
            {"documents": [self.order, misleading]},
            deterministic_check="pass",
        )
        self.assertEqual(result["possible_knowledge_overlaps"], [])

    def test_alias_collisions_are_bounded(self):
        names = [f"shared-alias-{i}" for i in range(70)]
        a = doc("domain", "DOMAIN-A", aliases=names)
        b = doc("domain", "DOMAIN-B", aliases=names)
        result = audit.evaluate({"documents": [a, b]}, deterministic_check="pass")
        self.assertEqual(len(result["domain_alias_collisions"]), 60)
        self.assertEqual(result["alias_collisions_suppressed"], 10)

    def test_comparison_budget_reports_incompleteness(self):
        docs = [self.order] + [
            doc("rule", f"RULE-ORDER-{n}", "DOMAIN-ORDER",
                title=f"Unique title {n}")
            for n in range(120)
        ]
        result = audit.evaluate({"documents": docs}, deterministic_check="pass")
        self.assertTrue(result["overlap_scan_truncated"])
        self.assertLessEqual(len(result["possible_knowledge_overlaps"]), 60)


if __name__ == "__main__":
    unittest.main()
