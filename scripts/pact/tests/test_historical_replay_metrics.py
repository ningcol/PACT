from __future__ import annotations

import importlib.util
import pathlib
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
MODULE_PATH = PROJECT_ROOT / "scripts" / "benchmark" / "historical_replay.py"

spec = importlib.util.spec_from_file_location("pact_historical_replay", MODULE_PATH)
historical_replay = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(historical_replay)


class HistoricalReplayMetricTests(unittest.TestCase):
    def test_context_metrics_are_oracle_based(self) -> None:
        context = {
            "code_artifacts": [
                {"path": "src/a.ts"},
                {"path": "src/b.ts"},
                {"path": "src/c.ts"},
            ],
            "known_unknowns": ["one"],
        }
        result = historical_replay.context_metrics(
            context,
            ["src/b.ts", "src/d.ts"],
        )

        self.assertEqual(result["matched_oracle_files"], ["src/b.ts"])
        self.assertEqual(result["missing_oracle_files"], ["src/d.ts"])
        self.assertEqual(result["oracle_ranks"], {"src/b.ts": 2})
        self.assertEqual(result["recall"], 0.5)
        self.assertAlmostEqual(result["precision_proxy"], 1 / 3)
        self.assertEqual(result["known_unknowns"], 1)

    def test_aggregate_compares_direct_and_expanded_without_gate(self) -> None:
        results = [
            {
                "query_expansion_recall_delta": 0.5,
                "direct": {
                    "oracle_files": 2,
                    "matched_oracle_files": ["a"],
                    "context_code_files": 4,
                },
                "expanded": {
                    "oracle_files": 2,
                    "matched_oracle_files": ["a", "b"],
                    "context_code_files": 5,
                },
            },
            {
                "query_expansion_recall_delta": 0.0,
                "direct": {
                    "oracle_files": 1,
                    "matched_oracle_files": [],
                    "context_code_files": 2,
                },
                "expanded": {
                    "oracle_files": 1,
                    "matched_oracle_files": [],
                    "context_code_files": 3,
                },
            },
        ]

        summary = historical_replay.aggregate(results)
        self.assertEqual(summary["case_count"], 2)
        self.assertEqual(summary["oracle_file_count"], 3)
        self.assertAlmostEqual(summary["direct_weighted_recall"], 1 / 3)
        self.assertAlmostEqual(summary["expanded_weighted_recall"], 2 / 3)
        self.assertEqual(summary["cases_improved_by_query_expansion"], 1)


if __name__ == "__main__":
    unittest.main()
