"""Task-local reuse stays bounded, advisory and separate from truth approval."""

from __future__ import annotations

import hashlib
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import audit
import knowledge_reuse
from knowledge_retention import review as review_retention


class KnowledgeReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)

    def put(self, path, body):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        return {"path": path, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}

    def rule(self, path, ident, title, scope, prose="Reserve stock until payment."):
        return self.put(path,
                        f'+++\n[pact]\ntype = "rule"\nid = "{ident}"\n'
                        f'status = "confirmed"\ndomains = ["DOMAIN-ORDER"]\n+++\n'
                        f'# {ident} — {title}\n\n## Scope\n{scope}\n\n## Rule\n{prose}\n')

    def run_review(self, outputs, prepared=(), convergence=None):
        return knowledge_reuse.review(
            self.root, {"artifacts": list(prepared)}, convergence,
            {"supported": True, "changed_files": outputs}, {"kind": "git", "dirty_files": {}},
        )

    def test_none_for_routine_code_change_performs_no_reads_or_processes(self):
        with patch.object(pathlib.Path, "open", side_effect=AssertionError("unexpected read")), \
                patch("subprocess.run", side_effect=AssertionError("unexpected subprocess")):
            result = self.run_review(["src/order.py"], [{"path": "docs/product/rules/unused.md"}],
                                     {"knowledge_retention": {"disposition": "none"}})
        self.assertEqual(result["status"], "skipped-no-knowledge-output")
        self.assertEqual(result["files_read"], 0)
        self.assertFalse(result["repository_scan"])
        self.assertFalse(result["retrieval_invoked"])

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires POSIX FIFO")
    def test_named_pipe_is_unread_without_blocking_open(self):
        path = "docs/product/specs/pipe.md"
        target = self.root / path
        target.parent.mkdir(parents=True)
        os.mkfifo(target)
        with patch.object(pathlib.Path, "open", side_effect=AssertionError("FIFO must not be opened")):
            result = self.run_review([path])
        self.assertEqual(result["files_read"], 0)
        self.assertEqual(result["unread_sources"][0]["path"], path)
        self.assertIn("not a regular file", result["unread_sources"][0]["reason"])

    def test_broken_links_consume_bounded_attempt_and_diagnostic_budget(self):
        seed = self.put("docs/product/specs/topic.md", "# Topic\n" + "\n".join(
            f"[Missing {i}](missing-{i}.md)" for i in range(250)))
        result = self.run_review([seed["path"]])
        self.assertEqual(result["source_attempts"], knowledge_reuse.MAX_FILES)
        self.assertEqual(result["files_read"], 1)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["omitted_source_occurrences"], 250 - knowledge_reuse.MAX_FILES + 1)
        self.assertLessEqual(len(result["unread_sources"]), knowledge_reuse.MAX_FILES)
        self.assertGreater(result["unread_diagnostics_suppressed"], 0)

    def test_domain_linked_plain_spec_is_unconfirmed_and_no_global_scan(self):
        router = self.put("docs/product/domains/order.md",
                          '+++\n[pact]\ntype="domain"\nid="DOMAIN-ORDER"\nstatus="confirmed"\n+++\n'
                          '# Orders\n[Process](../specs/order.md)\n')
        spec = self.put("docs/product/specs/order.md", "# Stock reservation\n\n## Scope\nOnline orders.\n")
        new = self.rule("docs/product/rules/new.md", "RULE-NEW", "Stock reservation", "Online orders.")
        self.put("docs/product/specs/unlinked.md", "# Stock reservation\n")
        with patch.object(pathlib.Path, "rglob", side_effect=AssertionError("no repository walk")):
            result = self.run_review([new["path"]], [router])
        plain = next(s for s in result["sources"] if s["path"] == spec["path"])
        self.assertEqual(plain["artifact_type"], "document")
        self.assertIsNone(plain["status"])
        self.assertFalse(plain["confirmation_inferred"])
        self.assertFalse(plain["agent_read_verified"])
        self.assertEqual(len(result["possible_overlaps"]), 1)
        self.assertNotIn("docs/product/specs/unlinked.md", [s["path"] for s in result["sources"]])
        self.assertFalse(result["absence_of_duplicates_verified"])

    def test_independent_branch_same_title_different_scopes_remains_advisory(self):
        a = self.rule("docs/product/rules/a.md", "RULE-A", "Stock reservation", "2025: student role.")
        b = self.rule("docs/product/rules/b.md", "RULE-B", "Stock reservation", "2026: operator role.")
        result = self.run_review([a["path"], b["path"]])
        hint = result["possible_overlaps"][0]
        self.assertEqual(hint["ids"], ["RULE-A", "RULE-B"])
        self.assertEqual(hint["scopes"], ["2025: student role.", "2026: operator role."])
        self.assertIn("no semantic verdict", hint["reason"])
        self.assertFalse(result["semantic_verification"])
        self.assertTrue((self.root / a["path"]).exists())
        self.assertTrue((self.root / b["path"]).exists())

    def test_shared_body_terms_signal_reordered_prose_without_confirmation(self):
        a = {"title": "Inventory hold", "text": "Pending payment orders reserve inventory until settlement or cancellation."}
        b = {"title": "Payment reservations", "text": "Until cancellation or settlement, reserve inventory for orders pending payment."}
        self.assertEqual(audit.overlap_signal(a, b), "shared-body-terms")

    def test_changed_prepared_source_cannot_be_used_as_aligned_proof(self):
        a = self.rule("docs/product/rules/a.md", "RULE-A", "Stock reservation", "2026")
        self.rule(a["path"], "RULE-A", "Stock reservation", "2027")
        result = self.run_review([a["path"]], [a])
        self.assertTrue(result["sources"][0]["prepared_source_changed"])
        self.assertTrue(any("aligned" in x for x in result["limitations"]))

    def test_standard_applies_to_scope_is_preserved_as_context(self):
        seed = self.put("docs/product/rules/order.md", "# Orders\n\n## Applies to\n2026 students; excludes trial accounts.\n")
        result = self.run_review([seed["path"]])
        self.assertEqual(result["sources"][0]["scope"], "2026 students; excludes trial accounts.")
        self.assertTrue(any("contextual excerpts" in x for x in result["limitations"]))
        self.put(seed["path"], "# Orders\n\n> **适用范围**：2026 学生；不含试用账户。\n")
        self.assertEqual(self.run_review([seed["path"]])["sources"][0]["scope"], "2026 学生；不含试用账户。")

    def test_route_candidates_and_prepared_retrieval_omissions_remain_visible(self):
        a = self.rule("docs/product/rules/a.md", "RULE-A", "Stock reservation", "2026")
        b = self.rule("docs/product/rules/b.md", "RULE-B", "Stock reservation", "2026")
        result = knowledge_reuse.review(
            self.root, {"artifacts": [], "scope_route": {"candidates": [b], "truncated_candidates": 3},
                        "context_budget": {"dropped_candidates": 2}}, None,
            {"supported": True, "changed_files": [a["path"]]}, {},
        )
        self.assertEqual(len(result["possible_overlaps"]), 1)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["prepared_retrieval_omissions"]["route_truncated_candidates"], 3)

    def test_angle_and_encoded_links_recall_local_files_and_unknown_syntax_is_visible(self):
        seed = self.put("docs/product/specs/order.md",
                        '# Orders\n[Angle](<scope space.md>)\n[Encoded](scope%20space.md "Scope")\n'
                        '[Special]({{ site.baseurl }}/scope.md)\n')
        linked = self.put("docs/product/specs/scope space.md", "# Student scope\n")
        result = self.run_review([seed["path"]])
        self.assertEqual({x["path"] for x in result["sources"]}, {seed["path"], linked["path"]})
        self.assertEqual(len(result["unresolved_references"]), 1)

    def test_malformed_metadata_is_unread_not_promoted_to_ordinary_document(self):
        for body in ['+++\npact = "wrong"\n+++\n# Order\n',
                     '+++\n[pact]\nstatus="confirmed"\n+++\n# Order\n',
                     '+++\n[pact]\ntype="spec"\n+++\n# Unsupported type\n',
                     '---\npact:\n  type: rule\n---\n# Old metadata\n']:
            with self.subTest(body=body):
                seed = self.put("docs/product/rules/broken.md", body)
                result = self.run_review([seed["path"]])
                self.assertEqual(result["sources"], [])
                self.assertEqual(result["unread_sources"][0]["path"], seed["path"])

    def test_malformed_retention_fields_do_not_crash_candidate_helper(self):
        seed = self.put("docs/product/specs/order.md", "# Order\n")
        for entry in [None, [], {"updated": 5, "created": None}, {"updated": [None], "created": {}}]:
            with self.subTest(entry=entry):
                result = self.run_review([seed["path"]], convergence={"knowledge_retention": entry})
                self.assertEqual(result["files_read"], 1)
                self.assertTrue(any("Malformed knowledge-retention" in x for x in result["limitations"]))

    def test_missing_large_and_escaping_sources_are_disclosed(self):
        seed = self.put("docs/product/specs/order.md",
                        "# Orders\n[Missing](missing.md)\n[Escape](../../../../outside.md)\n[Large](large.md)\n")
        self.put("docs/product/specs/large.md", "x" * (knowledge_reuse.MAX_FILE_BYTES + 1))
        result = self.run_review([seed["path"]])
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["unread_sources"]), 2)
        self.assertEqual(len(result["unresolved_references"]), 1)
        self.assertEqual(result["files_read"], 1)

    def test_existing_prepared_or_dirty_source_cannot_be_declared_created(self):
        path = "docs/product/specs/order.md"
        entry = {"knowledge_retention": {"disposition": "create", "rationale": "Retained process.",
                                          "created": [path], "updated": []}}
        for kwargs in [{"prepared_paths": [path]}, {"prepared_file_states": {path: "sha256:abc"}}]:
            with self.subTest(kwargs=kwargs):
                errors, _ = review_retention(entry, changed_files=[path], **kwargs)
                self.assertIn("already existed at preparation", " ".join(errors))
        errors, stats = review_retention(entry, changed_files=[path])
        self.assertEqual(errors, [])
        self.assertFalse(stats["kind_of_change_verified"])
        self.assertEqual(stats["operation_kind_unknown"], [path])
        errors, stats = review_retention(entry, prepared_file_states={path: "missing"})
        self.assertEqual(errors, [])
        self.assertTrue(stats["kind_of_change_verified"])
        self.assertIn("not knowledge novelty", stats["operation_kind_interpretation"])

    def test_audit_includes_linked_plain_specs_without_promoting_authority(self):
        docs = [
            {"path": "docs/product/domains/order.md", "artifact_type": "domain", "id": "DOMAIN-ORDER",
             "status": "confirmed", "links": ["../specs/order.md"]},
            {"path": "docs/product/specs/order.md", "artifact_type": "document", "id": None,
             "status": None, "title": "Stock reservation", "text": "Pending order stock."},
            {"path": "docs/product/rules/order.md", "artifact_type": "rule", "id": "RULE-ORDER",
             "status": "candidate", "title": "RULE-ORDER — Stock reservation", "domains": ["DOMAIN-ORDER"]},
        ]
        result = audit.knowledge_review_candidates(docs, domain="DOMAIN-ORDER")
        self.assertEqual(len(result["possible_knowledge_overlaps"]), 1)
        self.assertEqual(result["scoped_sources_count"], 2)
        spec = next(s for s in result["scoped_sources"] if s["artifact_type"] == "document")
        self.assertIsNone(spec["status"])


if __name__ == "__main__":
    unittest.main()
