"""No-model regression: explicit low-risk no-behavior-change retrieval is opt-in.

The default remains unchanged. Deferred implemented Decisions are never
silently declared inapplicable or source-independent.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))
import context


class NonfunctionalCandidateTests(unittest.TestCase):
    def hit(self, ident: str, reasons: list[str], *, kind: str = "decision") -> dict:
        return {
            "id": ident, "path": f".agents/decisions/{ident.lower()}.md",
            "title": ident, "artifact_type": kind, "status": "implemented",
            "reasons": reasons, "score": 8,
        }

    def test_defer_only_nonexplicit_decisions_and_keep_canonical_order(self):
        weak = self.hit("DEC-WEAK", ["body contains query"])
        exact_id = self.hit("DEC-ID", ["exact stable id"])
        exact_title = self.hit("DEC-TITLE", ["embedded exact title"])
        exact_alias = self.hit("DEC-ALIAS", ["secondary: exact alias"])
        fake_reason = self.hit("DEC-QUERY-SPOOF", ["matched query: exact stable id"])
        rule = self.hit("RULE-SAFE", ["body contains query"], kind="rule")
        document = self.hit("NONE", ["body contains query"], kind="document")
        records = [weak, rule, exact_id, document, fake_reason, exact_title, exact_alias]
        keep, deferred = context.split_nonfunctional_decisions(records)
        self.assertEqual(
            [r["id"] for r in keep],
            ["RULE-SAFE", "DEC-ID", "NONE", "DEC-TITLE", "DEC-ALIAS"],
        )
        self.assertEqual([r["id"] for r in deferred], ["DEC-WEAK", "DEC-QUERY-SPOOF"])
        self.assertEqual([r["id"] for r in records], [r["id"] for r in [
            weak, rule, exact_id, document, fake_reason, exact_title, exact_alias
        ]])

    def test_hints_are_bounded_source_bound_and_reject_missing(self):
        with tempfile.TemporaryDirectory(prefix="pact-nonfunctional-hints-") as td:
            root = pathlib.Path(td)
            entries = []
            for n in range(7):
                relative = f".agents/decisions/dec-weak-{n}.md"
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f"# Source truth {n}\n", encoding="utf-8")
                item = self.hit(f"DEC-WEAK-{n}", ["body contains query"])
                item["path"] = relative
                entries.append(item)
            with patch.object(context, "ROOT", root):
                packet = context.nonfunctional_decision_hints(entries)
                self.assertEqual(packet["total_candidates"], 7)
                self.assertEqual(packet["truncated_candidates"], 2)
                self.assertEqual(len(packet["candidates"]), 5)
                for hint in packet["candidates"]:
                    digest = hashlib.sha256((root / hint["path"]).read_bytes()).hexdigest()
                    self.assertEqual(hint["sha256"], digest)
                    self.assertNotIn("text", hint)
                (root / entries[0]["path"]).unlink()
                with self.assertRaisesRegex(ValueError, "source missing"):
                    context.nonfunctional_decision_hints(entries)

    def test_hints_fail_closed_on_missing_id(self):
        with tempfile.TemporaryDirectory(prefix="pact-nonfunctional-invalid-") as td:
            root = pathlib.Path(td)
            file = root / ".agents/decisions/test.md"
            file.parent.mkdir(parents=True)
            file.write_text("# Test\n", encoding="utf-8")
            item = self.hit("DEC-WEAK", ["body contains query"])
            item.update(id=None, path=".agents/decisions/test.md")
            with patch.object(context, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "stable ID"):
                    context.nonfunctional_decision_hints([item])


class InstalledNonfunctionalContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pact-installed-nonfunctional-")
        self.root = pathlib.Path(self.tmp.name) / "project"
        self.root.mkdir()
        (self.root / "README.md").write_text("# Example App\n", encoding="utf-8")
        init = subprocess.run(
            [sys.executable, str(ROOT / "scripts/pact/init.py"),
             "--target", str(self.root), "--apply"],
            capture_output=True, text=True,
        )
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        decision = self.root / ".agents/decisions/implemented/local-isolation.md"
        decision.parent.mkdir(parents=True, exist_ok=True)
        decision.write_text(
            '+++\n[pact]\ntype = "decision"\nid = "DEC-LOCAL-ISOLATION"\n'
            'status = "implemented"\naliases = ["test isolation policy"]\n'
            '+++\n# Local test isolation standard\n\n'
            'A local test variable rename must preserve production behavior '
            'and test isolation.\n',
            encoding="utf-8",
        )
        rule = self.root / "docs/product/rules/preserve-assertions.md"
        rule.parent.mkdir(parents=True, exist_ok=True)
        rule.write_text(
            '+++\n[pact]\ntype = "rule"\nid = "RULE-PRESERVE-ASSERTIONS"\n'
            'status = "confirmed"\n+++\n# Preserve local test assertions\n\n'
            'Local test renaming must not change assertions.\n',
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def pact(self, *args):
        return subprocess.run(
            [sys.executable, str(self.root / "pact.py"), *args],
            cwd=self.root, capture_output=True, text=True,
        )

    def context(self, task, *extra):
        return self.pact(
            "context", task, "--success", "Preserve current assertions",
            "--risk", "low", "--intent", "work",
            "--limit", "16", "--token-budget", "0", "--no-code", *extra,
        )

    def test_default_keeps_implicit_decision_but_nonfunctional_defers_it(self):
        task = "Rename a local test variable without changing production behavior"
        normal = self.context(task)
        self.assertEqual(normal.returncode, 0, normal.stderr)
        original = json.loads(normal.stdout)
        self.assertIn("DEC-LOCAL-ISOLATION", original["decisions"])
        self.assertIn("RULE-PRESERVE-ASSERTIONS", original["applicable_rules"])
        self.assertNotIn("nonfunctional_decision_hints", original)

        lean = self.context(task, "--nonfunctional")
        self.assertEqual(lean.returncode, 0, lean.stderr)
        packet = json.loads(lean.stdout)
        self.assertNotIn("DEC-LOCAL-ISOLATION", packet["decisions"])
        self.assertIn("RULE-PRESERVE-ASSERTIONS", packet["applicable_rules"])
        self.assertEqual(
            [d["id"] for d in packet["nonfunctional_decision_hints"]["candidates"]],
            ["DEC-LOCAL-ISOLATION"],
        )
        self.assertTrue(any(
            "rerun WITHOUT --nonfunctional" in warning
            for warning in packet["known_unknowns"]
        ))
        # No unmaterialized Decision may claim verification or authority.
        self.assertNotIn(
            "DEC-LOCAL-ISOLATION",
            [d["id"] for d in packet["artifacts"]],
        )
        self.assertLess(
            packet["context_budget"]["selected_estimated_tokens"],
            original["context_budget"]["selected_estimated_tokens"],
        )

    def test_explicit_decision_id_title_and_alias_are_still_materialized(self):
        for task in [
            "Review DEC-LOCAL-ISOLATION only; do not alter behavior",
            "Review Local test isolation standard language only",
            "Review the test isolation policy language only",
        ]:
            with self.subTest(task=task):
                out = self.context(task, "--nonfunctional")
                self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
                packet = json.loads(out.stdout)
                self.assertIn("DEC-LOCAL-ISOLATION", packet["decisions"])
                self.assertEqual(packet["nonfunctional_decision_hints"]["total_candidates"], 0)

    def test_reject_unsafe_risk_or_history_or_conflicting_routing(self):
        for mode in [
            ("--risk", "medium"),
            ("--risk", "high"),
            ("--intent", "history"),
            ("--intent", "decision"),
            ("--scope-first",),
        ]:
            with self.subTest(mode=mode):
                options = [
                    "context", "Rename local test variable",
                    "--success", "Unchanged functional behavior",
                    "--nonfunctional",
                ]
                if mode[0] == "--scope-first":
                    options.extend(["--risk", "low", "--scope-first"])
                elif mode[0] == "--risk":
                    options.extend(mode)
                else:
                    options.extend(["--risk", "low", *mode])
                result = self.pact(*options)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("--nonfunctional", result.stderr)

    def test_task_prepare_forwarding_and_default_unaltered(self):
        task = "Rename a local test variable without changing production behavior"
        done = self.pact(
            "task", "prepare", task, "--success", "Existing behavior preserved",
            "--risk", "low", "--intent", "work", "--nonfunctional",
            "--task-id", "TASK-NONFUNCTIONAL-ONE", "--json",
        )
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        receipt = json.loads(done.stdout)
        packet = json.loads(
            (self.root / receipt["context"]).read_text(encoding="utf-8")
        )
        self.assertIn("nonfunctional_decision_hints", packet)
        self.assertNotIn("DEC-LOCAL-ISOLATION", packet["decisions"])

        normal = self.pact(
            "task", "prepare", task, "--success", "Existing behavior preserved",
            "--risk", "low", "--intent", "work",
            "--task-id", "TASK-NONFUNCTIONAL-NORMAL", "--json",
        )
        self.assertEqual(normal.returncode, 0, normal.stdout + normal.stderr)
        normal_receipt = json.loads(normal.stdout)
        normal_packet = json.loads(
            (self.root / normal_receipt["context"]).read_text(encoding="utf-8")
        )
        self.assertIn("DEC-LOCAL-ISOLATION", normal_packet["decisions"])
        self.assertNotIn("nonfunctional_decision_hints", normal_packet)


if __name__ == "__main__":
    unittest.main()
