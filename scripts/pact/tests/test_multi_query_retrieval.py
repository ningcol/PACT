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

    def test_structured_symbol_scores_above_generic_identifier(self) -> None:
        structured_score, _ = discover.score_code_file(
            {
                "path": "src/service.ts",
                "symbols": ["dispatchTask"],
                "identifiers": [],
                "imports": [],
            },
            "dispatchTask",
        )
        generic_score, reasons = discover.score_code_file(
            {
                "path": "server/service.go",
                "symbols": [],
                "identifiers": ["dispatchTask"],
                "imports": [],
            },
            "dispatchTask",
        )

        self.assertGreater(structured_score, generic_score)
        self.assertIn("exact generic identifier", reasons)

    def test_generic_identifier_can_produce_direct_code_result(self) -> None:
        results = discover.ranked_code_results(
            {
                "files": [
                    {
                        "path": "server/service.go",
                        "language": "go",
                        "parser_mode": "generic-lexical",
                        "is_test": False,
                        "symbols": [],
                        "identifiers": ["roundRobinDispatch"],
                        "imports": [],
                    }
                ],
                "edges": [],
            },
            "roundRobinDispatch",
            limit=4,
        )

        self.assertEqual([item["path"] for item in results], ["server/service.go"])
        self.assertEqual(results[0]["parser_mode"], "generic-lexical")
        self.assertEqual(results[0]["confidence"], "direct")

    def test_code_limit_one_preserves_a_direct_match_over_an_import_neighbor(self) -> None:
        code_index = {
            "files": [
                {
                    "path": "src/payment.py",
                    "language": "python",
                    "is_test": False,
                    "symbols": ["execute_payment"],
                    "identifiers": [],
                    "imports": [],
                },
                {
                    "path": "tests/test_payment.py",
                    "language": "python",
                    "is_test": True,
                    "symbols": [],
                    "identifiers": [],
                    "imports": [],
                },
            ],
            "edges": [
                {
                    "from": "tests/test_payment.py",
                    "to": "src/payment.py",
                    "confidence": "relative-resolved",
                }
            ],
        }
        result = discover.ranked_code_results(
            code_index, "execute_payment", limit=1
        )
        self.assertEqual([item["path"] for item in result], ["src/payment.py"])
        self.assertEqual(result[0]["relation"], "direct-match")
        self.assertEqual(result[0]["confidence"], "direct")

    def test_code_limit_two_retains_direct_match_and_graph_neighbor(self) -> None:
        code_index = {
            "files": [
                {
                    "path": "src/payment.py", "language": "python",
                    "is_test": False, "symbols": ["execute_payment"],
                    "identifiers": [], "imports": [],
                },
                {
                    "path": "tests/test_payment.py", "language": "python",
                    "is_test": True, "symbols": [], "identifiers": [], "imports": [],
                },
            ],
            "edges": [{
                "from": "tests/test_payment.py", "to": "src/payment.py",
                "confidence": "relative-resolved",
            }],
        }
        results = discover.ranked_code_results(
            code_index, "execute_payment", limit=2
        )
        self.assertEqual(
            [(item["path"], item["relation"]) for item in results],
            [
                ("src/payment.py", "direct-match"),
                ("tests/test_payment.py", "import-neighbor"),
            ],
        )

    def test_code_limit_zero_still_keeps_one_direct_match(self) -> None:
        index = {
            "files": [
                {"path": "src/payment.py", "language": "python",
                 "is_test": False, "symbols": ["execute_payment"],
                 "identifiers": [], "imports": []},
                {"path": "tests/test_payment.py", "language": "python",
                 "is_test": True, "symbols": [], "identifiers": [], "imports": []},
            ],
            "edges": [{
                "from": "tests/test_payment.py", "to": "src/payment.py",
                "confidence": "relative-resolved",
            }],
        }
        self.assertEqual(
            [x["path"] for x in discover.ranked_code_results(
                index, "execute_payment", limit=0
            )],
            ["src/payment.py"],
        )

    def test_code_limit_is_a_hard_final_budget(self) -> None:
        files = []
        edges = []
        for index in range(10):
            files.append({
                "path": f"src/direct-{index}.ts",
                "language": "typescript",
                "is_test": False,
                "symbols": [f"target{index}"],
                "imports": [],
            })
        for index in range(10):
            files.append({
                "path": f"src/neighbor-{index}.ts",
                "language": "typescript",
                "is_test": False,
                "symbols": [],
                "imports": [],
            })
            edges.append({
                "from": f"src/neighbor-{index}.ts",
                "to": f"src/direct-{index}.ts",
                "kind": "import",
                "confidence": "relative-resolved",
            })

        results = discover.ranked_code_results(
            {"files": files, "edges": edges},
            "target",
            limit=6,
        )

        self.assertLessEqual(len(results), 6)
        self.assertTrue(any(item["relation"] == "direct-match" for item in results))
        self.assertTrue(any(item["relation"] == "import-neighbor" for item in results))

    def test_fusion_preserves_specialized_query_candidates_when_budget_allows(self) -> None:
        def item(path: str, score: int) -> dict:
            return {
                "path": path,
                "score": score,
                "reasons": [path],
                "language": "typescript",
                "is_test": False,
                "symbols": [],
                "relation": "direct-match",
                "confidence": "direct",
            }

        shared = [item(f"src/shared-{index}.ts", 100 - index) for index in range(8)]
        specialized = [
            item("src/specialized.ts", 500),
            *shared,
        ]
        noisy = [
            *shared,
            item("src/noisy-only.ts", 50),
        ]

        fused = discover.fuse_ranked_results(
            [
                ("specialized query", specialized),
                ("shared query", noisy),
            ],
            limit=6,
        )

        paths = [entry["path"] for entry in fused]
        self.assertEqual(len(paths), 6)
        self.assertIn("src/specialized.ts", paths)

    def test_each_query_gets_representation_when_budget_equals_query_count(self) -> None:
        def item(path: str, score: int) -> dict:
            return {
                "path": path,
                "score": score,
                "reasons": [path],
                "language": "typescript",
                "is_test": False,
                "symbols": [],
                "relation": "direct-match",
                "confidence": "direct",
            }

        first = [
            item("src/shared.ts", 100),
            item("src/first-only.ts", 90),
        ]
        second = [
            item("src/shared.ts", 100),
            item("src/second-only.ts", 1000),
        ]

        fused = discover.fuse_ranked_results(
            [("first query", first), ("second query", second)],
            limit=2,
        )

        paths = {entry["path"] for entry in fused}
        self.assertEqual(len(paths), 2)
        self.assertIn("src/shared.ts", paths)
        self.assertIn("src/second-only.ts", paths)

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


    def test_generic_query_prefers_current_to_equally_relevant_historical_decisions(self) -> None:
        def decision(path: str, status: str, ident: str) -> dict:
            return {
                "path": path,
                "artifact_type": "decision",
                "id": ident,
                "status": status,
                "title": "Cache rationale",
                "text": "cache constraints and limits",
                "domains": [],
                "aliases": [],
            }

        results = discover.ranked_knowledge_results(
            {
                "documents": [
                    decision(".agents/decisions/archived/old.md", "archived", "DEC-OLD"),
                    decision(".agents/decisions/implemented/old.md", "superseded", "DEC-SUPERSEDED"),
                    decision(".agents/decisions/implemented/current.md", "implemented", "DEC-CURRENT"),
                ],
            },
            "cache",
            limit=3,
        )
        self.assertEqual(
            [item["id"] for item in results],
            ["DEC-CURRENT", "DEC-OLD", "DEC-SUPERSEDED"],
        )
        self.assertNotIn("historical decision (not current guidance)", results[0]["reasons"])
        for item in results[1:]:
            self.assertIn("historical decision (not current guidance)", item["reasons"])

    def test_exact_historical_lookup_is_not_penalized_or_hidden(self) -> None:
        historical = {
            "path": ".agents/decisions/archived/old.md",
            "artifact_type": "decision",
            "id": "DEC-CACHE-OLD",
            "status": "archived",
            "title": "Previous cache boundary",
            "aliases": ["old cache trade-off"],
            "text": "cache reasoning remains useful as history",
        }
        for query in ("DEC-CACHE-OLD", "Previous cache boundary", "old cache trade-off"):
            score, reasons = discover.score_document(historical, query)
            self.assertNotIn("historical decision (not current guidance)", reasons)
            self.assertGreater(score, 100)

        generic = discover.ranked_knowledge_results(
            {"documents": [historical]},
            "cache",
            limit=1,
        )
        self.assertEqual([item["id"] for item in generic], ["DEC-CACHE-OLD"])
        self.assertEqual(generic[0]["status"], "archived")

    def test_rejected_decision_remains_a_current_warning_not_old_history(self) -> None:
        rejected = {
            "path": ".agents/decisions/rejected/avoid.md",
            "artifact_type": "decision",
            "id": "DEC-REJECTED",
            "status": "rejected",
            "title": "Cache alternative",
            "aliases": [],
            "text": "cache alternative rejected for correctness",
        }
        current = {**rejected, "status": "implemented"}
        rejected_score, rejected_reasons = discover.score_document(rejected, "cache")
        current_score, _ = discover.score_document(current, "cache")
        self.assertEqual(rejected_score, current_score)
        self.assertNotIn("historical decision (not current guidance)", rejected_reasons)


if __name__ == "__main__":
    unittest.main()
