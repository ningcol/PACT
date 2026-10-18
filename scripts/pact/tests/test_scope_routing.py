"""Opt-in Domain-first route: conservative source maps and no authority promotion."""
from __future__ import annotations

import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))
import context
import scope_routing
from discover import document_term_matches, score_document


class ScopeFirstTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pact-domain-first-")
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.write("docs/product/domains/login.md", '''+++
[pact]
type = "domain"
id = "DOMAIN-LOGIN"
status = "confirmed"
aliases = ["login", "sign in", "登录"]
paths = ["src/auth/**"]
+++

# User authentication

## Durable rules
- RULE-LOGIN-001

## Durable decisions
- DEC-LOGIN-001
''')
        self.write("docs/product/rules/login-security.md", '''+++
[pact]
type = "rule"
id = "RULE-LOGIN-001"
status = "confirmed"
domains = ["DOMAIN-LOGIN"]
+++

# Require approved sign-in attempts
''')
        self.write(".agents/decisions/implemented/login-session.md", '''+++
[pact]
type = "decision"
id = "DEC-LOGIN-001"
status = "implemented"
domains = ["DOMAIN-LOGIN"]
+++

# Session lifetime
## Decision
Keep the previously approved session lifetime.
''')
        self.write("docs/product/domains/payment.md", '''+++
[pact]
type = "domain"
id = "DOMAIN-PAY"
status = "confirmed"
aliases = ["payment", "pay"]
paths = ["src/payments/**"]
+++

# Payments
''')
        self.write("docs/product/rules/payment.md", '''+++
[pact]
type = "rule"
id = "RULE-PAY-001"
status = "confirmed"
domains = ["DOMAIN-PAY"]
+++
# Refund approvals
''')
        self.write("src/auth/login.py", "def login():\n    return True\n")
        self.write("src/payments/pay.py", "def payment():\n    return True\n")
        cmd = [
            sys.executable, str(ROOT / "scripts/pact/map.py"),
            "--root", str(self.root),
            "--output", str(self.root / ".pact/cache/project-map.json"),
        ]
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        self.index = scope_routing.load_index(self.root)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def hit(id_, kind, status, path, title, score, reasons=None):
        return {
            "id": id_, "artifact_type": kind, "status": status,
            "path": path, "title": title, "score": score,
            "reasons": reasons or [], "mixed_authority": False,
            "domains": [], "verification": [],
        }

    def lexical(self):
        # Simulates a weak all-repo lexical response; these are NOT authority.
        return [
            self.hit("DEC-PAY-001", "decision", "implemented",
                     "docs/product/rules/payment.md", "Payment", 25),
            self.hit("DEC-LOGIN-001", "decision", "implemented",
                     ".agents/decisions/implemented/login-session.md",
                     "Session lifetime", 10),
        ]

    def packet(self, task, args=None, hits=None):
        args = args or []
        hits = hits if hits is not None else self.lexical()

        def fake_discovery(*_, **__):
            return {"queries": [task], "results": hits, "code_results": []}

        argv = [
            "context", task, "--success", "Preserve existing behavior",
            "--risk", "low", "--no-code", "--limit", "4", "--token-budget",
            "2048", "--scope-first", *args,
        ]
        out = io.StringIO()
        err = io.StringIO()
        with mock.patch.object(context, "ROOT", self.root):
            with mock.patch.object(context, "run_discovery",
                                   side_effect=fake_discovery):
                with mock.patch.object(sys, "argv", argv):
                    with redirect_stdout(out), redirect_stderr(err):
                        code = context.main()
        self.assertEqual(code, 0, err.getvalue() + out.getvalue())
        return json.loads(out.getvalue())

    def test_scope_matches_explicit_alias_or_code_path_not_unrelated_text(self):
        for text in (
            "Review login retry messages",
            "Review 用户登录 after a failure",
            "Reformat src/auth/login.py without changing business behavior",
        ):
            with self.subTest(text=text):
                routed = scope_routing.resolve(text, self.index)
                self.assertEqual(routed["status"], "unique")
                self.assertEqual(routed["domains"][0]["id"], "DOMAIN-LOGIN")
                self.assertFalse(routed["applicability_verified"])
                self.assertEqual(
                    {x["id"] for x in routed["candidates"]},
                    {"DEC-LOGIN-001", "RULE-LOGIN-001"},
                )
        self.assertEqual(
            scope_routing.resolve("Use logins2 for tests", self.index)["status"],
            "unmapped",
        )
        self.assertEqual(
            scope_routing.resolve("login and payment account", self.index)["status"],
            "ambiguous",
        )

    def test_scope_first_materializes_domain_but_keeps_decisions_as_hints(self):
        p = self.packet("Reformat src/auth/login.py imports")
        self.assertEqual(p["scope_route"]["status"], "unique")
        self.assertTrue(p["scope_route"]["restricted_selection"])
        self.assertFalse(p["scope_route"]["applicability_verified"])
        self.assertEqual(p["decisions"], [])
        self.assertEqual(p["applicable_rules"], [])
        self.assertEqual([x["id"] for x in p["artifacts"]], ["DOMAIN-LOGIN"])
        self.assertEqual(
            {x["id"] for x in p["scope_route"]["candidates"]},
            {"DEC-LOGIN-001", "RULE-LOGIN-001"},
        )
        self.assertTrue(any("candidate hints" in s for s in p["known_unknowns"]))

    def test_routing_preserves_explicit_cross_domain_required_rule(self):
        rule = self.hit(
            "RULE-PAY-001", "rule", "confirmed",
            "docs/product/rules/payment.md", "Refund approvals", 200,
            ["exact stable id"],
        )
        p = self.packet(
            "Reformat src/auth/login.py imports",
            ["--require-rule", "RULE-PAY-001"], [rule],
        )
        self.assertEqual(p["applicable_rules"], ["RULE-PAY-001"])
        self.assertEqual(p["decisions"], [])
        self.assertEqual(p["scope_route"]["status"], "unique")

    def test_unknown_or_ambiguous_scope_preserves_baseline_candidates(self):
        for task, status in (
            ("Refactor opaque component without path", "unmapped"),
            ("Modify login and payment behavior", "ambiguous"),
        ):
            p = self.packet(task)
            self.assertEqual(p["scope_route"]["status"], status)
            self.assertFalse(p["scope_route"]["restricted_selection"])
            self.assertIn("DEC-PAY-001", p["decisions"])

    def test_high_risk_keeps_unrestricted_candidates(self):
        task = "Change login permissions"
        with mock.patch.object(context, "ROOT", self.root), mock.patch.object(
            context, "run_discovery",
            return_value={"queries": [task], "results": self.lexical(), "code_results": []},
        ), mock.patch.object(sys, "argv", [
            "context", task, "--success", "Keep approved permissions",
            "--risk", "high", "--no-code", "--scope-first", "--limit", "4",
        ]):
            out,err=io.StringIO(),io.StringIO()
            with redirect_stdout(out),redirect_stderr(err):
                code=context.main()
        self.assertEqual(code, 0, err.getvalue())
        p=json.loads(out.getvalue())
        self.assertFalse(p["scope_route"]["restricted_selection"])
        self.assertIn("DEC-PAY-001", p["decisions"])

    def test_index_fails_closed_on_stale_or_forged_metadata(self):
        idx = self.root / ".pact/cache/project-map.json"
        contents = json.loads(idx.read_text())
        contents["documents"].append({"path": "docs/ghost.md", "id": None})
        idx.write_text(json.dumps(contents), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "stale or malformed"):
            scope_routing.load_index(self.root)

    def test_boundary_scoring_preserves_exact_ids_and_cjk(self):
        decision = {
            "id": "DEC-LOGIN-001", "title": "Login Authentication",
            "aliases": ["sign in"], "domains": [],
            "status": "implemented", "artifact_type": "decision",
            "text": "The Python login endpoint requires a screen reader.",
        }
        self.assertFalse(document_term_matches("py", "Python"))
        self.assertFalse(document_term_matches("s", "Session"))
        self.assertFalse(document_term_matches("unit", "opportunity"))
        self.assertTrue(document_term_matches("reader", "screen reader"))
        self.assertTrue(document_term_matches("登录", "用户登录验证码"))
        self.assertEqual(score_document(decision, "Reformat app.py imports")[0], 0)
        self.assertGreater(score_document(decision, "DEC-LOGIN-001")[0], 200)
        self.assertGreater(score_document(decision, "screen reader")[0], 0)
        self.assertGreater(score_document(decision, "sign in")[0], 100)


if __name__ == "__main__":
    unittest.main()
