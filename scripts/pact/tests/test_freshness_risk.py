from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
MAP = PROJECT_ROOT / "scripts" / "pact" / "map.py"
CODE_MAP = PROJECT_ROOT / "scripts" / "pact" / "code_map.py"
CONTEXT = PROJECT_ROOT / "scripts" / "pact" / "context.py"
IMPACT = PROJECT_ROOT / "scripts" / "pact" / "impact.py"
RISK = PROJECT_ROOT / "scripts" / "pact" / "risk.py"


class FreshnessAndRiskTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-freshness-test-")
        self.root = pathlib.Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, relative: str, content: str) -> pathlib.Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def run_map(self, output: pathlib.Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(MAP),
                "--root",
                str(self.root),
                "--output",
                str(output),
                "--ensure",
            ],
            capture_output=True,
            text=True,
        )

    def run_code_map(self, output: pathlib.Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(CODE_MAP),
                "--root",
                str(self.root),
                "--output",
                str(output),
                "--ensure",
            ],
            capture_output=True,
            text=True,
        )

    def test_project_map_reuses_fresh_cache_and_rebuilds_after_change(self) -> None:
        self.write("README.md", "# Alpha\n")
        output = self.root / ".pact/cache/project-map.json"

        first = self.run_map(output)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        first_data = json.loads(output.read_text(encoding="utf-8"))

        second = self.run_map(output)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn("fresh ->", second.stdout)
        second_data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(first_data["generated_at"], second_data["generated_at"])
        self.assertEqual(
            first_data["source_fingerprint"],
            second_data["source_fingerprint"],
        )

        self.write("README.md", "# Beta\n")
        third = self.run_map(output)
        self.assertEqual(third.returncode, 0, third.stdout + third.stderr)
        third_data = json.loads(output.read_text(encoding="utf-8"))
        self.assertNotEqual(
            first_data["source_fingerprint"],
            third_data["source_fingerprint"],
        )

    def test_code_map_reuses_fresh_cache_and_rebuilds_after_change(self) -> None:
        self.write("src/a.ts", 'import { value } from "./b";\n')
        self.write("src/b.ts", "export const value = 1;\n")
        output = self.root / ".pact/cache/code-map.json"

        first = self.run_code_map(output)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        first_data = json.loads(output.read_text(encoding="utf-8"))

        second = self.run_code_map(output)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn("fresh ->", second.stdout)
        second_data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(
            first_data["source_fingerprint"],
            second_data["source_fingerprint"],
        )

        self.write("src/b.ts", "export const value = 2;\n")
        third = self.run_code_map(output)
        self.assertEqual(third.returncode, 0, third.stdout + third.stderr)
        third_data = json.loads(output.read_text(encoding="utf-8"))
        self.assertNotEqual(
            first_data["source_fingerprint"],
            third_data["source_fingerprint"],
        )

    def run_context(self, risk: str) -> dict:
        result = subprocess.run(
            [
                sys.executable,
                str(CONTEXT),
                "upgrade runtime",
                "--success",
                "Relevant implementation context is located",
                "--risk",
                risk,
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_risk_profile_changes_context_defaults(self) -> None:
        low = self.run_context("low")
        medium = self.run_context("medium")
        high = self.run_context("high")

        self.assertFalse(low["risk_policy"]["code_context"])
        self.assertTrue(medium["risk_policy"]["code_context"])
        self.assertTrue(high["risk_policy"]["code_context"])

        self.assertLess(
            low["risk_policy"]["knowledge_limit"],
            medium["risk_policy"]["knowledge_limit"],
        )
        self.assertLess(
            medium["risk_policy"]["knowledge_limit"],
            high["risk_policy"]["knowledge_limit"],
        )
        self.assertGreaterEqual(
            high["risk_policy"]["code_limit"],
            medium["risk_policy"]["code_limit"],
        )
        self.assertTrue(
            any("High-risk task" in item for item in high["known_unknowns"])
        )

    def run_impact(self, risk: str) -> dict:
        result = subprocess.run(
            [
                sys.executable,
                str(IMPACT),
                "--files",
                "scripts/pact/upgrade.py",
                "--risk",
                risk,
                "--json",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_risk_profile_changes_impact_code_analysis(self) -> None:
        low = self.run_impact("low")
        medium = self.run_impact("medium")

        self.assertFalse(low["code_analysis"])
        self.assertTrue(medium["code_analysis"])
        self.assertEqual(low["risk_level"], "low")
        self.assertEqual(medium["risk_level"], "medium")
        self.assertTrue(
            all(
                item["confidence"] in {
                    "relative-resolved",
                    "ast-resolved",
                    "heuristic",
                }
                for item in medium["code_candidate_impacts"]
            )
        )

    def test_risk_command_exposes_high_rigor_policy(self) -> None:
        result = subprocess.run(
            [sys.executable, str(RISK), "high", "--json"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data["code_context_default"])
        self.assertTrue(
            any("Convergence" in item for item in data["completion"])
        )


if __name__ == "__main__":
    unittest.main()
