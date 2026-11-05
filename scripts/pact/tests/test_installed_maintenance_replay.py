"""Independent synthetic install/upgrade replay; no real Owner approval is implied."""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = pathlib.Path(__file__).resolve().parents[3]


@unittest.skipUnless(shutil.which("git"), "the installed replay requires Git")
class InstalledMaintenanceReplayTests(unittest.TestCase):
    def test_registered_chinese_retrieval_authority_and_upgrade_preservation(self):
        """Replay actual installed commands against an isolated synthetic project."""
        with tempfile.TemporaryDirectory(prefix="pact-independent-maintenance-") as tmp:
            root = pathlib.Path(tmp).resolve()

            def write(relative: str, text: str) -> None:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")

            def digest(relative: str) -> str:
                return hashlib.sha256((root / relative).read_bytes()).hexdigest()

            def run(*command: str) -> subprocess.CompletedProcess:
                process = subprocess.run(
                    command, cwd=root, capture_output=True, text=True, timeout=60,
                )
                self.assertEqual(
                    process.returncode, 0,
                    f"{command!r}\n{process.stdout}\n{process.stderr}",
                )
                return process

            def pact(*arguments: str) -> dict:
                return json.loads(run(sys.executable, str(root / "pact.py"), *arguments).stdout)

            write(
                "AGENTS.md",
                "# Synthetic project instructions\n\n"
                "Preserve this fixture-specific project guide.\n",
            )
            write(
                "README.md",
                "# Synthetic maintenance replay\n\n"
                "No real project or actual Owner approval is represented.\n",
            )
            agents_sha = digest("AGENTS.md")
            run(
                sys.executable, str(SOURCE / "scripts/pact/init.py"),
                "--target", str(root), "--apply", "--json",
            )
            self.assertEqual(digest("AGENTS.md"), agents_sha)
            write(
                ".pact/config.toml",
                (SOURCE / ".pact/config.example.toml").read_text(encoding="utf-8")
                .replace('language = "auto"', 'language = "zh-CN"'),
            )
            write(
                "docs/product/owner-specification.md",
                "# Synthetic fixture Owner specification\n\n"
                "This artificial test authority was created by the review harness; "
                "it represents no real user approval. For this fixture only, "
                "preserve original receipt bytes for the specified retention "
                "duration after delivery archival. Extended retention remains "
                "a candidate proposal.\n",
            )
            write(
                "docs/product/domains/delivery.md",
                '+++\n[pact]\ntype = "domain"\n'
                'id = "DOMAIN-SYNTHETIC-DELIVERY"\nstatus = "confirmed"\n'
                'aliases = ["交付留存"]\n'
                'related = ["RULE-SYNTHETIC-DELIVERY-001", '
                '"RULE-SYNTHETIC-DELIVERY-002"]\n+++\n'
                "# Synthetic delivery records\n\n"
                "Synthetic fixture navigation only. Authority: "
                "docs/product/owner-specification.md.\n",
            )
            for number, status, statement in (
                ("001", "confirmed", "Preserve original receipt bytes for the fixture retention duration."),
                ("002", "candidate", "Potential extended retention remains a proposal only."),
            ):
                write(
                    f"docs/product/rules/retention-{number}.md",
                    '+++\n[pact]\ntype = "rule"\n'
                    f'id = "RULE-SYNTHETIC-DELIVERY-{number}"\n'
                    f'status = "{status}"\n'
                    'domains = ["DOMAIN-SYNTHETIC-DELIVERY"]\n'
                    'aliases = ["交付留存"]\n+++\n'
                    f"# Synthetic fixture receipt rule {number}\n\n"
                    f"## Rule\n\n{statement}\n\n"
                    "## Authority\n\nSynthetic fixture Owner specification: "
                    "docs/product/owner-specification.md. Created only for this "
                    "isolated replay; no actual user approval is claimed.\n",
                )
            candidate_sha = digest("docs/product/rules/retention-002.md")
            config_sha = digest(".pact/config.toml")
            for arguments in (
                ("init", "-q"),
                ("config", "user.name", "Synthetic review fixture"),
                ("config", "user.email", "synthetic@example.invalid"),
                ("add", "."),
                ("commit", "-qm", "Synthetic fixture baseline"),
            ):
                run("git", *arguments)

            query = (
                "请帮我检查一下交付留存完成以后原来的回执应该怎样保留，"
                "尤其是在后续编辑再保存时需要遵守哪些已经登记的规则，"
                "并指出尚未确认的提议"
            )
            inspected = pact("inspect", query, "--no-code", "--json")
            self.assertEqual(inspected["queries"], [query])
            truth = inspected["explanation"]["product_truth"]
            self.assertEqual(
                {item["id"] for item in truth},
                {"DOMAIN-SYNTHETIC-DELIVERY", "RULE-SYNTHETIC-DELIVERY-001"},
            )
            candidate = next(
                item for item in inspected["explanation"]["other"]
                if item["id"] == "RULE-SYNTHETIC-DELIVERY-002"
            )
            self.assertEqual(candidate["status"], "candidate")
            domain_hit = next(
                item for item in inspected["discovery"]["results"]
                if item["id"] == "DOMAIN-SYNTHETIC-DELIVERY"
            )
            self.assertIn("embedded exact alias", domain_hit["reasons"])

            pact(
                "task", "prepare", query, "--task-id", "TASK-SYNTHETIC-AC16",
                "--success", "Recover synthetic authority and preserve candidate status",
                "--risk", "low", "--no-code", "--json",
            )
            context = json.loads(
                (root / ".pact/tasks/TASK-SYNTHETIC-AC16/context.json")
                .read_text(encoding="utf-8")
            )
            self.assertEqual(context["discovery_queries"], [query])
            self.assertEqual(
                context["applicable_rules"], ["RULE-SYNTHETIC-DELIVERY-001"],
            )
            self.assertIn(
                "RULE-SYNTHETIC-DELIVERY-002",
                {item["id"] for item in context["artifacts"]},
            )
            self.assertEqual(digest("docs/product/rules/retention-002.md"), candidate_sha)

            run(
                sys.executable, str(SOURCE / "pact.py"), "upgrade",
                "--target", str(root), "--source", str(SOURCE), "--apply", "--json",
            )
            self.assertEqual(digest("AGENTS.md"), agents_sha)
            self.assertEqual(digest(".pact/config.toml"), config_sha)
            self.assertEqual(digest("docs/product/rules/retention-002.md"), candidate_sha)

            doctor = pact("doctor", "--json")
            self.assertEqual(doctor["overall"], "pass")
            identity = doctor["runtime"]
            self.assertEqual(identity["integrity"], "matched")
            self.assertEqual(identity["sha256"], digest(".pact/pact.pyz"))
            self.assertEqual(
                identity["version"],
                (root / ".pact/VERSION").read_text(encoding="utf-8").strip(),
            )
            self.assertEqual(identity["errors"], [])
            self.assertTrue(
                {"chinese-registered-phrase", "task-generation-history", "coverage-review-draft"}
                .issubset(identity["capabilities"])
            )


if __name__ == "__main__":
    unittest.main()
