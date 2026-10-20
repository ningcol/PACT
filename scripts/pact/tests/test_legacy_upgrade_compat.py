"""PACT 0.1/0.2/0.3 to current upgrade: no silent Owner/Decision loss.

Fixtures use real historical YAML layout and actual current install-manifest
ownership. The separate Actions job tests installs at the pinned old Git SHAs.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))
import legacy_upgrade


OLD_OWNER = """version: 1
owner:
  role: product_project_owner
  language: zh-CN
  technical_depth: balanced
  communication:
    prefer:
      - business_behavior
      - verification
    hide_by_default:
      - internal_class_design
    explain_consequence_before_technical_term: true
    progressive_disclosure: true
    decision_translation: consequence_first
paths:
  product_truth: docs/product
  architecture: docs/architecture
  decisions: .agents/decisions
  changes: docs/changes
  drift: docs/drift
  skills: .agents/skills
risk:
  levels:
    - low
    - medium
    - high
discovery:
  use_canonical_vocabulary: true
  derived_cache: .pact/cache
convergence:
  code_wins_product_truth: false
  deterministic_fact_mismatch: fail
  heuristic_drift: warn
"""
OLD_BASELINE = """version: 1
reviews:
  vocabulary: reviewed
  product_truth: pending
  architecture: reviewed
  truth_ownership: pending
  owner_profile: reviewed
  verification: pending
  known_drift: not_applicable
notes:
  vocabulary: "Owner verified the original wording"
"""
OLD_FITNESS = """version: 1
checks: []
"""
OLD_DECISION = """---
pact:
  type: decision
  id: DEC-APPROVAL-001
  status: implemented
  domains: []
  aliases:
    - approval gating
---
# Binding authorization decision

