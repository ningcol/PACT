"""S3: opt-in intent, explicit Rule authority and metadata-only path hints."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))

import context
from discover import rerank_for_intent


def artifact(identifier, kind="rule", status="confirmed", *, mixed=False, score=10):
    return {
        "id": identifier, "path": f"docs/product/{identifier}.md",
        "artifact_type": kind, "status": status,
        "mixed_authority": mixed, "score": score, "reasons": [],
    }


class ExplicitRuleAndIntentTests(unittest.TestCase):
    def test_default_intent_does_not_change_lexical_order(self):
        docs = [
            artifact("DEC-OLD", "decision", "superseded", score=90),
            artifact("RULE-ONE", score=80),
        ]
        self.assertEqual(rerank_for_intent(docs, None), docs)

    def test_retrieval_intents_prioritize_without_promoting_authority(self):
        items = [
            artifact("DEC-PAST", "decision", "superseded", score=100),
            artifact("DEC-NO", "decision", "rejected", score=50),
            artifact("RULE-LIVE", score=30),
            artifact("DEC-YES", "decision", "implemented", score=40),
        ]
        self.assertEqual(rerank_for_intent(items, "work")[0]["id"], "RULE-LIVE")
        self.assertIn(
            rerank_for_intent(items, "decision")[0]["id"],
            {"DEC-NO", "DEC-YES"},
        )
        self.assertIn(
            rerank_for_intent(items, "history")[0]["id"],
            {"DEC-PAST", "DEC-NO"},
        )

    def test_explicit_rule_must_be_selected_and_wholly_confirmed(self):
        rule = artifact("RULE-VALID")
        self.assertEqual(context.required_rule_gaps(
            ["RULE-VALID"], [rule], [rule], {},
        ), [])
        for item, reason in [
            (artifact("RULE-VALID", status="pending"), "not confirmed"),
            (artifact("RULE-VALID", mixed=True), "mixed"),
            (artifact("RULE-VALID", kind="domain"), "non-Rule"),
            (artifact("RULE-VALID"), "budget"),
        ]:
            with self.subTest(reason=reason):
                gaps = context.required_rule_gaps(
                    ["RULE-VALID"], [], [item], {},
                )
                self.assertEqual(len(gaps), 1)
                self.assertIn(reason, gaps[0])

    def test_context_and_task_prepare_fail_closed_on_explicit_missing_rule(self):
        with tempfile.TemporaryDirectory(prefix="pact-s3-rule-cli-") as td:
            target = pathlib.Path(td) / "adopted"
            initialized = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "pact" / "init.py"),
                 "--target", str(target), "--apply"],
                capture_output=True, text=True,
            )
            self.assertEqual(
                initialized.returncode, 0,
                initialized.stdout + initialized.stderr,
            )
            output = target / ".pact" / "tmp" / "missing-rule-context.json"
            ctx = subprocess.run(
                [sys.executable, str(target / "pact.py"), "context",
                 "Fix an unrelated task", "--success", "Observable behavior",
                 "--risk", "medium", "--no-code",
                 "--require-rule", "RULE-ABSENT",
                 "--output", str(output)],
                cwd=target, capture_output=True, text=True,
            )
            self.assertEqual(ctx.returncode, 2, ctx.stdout + ctx.stderr)
            self.assertIn("required Rule RULE-ABSENT", ctx.stderr)
            self.assertFalse(output.exists())
            prep = subprocess.run(
                [sys.executable, str(target / "pact.py"),
                 "task", "prepare", "Fix an unrelated task",
                 "--task-id", "TASK-MISSING-RULE",
                 "--success", "Observable behavior",
                 "--risk", "medium", "--no-code",
                 "--require-rule", "RULE-ABSENT", "--json"],
                cwd=target, capture_output=True, text=True,
            )
            self.assertEqual(prep.returncode, 2, prep.stdout + prep.stderr)
            self.assertIn("required Rule RULE-ABSENT", prep.stderr)
            self.assertFalse((
                target / ".pact" / "tasks" / "TASK-MISSING-RULE" / "task.json"
            ).exists())

    def test_missing_explicit_rule_remains_error(self):
        gaps = context.required_rule_gaps(
            ["RULE-ABSENT"], [], [], {"RULE-ABSENT": None},
        )
        self.assertEqual(len(gaps), 1)
        self.assertIn("absent", gaps[0])
        self.assertTrue(context.RULE_ID.fullmatch("RULE-ABC-1"))
        self.assertFalse(context.RULE_ID.fullmatch("../../file"))
        self.assertFalse(context.RULE_ID.fullmatch("DOMAIN-ABC"))

    def test_exact_id_lookup_does_not_replace_confirmed_required_status(self):
        exact = artifact("RULE-FROM-EXACT", status="candidate")
        gaps = context.required_rule_gaps(
            ["RULE-FROM-EXACT"], [], [], {"RULE-FROM-EXACT": exact},
        )
        self.assertTrue(any("not confirmed" in text for text in gaps), gaps)

    def test_metadata_hints_bounded_and_do_not_open_readme_content(self):
        with tempfile.TemporaryDirectory(prefix="pact-s3-readme-") as d:
            project = pathlib.Path(d)
            (project / "src" / "api").mkdir(parents=True)
            (project / "src" / "README.md").write_text(
                "# Parent module explanation\n"
            )
            (project / "src" / "api" / "README.md").write_text(
                "# Local explanation\n"
            )
            (project / "src" / "api" / "engine.py").write_text(
                "def engine(): pass\n"
            )
            with mock.patch.object(context, "ROOT", project):
                hints = context.nearby_readme_hints(
                    [{"path": "src/api/engine.py"}], limit=1,
                )
            self.assertEqual(len(hints), 1)
            self.assertIn("src/api/README.md", hints[0])
            self.assertNotIn("Local explanation", hints[0])
            self.assertIn("metadata only", hints[0])

    def test_readme_probe_is_bounded_even_with_huge_code_limit(self):
        with tempfile.TemporaryDirectory(prefix="pact-s3-many-modules-") as td:
            root = pathlib.Path(td)
            late = root / "src" / "mod40"
            late.mkdir(parents=True, exist_ok=True)
            (late / "README.md").write_text("late", encoding="utf-8")
            candidates = [
                {"path": f"src/mod{i}/entry.py"} for i in range(80)
            ]
            with mock.patch.object(context, "ROOT", root):
                hints = context.nearby_readme_hints(candidates, limit=1)
            self.assertEqual(hints, [])
            self.assertEqual(context.MODULE_README_CODE_CANDIDATES, 24)

    def test_symlink_and_oversized_readme_are_not_promoted(self):
        with tempfile.TemporaryDirectory(prefix="pact-s3-unsafe-") as d:
            root = pathlib.Path(d)
            (root / "src").mkdir()
            (root / "src" / "README.md").write_bytes(b"x" * (128 * 1024 + 1))
            with mock.patch.object(context, "ROOT", root):
                self.assertEqual(context.nearby_readme_hints(
                    [{"path": "src/app.py"}],
                ), [])
            (root / "src" / "README.md").unlink()
            outside = root.parent / (root.name + "-outside-readme")
            outside.write_text("external secret", encoding="utf-8")
            self.addCleanup(outside.unlink)
            try:
                (root / "src" / "README.md").symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable in this OS")
            with mock.patch.object(context, "ROOT", root):
                self.assertEqual(context.nearby_readme_hints(
                    [{"path": "src/app.py"}],
                ), [])

    def test_git_ignored_readme_is_never_a_navigation_hint(self):
        with tempfile.TemporaryDirectory(prefix="pact-s3-ignore-") as td:
            root = pathlib.Path(td)
            subprocess.run(
                ["git", "init", "-q"], cwd=root, check=True, capture_output=True,
            )
            folder = root / "src" / "ignored"
            folder.mkdir(parents=True)
            (folder / "README.md").write_text("# ignored", encoding="utf-8")
            (root / ".gitignore").write_text(
                "src/ignored/README.md\n", encoding="utf-8",
            )
            with mock.patch.object(context, "ROOT", root):
                result = context.nearby_readme_hints(
                    [{"path": "src/ignored/app.py"}],
                )
            self.assertEqual(result, [])

    def test_symlinked_parent_directory_is_excluded(self):
        with tempfile.TemporaryDirectory(prefix="pact-s3-symlink-parent-") as td:
            root = pathlib.Path(td) / "project"
            root.mkdir()
            outside = pathlib.Path(td) / "outside"
            outside.mkdir()
            (outside / "README.md").write_text(
                "# must not use this", encoding="utf-8",
            )
            try:
                (root / "src").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with mock.patch.object(context, "ROOT", root):
                result = context.nearby_readme_hints(
                    [{"path": "src/app.py"}],
                )
            self.assertEqual(result, [])

    def test_governance_refs_are_metadata_not_confirmed_rules(self):
        with tempfile.TemporaryDirectory(prefix="pact-s3-gov-") as d:
            root = pathlib.Path(d)
            gov = root / "docs" / "governance"
            gov.mkdir(parents=True)
            (gov / "truth-ownership.md").write_text("# Governance\n")
            with mock.patch.object(context, "ROOT", root):
                refs = context.governance_path_hints()
            self.assertEqual(len(refs), 1)
            self.assertIn("truth-ownership.md", refs[0])
            self.assertIn("not a business Rule", refs[0])

    def test_context_schema_keeps_old_closed_v1_contract(self):
        schema = json.loads((ROOT / ".pact" / "schema" /
                             "context-envelope.schema.json").read_text())
        self.assertEqual(schema["properties"]["version"]["const"], 1)
        self.assertIs(schema["additionalProperties"], False)
        self.assertNotIn("intent", schema["properties"])
        self.assertNotIn("module_readme_hints", schema["properties"])


if __name__ == "__main__":
    unittest.main()
