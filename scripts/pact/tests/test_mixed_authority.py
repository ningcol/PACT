"""Review-only detection for explicitly mixed-confirmation Product Rules."""

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
            "## 待确认事项",
            "## 待确认需求：门户页面",
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
            "# Good\n\n````markdown\n```\n## 待确认\n```\n````",
            "# Good\n\n~~~~markdown\n~~~\n## 未确认\n~~~\n~~~~",
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
        self.assertEqual(mixed["mixed_authority"], True
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


class MixedAuthorityIntegrationTests(unittest.TestCase):
    def test_initialized_project_keeps_mixed_rule_non_normative(self) -> None:
        """End-to-end: Project Map -> Discovery -> Context -> Audit."""
        init = ROOT / "scripts" / "pact" / "init.py"
        with tempfile.TemporaryDirectory(prefix="pact-mixed-rule-") as tmp:
            target = pathlib.Path(tmp) / "project"
            target.mkdir()
            (target / "README.md").write_text("# User project\n", encoding="utf-8")
            initialized = subprocess.run(
                [sys.executable, str(init), "--target", str(target), "--apply"],
                capture_output=True, text=True,
            )
            self.assertEqual(
                initialized.returncode, 0,
                initialized.stdout + initialized.stderr,
            )
            rules = target / "docs" / "product" / "rules"
            rules.mkdir(parents=True, exist_ok=True)
            (rules / "home-mixed.md").write_text(
                '+++\n[pact]\ntype = "rule"\nid = "RULE-HOME-MIXED"\n'
                'status = "confirmed"\nverification = ["tests/mixed.py"]\n'
                '+++\n# Home\n\n## 已确认\nWork.\n\n## 待确认\nQuestion.\n',
                encoding="utf-8",
            )
            (rules / "home-clean.md").write_text(
                '+++\n[pact]\ntype = "rule"\nid = "RULE-HOME-CLEAN"\n'
                'status = "confirmed"\nverification = ["tests/clean.py"]\n'
                '+++\n# Home\n\nThe existing confirmed behavior.\n',
                encoding="utf-8",
            )
            def pact(*args: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [sys.executable, str(target / "pact.py"), *args],
                    cwd=target, capture_output=True, text=True,
                )

            prepared = pact(
                "context", "Home",
                "--success", "Home behavior follows confirmed intent",
                "--risk", "medium", "--no-code",
                "--output", ".pact/cache/mixed-context.json",
            )
            self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
            context_file = target / ".pact" / "cache" / "mixed-context.json"
            envelope = json.loads(context_file.read_text(encoding="utf-8"))
            selected = {item["id"]: item for item in envelope["artifacts"] if item.get("id")}
            self.assertTrue(selected["RULE-HOME-MIXED"]["mixed_authority"])
            self.assertFalse(selected["RULE-HOME-CLEAN"]["mixed_authority"])
            self.assertEqual(envelope["applicable_rules"], ["RULE-HOME-CLEAN"])
            self.assertEqual(envelope["verification_targets"], ["tests/clean.py"])
            self.assertTrue(any(
                "mixed" in item.lower() or "unconfirmed" in item.lower()
                for item in envelope["known_unknowns"]
            ))

            audited = pact("audit", "--json")
            self.assertEqual(audited.returncode, 0, audited.stdout + audited.stderr)
            report = json.loads(audited.stdout)
            self.assertEqual(
                [item["id"] for item in report["mixed_rule_candidates"]],
                ["RULE-HOME-MIXED"],
            )


if __name__ == "__main__":
    unittest.main()
