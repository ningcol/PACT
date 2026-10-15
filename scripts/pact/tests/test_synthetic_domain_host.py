"""S7-B: fictional PACT-only brownfield Domain/Rule/README/host workflow.

This represents an isolated mechanism, not a real zx-zsb run or confirmed Owner
product policy. All fixture mutations are local to a disposable test directory.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


SOURCE = pathlib.Path(__file__).resolve().parents[3]
INIT = SOURCE / "scripts" / "pact" / "init.py"


class SyntheticDomainHostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pact-synthetic-domain-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name) / "project"
        self.root.mkdir()
        (self.root / "README.md").write_text(
            "# Fictional admission workflow\n", encoding="utf-8"
        )
        result = subprocess.run(
            [sys.executable, str(INIT), "--target", str(self.root), "--apply"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.write("src/admission/enrollment.py", (
            "def school_enrollment_request(student_id):\n"
            "    # Fictional intake implementation, not approved product semantics\n"
            "    return student_id\n"
        ))
        self.write("src/admission/README.md", (
            "# Fictional admission module\n"
            "This README is only a code navigation hint.\n"
        ))
        self.write("docs/product/domains/admission.md", (
            "+++\n[pact]\ntype = \"domain\"\n"
            "id = \"DOMAIN-SCHOOL-001\"\nstatus = \"candidate\"\n"
            "domains = []\n+++\n\n"
            "# Fictional school enrollment process\n"
            "Unconfirmed domain vocabulary.\n"
        ))
        self.write("docs/product/rules/intake.md", self.rule("candidate"))

    def write(self, path: str, body: str) -> pathlib.Path:
        output = self.root / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(body, encoding="utf-8")
        return output

    def rule(self, status: str) -> str:
        return (
            "+++\n[pact]\ntype = \"rule\"\n"
            "id = \"RULE-SCHOOL-001\"\n"
            f"status = \"{status}\"\n"
            "domains = [\"DOMAIN-SCHOOL-001\"]\n+++\n\n"
            "# Fictional school enrollment intake\n"
            "Candidate rule: intake requires manual approval by an actual Owner.\n"
        )

    def pact(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.root / "pact.py"), *args],
            cwd=self.root, capture_output=True, text=True,
        )

    def context(self, *, required: bool = False) -> subprocess.CompletedProcess[str]:
        args = [
            "context", "school enrollment intake",
            "--success", "Locate fictional intake implementation",
            "--risk", "low", "--code", "--json"  # CLI emits JSON by default
        ]
        args.remove("--json")
        if required:
            args.extend(["--require-rule", "RULE-SCHOOL-001"])
        return self.pact(*args)

    def test_candidate_rule_remains_non_normative_and_host_check_read_only(self):
        check = self.pact("check")
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        context_result = self.context()
        self.assertEqual(
            context_result.returncode, 0,
            context_result.stdout + context_result.stderr,
        )
        envelope = json.loads(context_result.stdout)
        self.assertNotIn("RULE-SCHOOL-001", envelope["applicable_rules"])
        self.assertTrue(
            any("No confirmed Product Rule" in s for s in envelope["known_unknowns"])
        )
        self.assertTrue(
            any("src/admission/README.md" in s for s in envelope["known_unknowns"])
        )
        self.assertFalse(
            any("DOMAIN-SCHOOL-001" == x for x in envelope["applicable_rules"])
        )
        blocked = self.context(required=True)
        self.assertEqual(blocked.returncode, 2, blocked.stdout + blocked.stderr)
        self.assertIn("RULE-SCHOOL-001", blocked.stderr)
        host = self.pact("doctor", "--host-wiring-only", "--json")
        self.assertEqual(host.returncode, 0, host.stdout + host.stderr)
        self.assertIs(json.loads(host.stdout)["host_ci_executed"], False)

    def test_confirmed_rule_requires_deliberate_fixture_change(self):
        rule = self.root / "docs" / "product" / "rules" / "intake.md"
        rule.write_text(self.rule("confirmed"), encoding="utf-8")
        envelope_result = self.context(required=True)
        self.assertEqual(
            envelope_result.returncode, 0,
            envelope_result.stdout + envelope_result.stderr,
        )
        envelope = json.loads(envelope_result.stdout)
        self.assertIn("RULE-SCHOOL-001", envelope["applicable_rules"])
        self.assertEqual(envelope["status"], "candidate")
        self.assertIn("src/admission/README.md", "\n".join(envelope["known_unknowns"]))


if __name__ == "__main__":
    unittest.main()
