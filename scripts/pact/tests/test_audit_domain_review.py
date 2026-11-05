"""No-model tests: domain knowledge overlap is review-only, never authority."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
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

    def test_malformed_related_and_domains_are_not_promoted_or_crashing(self):
        domain = doc(
            "domain", "DOMAIN-BROKEN",
            related=["RULE-GOOD-1", None, 42, {"not": "an-id"}, ["nested"]],
            aliases=[None, {"bad": "alias"}, "safe alias"],
        )
        good = doc(
            "rule", "RULE-GOOD-1", None, title="Stable policy",
            domains=["DOMAIN-BROKEN", None, {"invalid": "domain"}],
        )
        unrelated = doc("rule", "RULE-OTHER-1", None)
        for selected in (None, "DOMAIN-BROKEN"):
            with self.subTest(selected=selected):
                result = audit.evaluate(
                    {"documents": [domain, good, unrelated]},
                    deterministic_check="fail", domain=selected,
                )
                self.assertEqual(result["deterministic_check"], "fail")
                self.assertEqual(result["possible_knowledge_overlaps"], [])
                if selected:
                    self.assertEqual(
                        [x["id"] for x in result["scoped_sources"]],
                        ["RULE-GOOD-1"],
                    )

    def test_malformed_supersedes_does_not_crash_decision_comparison(self):
        old = doc(
            "decision", "DEC-OLD", "DOMAIN-ORDER",
            title="Stock invariant",
        )
        new = doc(
            "decision", "DEC-NEW", "DOMAIN-ORDER",
            title="Stock invariant",
            supersedes=[{"untrusted": "DEC-OLD"}, None],
        )
        result = audit.evaluate(
            {"documents": [self.order, old, new]},
            deterministic_check="fail",
        )
        self.assertEqual(len(result["possible_knowledge_overlaps"]), 1)
        self.assertEqual(result["possible_knowledge_overlaps"][0]["signal"], "same-title")

    def test_malformed_related_containers_do_not_crash(self):
        for malformed in ("RULE-GOOD-1", 5, {"RULE-GOOD-1": True}, None):
            with self.subTest(value=malformed):
                router = doc("domain", "DOMAIN-TEST", related=malformed)
                result = audit.evaluate(
                    {"documents": [router]}, deterministic_check="fail",
                    domain="DOMAIN-TEST",
                )
                self.assertEqual(result["scoped_sources"], [])
                self.assertEqual(result["possible_knowledge_overlaps"], [])

    def test_installed_audit_reports_invalid_relation_without_crashing(self):
        """Check rejects mixed TOML types; audit still returns a JSON inventory."""
        init = ROOT / "scripts/pact/init.py"
        with tempfile.TemporaryDirectory(prefix="pact-audit-metadata-") as tmp:
            root = pathlib.Path(tmp)
            installed = subprocess.run(
                [sys.executable, str(init), "--target", str(root), "--apply"],
                text=True, capture_output=True,
            )
            self.assertEqual(
                installed.returncode, 0, installed.stdout + installed.stderr,
            )
            domain = root / "docs/product/domains/broken.md"
            domain.parent.mkdir(parents=True)
            domain.write_text(
                '+++\n[pact]\ntype = "domain"\nid = "DOMAIN-BROKEN"\n'
                'status = "confirmed"\nrelated = ["RULE-ONE", 42, { invalid = "record" }]\n+++\n'
                '# Broken domain\n',
                encoding="utf-8",
            )
            rule = root / "docs/product/rules/one.md"
            rule.parent.mkdir(parents=True)
            rule.write_text(
                '+++\n[pact]\ntype = "rule"\nid = "RULE-ONE"\n'
                'status = "confirmed"\ndomains = ["DOMAIN-BROKEN"]\n'
                '+++\n# Original confirmed source\n',
                encoding="utf-8",
            )
            checked = subprocess.run(
                [sys.executable, str(root / "pact.py"), "check"],
                cwd=root, capture_output=True, text=True,
            )
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("schema error", checked.stderr)

            audit = subprocess.run(
                [sys.executable, str(root / "pact.py"), "audit",
                 "--domain", "DOMAIN-BROKEN", "--json"],
                cwd=root, capture_output=True, text=True,
            )
            self.assertEqual(audit.returncode, 1, audit.stdout + audit.stderr)
            output = json.loads(audit.stdout)
            self.assertEqual(output["deterministic_check"], "fail")
            self.assertEqual(
                [x["id"] for x in output["scoped_sources"]], ["RULE-ONE"],
            )
            self.assertNotIn("TypeError", audit.stderr)
            self.assertNotIn("Traceback", audit.stderr)

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