## Decision
Always require human approval before a new authorization policy.
Never automatically change this decision because a test passes.
"""


class LegacyUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pact-legacy-upgrade-")
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.project = self.root / "project"
        init = subprocess.run(
            [sys.executable, str(ROOT / "scripts/pact/init.py"),
             "--target", str(self.project), "--apply"],
            capture_output=True, text=True, timeout=100,
        )
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)

    def run_upgrade(self, *args, env=None):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/pact/upgrade.py"),
             "--source", str(ROOT), "--target", str(self.project), "--json", *args],
            capture_output=True, text=True, timeout=110, env=env,
        )

    def old(self, *, notes=True):
        manifest_path = self.project / ".pact/install.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["runtime_version"] = "0.2.0"
        version = self.project / ".pact/VERSION"
        version.write_text("0.2.0\n")
        manifest["files"][".pact/VERSION"]["installed_sha256"] = hashlib.sha256(
            version.read_bytes()
        ).hexdigest()
        for kind, data in (
            ("config", OLD_OWNER), ("baseline", OLD_BASELINE), ("fitness", OLD_FITNESS),
        ):
            toml = f".pact/{kind}.toml"
            manifest["files"].pop(toml, None)
            (self.project / toml).unlink()
            rel = f".pact/{kind}.yaml"
            file = self.project / rel
            file.write_text(data, encoding="utf-8")
            h = hashlib.sha256(file.read_bytes()).hexdigest()
            manifest["files"][rel] = {
                "management": "seed", "source_path": f".pact/{kind}.example.yaml",
                "source_sha256": h, "installed_sha256": h,
            }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        if notes:
            target = self.project / ".agents/decisions/implemented/approval.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(OLD_DECISION, encoding="utf-8")
        return manifest

    def test_normal_upgrade_blocks_legacy_yaml_without_modifying_any_source(self):
        self.old()
        before = {
            p.relative_to(self.project).as_posix(): p.read_bytes()
            for p in self.project.rglob("*") if p.is_file()
        }
        plan = self.run_upgrade()
        self.assertEqual(plan.returncode, 0, plan.stderr)
        data = json.loads(plan.stdout)
        self.assertGreaterEqual(len(data["conflicts"]), 4)
        self.assertIn("migrate-legacy", json.dumps(data["conflicts"]))
        refused = self.run_upgrade("--apply")
        self.assertEqual(refused.returncode, 1, refused.stdout + refused.stderr)
        for path, original in before.items():
            self.assertEqual((self.project / path).read_bytes(), original, path)
        self.assertFalse((self.project / ".pact/config.toml").exists())

    def test_explicit_conversion_preserves_owner_reviews_and_decision_body(self):
        self.old()
        original = (self.project / ".agents/decisions/implemented/approval.md").read_text()
        dry = self.run_upgrade("--migrate-legacy")
        self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
        actions = [x["action"] for x in json.loads(dry.stdout)["operations"]]
        self.assertEqual(actions.count("migrate-legacy-seed"), 3)
        self.assertIn("migrate-legacy-metadata", actions)
        self.assertFalse((self.project / ".pact/config.toml").exists())

        applied = self.run_upgrade("--migrate-legacy", "--apply")
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        data = json.loads(applied.stdout)
        self.assertTrue(data["applied"])
        self.assertFalse(data["rolled_back"])

        from formats import parse_markdown_metadata, load_toml
        owner = load_toml(self.project / ".pact/config.toml")
        self.assertEqual(owner["owner"]["language"], "zh-CN")
        self.assertEqual(owner["owner"]["technical_depth"], "balanced")
        self.assertEqual(owner["owner"]["communication"]["prefer"], [
            "business_behavior", "verification",
        ])
        baseline = load_toml(self.project / ".pact/baseline.toml")
        self.assertEqual(baseline["reviews"]["vocabulary"], "reviewed")
        self.assertEqual(baseline["reviews"]["agent_bootstrap"], "pending")
        self.assertEqual(baseline["notes"]["vocabulary"],
                         "Owner verified the original wording")
        self.assertEqual(load_toml(self.project / ".pact/fitness.toml")["checks"], [])
        decision = (self.project / ".agents/decisions/implemented/approval.md").read_text()
        self.assertTrue(decision.startswith("+++\n"))
        parsed, body, fmt = parse_markdown_metadata(decision)
        self.assertEqual(fmt, "toml")
        self.assertEqual(parsed["pact"]["id"], "DEC-APPROVAL-001")
        self.assertEqual(parsed["pact"]["status"], "implemented")
        self.assertEqual(body, original.split("---\n", 2)[-1])
        manifest = json.loads((self.project / ".pact/install.json").read_text())
        self.assertEqual(manifest["runtime_version"], (ROOT / ".pact/VERSION").read_text().strip())
        self.assertEqual(manifest["files"][".pact/config.toml"]["management"], "seed")
        self.assertNotIn(".agents/decisions/implemented/approval.md", manifest["files"])
        for kind in ("config", "baseline", "fitness"):
            self.assertTrue((self.project / f".pact/{kind}.yaml").is_file())
        for command in (["owner", "--strict"], ["readiness", "--json"]):
            v = subprocess.run(
                [sys.executable, str(self.project / "pact.py"), *command],
                cwd=self.project, capture_output=True, text=True, timeout=100,
            )
            self.assertEqual(v.returncode, 0, v.stdout + v.stderr)

    def test_repeat_upgrade_does_not_overwrite_owner_toml(self):
        self.old()
        r = self.run_upgrade("--migrate-legacy", "--apply")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        path = self.project / ".pact/config.toml"
        path.write_text(path.read_text() + "\n# Owner-added after migration\n")
        plan = self.run_upgrade("--migrate-legacy")
        self.assertEqual(plan.returncode, 0)
        data = json.loads(plan.stdout)
        self.assertFalse(data["conflicts"])
        self.assertTrue(any(x["kind"] == "archived-YAML-seed" for x in data["notices"]))
        r = self.run_upgrade("--migrate-legacy", "--apply")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Owner-added", path.read_text())

    def test_custom_retired_config_fails_closed(self):
        self.old()
        path = self.project / ".pact/config.yaml"
        path.write_text(OLD_OWNER.replace(
            "product_truth: docs/product", "product_truth: my-custom-business-rules"
        ))
        before = (self.project / ".pact/install.json").read_bytes()
        result = self.run_upgrade("--migrate-legacy", "--apply")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("custom legacy paths", result.stdout)
        self.assertEqual((self.project / ".pact/install.json").read_bytes(), before)
        self.assertFalse((self.project / ".pact/config.toml").exists())

    def test_modified_historical_framework_document_blocks_silent_detach(self):
        manifest = self.old()
        rel = "docs/product/rules/old-framework-example.md"
        file = self.project / rel
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("# Original framework-provided example\n")
        source_hash = hashlib.sha256(file.read_bytes()).hexdigest()
        manifest["files"][rel] = {
            "management": "framework", "source_path": rel,
            "source_sha256": source_hash, "installed_sha256": source_hash,
        }
        (self.project / ".pact/install.json").write_text(
            json.dumps(manifest, indent=2) + "\n"
        )
        file.write_text(
            "---\npact:\n  type: rule\n  id: RULE-OWNER-SAFETY\n"
            "  status: confirmed\n---\n# User modified this rule\n"
        )
        before = file.read_bytes()
        result = self.run_upgrade("--migrate-legacy", "--apply")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("framework-owned knowledge was locally modified", result.stdout)
        self.assertEqual(file.read_bytes(), before)

    def test_historical_agent_guide_remains_project_owned_with_warning(self):
        self.old()
        guide = self.project / "AGENTS.md"
        existing = guide.read_bytes()
        plan = self.run_upgrade("--migrate-legacy")
        self.assertEqual(plan.returncode, 0)
        notes = json.loads(plan.stdout)["notices"]
        self.assertTrue(any(n["kind"] == "legacy-agent-guide" for n in notes))
        applied = self.run_upgrade("--migrate-legacy", "--apply")
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertEqual(guide.read_bytes(), existing)

    def test_no_machine_decision_id_requires_manual_owner_review(self):
        self.old()
        p = self.project / ".agents/decisions/implemented/approval.md"
        p.write_text("# Decision\nStatus: implemented\n\nDo not guess this ID.\n")
        result = self.run_upgrade("--migrate-legacy", "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("lacks machine-readable YAML metadata", result.stdout)
        self.assertEqual(p.read_text(), "# Decision\nStatus: implemented\n\nDo not guess this ID.\n")

    def test_duplicate_metadata_keys_and_symlinks_are_not_migrated(self):
        self.old()
        path = self.project / ".pact/baseline.yaml"
        path.write_text(OLD_BASELINE + "reviews:\n  verification: reviewed\n")
        output = self.run_upgrade("--migrate-legacy")
        self.assertEqual(output.returncode, 0)
        self.assertTrue(json.loads(output.stdout)["conflicts"])

    def test_rollback_restores_all_old_project_sources_and_manifest(self):
        self.old()
        manifest_path = self.project / ".pact/install.json"
        manifest_original = manifest_path.read_bytes()
        note = self.project / ".agents/decisions/implemented/approval.md"
        original_note = note.read_bytes()
        env = os.environ.copy()
        env["PACT_TEST_FAIL_AFTER_REPLACE"] = "4"
        result = self.run_upgrade("--migrate-legacy", "--apply", env=env)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        info = json.loads(result.stdout)
        self.assertTrue(info["rolled_back"], info)
        self.assertEqual(manifest_path.read_bytes(), manifest_original)
        self.assertEqual(note.read_bytes(), original_note)
        for kind in ("config", "baseline", "fitness"):
            self.assertFalse((self.project / f".pact/{kind}.toml").exists())
            self.assertTrue((self.project / f".pact/{kind}.yaml").is_file())

    def test_incomplete_old_tasks_cannot_be_silently_completed(self):
        self.old()
        path = self.project / ".pact/tasks/TASK-OLD/task.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"task_id": "TASK-OLD", "status": "prepared"}))
        r = self.run_upgrade("--migrate-legacy", "--apply")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("incomplete historical task", r.stdout)
        self.assertTrue(path.is_file())

    def test_current_installed_task_is_not_misclassified_as_legacy(self):
        path = self.project / ".pact/tasks/TASK-MODERN/task.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"status": "prepared"}))
        result = self.run_upgrade()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["conflicts"])

    def test_untracked_pre_manifest_install_refuses_to_guess_ownership(self):
        (self.project / ".pact/install.json").unlink()
        result = self.run_upgrade("--migrate-legacy", "--apply")
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing .pact/install.json", result.stderr)

    def test_source_bound_converter_rejects_ambiguous_and_wrong_metadata(self):
        with self.assertRaisesRegex(ValueError, "duplicate YAML"):
            legacy_upgrade.parse_yaml("pact:\n  id: DEC-X\n  id: DEC-Y\n")
        with self.assertRaisesRegex(ValueError, "Decision needs original stable ID"):
            legacy_upgrade.document_bytes(b"---\npact:\n  type: decision\n  status: implemented\n---\n# X\n")
        with self.assertRaisesRegex(ValueError, "historical seed must have version"):
            legacy_upgrade.seed_bytes(ROOT, "fitness", b"checks: []\n")


if __name__ == "__main__":
    unittest.main()
