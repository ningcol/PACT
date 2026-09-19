from __future__ import annotations

import importlib.util
import pathlib
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
