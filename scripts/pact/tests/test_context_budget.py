from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
RUNTIME = PROJECT_ROOT / "scripts" / "pact"
sys.path.insert(0, str(RUNTIME))

spec = importlib.util.spec_from_file_location(
    "pact_context_budget",
    RUNTIME / "context.py",
)
context = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(context)


class ContextBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-context-budget-")
        self.root = pathlib.Path(self.temp.name)
        self.previous_root = context.ROOT
        context.ROOT = self.root

    def tearDown(self) -> None:
        context.ROOT = self.previous_root
        self.temp.cleanup()

    def write_bytes(self, relative: str, size: int) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * size)

    def test_wider_pool_only_appends_fallback_candidates(self) -> None:
        primary = [
            {"path": "src/a.ts", "score": 10},
            {"path": "src/b.ts", "score": 9},
        ]
        wider = [
            {"path": "src/x.ts", "score": 1000},
            {"path": "src/a.ts", "score": 999},
            {"path": "src/c.ts", "score": 998},
        ]

        merged = context.extend_candidate_pool(primary, wider)

        self.assertEqual(
            [item["path"] for item in merged],
            ["src/a.ts", "src/b.ts", "src/x.ts", "src/c.ts"],
        )
        self.assertEqual(
            [item["_pool_tier"] for item in merged],
            [0, 0, 1, 1],
        )

    def test_selection_preserves_canonical_code_order(self) -> None:
        for name in ["a.ts", "b.ts", "c.ts"]:
            self.write_bytes(f"src/{name}", 100)

        code = context.extend_candidate_pool(
            [
                {
                    "path": "src/a.ts",
                    "score": 1,
                    "language": "typescript",
                    "is_test": False,
                    "symbols": [],
                    "relation": "direct-match",
                    "confidence": "direct",
                },
                {
                    "path": "src/b.ts",
                    "score": 1000,
                    "language": "typescript",
                    "is_test": False,
                    "symbols": [],
                    "relation": "direct-match",
                    "confidence": "direct",
                },
            ],
            [
                {
                    "path": "src/c.ts",
                    "score": 5000,
                    "language": "typescript",
                    "is_test": False,
                    "symbols": [],
                    "relation": "direct-match",
                    "confidence": "direct",
                }
            ],
        )

        _, selected, _ = context.select_context_candidates(
            [],
            code,
            token_budget=0,
            knowledge_limit=8,
            code_limit=2,
        )

        self.assertEqual(
            [item["path"] for item in selected],
            ["src/a.ts", "src/b.ts"],
        )

    def test_task_wording_is_only_primary_when_explicitly_preserved(self) -> None:
        self.assertTrue(
            context.preserves_task_as_primary(
                "owner task",
                [" owner task ", "code symbol"],
            )
        )
        self.assertFalse(
            context.preserves_task_as_primary(
                "owner task",
                ["code symbol", "owner task"],
            )
        )
        self.assertFalse(
            context.preserves_task_as_primary(
                "owner task",
                ["owner task"],
            )
        )

    def test_primary_selected_context_precedes_fused_fallback(self) -> None:
        primary = [
            {"path": "src/primary-a.ts", "score": 10},
            {"path": "src/primary-b.ts", "score": 9},
        ]
        fused = [
            {"path": "src/supplemental.ts", "score": 1000},
            {"path": "src/primary-a.ts", "score": 999},
        ]
        wider = [
            {"path": "src/wider.ts", "score": 5000},
        ]

        merged = context.compose_primary_preserving_pool(
            primary,
            fused,
            wider,
        )

        self.assertEqual(
            [item["path"] for item in merged],
            [
                "src/primary-a.ts",
                "src/primary-b.ts",
                "src/supplemental.ts",
                "src/wider.ts",
            ],
        )
        self.assertEqual(
            [item["_pool_tier"] for item in merged],
            [0, 0, 1, 1],
        )

    def test_supplemental_candidates_do_not_displace_selected_primary_under_token_pressure(self) -> None:
        self.write_bytes("src/primary-a.ts", 400)
        self.write_bytes("src/primary-b.ts", 400)
        self.write_bytes("src/supplemental.ts", 400)

        def code(path: str, score: int) -> dict:
            return {
                "path": path,
                "score": score,
                "language": "typescript",
                "is_test": False,
                "symbols": [],
                "relation": "direct-match",
                "confidence": "direct",
            }

        merged = context.compose_primary_preserving_pool(
            [
                code("src/primary-a.ts", 10),
                code("src/primary-b.ts", 9),
            ],
            [code("src/supplemental.ts", 100000)],
            [],
        )

        _, selected, budget = context.select_context_candidates(
            [],
            merged,
            token_budget=200,
            knowledge_limit=8,
            code_limit=3,
        )

        self.assertEqual(
            [item["path"] for item in selected],
            ["src/primary-a.ts", "src/primary-b.ts"],
        )
        self.assertEqual(budget["dropped_for_token_budget"], 1)

    def test_large_low_priority_candidate_can_be_skipped_for_smaller_useful_file(self) -> None:
        self.write_bytes("src/huge.ts", 40_000)
        self.write_bytes("src/small.ts", 800)

        code = [
            {
                "path": "src/huge.ts",
                "score": 1000,
                "language": "typescript",
                "is_test": False,
                "symbols": ["huge"],
                "relation": "direct-match",
                "confidence": "direct",
            },
            {
                "path": "src/small.ts",
                "score": 500,
                "language": "typescript",
                "is_test": False,
                "symbols": ["small"],
                "relation": "direct-match",
                "confidence": "direct",
            },
        ]

        knowledge, selected, budget = context.select_context_candidates(
            [],
            code,
            token_budget=1000,
            knowledge_limit=8,
            code_limit=4,
        )

        self.assertEqual(knowledge, [])
        self.assertEqual([item["path"] for item in selected], ["src/small.ts"])
        self.assertEqual(budget["dropped_for_token_budget"], 1)
        self.assertLessEqual(budget["selected_estimated_tokens"], 1000)
        self.assertEqual(budget["authority_overage_tokens"], 0)

    def test_confirmed_rule_can_explicitly_exceed_soft_budget(self) -> None:
        self.write_bytes("docs/product/rules/large.md", 8_000)
        knowledge = [
            {
                "path": "docs/product/rules/large.md",
                "id": "RULE-LARGE-001",
                "artifact_type": "rule",
                "status": "confirmed",
                "title": "Large authoritative rule",
                "score": 10,
                "reasons": ["rule match"],
                "domains": [],
                "verification": [],
            }
        ]

        selected, code, budget = context.select_context_candidates(
            knowledge,
            [],
            token_budget=100,
            knowledge_limit=8,
            code_limit=4,
        )

        self.assertEqual(code, [])
        self.assertEqual([item["path"] for item in selected], [
            "docs/product/rules/large.md"
        ])
        self.assertGreater(budget["authority_overage_tokens"], 0)
        self.assertEqual(budget["authority_candidates_dropped"], 0)

    def test_count_limits_remain_hard_when_token_budget_disabled(self) -> None:
        code = []
        for index in range(3):
            path = f"src/{index}.ts"
            self.write_bytes(path, 100)
            code.append({
                "path": path,
                "score": 100 - index,
                "language": "typescript",
                "is_test": False,
                "symbols": [],
                "relation": "direct-match",
                "confidence": "direct",
            })

        _, selected, budget = context.select_context_candidates(
            [],
            code,
            token_budget=0,
            knowledge_limit=8,
            code_limit=1,
        )

        self.assertEqual(len(selected), 1)
        self.assertEqual(budget["dropped_for_count_limit"], 2)
        self.assertEqual(budget["limit_tokens"], 0)

    def test_estimation_is_stable_utf8_byte_based(self) -> None:
        path = self.root / "docs" / "guide.md"
        path.parent.mkdir(parents=True)
        path.write_text("中文中文", encoding="utf-8")

        expected = max((path.stat().st_size + 3) // 4, 1)
        self.assertEqual(
            context.estimated_file_tokens("docs/guide.md"),
            expected,
        )


if __name__ == "__main__":
    unittest.main()
