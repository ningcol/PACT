"""Unicode JSON values must survive locale-dependent subprocess pipes."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
QUERY = "请检查专业选择确认后的显示🧪"
CLAIM = "已验证中文与非 BMP 字符🧪保持原值"


class JsonTransportTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory(prefix="pact-json-pipe-")))
        self.env = dict(os.environ, PYTHONIOENCODING="cp1252:strict", PYTHONUTF8="0")
        self.invoke(sys.executable, ROOT / "scripts/pact/init.py", "--target", self.root, "--apply", "--json")
        domain = self.root / "docs/product/domains/selection.md"
        domain.parent.mkdir(parents=True)
        domain.write_text(
            '+++\n[pact]\ntype = "domain"\nid = "DOMAIN-SELECTION"\n'
            'status = "candidate"\naliases = ["专业选择"]\n+++\n'
            '# 专业选择🧪\n\nSynthetic transport fixture, not approved product truth.\n',
            encoding="utf-8",
        )

    def invoke(self, *command, expected=0):
        result = subprocess.run([str(x) for x in command], cwd=self.root, env=self.env,
                                capture_output=True, encoding="ascii", timeout=60)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        # ASCII decoding above also checks accented/BMP/non-BMP values do not
        # depend on whichever locale the parent uses to decode the pipe.
        return json.loads(result.stdout)

    def pact(self, *args, expected=0):
        return self.invoke(sys.executable, self.root / "pact.py", *args, expected=expected)

    def prepare(self):
        return self.pact("task", "prepare", QUERY, "--success", CLAIM, "--risk", "low",
                         "--no-code", "--task-id", "TASK-JSON-PIPE", "--json")

    def test_installed_retrieval_round_trips_unicode_through_legacy_pipes(self):
        for command in ("discover", "explain", "inspect"):
            with self.subTest(command=command):
                flags = ["--no-code"] if command == "inspect" else []
                result = self.pact(command, QUERY, *flags, "--json")
                self.assertEqual(result["query"], QUERY)
        context = self.pact("context", QUERY, "--success", CLAIM, "--risk", "low", "--no-code")
        self.assertEqual(context["task"], QUERY)
        prepared = self.prepare()
        self.assertEqual(prepared["task"], QUERY)
        self.assertEqual(self.pact("task", "status", "TASK-JSON-PIPE", "--json")["task"], QUERY)
        # Only stdout transport is escaped: persisted, SHA-bound artifacts keep
        # their existing UTF-8 serialization rather than changing file hashes.
        contract = (self.root / prepared["contract"]).read_text(encoding="utf-8")
        self.assertIn(CLAIM, contract)
        self.assertIn(QUERY, (self.root / prepared["context"]).read_text(encoding="utf-8"))

    def test_completion_helpers_preserve_unicode_claims_without_completing(self):
        prepared = self.prepare()
        self.pact("task", "draft", "TASK-JSON-PIPE", "--json")
        self.pact("task", "verify", "TASK-JSON-PIPE", "--criterion", "AC-1", "--claim", CLAIM,
                  "--json", "--", sys.executable, "-c", "print('checked')")
        result = self.pact("task", "assist", "TASK-JSON-PIPE", "--write-draft", "--json")
        self.assertTrue(result["draft_written"])
        owner = json.loads((self.root / prepared["completion_bundle"] / "owner-report.json").read_text(encoding="utf-8"))
        self.assertEqual(owner["status"], "partial")
        self.assertEqual(owner["verification"][0]["claim"], CLAIM)
        resumed = self.pact("task", "resume", "TASK-JSON-PIPE", "--json", expected=1)
        self.assertEqual(resumed["task_intent"], QUERY)
        self.assertFalse(resumed["task_delta"]["supported"])  # fixture intentionally has no Git
        self.pact("eval", "--task", "TASK-JSON-PIPE", "--json")
        finished = self.pact("task", "finish", "TASK-JSON-PIPE", "--json", expected=1)
        self.assertFalse(finished["complete"])


if __name__ == "__main__":
    unittest.main()
