"""Regression tests for explicit repository-local verification source provenance."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
RUN = PROJECT_ROOT / "scripts" / "pact" / "run.py"
RUNTIME = PROJECT_ROOT / "scripts" / "pact"
sys.path.insert(0, str(RUNTIME))
from evidence import provenance_review, readiness


class VerificationInputOriginsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-run-inputs-")
        self.root = pathlib.Path(self.temp.name) / "project"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "PACT Test"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "pact@example.invalid"],
            cwd=self.root, check=True,
        )
        (self.root / "README.md").write_text("# Verified project\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.root, check=True)
        self.outside = pathlib.Path(self.temp.name) / "external-check.py"
        self.outside.write_text("print('external script ran')\n", encoding="utf-8")
        self.local = self.root / "checks" / "verify.py"
        self.local.parent.mkdir()
        self.local.write_text("print('local script ran')\n", encoding="utf-8")
        self.receipt = self.root / ".pact" / "runs" / "TASK-INPUTS" / "run.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_pact(self, options: list[str], command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable, str(RUN),
                "--task-id", "TASK-INPUTS",
                "--cwd", str(self.root),
                "--output", str(self.receipt),
                *options, "--", *command,
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def test_external_script_is_rejected_by_default_without_receipt(self) -> None:
        result = self.run_pact([], [sys.executable, str(self.outside)])
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("external script/schema/config path", result.stderr)
        self.assertFalse(self.receipt.exists())

    def test_external_script_with_spaces_is_not_mistaken_for_shell_tokens(self) -> None:
        spaced = pathlib.Path(self.temp.name) / "external script.py"
        spaced.write_text("print('unsafe')\n", encoding="utf-8")
        result = self.run_pact([], [sys.executable, str(spaced)])
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse(self.receipt.exists())

    def test_external_dotenv_config_is_not_silent_input(self) -> None:
        outside_config = pathlib.Path(self.temp.name) / ".env"
        outside_config.write_text("SYNTHETIC=1\n", encoding="utf-8")
        result = self.run_pact(
            [], [sys.executable, "-c", "print('ok')", str(outside_config)]
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse(self.receipt.exists())

    def test_external_script_requires_opt_in_and_cannot_complete_medium_risk(self) -> None:
        result = self.run_pact(
            ["--allow-external-inputs"], [sys.executable, str(self.outside)]
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        record = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(record["verification_input_scope"], "external-opt-in")
        self.assertEqual(record["external_input_count"], 1)

        evidence = {
            "task_id": "TASK-INPUTS",
            "risk_level": "medium",
            "claims": [{
                "id": "EV-EXTERNAL",
                "claim": "The external check passes",
                "required": True,
                "status": "pass",
                "evidence": [{
                    "kind": "test", "provenance": "pact-run",
                    "ref": self.receipt.relative_to(self.root).as_posix(),
                }],
            }],
        }
        errors, gaps, _ = provenance_review(evidence, self.root)
        self.assertEqual(errors, [])
        self.assertTrue(any("external verification sources" in item for item in gaps))
        self.assertEqual(readiness(evidence, gaps), "incomplete")

    def test_declared_local_source_is_hashed_and_current(self) -> None:
        result = self.run_pact(
            ["--source", "checks/verify.py"],
            [sys.executable, str(self.local)],
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        record = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(record["verification_input_scope"], "declared-files")
        self.assertEqual(record["external_input_count"], 0)
        self.assertEqual(record["verification_sources"][0]["path"], "checks/verify.py")
        self.assertRegex(record["verification_sources"][0]["sha256"], "^[a-f0-9]{64}$")

    def test_missing_or_escaping_declared_source_is_refused(self) -> None:
        for source in ("../external-check.py", "checks/missing.py", str(self.outside)):
            with self.subTest(source=source):
                result = self.run_pact(
                    ["--source", source], [sys.executable, str(self.local)]
                )
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertFalse(self.receipt.exists())

    def test_mutating_declared_source_cannot_publish_passing_receipt(self) -> None:
        self.local.write_text(
            "from pathlib import Path\n"
            "p = Path(__file__)\n"
            "p.write_text(p.read_text() + '# changed\\n')\n",
            encoding="utf-8",
        )
        result = self.run_pact(
            ["--source", "checks/verify.py"],
            [sys.executable, str(self.local)],
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("source changed during execution", result.stderr)
        self.assertFalse(self.receipt.exists())

    def test_required_medium_high_pass_rejects_run_that_changed_managed_files(self) -> None:
        script = (
            "from pathlib import Path; "
            "p = Path('README.md'); p.write_text(p.read_text() + 'changed\\n')"
        )
        run = self.run_pact([], [sys.executable, "-c", script])
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertTrue(receipt["workspace_changed"])
        ref = self.receipt.relative_to(self.root).as_posix()

        for risk in ("medium", "high"):
            with self.subTest(risk=risk):
                evidence = {
                    "task_id": "TASK-INPUTS", "risk_level": risk,
                    "claims": [{
                        "id": "EV-MUTATED", "claim": "Executed with a managed edit",
                        "required": True, "status": "pass",
                        "evidence": [{"kind": "test", "provenance": "pact-run", "ref": ref}],
                    }],
                }
                errors, gaps, metrics = provenance_review(evidence, self.root)
                self.assertEqual(errors, [])
                self.assertTrue(any("workspace_changed" in g for g in gaps), gaps)
                self.assertEqual(metrics["workspace_bound_claims"], 0)
                self.assertEqual(readiness(evidence, gaps), "incomplete")

    def test_managed_edit_is_allowed_for_low_risk_diagnostic_claim(self) -> None:
        result = self.run_pact(
            [], [sys.executable, "-c", "from pathlib import Path; Path('new.txt').write_text('changed')"]
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(self.receipt.read_text())["workspace_changed"])
        evidence = {
            "task_id": "TASK-INPUTS", "risk_level": "low",
            "claims": [{
                "id": "EV-LOW", "claim": "Exploratory work",
                "required": True, "status": "pass",
                "evidence": [{"kind": "test", "provenance": "pact-run",
                              "ref": self.receipt.relative_to(self.root).as_posix()}],
            }],
        }
        errors, gaps, _ = provenance_review(evidence, self.root)
        self.assertEqual(errors, [])
        self.assertEqual(gaps, [])

    def test_ignored_generated_files_do_not_poison_required_high_risk_pass(self) -> None:
        result = self.run_pact(
            [], [sys.executable, "-c",
                 "from pathlib import Path; p=Path('.pact/tmp/generated.txt'); "
                 "p.parent.mkdir(parents=True, exist_ok=True); p.write_text('output')"]
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(json.loads(self.receipt.read_text())["workspace_changed"])
        evidence = {
            "task_id": "TASK-INPUTS", "risk_level": "high",
            "claims": [{
                "id": "EV-STABLE", "claim": "Generated output only",
                "required": True, "status": "pass",
                "evidence": [{"kind": "test", "provenance": "pact-run",
                              "ref": self.receipt.relative_to(self.root).as_posix()}],
            }],
        }
        errors, gaps, metrics = provenance_review(evidence, self.root)
        self.assertEqual(errors, [])
        self.assertEqual(gaps, [])
        self.assertEqual(metrics["workspace_bound_claims"], 1)

    def test_external_script_in_shell_argument_is_detected(self) -> None:
        result = self.run_pact(
            [], ["bash", "-lc", f"{sys.executable} {self.outside}"]
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse(self.receipt.exists())


if __name__ == "__main__":
    unittest.main()
