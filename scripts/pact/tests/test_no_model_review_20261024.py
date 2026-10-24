"""PACT-only no-model review probes for Decision/control-plane boundaries.

Developer-authored engineering cases, NOT a blinded Agent/Owner trial.
The count-cap gate is verified on an actual source-bound Context.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / "scripts" / "pact"))

import context as pact_context
import discover
from convergence_coverage import review as review_coverage


class NoModelAdversarialReview(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="pact-no-model-review-")
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)

    def put(self, name: str, content: str) -> pathlib.Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_routine_scattered_terms_do_not_promote_unrelated_decision(self):
        task = "Tidy unit test scaffolding"
        rel = ".agents/decisions/implemented/payment-auth.md"
        raw = (
            '# Payment authorization policy\n'
            'A new unit must be isolated from payment verification.\n'
            'The old test ran after billing validation; the scaffolding is tidy.\n'
        )
        self.put(rel, raw)
        doc = {
            "id": "DEC-PAYMENT-AUTH", "artifact_type": "decision",
            "status": "implemented", "title": "Payment authorization policy",
            "aliases": [], "domains": [], "text": raw,
        }
        score, reasons = discover.score_document(doc, task)
        self.assertGreater(score, 0)
        self.assertIn("all query terms matched", reasons)
        hit = {**doc, "path": rel, "score": score, "reasons": reasons}
        with patch.object(pact_context, "ROOT", self.root):
            selected, hints = pact_context.split_weak_lexical_decisions([hit], task)
        self.assertEqual(selected, [], "scattered body tokens are not authority")
        self.assertEqual([x["id"] for x in hints], ["DEC-PAYMENT-AUTH"])

    def test_mixed_pending_rule_sections_are_not_wholly_confirmed(self):
        mixed = {
            "artifact_type": "rule", "status": "confirmed",
            "text": "# Confirmed pricing\n\n## Pending confirmation\nNew limit not approved.\n",
        }
        self.assertTrue(discover.mixed_rule_authority(mixed))
        fenced = {
            **mixed,
            "text": "# Confirmed pricing\n\n~~~md\n## Pending confirmation\n~~~\n",
        }
        self.assertFalse(discover.mixed_rule_authority(fenced))

    def test_user_controlled_query_label_cannot_impersonate_exact_id(self):
        fake = {"path": "noise.md", "score": 2000,
                "reasons": ["body contains query"], "artifact_type": "decision"}
        exact = {"path": "verified.md", "score": 1,
                 "reasons": ["exact stable id"], "artifact_type": "decision"}
        rows = discover.fuse_ranked_results([
            ("matched query: exact stable id", [fake]),
            ("DEC-VERIFIED", [exact]),
        ], 1, preserve_exact=True)
        self.assertEqual([item["path"] for item in rows], ["verified.md"])

    def test_deferred_source_hash_change_blocks_aligned_claim(self):
        rel = ".agents/decisions/implemented/rate-limit.md"
        path = self.put(rel, "# Rate limit\n\nCurrent decision: deny unlimited calls.\n")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        ctx = {"artifacts": [], "weak_decision_hints": {
            "total_candidates": 1, "truncated_candidates": 0,
            "candidates": [{"id": "DEC-RATE-LIMIT", "path": rel,
                            "title": "Rate limit", "status": "implemented",
                            "sha256": digest}],
        }}
        ctx_path = self.put("context.json", json.dumps(ctx))
        ctx_sha = hashlib.sha256(ctx_path.read_bytes()).hexdigest()
        report = {"context_sha256": ctx_sha, "findings": [], "coverage": [
            {"path": rel, "disposition": "aligned", "rationale": "Reviewed original policy"}
        ]}
        errors, _ = review_coverage(ctx, report, root=self.root,
                                    context_path=ctx_path,
                                    expected_context_sha256=ctx_sha)
        self.assertEqual(errors, [], errors)
        path.write_text("# Rate limit\n\nCurrent decision: allow unlimited calls.\n",
                        encoding="utf-8")
        errors, _ = review_coverage(ctx, report, root=self.root,
                                    context_path=ctx_path,
                                    expected_context_sha256=ctx_sha)
        self.assertTrue(any("changed since Task preparation" in x for x in errors), errors)

    def test_truncated_hints_cannot_be_accepted_as_complete_coverage(self):
        rel = ".agents/decisions/implemented/cap.md"
        path = self.put(rel, "# Cap\n")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        ctx = {"artifacts": [], "weak_decision_hints": {
            "total_candidates": 2, "truncated_candidates": 1,
            "candidates": [{"id": "DEC-CAP", "path": rel,
                            "title": "Cap", "status": "implemented",
                            "sha256": digest}],
        }}
        ctx_path = self.put("context.json", json.dumps(ctx))
        ctx_sha = hashlib.sha256(ctx_path.read_bytes()).hexdigest()
        report = {"context_sha256": ctx_sha, "findings": [], "coverage": [
            {"path": rel, "disposition": "aligned", "rationale": "Reviewed"}
        ]}
        errors, _ = review_coverage(ctx, report, root=self.root,
                                    context_path=ctx_path,
                                    expected_context_sha256=ctx_sha)
        self.assertTrue(any("unlisted or inconsistent" in x for x in errors), errors)

    def test_no_id_task_finds_real_source_titled_decision(self):
        """A new task names behavior but supplies neither Decision ID nor title."""
        task = "Protect CSV export when spreadsheet formulas are present"
        rel = ".agents/decisions/implemented/spreadsheet-export.md"
        raw = (
            "# CSV export integrity\n"
            "Spreadsheet formulas must be escaped before sharing exported rows.\n"
            "Rationale: prevent untrusted export cells from becoming commands.\n"
        )
        self.put(rel, raw)
        doc = {
            "id": "DEC-EXPORT-CELLS", "artifact_type": "decision",
            "status": "implemented", "title": "CSV export integrity",
            "aliases": [], "domains": [], "text": raw,
        }
        score, reasons = discover.score_document(doc, task)
        self.assertGreater(score, 0)
        hit = {**doc, "path": rel, "score": score, "reasons": reasons}
        with patch.object(pact_context, "ROOT", self.root):
            selected, hints = pact_context.split_weak_lexical_decisions([hit], task)
        self.assertEqual([x["id"] for x in selected], ["DEC-EXPORT-CELLS"])
        self.assertEqual(hints, [])

    def test_superseded_rationale_stays_retrievable_without_becoming_current(self):
        old = {
            "id": "DEC-OLD-NOTIFY", "artifact_type": "decision",
            "status": "superseded",
            "title": "Allow notifications without consent",
            "aliases": [], "domains": [],
            "text": "Legacy notifications without consent were once allowed.",
        }
        generic_score, generic_reasons = discover.score_document(
            old, "notifications without consent",
        )
        id_score, id_reasons = discover.score_document(old, "DEC-OLD-NOTIFY")
        self.assertIn("historical decision (not current guidance)", generic_reasons)
        self.assertIn("exact stable id", id_reasons)
        self.assertGreater(id_score, generic_score)
        self.assertFalse(pact_context.knowledge_priority({**old, "score": id_score})[1])
        active = {**old, "status": "implemented"}
        self.assertTrue(pact_context.knowledge_priority(active)[1])

    def test_no_required_proof_cannot_satisfy_task_acceptance(self):
        from evidence import readiness as evidence_readiness
        from task_contract import acceptance_review
        contract = {
            "task_id": "TASK-REVIEW",
            "acceptance_criteria": [
                {"id": "AC-1", "kind": "outcome",
                 "text": "Preserve the original policy"}
            ],
        }
        evidence = {
            "task_id": "TASK-REVIEW", "risk_level": "low",
            "claims": [], "limitations": [],
        }
        owner = {
            "task_id": "TASK-REVIEW", "status": "completed",
            "acceptance": [], "verification": [],
        }
        errors, stats = acceptance_review(contract, evidence, owner)
        self.assertTrue(any("no passing Evidence" in x for x in errors))
        self.assertEqual(stats["evidence_verified"], 0)
        self.assertEqual(evidence_readiness(evidence), "incomplete")

    def test_known_count_omitted_authority_must_block_completion(self):
        """A missing current authority candidate requires widened Context."""
        records = []
        for index in (1, 2):
            rel = f"docs/product/rules/policy-{index}.md"
            self.put(rel, f"# Confirmed policy {index}\n")
            records.append({"path": rel, "id": f"RULE-{index}",
                            "artifact_type": "rule", "status": "confirmed",
                            "mixed_authority": False, "score": 100-index})
        with patch.object(pact_context, "ROOT", self.root):
            selected, _, budget = pact_context.select_context_candidates(
                records, [], token_budget=0, knowledge_limit=1, code_limit=1)
        self.assertEqual(len(selected), 1)
        self.assertEqual(budget["authority_candidates_dropped"], 1)
        artifact = {"path": selected[0]["path"],
                    "sha256": hashlib.sha256(
                        (self.root / selected[0]["path"]).read_bytes()
                    ).hexdigest()}
        ctx = {"artifacts": [artifact], "context_budget": budget}
        ctx_path = self.put("context.json", json.dumps(ctx))
        ctx_sha = hashlib.sha256(ctx_path.read_bytes()).hexdigest()
        report = {"context_sha256": ctx_sha, "findings": [], "coverage": [
            {"path": artifact["path"], "disposition": "aligned", "rationale": "Checked"}
        ]}
        errors, _ = review_coverage(ctx, report, root=self.root,
                                    context_path=ctx_path,
                                    expected_context_sha256=ctx_sha)
        self.assertTrue(errors, "known omitted authority must not pass Convergence")


if __name__ == "__main__":
    unittest.main()
