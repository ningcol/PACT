"""Opt-in Domain-first route: conservative source maps and no authority promotion."""
from __future__ import annotations

import hashlib
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
import convergence_coverage
import scope_routing
from discover import document_term_matches, score_document, document_phrase_matches


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

    def test_cache_tamper_cannot_redirect_domain_alias_or_code_path(self):
        idx = self.root / ".pact/cache/project-map.json"
        base = json.loads(idx.read_text(encoding="utf-8"))
        target = next(d for d in base["documents"] if d.get("id") == "DOMAIN-LOGIN")
        for field, fake in (
            ("aliases", ["payments", "refund"]),
            ("paths", ["src/payments/**"]),
            ("text", "# Forged business rationale\nDEC-FAKE-001"),
            ("status", "candidate"),
        ):
            with self.subTest(field=field):
                poisoned = json.loads(json.dumps(base))
                doc = next(x for x in poisoned["documents"]
                           if x.get("id") == "DOMAIN-LOGIN")
                doc[field] = fake
                idx.write_text(json.dumps(poisoned), encoding="utf-8")
                # Fingerprint/id_to_path/visible files remain unchanged.
                with self.assertRaisesRegex(
                    ValueError, "cached metadata differs from source"
                ):
                    scope_routing.load_index(self.root)
        idx.write_text(json.dumps(base), encoding="utf-8")
        self.assertEqual(scope_routing.load_index(self.root), base)

    def test_unconfirmed_domain_or_forged_non_domain_cannot_claim_unique_route(self):
        self.write("docs/product/domains/login.md", '''+++
[pact]
type = "domain"
id = "DOMAIN-LOGIN"
status = "candidate"
aliases = ["login", "登录"]
paths = ["src/auth/**"]
+++
# User authentication
''')
        rebuilt = subprocess.run([
            sys.executable, str(ROOT / "scripts/pact/map.py"),
            "--root", str(self.root),
            "--output", str(self.root / ".pact/cache/project-map.json"),
        ], capture_output=True, text=True, timeout=30)
        self.assertEqual(rebuilt.returncode, 0, rebuilt.stdout + rebuilt.stderr)
        restored = scope_routing.load_index(self.root)
        self.assertEqual(scope_routing.resolve("login", restored)["status"], "unmapped")

    def test_domain_route_requires_convergence_for_unmaterialized_hints(self):
        packet = self.packet("Reformat src/auth/login.py imports")
        candidates = packet["scope_route"]["candidates"]
        self.assertEqual(len(candidates), 2)
        self.assertTrue(all(
            isinstance(item["sha256"], str) and len(item["sha256"]) == 64
            for item in candidates
        ))
        with tempfile.TemporaryDirectory(prefix="pact-scope-coverage-") as td:
            location = pathlib.Path(td) / "task-context.json"
            location.write_text(json.dumps(packet), encoding="utf-8")
            checksum = hashlib.sha256(location.read_bytes()).hexdigest()
            covered_domain = [{
                "path": packet["artifacts"][0]["path"],
                "disposition": "aligned",
                "rationale": "Domain router was inspected.",
            }]
            report = {"context_sha256": checksum, "coverage": covered_domain,
                      "findings": []}
            errors, stats = convergence_coverage.review(
                packet, report, root=self.root, context_path=location,
                expected_context_sha256=checksum,
            )
            self.assertEqual(
                set(stats["missing_artifacts"]),
                {candidate["path"] for candidate in candidates},
            )
            self.assertTrue(any("missing from Convergence" in e for e in errors))
            self.assertEqual(stats["required_artifacts"], 3)

            report["coverage"].extend({
                "path": item["path"], "disposition": "not-applicable",
                "rationale": "Source was read; formatting-only task does not "
                             "change this business constraint.",
            } for item in candidates)
            cleared, summary = convergence_coverage.review(
                packet, report, root=self.root, context_path=location,
                expected_context_sha256=checksum,
            )
            self.assertEqual(cleared, [])
            self.assertEqual(summary["covered_artifacts"], 3)

            source = self.root / candidates[0]["path"]
            source.write_text(source.read_text(encoding="utf-8") + "\nNew rule.\n",
                              encoding="utf-8")
            changed, _ = convergence_coverage.review(
                packet, report, root=self.root, context_path=location,
                expected_context_sha256=checksum,
            )
            self.assertTrue(any("changed since Task preparation" in e
                                for e in changed), changed)

    def test_more_than_twelve_linked_decisions_never_suppress_exact_id(self):
        for n in range(2, 16):
            ident = f"DEC-LOGIN-{n:03d}"
            self.write(f".agents/decisions/implemented/extra-{n:03d}.md",
                       f'+++\n[pact]\ntype = "decision"\nid = "{ident}"\n'
                       'status = "implemented"\ndomains = ["DOMAIN-LOGIN"]\n'
                       f'+++\n# Decision {ident}\n')
        built = subprocess.run([
            sys.executable, str(ROOT / "scripts/pact/map.py"),
            "--root", str(self.root),
            "--output", str(self.root / ".pact/cache/project-map.json"),
        ], capture_output=True, text=True, timeout=30)
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        route = scope_routing.load_index(self.root)
        chosen = scope_routing.resolve("login", route)
        self.assertGreater(chosen["truncated_candidates"], 0)
        self.assertIn(".agents/decisions/implemented/extra-015.md",
                      chosen["_all_candidate_paths"])
        explicit = self.hit(
            "DEC-LOGIN-015", "decision", "implemented",
            ".agents/decisions/implemented/extra-015.md",
            "Decision DEC-LOGIN-015", 100, ["exact stable id"],
        )
        result = self.packet("Reformat src/auth/login.py", hits=[explicit])
        self.assertEqual(result["scope_route"]["status"], "unique")
        self.assertFalse(result["scope_route"]["restricted_selection"])
        self.assertIn("DEC-LOGIN-015", result["decisions"])
        self.assertTrue(any(
            "selection was NOT narrowed" in note
            for note in result["known_unknowns"]
        ))

    def test_kana_and_hangul_unspaced_search_preserved(self):
        self.assertTrue(document_term_matches(
            "ログイン", "ユーザーログイン認証パラメータ"
        ))
        self.assertTrue(document_term_matches(
            "パラメータ", "ログイン認証パラメータ変更"
        ))
        self.assertTrue(document_term_matches(
            "로그인", "사용자로그인인증"
        ))
        self.assertTrue(document_phrase_matches(
            "로그인", "사용자로그인인증"
        ))
        doc = {
            "id": "DEC-AUTH-001", "title": "Session choice",
            "aliases": [], "domains": [], "status": "implemented",
            "artifact_type": "decision",
            "text": ("ユーザーログイン認証パラメータ変更を防ぐ。"
                     "사용자로그인인증 세션 변경을 거절한다."),
        }
        self.assertGreater(score_document(doc, "ログイン パラメータ 変更")[0], 0)
        self.assertGreater(score_document(doc, "로그인 세션")[0], 0)
        self.assertEqual(
            score_document(doc, "unit")[0], 0,
            "substring query 'unit' may not match a longer unrelated token",
        )
        self.assertFalse(document_term_matches("py", "Python"))

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
