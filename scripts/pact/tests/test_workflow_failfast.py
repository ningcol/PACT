"""Prevent GitHub Actions falsely green portability and release jobs on Windows.

PowerShell can continue after an earlier native command exits nonzero. A final
successful command then masks a failed unittest command. Declare Bash with
fail-fast semantics for multi-command steps on every target OS.
"""

from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]


class WorkflowFailFastTests(unittest.TestCase):
    def test_os_matrix_commands_are_fail_fast_on_every_platform(self):
        for filename in ("core-matrix.yml", "release.yml"):
            with self.subTest(filename=filename):
                config = (
                    ROOT / ".github" / "workflows" / filename
                ).read_text(encoding="utf-8")
                for step in ("Runtime entry points", "Cross-platform portability tests"):
                    with self.subTest(step=step):
                        expected = (
                            f"      - name: {step}\n"
                            "        shell: bash\n"
                            "        run: |\n"
                            "          set -euo pipefail\n"
                        )
                        self.assertIn(expected, config)
                        self.assertIn(
                            "python -m unittest discover -s scripts/pact/tests "
                            "-p 'test_*.py'", config,
                            "every PACT test must run on all 9 portability cells",
                        )

    def test_release_source_validation_is_fail_fast_too(self):
        release = (
            ROOT / ".github" / "workflows" / "release.yml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "      - name: Validate release source\n"
            "        shell: bash\n"
            "        run: |\n"
            "          set -euo pipefail\n",
            release,
        )


    def test_all_synthetic_cases_remain_an_explicit_failfast_check(self):
        config = (
            ROOT / ".github" / "workflows" / "pact-check.yml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "      - name: Run all three PACT-only synthetic evaluation cases\n"
            "        shell: bash\n"
            "        run: |\n"
            "          set -euo pipefail\n"
            "          python scripts/benchmark/eight_stage_synthetic.py",
            config,
        )
        self.assertIn('assert report["case_count"] == 3', config)
        self.assertIn('assert report["owner_time_minutes"] is None', config)
        self.assertIn('assert report["release_attestation"] is False', config)


if __name__ == "__main__":
    unittest.main()
