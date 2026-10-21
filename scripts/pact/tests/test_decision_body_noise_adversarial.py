"""Adversarial no-model Decision retrieval: full-text coincidence is not authority.

Frozen test wording and source records precede any scorer fix. This is an
assistant-authored engineering probe, NOT an independent model/Owner holdout.
"""
from __future__ import annotations

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
import discover

QUERY = "Adjust code test fixtures"
NOISE_ID = "DEC-DB-ISOLATION"
NOISE_REL = ".agents/decisions/implemented/database-isolation.md"
OLD_ID = "DEC-OLD-DB-ISOLATION"
OLD_REL = ".agents/decisions/superseded/old-database-isolation.md"
NOISE_TEXT = (
    "+++\n[pact]\ntype = \"decision\"\nid = \"DEC-DB-ISOLATION\"\n"
    "status = \"implemented\"\nsupersedes = [\"DEC-OLD-DB-ISOLATION\"]\n"
    "+++\n# Database transaction isolation\n\n"
    "Decision: serialize writes to prevent database transaction anomalies.\n"
    "Generic old maintenance checklist copied into this unrelated rationale: "
    "Adjust code test fixtures. This does not govern variable renaming.\n"
)
OLD_TEXT = (
    "+++\n[pact]\ntype = \"decision\"\nid = \"DEC-OLD-DB-ISOLATION\"\n"
    "status = \"superseded\"\nsuperseded_by = \"DEC-DB-ISOLATION\"\n"
    "+++\n# Original historical database isolation\n\n"
    "The original transaction-isolation choice was replaced; consult current Decision.\n"
)


class FullBodyCoincidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-adversarial-body-match-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name) / "project"
        self.root.mkdir()
        (self.root / "README.md").write_text("# Unrelated test project\n", encoding="utf-8")
        for relative, body in [(NOISE_REL, NOISE_TEXT), (OLD_REL, OLD_TEXT)]:
            dest = self.root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(body, encoding="utf-8")

    def pact(self, *args: str) -> dict:
        run = subprocess.run(
            [sys.executable, str(self.root / "pact.py"), *args],
            cwd=self.root, capture_output=True, text=True, timeout=65,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        return json.loads(run.stdout)

    def install(self) -> None:
        run = subprocess.run(
            [sys.executable, str(ROOT / "scripts/pact/init.py"),
             "--target", str(self.root), "--apply"],
            capture_output=True, text=True, timeout=80,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_scored_full_body_overlap_must_remain_unconfirmed(self) -> None:
        source = {
            "id": NOISE_ID, "artifact_type": "decision",
            "status": "implemented", "title": "Database transaction isolation",
            "aliases": [], "domains": [], "text": NOISE_TEXT,
        }
        score, reasons = discover.score_document(source, QUERY)
        self.assertGreater(score, 0)
        self.assertIn("body contains query", reasons)
        self.assertIn("all query terms matched", reasons)
        hit = {
            "id": NOISE_ID, "artifact_type": "decision",
            "status": "implemented", "title": source["title"],
            "path": NOISE_REL, "score": score, "reasons": reasons,
        }
        with patch.object(context, "ROOT", self.root):
            materialized, hinted = context.split_weak_lexical_decisions([hit], QUERY)
        self.assertEqual(materialized, [], "body coincidence cannot promote applicability")
        self.assertEqual(hinted, [hit], "unrelated source must remain reviewable as hint")

    def test_installed_low_risk_defers_bait_and_full_optout_preserves_it(self) -> None:
        self.install()
        usual = self.pact(
            "context", QUERY, "--success", "Only fixture edits, no behavior change",
            "--risk", "low", "--no-code", "--limit", "12", "--token-budget", "0",
        )
        self.assertNotIn(NOISE_ID, usual["decisions"])
        self.assertEqual(
            [x["id"] for x in usual["weak_decision_hints"]["candidates"]],
            [NOISE_ID],
        )
        self.assertGreaterEqual(usual["weak_decision_hints"]["total_candidates"], 1)

        full = self.pact(
            "context", QUERY, "--success", "Only fixture edits, no behavior change",
            "--risk", "low", "--no-code", "--limit", "12", "--token-budget", "0",
            "--full-decisions",
        )
        self.assertIn(NOISE_ID, full["decisions"])
        self.assertNotIn("weak_decision_hints", full)

    def test_historical_exact_id_is_retrievable_not_current_authority(self) -> None:
        self.install()
        old = self.pact(
            "context", OLD_ID, "--success", "Explain historical isolation rationale",
            "--risk", "medium", "--intent", "history", "--no-code",
            "--limit", "12", "--token-budget", "0",
        )
        matches = [row for row in old["artifacts"] if row.get("id") == OLD_ID]
        self.assertEqual(len(matches), 1, old)
        # Context Envelope v1 exposes ID/path/score/source SHA, not a
        # mutable lifecycle label. Confirm historical status from source.
        self.assertEqual(matches[0]["path"], OLD_REL)
        self.assertIn(
            'status = "superseded"',
            (self.root / OLD_REL).read_text(encoding="utf-8"),
        )
        self.assertNotIn(OLD_ID, old["decisions"])

        active = self.pact(
            "context", NOISE_ID, "--success", "Explain current isolation rationale",
            "--risk", "high", "--no-code", "--limit", "12", "--token-budget", "0",
        )
        self.assertIn(NOISE_ID, active["decisions"])


if __name__ == "__main__":
    unittest.main()
