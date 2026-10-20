"""Default weak lexical Decision deferral: preserve owner truth, not guess it.

Real-source positive and negative benchmark gates are separate. Here we cover
the deterministic evidence boundary, installed CLI, and completion semantics.
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
import convergence_coverage
import task_review


class WeakLexicalScoringTests(unittest.TestCase):
    def hit(self, ident, score, reasons=None, kind="decision", status="implemented"):
        return {
            "id": ident, "artifact_type": kind, "status": status,
            "path": f".agents/decisions/{ident.lower()}.md",
            "title": "Unrelated thing", "score": score,
            "reasons": list(reasons or []),
        }

    def test_only_unreasoned_current_single_body_hits_are_deferred(self):
        rows = [
            self.hit("DEC-ONE", 8),
            self.hit("DEC-TWO", 16),
            self.hit("DEC-THREE", 24),
            self.hit("DEC-EXPLICIT", 8, ["exact stable id"]),
            self.hit("DEC-TITLE", 16, ["embedded exact title"]),
            self.hit("DEC-FUSED", 8, ["matched query: exact stable id"]),
            self.hit("DEC-PAST", 8, status="superseded"),
            self.hit("RULE-GOOD", 8, kind="rule", status="confirmed"),
            self.hit("DOC-GUIDE", 8, kind="document"),
        ]
        material, weak = context.split_weak_lexical_decisions(
            rows, "Rename a local variable in tests without changing behavior",
        )
        self.assertEqual([x["id"] for x in weak], ["DEC-ONE", "DEC-TWO", "DEC-THREE"])
        self.assertEqual(
            [x["id"] for x in material],
            ["DEC-EXPLICIT", "DEC-TITLE", "DEC-FUSED",
             "DEC-PAST", "RULE-GOOD", "DOC-GUIDE"],
        )
        self.assertEqual(len(rows), 9)
        self.assertTrue(all(x["reasons"] == [] for x in weak))

    def test_malformed_and_fused_metadata_never_qualifies(self):
        bad = [
            self.hit("DEC-BAD", True),
            self.hit("DEC-NEGATIVE", -1),
            self.hit("DEC-ZERO", 0),
            self.hit("DEC-NONE", None),
            self.hit("DEC-NO-REASONS", 8, ["body contains query"]),
            self.hit("DEC-UNKNOWN", 8, status="candidate"),
        ]
        keep, defer = context.split_weak_lexical_decisions(
            bad, "Rename a local variable in tests without changing behavior",
        )
        self.assertEqual(keep, bad)
        self.assertEqual(defer, [])


class SourceCorroborationTests(unittest.TestCase):
    def test_title_and_exact_source_compounds_protect_opaque_decisions(self):
        with tempfile.TemporaryDirectory(prefix="pact-anchor-evidence-") as td:
            root = pathlib.Path(td)
            rel = ".agents/decisions/implemented/opaque.md"
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "# Undescriptive\n\nThe source prohibits auto_accept_rules "
                "and insists on a usable screen reader.\n",
                encoding="utf-8",
            )
            generic = {
                "path": rel, "artifact_type": "decision",
                "status": "implemented", "title": "Undescriptive",
                "score": 56, "reasons": [],
            }
            with patch.object(context, "ROOT", root):
                self.assertTrue(context._weak_source_unconfirmed(
                    generic, "Rename a local test variable without changing production behavior",
                ))
                self.assertFalse(context._weak_source_unconfirmed(
                    generic, "Change startup logic to silently migrate auto_accept_rules from old installs",
                ))
                self.assertFalse(context._weak_source_unconfirmed(
                    generic, "Replace screen-reader cues with a visual-only status indicator",
                ))
                self.assertFalse(context._weak_source_unconfirmed(
                    {**generic, "title": "Unattended session safety"},
                    "Change unattended sessions so requests run without human approval",
                ))
                self.assertFalse(context._weak_source_unconfirmed(
                    generic, "登录认证流程修改，不改变目前会话行为",
                ))
                self.assertFalse(context._weak_source_unconfirmed(
                    generic, "Change policy",
                ))
                path.unlink()
                # Unverifiable provenance never grants an automatic omission.
                self.assertFalse(context._weak_source_unconfirmed(
                    generic, "Change startup logic to silently migrate auto_accept_rules from old installs",
                ))


class InstalledDefaultWeakTests(unittest.TestCase):
    TASK = (
        "Rename a local variable inside an existing CSV test without changing "
        "assertions, behavior or production code."
    )
    WEAK = "DEC-UNRELATED-RENAMING"
    STRONG = "DEC-CSV-TEST-BEHAVIOR"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pact-weak-default-")
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name) / "project"
        self.root.mkdir()
        (self.root / "README.md").write_text("# Example\n", encoding="utf-8")
        init = subprocess.run(
            [sys.executable, str(ROOT / "scripts/pact/init.py"),
             "--target", str(self.root), "--apply"],
            capture_output=True, text=True,
        )
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.weak_path = ".agents/decisions/implemented/weak-policy.md"
        self.strong_path = ".agents/decisions/implemented/strong-policy.md"
        self.write(
            self.weak_path,
            '+++\n[pact]\ntype = "decision"\nid = "' + self.WEAK + '"\n'
            'status = "implemented"\naliases = []\ndomains = []\n'
            '+++\n# An opaque unrelated historical commitment\n\n'
            'Rename is allowed only after checking the recorded Owner constraint.\n'
        )
        self.write(
            self.strong_path,
            '+++\n[pact]\ntype = "decision"\nid = "' + self.STRONG + '"\n'
            'status = "implemented"\naliases = []\ndomains = []\n'
            '+++\n# CSV test behavior preservation\n\n'
            'Changing CSV tests must not loosen the existing output contract.\n'
        )

    def write(self, relative, text):
        p = self.root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def pact(self, *args):
        return subprocess.run(
            [sys.executable, str(self.root / "pact.py"), *args],
            cwd=self.root, capture_output=True, text=True,
        )

    def envelope(self, *flags):
        result = self.pact(
            "context", self.TASK,
            "--success", "The original CSV test behavior stays unchanged",
            "--limit", "20", "--no-code", "--token-budget", "0",
            *flags,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_default_low_and_medium_defer_weak_but_materialize_strong(self):
        for risk in ("low", "medium"):
            for intent in ((), ("--intent", "work")):
                with self.subTest(risk=risk, intent=intent):
                    result = self.envelope("--risk", risk, *intent)
                    self.assertNotIn(self.WEAK, result["decisions"])
                    self.assertIn(self.STRONG, result["decisions"])
                    self.assertNotIn(self.weak_path, [
                        row["path"] for row in result["artifacts"]
                    ])
                    group = result["weak_decision_hints"]
                    self.assertEqual(group["total_candidates"], 1)
                    self.assertEqual(group["truncated_candidates"], 0)
                    self.assertEqual([h["id"] for h in group["candidates"]], [self.WEAK])
                    h = group["candidates"][0]
                    self.assertEqual(h["path"], self.weak_path)
                    self.assertEqual(
                        h["sha256"],
                        hashlib.sha256((self.root / self.weak_path).read_bytes()).hexdigest(),
                    )
                    self.assertTrue(any("--full-decisions" in x
                                        for x in result["known_unknowns"]))

    def test_high_risk_full_history_and_multiquery_never_hide_weak(self):
        modes = [
            ("--risk", "high"),
            ("--risk", "medium", "--full-decisions"),
            ("--risk", "low", "--intent", "history"),
            ("--risk", "low", "--intent", "decision"),
            ("--risk", "low", "--query", self.TASK, "--query", "CSV"),
            ("--risk", "low", "--scope-first"),
        ]
        for flags in modes:
            with self.subTest(flags=flags):
                packet = self.envelope(*flags)
                self.assertIn(self.WEAK, packet["decisions"])
                self.assertNotIn("weak_decision_hints", packet)

    def test_explicit_nonfunctional_still_works_without_implicit_weak_group(self):
        packet = self.envelope("--risk", "low", "--nonfunctional")
        self.assertNotIn(self.WEAK, packet["decisions"])
        self.assertIn("nonfunctional_decision_hints", packet)
        self.assertNotIn("weak_decision_hints", packet)
        disallowed = self.pact(
            "context", self.TASK, "--success", "No change",
            "--risk", "low", "--nonfunctional", "--full-decisions",
        )
        self.assertNotEqual(disallowed.returncode, 0)
        self.assertIn("--full-decisions", disallowed.stderr)

    def test_task_prepare_propagates_auto_and_opt_out(self):
        a = self.pact(
            "task", "prepare", self.TASK, "--success", "Preserve behavior",
            "--risk", "low", "--no-code",
            "--task-id", "TASK-WEAK-AUTO", "--json",
        )
        self.assertEqual(a.returncode, 0, a.stdout + a.stderr)
        info = json.loads(a.stdout)
        packet = json.loads((self.root / info["context"]).read_text(encoding="utf-8"))
        self.assertIn("weak_decision_hints", packet)
        self.assertNotIn(self.WEAK, packet["decisions"])
        b = self.pact(
            "task", "prepare", self.TASK, "--success", "Preserve behavior",
            "--risk", "low", "--no-code", "--full-decisions",
            "--task-id", "TASK-WEAK-ALL", "--json",
        )
        self.assertEqual(b.returncode, 0, b.stdout + b.stderr)
        info_b = json.loads(b.stdout)
        packet_b = json.loads((self.root / info_b["context"]).read_text(encoding="utf-8"))
        self.assertIn(self.WEAK, packet_b["decisions"])
        self.assertNotIn("weak_decision_hints", packet_b)

    def test_convergence_and_assist_refuse_to_skip_weak_source(self):
        packet = self.envelope("--risk", "medium")
        ctx_file = self.root / "context-for-review.json"
        ctx_file.write_text(json.dumps(packet), encoding="utf-8")
        digest = hashlib.sha256(ctx_file.read_bytes()).hexdigest()
        report = {"context_sha256": digest, "findings": [],
                  "coverage": [
                      {"path": x["path"], "disposition": "aligned",
                       "rationale": "Inspected source."}
                      for x in packet["artifacts"]
                  ]}
        errors, stats = convergence_coverage.review(
            packet, report, root=self.root, context_path=ctx_file,
            expected_context_sha256=digest,
        )
        self.assertIn(self.weak_path, stats["missing_artifacts"])
        self.assertIn(self.weak_path, stats["deferred_decision_paths"])
        self.assertTrue(any("missing from Convergence" in e for e in errors), errors)

        group = packet["weak_decision_hints"]
        report["coverage"].append({
            "path": self.weak_path, "disposition": "not-applicable",
            "rationale": "Read original source; no relevant behavior is changed.",
        })
        clean, _ = convergence_coverage.review(
            packet, report, root=self.root, context_path=ctx_file,
            expected_context_sha256=digest,
        )
        self.assertEqual(clean, [])
        group["truncated_candidates"] = 1
        group["total_candidates"] = 2
        bad, _ = convergence_coverage.review(
            packet, report, root=self.root, context_path=ctx_file,
            expected_context_sha256=digest,
        )
        self.assertTrue(any("Weak lexical Context has unlisted" in e for e in bad), bad)

        task = {"task_id": "TASK-WEAK", "status": "prepared",
                "risk_level": "low", "contract_sha256": "a" * 64,
                "context_sha256": "b" * 64}
        contract = {"acceptance_criteria": [{"id": "AC-1", "text": "Done"}]}
        evidence = {"claims": [{
            "id": "EV-ONE", "required": True, "status": "pass",
            "claim": "Executed check", "criteria": ["AC-1"], "evidence": [],
        }]}
        opts = {"manifest": task, "contract": contract, "context": packet,
                "evidence": evidence, "owner": None,
                "task_change": {"supported": True, "changed_files": []},
                "provenance_errors": [], "policy_gaps": []}
        with patch.object(task_review, "ROOT", self.root):
            blocked = task_review._diagnose(convergence=report, **opts)
            self.assertEqual(blocked["safe_mechanical_acceptance"], [])
            self.assertTrue(any("--full-decisions" in s
                                for s in blocked["policy_gaps"]))
            group["truncated_candidates"] = 0
            group["total_candidates"] = 1
            incomplete = task_review._diagnose(convergence=None, **opts)
            self.assertEqual(incomplete["safe_mechanical_acceptance"], [])
            self.assertIn(self.weak_path, incomplete["missing_context_coverage"])
            self.write(self.weak_path,
                       (self.root / self.weak_path).read_text(encoding="utf-8") +
                       "\nA post-prepare unauthorized Decision mutation.\n")
            stale, _ = convergence_coverage.review(
                packet, report, root=self.root, context_path=ctx_file,
                expected_context_sha256=digest,
            )
            self.assertTrue(any("Deferred Decision changed since Task preparation" in x
                                for x in stale), stale)


if __name__ == "__main__":
    unittest.main()
