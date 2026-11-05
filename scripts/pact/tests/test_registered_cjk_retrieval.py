"""Sanitized owner-language regressions; no private project/session inputs."""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


RUNTIME = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME))
import discover
import explain


def document(**overrides):
    return {
        "path": "docs/product/domains/editing.md", "artifact_type": "domain",
        "id": "DOMAIN-EDITING", "status": "candidate", "title": "方案管理",
        "aliases": ["保存"], "text": "", "domains": [], "related": [],
        **overrides,
    }


class RegisteredCjkRetrievalTests(unittest.TestCase):
    def test_registered_single_token_chinese_title_and_alias_in_owner_sentence(self):
        for field in ("title", "aliases"):
            with self.subTest(field=field):
                doc = document(**({field: "专业选择"} if field == "title"
                                  else {field: ["专业选择"]}))
                self.assertEqual(len(discover.document_tokens("专业选择")), 1)
                score, reasons = discover.score_document(doc, "请检查专业选择确认后的显示")
                self.assertGreaterEqual(score, 80)
                self.assertIn(f"embedded exact {field[:-2] if field == 'aliases' else field}", reasons)

    def test_three_character_name_stays_exact_only(self):
        doc = document(title="导出单", aliases=[])
        _, embedded = discover.score_document(doc, "请检查导出单的显示")
        self.assertNotIn("embedded exact title", embedded)
        _, exact = discover.score_document(doc, "导出单")
        self.assertIn("exact title", exact)

    def test_english_word_noise_and_embedded_historical_status_are_preserved(self):
        self.assertFalse(discover.embedded_document_name("save", "autosave"))
        self.assertFalse(discover.document_term_matches("py", "Python policy"))
        doc = document(artifact_type="decision", status="archived",
                       id="DEC-EDITING", title="专业选择", aliases=[])
        _, embedded = discover.score_document(doc, "请检查专业选择确认后的显示")
        self.assertIn("historical decision (not current guidance)", embedded)
        _, exact = discover.score_document(doc, "DEC-EDITING")
        self.assertNotIn("historical decision (not current guidance)", exact)

    def test_weak_suggestions_are_bounded_registered_domain_names_only(self):
        docs = [document(path=f"docs/product/domains/{i}.md", title=f"保存入口{i}")
                for i in range(8)]
        docs += [document(artifact_type="rule", title="保存机密别名", aliases=[]),
                 document(status="retired", title="保存退役词", aliases=[]),
                 document(title="别的领域", aliases=[], text="保存正文不作建议")]
        index = {"documents": docs}
        before = json.dumps(index, ensure_ascii=False)
        suggestions = discover.domain_query_suggestions(index, ["看看保存失败后怎样恢复"])
        self.assertEqual(len(suggestions), 5)
        joined = " ".join(suggestions)
        self.assertNotIn("保存机密别名", joined)
        self.assertNotIn("保存退役词", joined)
        self.assertNotIn("保存正文不作建议", joined)
        self.assertIn("candidate", joined)
        self.assertIn("hypothesis only", joined)
        self.assertEqual(before, json.dumps(index, ensure_ascii=False))

    def test_zero_and_change_only_hits_explain_retrieval_scope_not_missing_truth(self):
        index = {"documents": [document()]}
        query = ["看看保存失败后怎样恢复"]
        empty = discover.retrieval_scope_gaps(index, query, [])
        self.assertIn("does not establish", empty[0])
        changes = discover.retrieval_scope_gaps(index, query, [document(artifact_type="change")])
        self.assertIn("Only Change", changes[0])
        self.assertEqual(discover.retrieval_scope_gaps(index, query, [document()]), [])

    def test_explain_keeps_primary_query_and_never_executes_suggestions(self):
        query = "看看保存失败后怎样恢复"
        index = {"documents": [document()]}
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            path = root / ".pact/cache/project-map.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(index), encoding="utf-8")
            with (patch.object(explain, "ROOT", root),
                  patch.object(explain, "build_index"),
                  patch.object(explain, "run_discovery", return_value={
                      "queries": [query], "results": []}) as retrieval,
                  patch.object(sys, "argv", ["explain", query, "--json"]),
                  contextlib.redirect_stdout(io.StringIO()) as stdout):
                self.assertEqual(explain.main(), 0)
            packet = json.loads(stdout.getvalue())
            self.assertEqual(explain.validate(packet), [])
            self.assertEqual(packet["query"], query)
            self.assertEqual(packet["queries"], [query])
            self.assertEqual(packet["product_truth"], [])
            self.assertEqual(packet["other"], [])
            self.assertIn("semantic-search", packet["followup"])
            self.assertNotIn("owner-confirmation", packet["followup"])
            self.assertTrue(any("Possible follow-up" in gap for gap in packet["gaps"]))
            retrieval.assert_called_once_with([query], path, 12)

    def test_installed_inspect_keeps_candidate_and_suggestions_non_authoritative(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            initialized = subprocess.run(
                [sys.executable, str(RUNTIME / "init.py"), "--target", td, "--apply"],
                capture_output=True, text=True,
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            domain = root / "docs/product/domains/editing.md"
            domain.parent.mkdir(parents=True)
            domain.write_text(
                '+++\n[pact]\ntype = "domain"\nid = "DOMAIN-EDITING"\n'
                'status = "candidate"\naliases = ["保存", "专业选择"]\n+++\n'
                '# 方案管理\n\nSynthetic navigation, not an approved requirement.\n',
                encoding="utf-8",
            )
            for query, embedded in [("请检查专业选择确认后的显示", True),
                                    ("看看保存失败后怎样恢复", False)]:
                with self.subTest(query=query):
                    process = subprocess.run(
                        [sys.executable, str(root / "pact.py"), "inspect", query,
                         "--no-code", "--json"], cwd=root, capture_output=True, text=True,
                    )
                    self.assertEqual(process.returncode, 0, process.stderr)
                    result = json.loads(process.stdout)
                    self.assertEqual(result["queries"], [query])
                    packet = result["explanation"]
                    self.assertEqual(packet["product_truth"], [])
                    hits = result["discovery"]["results"]
                    if embedded:
                        match = next(hit for hit in hits if hit["id"] == "DOMAIN-EDITING")
                        self.assertEqual(match["status"], "candidate")
                        self.assertIn("embedded exact alias", match["reasons"])
                    else:
                        self.assertFalse(any(hit["id"] == "DOMAIN-EDITING" for hit in hits))
                        self.assertTrue(any("Possible follow-up" in gap for gap in packet["gaps"]))
                        self.assertIn("semantic-search", result["next_steps"])
            task_query = "核查保存动作的恢复方案"
            change = root / "docs/changes/active/recovery.md"
            change.parent.mkdir(parents=True)
            change.write_text(
                '+++\n[pact]\ntype = "change"\nstatus = "active"\n+++\n'
                f'# {task_query}\n\nSynthetic plan only.\n', encoding="utf-8",
            )
            prepared = subprocess.run(
                [sys.executable, str(root / "pact.py"), "task", "prepare", task_query,
                 "--task-id", "TASK-RETRIEVAL", "--success", "Inspect recovery sources",
                 "--risk", "low", "--no-code", "--json"],
                cwd=root, capture_output=True, text=True,
            )
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            context = json.loads((root / ".pact/tasks/TASK-RETRIEVAL/context.json").read_text())
            self.assertEqual(context["discovery_queries"], [task_query])
            self.assertTrue(context["artifacts"])
            self.assertTrue(all(item["artifact_type"] == "change" for item in context["artifacts"]))
            self.assertEqual(context["applicable_rules"], [])
            self.assertTrue(any("Only Change" in gap for gap in context["known_unknowns"]))
            self.assertTrue(any("Possible follow-up" in gap for gap in context["known_unknowns"]))
            # Initial discovery also finds ordinary knowledge, but Context's
            # existing token budget drops it. Diagnose the final materialized
            # window, rather than trusting the unbudgeted discovery types.
            notes = root / "docs/recovery-notes.md"
            notes.write_text(
                f"# Recovery notes\n\n{task_query}\n" + "Synthetic ordinary notes. " * 5000,
                encoding="utf-8",
            )
            initial = subprocess.run(
                [sys.executable, str(root / "pact.py"), "discover", task_query, "--json"],
                cwd=root, capture_output=True, text=True,
            )
            self.assertEqual(initial.returncode, 0, initial.stderr)
            self.assertTrue(any(item["artifact_type"] == "document"
                                for item in json.loads(initial.stdout)["results"]))
            budgeted = subprocess.run(
                [sys.executable, str(root / "pact.py"), "task", "prepare", task_query,
                 "--task-id", "TASK-BUDGETED-RETRIEVAL", "--success", "Inspect recovery sources",
                 "--risk", "low", "--no-code", "--token-budget", "200", "--json"],
                cwd=root, capture_output=True, text=True,
            )
            self.assertEqual(budgeted.returncode, 0, budgeted.stderr)
            final = json.loads((root / ".pact/tasks/TASK-BUDGETED-RETRIEVAL/context.json").read_text())
            self.assertGreater(final["context_budget"]["dropped_for_token_budget"], 0)
            self.assertTrue(final["artifacts"])
            self.assertTrue(all(item["artifact_type"] == "change" for item in final["artifacts"]))
            self.assertTrue(any("Only Change" in gap for gap in final["known_unknowns"]))
            self.assertEqual(final["discovery_queries"], [task_query])
            self.assertEqual(final["applicable_rules"], [])


if __name__ == "__main__":
    unittest.main()
