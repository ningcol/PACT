"""Full-review M0: fail-closed responses and task knowledge identity."""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import subprocess
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))
import context as pact_context


class FullReviewM0Tests(unittest.TestCase):
    def query(self):
        return pact_context.run_discovery(
            ["Is the existing Decision still binding?"],
            4, code=False, code_limit=0,
        )

    def test_empty_successful_discover_is_not_zero_results(self):
        fake = subprocess.CompletedProcess(
            ["pact.py", "discover"], 0, stdout="", stderr="",
        )
        with mock.patch.object(pact_context.subprocess, "run",
                               return_value=fake):
            with self.assertRaisesRegex(RuntimeError, "without a response"):
                self.query()

    def test_incomplete_discover_json_never_acts_as_no_matches(self):
        invalid = [
            None, [], {}, {"results":[]}, {"results":{},"code_results":[]},
            {"results":[],"code_results":{}},
            {"results":[None],"code_results":[]},
            {"results":[],"code_results":[None]},
            {"results":[],"code_results":[],"result_count":42},
        ]
        for packet in invalid:
            with self.subTest(packet=packet):
                fake = subprocess.CompletedProcess(
                    ["pact.py", "discover"], 0,
                    stdout=json.dumps(packet), stderr="",
                )
                with mock.patch.object(pact_context.subprocess, "run",
                                       return_value=fake):
                    with self.assertRaises(RuntimeError):
                        self.query()

    def test_partial_source_rows_cannot_silently_disappear(self):
        valid = {
            "path": ".agents/decisions/implemented/owner.md",
            "score": 180,
            "reasons": ["exact stable id"],
            "id": "DEC-OWNER",
            "artifact_type": "decision",
            "status": "implemented",
            "title": "Owner approval",
            "mixed_authority": False,
            "domains": [],
            "related": [],
            "verification": [],
        }
        for bad in (
            {},
            {"path": "", "score": 12},
            {key: value for key, value in valid.items() if key != "path"},
            {key: value for key, value in valid.items() if key != "status"},
            {**valid, "score": "500"},
            {**valid, "reasons": None},
            {**valid, "domains": "DOMAIN-AUTH"},
        ):
            with self.subTest(bad=bad):
                payload = {
                    "results": [bad], "result_count": 1,
                    "code_results": [], "code_result_count": 0,
                }
                fake = subprocess.CompletedProcess(
                    ["pact.py", "discover"], 0,
                    stdout=json.dumps(payload), stderr="",
                )
                with mock.patch.object(pact_context.subprocess, "run",
                                       return_value=fake):
                    with self.assertRaisesRegex(
                        RuntimeError, "malformed/inconsistent results"
                    ):
                        self.query()

    def test_invalid_code_row_cannot_silently_disappear(self):
        payload = {
            "results": [], "result_count": 0,
            "code_results": [{"language": "python", "is_test": False,
                              "symbols": [], "score": 50,
                              "reasons": ["exact symbol"]}],
            "code_result_count": 1,
        }
        fake = subprocess.CompletedProcess(
            ["pact.py", "discover"], 0,
            stdout=json.dumps(payload), stderr="",
        )
        with mock.patch.object(pact_context.subprocess, "run",
                               return_value=fake):
            with self.assertRaisesRegex(RuntimeError, "malformed/inconsistent"):
                self.query()

    def test_source_bound_complete_discover_row_remains_valid(self):
        item = {
            "path": ".agents/decisions/implemented/owner.md",
            "score": 180,
            "reasons": ["exact stable id"], "id": "DEC-OWNER",
            "artifact_type": "decision", "status": "implemented",
            "title": "Owner approval", "mixed_authority": False,
            "domains": [], "related": [], "verification": [],
        }
        payload = {
            "results": [item], "result_count": 1,
            "code_results": [], "code_result_count": 0,
        }
        fake = subprocess.CompletedProcess(
            ["pact.py", "discover"], 0,
            stdout=json.dumps(payload), stderr="",
        )
        with mock.patch.object(pact_context.subprocess, "run",
                               return_value=fake):
            self.assertEqual(self.query(), payload)

    def test_genuine_empty_json_is_valid(self):
        expected = {
            "query": "Is the existing Decision still binding?",
            "result_count": 0, "results": [],
            "code_result_count": 0, "code_results": [],
        }
        fake = subprocess.CompletedProcess(
            ["pact.py", "discover"], 0,
            stdout=json.dumps(expected), stderr="",
        )
        with mock.patch.object(pact_context.subprocess, "run",
                               return_value=fake):
            self.assertEqual(self.query(), expected)

    def test_failed_discover_stays_failed(self):
        fake = subprocess.CompletedProcess(
            ["pact.py", "discover"], 2, stdout="",
            stderr="tampered cache",
        )
        with mock.patch.object(pact_context.subprocess, "run",
                               return_value=fake):
            with self.assertRaisesRegex(RuntimeError, "tampered cache"):
                self.query()


if __name__ == "__main__":
    unittest.main()
