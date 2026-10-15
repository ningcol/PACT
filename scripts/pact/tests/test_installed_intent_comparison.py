"""S3: fixed-budget installed-runtime intent experiment on PACT-owned facts.

A deterministic synthetic fixture exercises real discover/context CLI modes.
It is *not* a withheld blind case or a claimed real retrieval improvement.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest


SOURCE = pathlib.Path(__file__).resolve().parents[3]
INIT = SOURCE / "scripts" / "pact" / "init.py"
QUERY = "cache"
KNOWLEDGE_LIMIT = 5
TOKEN_BUDGET = 4096


class InstalledIntentComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="pact-intent-fixed-")
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name) / "project"
        self.root.mkdir()
        (self.root / "README.md").write_text("# Fictional cache\n")
        initialized = subprocess.run(
            [sys.executable, str(INIT), "--target", str(self.root), "--apply"],
            capture_output=True, text=True,
        )
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        self.write(
            "docs/product/rules/cache.md",
            "rule", "RULE-CACHE-001", "confirmed",
            "Cache policy", "Current confirmed fictional cache rule for a local fixture.",
        )
        self.write(
            ".agents/decisions/implemented/current.md",
            "decision", "DEC-CACHE-CURRENT", "implemented",
            "Cache current choice", "Current engineering rationale for guarded cache writes.",
        )
        self.write(
            ".agents/decisions/rejected/unsafe.md",
            "decision", "DEC-CACHE-REJECTED", "rejected",
            "Cache rejected alternative",
            "Rejected unbounded cache because eviction was absent; revisit with durable eviction.",
        )
        self.write(
            ".agents/decisions/implemented/old.md",
            "decision", "DEC-CACHE-OLD", "superseded",
            "Cache old design", "Historical old cache rationale retained for future reasoning.",
        )

    def write(self, relative, kind, ident, status, title, description):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "+++\n[pact]\n"
            f'type = "{kind}"\n'
            f'id = "{ident}"\n'
            f'status = "{status}"\n'
            "domains = []\n+++\n\n"
            f"# {title}\n\n{description}\n",
            encoding="utf-8",
        )

    def pact(self, *command):
        start = time.perf_counter()
        result = subprocess.run(
            [sys.executable, str(self.root / "pact.py"), *command],
            cwd=self.root, capture_output=True, text=True,
        )
        elapsed = time.perf_counter() - start
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout), elapsed

    def discover(self, intent):
        args = ["discover", QUERY, "--limit", str(KNOWLEDGE_LIMIT), "--json"]
        if intent is not None:
            args.extend(["--intent", intent])
        return self.pact(*args)

    def context(self, intent):
        args = [
            "context", QUERY, "--success", "Locate cached implementation rationale",
            "--risk", "low", "--no-code",
            "--limit", str(KNOWLEDGE_LIMIT),
            "--token-budget", str(TOKEN_BUDGET),
        ]
        if intent is not None:
            args.extend(["--intent", intent])
        return self.pact(*args)

    def test_installed_tenth_query_exact_id_survives_budget_one(self):
        # Nine broad queries repeatedly match nine confirmed Rules. Their
        # fused RRF scores are much higher than one exact-ID lookup placed
        # in the tenth query. Optional intent MUST reserve the exact result
        # before the truncated nine-slot candidate pool is published.
        queries = [
            "cachetermnorth", "cachetermsouth", "cachetermeast",
            "cachetermwest", "cachetermspring", "cachetermwinter",
            "cachetermsummer", "cachetermautumn", "cachetermdelta",
        ]
        terms = " ".join(queries)
        for i in range(9):
            self.write(
                f"docs/product/rules/broad-{i}.md",
                "rule", f"RULE-BROAD-{i}", "confirmed",
                f"Common test rule {i}",
                f"Fictional shared words for retrieval only: {terms}",
            )
        argv = ["discover", queries[0], "--limit", "1", "--json"]
        for query in [*queries[1:], "DEC-CACHE-OLD"]:
            argv.extend(["--query", query])
        normal, _ = self.pact(*argv)
        self.assertEqual(normal["query_count"], 10)
        self.assertEqual(normal["result_count"], 1)
        self.assertNotEqual(
            normal["results"][0]["id"], "DEC-CACHE-OLD",
            "RED fixture: default broad RRF should crowd out the tenth hit",
        )
        intent, _ = self.pact(*argv, "--intent", "work")
        self.assertEqual(intent["query_count"], 10)
        self.assertEqual(intent["result_count"], 1)
        self.assertEqual(intent["results"][0]["id"], "DEC-CACHE-OLD")
        self.assertEqual(intent["intent"], "work")
        self.assertTrue(any(
            reason.endswith(": exact stable id")
            for reason in intent["results"][0]["reasons"]
        ), intent["results"][0]["reasons"])

    def test_real_installed_modes_preserve_authority_and_same_limits(self):
        # Check fixture front matter before indexed discovery.
        checked = subprocess.run(
            [sys.executable, str(self.root / "pact.py"), "check"],
            cwd=self.root, capture_output=True, text=True,
        )
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        scenarios = (None, "work", "decision", "history")
        found = {}
        contexts = {}
        timing = {}
        for intent in scenarios:
            label = intent or "default"
            found[label], discover_s = self.discover(intent)
            contexts[label], context_s = self.context(intent)
            timing[label] = {
                "discover_elapsed_ms": round(discover_s * 1000, 2),
                "context_elapsed_ms": round(context_s * 1000, 2),
            }
            self.assertLessEqual(found[label]["result_count"], KNOWLEDGE_LIMIT)
            self.assertEqual(
                contexts[label]["risk_policy"]["knowledge_limit"],
                KNOWLEDGE_LIMIT,
            )
            self.assertEqual(
                contexts[label]["risk_policy"]["materialization_token_budget"],
                TOKEN_BUDGET,
            )
            self.assertEqual(contexts[label]["status"], "candidate")
            self.assertEqual(contexts[label]["version"], 1)
            self.assertIn("RULE-CACHE-001", contexts[label]["applicable_rules"])
            self.assertNotIn("DEC-CACHE-REJECTED", contexts[label]["applicable_rules"])
        # Freeze the historical no-intent lexical order. Here the three
        # equally scored matching titles are resolved by repository path,
        # not by the new optional work/decision/history intent.
        # A real project README has no stable PACT ID. It still scores
        # lexically and sorts ahead of the rule on this exact fixture.
        # Pin both identity *and path* to protect default ordering without
        # assuming every result is a structured Rule or Decision artifact.
        self.assertEqual(found["default"]["result_count"], KNOWLEDGE_LIMIT)
        self.assertEqual(
            [(item["id"], item["path"])
             for item in found["default"]["results"]],
            [
                ("DEC-CACHE-CURRENT",
                 ".agents/decisions/implemented/current.md"),
                ("DEC-CACHE-REJECTED",
                 ".agents/decisions/rejected/unsafe.md"),
                (None, "README.md"),
                ("RULE-CACHE-001", "docs/product/rules/cache.md"),
                ("DEC-CACHE-OLD",
                 ".agents/decisions/implemented/old.md"),
            ],
        )
        self.assertEqual(found["work"]["results"][0]["id"], "RULE-CACHE-001")
        self.assertIn(
            found["decision"]["results"][0]["id"],
            {"DEC-CACHE-CURRENT", "DEC-CACHE-REJECTED"},
        )
        self.assertIn(
            found["history"]["results"][0]["id"],
            {"DEC-CACHE-OLD", "DEC-CACHE-REJECTED"},
        )
        self.assertEqual(
            contexts["default"]["risk_policy"],
            contexts["work"]["risk_policy"],
        )
        self.assertNotIn("intent", contexts["history"])
        # Measured environment-dependent timings are diagnostics only; no
        # invented latency advantage or absolute limit is asserted.
        print("PACT intent fixed-budget diagnostics (synthetic, not blind): "
              + json.dumps(timing, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
