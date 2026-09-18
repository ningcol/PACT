from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
RUNTIME = PROJECT_ROOT / "scripts" / "pact"
sys.path.insert(0, str(RUNTIME))

spec = importlib.util.spec_from_file_location(
    "pact_discover_multi_query",
    RUNTIME / "discover.py",
)
discover = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(discover)


class MultiQueryRetrievalTests(unittest.TestCase):
    def test_queries_are_trimmed_deduplicated_and_ordered(self) -> None:
        self.assertEqual(
            discover.normalize_queries(
                " owner task ",
                ["code symbol", "OWNER TASK", "", "code symbol"],
            ),
            ["owner task", "code symbol"],
        )

    def test_rrf_promotes_cross_query_matches_and_respects_budget(self) -> None:
        first = [
            {
                "path": "src/a.ts",
                "score": 100,
                "reasons": ["a"],
                "language": "typescript",
                "is_test": False,
                "symbols": [],
                "relation": "direct-match",
                "confidence": "direct",
            },
            {
                "path": "src/shared.ts",
                "score": 90,
                "reasons": ["shared from first"],
                "language": "typescript",
                "is_test": False,
                "symbols": [],
                "relation": "direct-match",
                "confidence": "direct",
            },
        ]
        second = [
            {
                "path": "src/shared.ts",
                "score": 70,
                "reasons": ["shared from second"],
                "language": "typescript",
                "is_test": False,
                "symbols": [],
                "relation": "direct-match",
                "confidence": "direct",
            },
            {
                "path": "src/b.ts",
                "score": 120,
                "reasons": ["b"],
                "language": "typescript",
                "is_test": False,
                "symbols": [],
                "relation": "direct-match",
                "confidence": "direct",
            },
        ]

        fused = discover.fuse_ranked_results(
            [("owner language", first), ("code language", second)],
            limit=2,
        )

        self.assertEqual(len(fused), 2)
        self.assertEqual(fused[0]["path"], "src/shared.ts")
        self.assertIn(
            "matched query: owner language",
            fused[0]["reasons"],
        )
        self.assertIn(
            "matched query: code language",
            fused[0]["reasons"],
        )

    def test_identifier_family_expansion_stays_within_anchored_directory(self) -> None:
        code_index = {
            "files": [
                {
                    "path": "src/sync/dynamic/webhook.ts",
                    "language": "typescript",
                    "is_test": False,
                    "symbols": ["DynamicWebhook"],
                    "identifiers": [],
                    "imports": [],
                },
                {
                    "path": "src/sync/dynamic/facebook.ts",
                    "language": "typescript",
                    "is_test": False,
                    "symbols": ["DynamicFacebook"],
                    "identifiers": ["autoPublish"],
                    "imports": [],
                },
                {
                    "path": "src/other/foo.ts",
                    "language": "typescript",
                    "is_test": False,
                    "symbols": ["Foo"],
                    "identifiers": ["autoPublish"],
                    "imports": [],
                },
            ],
            "edges": [],
        }
        query_results = [
            (
                "webhook",
                [
                    {
                        "path": "src/sync/dynamic/webhook.ts",
                        "score": 100,
                        "reasons": ["path contains query"],
                        "language": "typescript",
                        "is_test": False,
                        "symbols": ["DynamicWebhook"],
                        "relation": "direct-match",
                        "confidence": "direct",
                    }
                ],
            ),
            ("autoPublish", []),
        ]

        family = discover.ranked_query_family_results(
            code_index,
            ["webhook", "autoPublish"],
            query_results,
            limit=8,
        )

        self.assertEqual(
            [item["path"] for item in family],
            ["src/sync/dynamic/facebook.ts"],
        )
        self.assertEqual(family[0]["relation"], "query-family")
        self.assertIn(
            "shared query identifier(s): autopublish",
            family[0]["reasons"],
        )

    def test_direct_match_wins_relation_when_another_query_finds_neighbor(self) -> None:
        fused = discover.fuse_ranked_results(
            [
                (
                    "graph query",
                    [
                        {
                            "path": "src/shared.ts",
                            "score": 30,
                            "reasons": ["neighbor"],
                            "language": "typescript",
                            "is_test": False,
                            "symbols": [],
                            "relation": "import-neighbor",
                            "confidence": "relative-resolved",
                        }
                    ],
                ),
                (
                    "symbol query",
                    [
                        {
                            "path": "src/shared.ts",
                            "score": 80,
                            "reasons": ["symbol"],
                            "language": "typescript",
                            "is_test": False,
                            "symbols": ["shared"],
                            "relation": "direct-match",
                            "confidence": "direct",
                        }
                    ],
                ),
            ],
            limit=4,
        )

        self.assertEqual(fused[0]["relation"], "direct-match")
        self.assertEqual(fused[0]["confidence"], "direct")


if __name__ == "__main__":
    unittest.main()
