from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
RUNTIME = PROJECT_ROOT / "scripts" / "pact"
sys.path.insert(0, str(RUNTIME))

spec = importlib.util.spec_from_file_location(
    "pact_eval_machine_summary",
    RUNTIME / "eval.py",
)
pact_eval = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(pact_eval)


class EvalMachineSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-eval-machine-")
        self.root = pathlib.Path(self.temp.name)
        self.previous_root = pact_eval.ROOT
        pact_eval.ROOT = self.root

    def tearDown(self) -> None:
        pact_eval.ROOT = self.previous_root
        self.temp.cleanup()

    def write_json(self, relative: str, data: dict) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_derive_task_reports_context_change_and_change_coverage_metrics(self) -> None:
        task_id = "TASK-EVAL-MACHINE"
        self.write_json(
            f".pact/tasks/{task_id}/task.json",
            {
                "version": 1,
                "task_id": task_id,
                "status": "prepared",
                "risk_level": "medium",
                "context": f".pact/tasks/{task_id}/context.json",
                "completion_bundle": f".pact/completions/{task_id}",
                "task_change": {
                    "supported": True,
                    "changed_files": ["src/a.py", "src/b.py"],
                },
                "final_impact": f".pact/tasks/{task_id}/final-impact.json",
            },
        )
        self.write_json(
            f".pact/tasks/{task_id}/context.json",
            {
                "artifacts": [{"path": "docs/product/rule.md"}],
                "code_artifacts": [{"path": "src/a.py"}, {"path": "src/b.py"}],
                "known_unknowns": ["Need runtime verification"],
                "risk_policy": {
                    "materialization_token_budget": 40000,
                },
                "context_budget": {
                    "limit_tokens": 40000,
                    "selected_estimated_tokens": 12500,
                    "candidate_estimated_tokens": 24000,
                    "dropped_candidates": 3,
                    "authority_overage_tokens": 0,
                },
            },
        )
        self.write_json(
            f".pact/tasks/{task_id}/final-impact.json",
            {"changed_files": ["src/a.py", "src/b.py"]},
        )
        attempts = self.root / ".pact" / "tasks" / task_id / "completion-attempts.jsonl"
        attempts.write_text(
            json.dumps(
                {
                    "complete": False,
                    "blockers": ["change-coverage"],
                    "errors": [
                        "change coverage: Task changed file missing from Convergence change coverage"
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )

        observation = pact_eval.derive_task(task_id)

        self.assertEqual(observation["context"]["token_budget"], 40000)
        self.assertEqual(
            observation["context"]["selected_estimated_tokens"],
            12500,
        )
        self.assertEqual(observation["context"]["dropped_candidates"], 3)
        self.assertTrue(observation["task_change"]["supported"])
        self.assertEqual(observation["task_change"]["changed_files"], 2)
        self.assertEqual(
            observation["task_change"]["paths"],
            ["src/a.py", "src/b.py"],
        )
        self.assertTrue(observation["task_change"]["final_impact"])
        self.assertEqual(
            observation["completion"]["change_coverage_blocks"],
            1,
        )

    def test_unobserved_task_change_is_explicitly_null_not_zero(self) -> None:
        task_id = "TASK-EVAL-OLD"
        self.write_json(
            f".pact/tasks/{task_id}/task.json",
            {
                "version": 1,
                "task_id": task_id,
                "status": "prepared",
                "risk_level": "low",
                "context": f".pact/tasks/{task_id}/context.json",
                "completion_bundle": f".pact/completions/{task_id}",
            },
        )
        self.write_json(
            f".pact/tasks/{task_id}/context.json",
            {
                "artifacts": [],
                "code_artifacts": [],
                "known_unknowns": [],
            },
        )

        observation = pact_eval.derive_task(task_id)

        self.assertFalse(observation["task_change"]["supported"])
        self.assertIsNone(observation["task_change"]["changed_files"])
        self.assertIsNone(observation["task_change"]["paths"])
        self.assertIsNone(observation["context"]["token_budget"])

    def test_machine_summary_keeps_risk_groups_and_no_single_score(self) -> None:
        def observation(task_id: str, risk: str, changed: int) -> dict:
            return {
                "task_id": task_id,
                "risk_level": risk,
                "context": {
                    "knowledge_artifacts": 2,
                    "code_artifacts": 4,
                    "selected_estimated_tokens": 10000,
                    "token_budget": 40000,
                    "dropped_candidates": 0,
                },
                "runs": {"total": 2, "failed": 0},
                "completion": {
                    "attempts": 1,
                    "failed_attempts": 0,
                    "stale_workspace_blocks": 0,
                    "stale_contract_blocks": 0,
                    "acceptance_gap_blocks": 0,
                    "convergence_coverage_blocks": 0,
                    "change_coverage_blocks": 0,
                    "ci_requirement_blocks": 0,
                    "final_complete": True,
                },
                "task_change": {
                    "changed_files": changed,
                    "final_impact": changed > 0,
                },
            }

        summary = pact_eval.summarize_observations(
            [
                observation("TASK-LOW", "low", 1),
                observation("TASK-MEDIUM", "medium", 3),
            ]
        )

        self.assertEqual(summary["task_count"], 2)
        self.assertEqual(summary["overall"]["total_changed_files"], 4)
        self.assertIn("low", summary["by_risk"])
        self.assertIn("medium", summary["by_risk"])
        self.assertNotIn("score", summary)
        self.assertIn("do not collapse", summary["interpretation_note"])


if __name__ == "__main__":
    unittest.main()
