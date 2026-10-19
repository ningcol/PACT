"""Developer-only no-model paired negative-case scoring, not blind Agent evidence."""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
import privacyfence_nonfunctional_probe as probe


def row(ident: str, *, mode: str, decisions: list[str], tokens: int):
    return {
        "id": ident,
        "kind": "routine-negative",
        "source_verified_decisions": decisions,
        "budget": {"selected_estimated_tokens": tokens},
        **({"nonfunctional_decision_hints": {
            "total_candidates": len(decisions) + 2,
            "truncated_candidates": 0,
            "candidates": [],
        }} if mode == "opt" else {}),
    }


class PrivacyFenceExplicitModeScoringTests(unittest.TestCase):
    def test_paired_developer_only_routine_denominator_and_tokens(self):
        a = [
            row("docs-whitespace", mode="base", decisions=["DEC-ONE"], tokens=5000),
            row("test-variable", mode="base", decisions=["DEC-TWO", "DEC-THREE"], tokens=8000),
        ] + [{
            "id": f"conflict-{n}", "kind": "conflict",
            "source_verified_decisions": ["DEC-TARGET"],
            "budget": {"selected_estimated_tokens": 4000},
        } for n in range(10)]
        b = [
            row("test-variable", mode="opt", decisions=[], tokens=2100),
            row("docs-whitespace", mode="opt", decisions=[], tokens=1800),
        ]
        scored = probe.paired_metrics(a, b)
        self.assertEqual(scored["baseline_routine_cases_with_current_decisions"], 2)
        self.assertEqual(scored["opt_in_routine_cases_with_current_decisions"], 0)
        self.assertEqual(scored["baseline_routine_selected_estimated_tokens"], 13000)
        self.assertEqual(scored["opt_in_routine_selected_estimated_tokens"], 3900)
        self.assertEqual(
            [x["id"] for x in scored["per_case"]],
            ["docs-whitespace", "test-variable"],
        )

    def test_reject_pair_missing_instead_of_shrinking_denominator(self):
        base = [row("docs-whitespace", mode="base", decisions=[], tokens=100)]
        opt = [row("docs-whitespace", mode="opt", decisions=[], tokens=100)]
        with self.assertRaisesRegex(ValueError, "mismatched"):
            probe.paired_metrics(base, opt)
        base.append(row("test-variable", mode="base", decisions=[], tokens=100))
        with self.assertRaisesRegex(ValueError, "mismatched"):
            probe.paired_metrics(base, opt)
        opt.append(row("different-case", mode="opt", decisions=[], tokens=100))
        with self.assertRaisesRegex(ValueError, "mismatched"):
            probe.paired_metrics(base, opt)
        opt.pop()
        opt.append(row("test-variable", mode="opt", decisions=[], tokens=100))
        opt.append(row("test-variable", mode="opt", decisions=[], tokens=100))
        with self.assertRaisesRegex(ValueError, "mismatched"):
            probe.paired_metrics(base, opt)


if __name__ == "__main__":
    unittest.main()
