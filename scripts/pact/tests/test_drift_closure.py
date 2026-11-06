from __future__ import annotations

import json
import importlib.util
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
CHECK = ROOT / "scripts/pact/check.py"
SCHEMA = ROOT / ".pact/schema/artifact.schema.json"


class DriftClosureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pact-drift-closure-")
        self.root = pathlib.Path(self.temp.name)
        (self.root / ".pact/schema").mkdir(parents=True)
        shutil.copy2(SCHEMA, self.root / ".pact/schema/artifact.schema.json")
        self.write("sources/decision.md", "# Owner decision\nRecorded choice with source revision.\n")
        self.write("sources/implementation.py", "# Current implementation\n")
        self.write("sources/evidence.txt", "Verified fixture behavior.\n")
        self.write("docs/product/specs/body.md", "# Current body\nOne business authority.\n")

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return path

    def body(self, status="resolved", ident="DRIFT-PILOT-001"):
        return f'''+++
[pact]
type = "drift"
id = "{ident}"
status = "{status}"
+++
# {ident} — Authority conflict

## Conflict sources
[Original decision](../../../sources/decision.md) at the preserved revision disagreed with current behavior.

## Scope
2026 end-user selection flow, including empty input; not the staff workflow.

## Decision basis
The Owner chose the behavior recorded in [decision](../../../sources/decision.md).

## Current authority
Follow the [canonical body](../../product/specs/body.md) for the selected scope.

## Implementation and verification
### Implementation
[Implementation](../../../sources/implementation.py) now follows the body.
### Verification
[Evidence](../../../sources/evidence.txt) records the bounded result.

## Remaining issues
{"None." if status == "resolved" else "Current implementation still allows empty input. Owner accepted that temporary deviation in the linked decision; revisit before release."}
'''

    def drift(self, status="resolved", ident="DRIFT-PILOT-001", body=None, filename="pilot.md"):
        return self.write(f"docs/drift/{status}/{filename}", body if body is not None else self.body(status, ident))

    def run_check(self, *paths, extra=()):
        args = [sys.executable, str(CHECK), "--root", str(self.root), "--json"]
        for path in paths:
            args.extend(["--drift-closure", str(path)])
        return subprocess.run([*args, *extra], capture_output=True, text=True)

    def result(self, *paths):
        proc = self.run_check(*paths)
        self.assertIn(proc.returncode, {0, 1}, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 1 if result["errors"] else 0)
        return result

    def test_resolved_checks_only_explicit_sources_and_reports_semantic_limits(self):
        path = self.drift()
        self.write("docs/drift/resolved/unrelated.md", "+++\nINVALID FRONTMATTER\n+++\n")
        # Links in a direct source do not trigger transitive traversal.
        self.write("sources/decision.md", "# Decision\n[transitive missing](missing.md)\n")
        result = self.result(path)
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertEqual(len(result["checked_paths"]), 6)
        self.assertNotIn("docs/drift/resolved/unrelated.md", result["checked_paths"])
        self.assertFalse(result["verification_boundaries"]["repository_inventory_scanned"])
        self.assertFalse(result["verification_boundaries"]["owner_confirmation_verified"])
        self.assertFalse(result["verification_boundaries"]["implementation_behavior_verified"])
        self.assertFalse(result["verification_boundaries"]["global_id_uniqueness_verified"])

    def test_status_only_does_not_establish_closure(self):
        path = self.drift(body='+++\n[pact]\ntype = "drift"\nid = "DRIFT-PILOT-001"\nstatus = "resolved"\n+++\n# Closed\n')
        result = self.result(path)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("Decision basis" in error for error in result["errors"]))
        self.assertTrue(any("Verification" in error for error in result["errors"]))

    def test_resolved_requires_implementation_and_verification_locators(self):
        for marker in ("[Implementation](../../../sources/implementation.py)", "[Evidence](../../../sources/evidence.txt)"):
            with self.subTest(marker=marker):
                path = self.drift(body=self.body().replace(marker, "Unlinked assertion"))
                result = self.result(path)
                self.assertEqual(result["status"], "fail")
                self.assertTrue(any("requires" in error for error in result["errors"]))

    def test_accepted_requires_chosen_authority_and_remaining_deviation(self):
        path = self.drift("accepted")
        self.assertEqual(self.result(path)["status"], "pass")
        unresolved = self.body("accepted").replace("Follow the [canonical body](../../product/specs/body.md) for the selected scope.", "Undecided. [Options](../../product/specs/body.md) are still under review.")
        path = self.drift("accepted", body=unresolved)
        self.assertTrue(any("authority selection" in error for error in self.result(path)["errors"]))
        none = self.body("accepted").split("## Remaining issues")[0] + "## Remaining issues\nNone.\n"
        path = self.drift("accepted", body=none)
        self.assertTrue(any("remaining deviation" in error for error in self.result(path)["errors"]))

    def test_template_placeholders_and_duplicate_sections_fail(self):
        path = self.drift(body=self.body().replace("2026 end-user", "<Describe scope> 2026 end-user") + "\n## Scope\nTBD\n")
        result = self.result(path)
        self.assertTrue(any("duplicate section" in error for error in result["errors"]))
        self.assertTrue(any("placeholders" in error for error in result["errors"]))

    def test_accepted_real_pending_work_is_not_an_empty_template(self):
        body = self.body("accepted").split("## Remaining issues")[0]
        path = self.drift("accepted", body=body + "## Remaining issues\n接口切换日期待确认，Owner已接受当前偏差，发布前复查。\n")
        self.assertEqual(self.result(path)["status"], "pass")
        for prompt in ("待确认", "待补充。"):
            with self.subTest(prompt=prompt):
                path = self.drift("accepted", body=body + "## Remaining issues\n" + prompt + "\n")
                self.assertTrue(any("placeholders" in e for e in self.result(path)["errors"]))

    def test_metadata_type_id_status_and_directory_are_validated(self):
        for source, target in (("type = \"drift\"", "type = \"rule\""), ("DRIFT-PILOT-001", "invalid"), ("status = \"resolved\"", "status = \"accepted\"")):
            with self.subTest(target=target):
                path = self.drift(body=self.body().replace(source, target))
                self.assertEqual(self.result(path)["status"], "fail")
        known = self.drift("known")
        self.assertTrue(any("known/open" in error for error in self.result(known)["errors"]))

    def test_missing_direct_target_and_root_escape_fail(self):
        for destination in ("../../../sources/missing.md", "../../../../outside.md"):
            with self.subTest(destination=destination):
                path = self.drift(body=self.body().replace("../../../sources/decision.md", destination))
                self.assertEqual(self.result(path)["status"], "fail")

    def test_malformed_status_is_reported_without_crashing(self):
        path = self.drift(body=self.body().replace('status = "resolved"', 'status = {invalid = true}'))
        result = self.result(path)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("invalid Drift status" in error for error in result["errors"]))

    def test_malformed_remote_locator_is_not_treated_as_locatable(self):
        path = self.drift(body=self.body().replace("../../../sources/decision.md", "https:///"))
        self.assertTrue(any("requires a host" in error for error in self.result(path)["errors"]))

    def test_unknown_scheme_does_not_satisfy_required_evidence(self):
        path = self.drift(body=self.body().replace("../../../sources/decision.md", "nonsense:fake"))
        result = self.result(path)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("Decision basis" in error for error in result["errors"]))

    def test_installed_compact_runtime_uses_embedded_schema(self):
        spec = importlib.util.spec_from_file_location("closure_runtime_bundle", ROOT / "scripts/pact/runtime_bundle.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        bundle = self.root / ".pact/pact.pyz"
        module.build_runtime_bundle(ROOT, bundle)
        shutil.rmtree(self.root / ".pact/schema")
        path = self.drift()
        proc = subprocess.run([
            sys.executable, str(bundle), "check", "--root", str(self.root),
            "--drift-closure", path, "--json",
        ], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["status"], "pass")
        self.assertNotIn(".pact/schema/artifact.schema.json", result["checked_paths"])

    def test_symlink_target_fails(self):
        try:
            (self.root / "sources/alias.md").symlink_to(self.root / "sources/decision.md")
        except (OSError, NotImplementedError):
            self.skipTest("filesystem cannot create symbolic links")
        path = self.drift(body=self.body().replace("../../../sources/decision.md", "../../../sources/alias.md"))
        self.assertTrue(any("symlink" in error for error in self.result(path)["errors"]))

    def test_unknown_anchor_remote_and_host_import_are_explicitly_unverified(self):
        body = self.body().replace("../../../sources/decision.md)", "../../../sources/decision.md#unknown)")
        body += "\n[External](https://example.invalid/decision)\n@host/import\n[[special-note]]\n"
        path = self.drift(body=body)
        result = self.result(path)
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertTrue(any("anchor/query" in row for row in result["unverified"]))
        self.assertTrue(any("not fetched" in row for row in result["unverified"]))
        self.assertTrue(any("import syntax" in row for row in result["unverified"]))
        self.assertIn("remote-unverified", {row["status"] for row in result["references"]})

    def test_reference_style_and_angle_destinations_with_spaces(self):
        self.write("sources/review (final).txt", "Review result\n")
        body = self.body().replace("[Evidence](../../../sources/evidence.txt)", "[Evidence][review]")
        body += '\n[review]: <../../../sources/review (final).txt> "Review title"\n'
        path = self.drift(body=body)
        result = self.result(path)
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertIn("sources/review (final).txt", result["checked_paths"])
        inline = self.body().replace("[Evidence](../../../sources/evidence.txt)", "[Evidence](<../../../sources/review (final).txt>)")
        self.assertEqual(self.result(self.drift(body=inline))["status"], "pass")

    def test_repeated_records_duplicate_ids_and_id_only_edges(self):
        first = self.drift()
        second = self.drift(filename="second.md")
        self.assertTrue(any("duplicate stable ID" in error for error in self.result(first, second)["errors"]))
        body = self.body().replace('status = "resolved"', 'status = "resolved"\nrelated = ["RULE-OTHER-001"]')
        path = self.drift(body=body)
        self.assertTrue(any("no direct linked locator" in error for error in self.result(path)["errors"]))
        self.write("docs/product/rules/other.md", '+++\n[pact]\ntype = "rule"\nid = "RULE-OTHER-001"\nstatus = "confirmed"\n+++\n# Other\n')
        body += "\n[Related rule](../../product/rules/other.md)\n"
        self.assertEqual(self.result(self.drift(body=body))["status"], "pass")

    def test_default_checks_remain_compatible_and_modes_are_exclusive(self):
        self.drift(body='+++\n[pact]\ntype = "drift"\nid = "DRIFT-OLD-001"\nstatus = "resolved"\n+++\n# Historical record\n')
        default = self.run_check()
        self.assertEqual(default.returncode, 0, default.stderr)
        proc = self.run_check("docs/drift/resolved/pilot.md", extra=("--artifact-only",))
        self.assertEqual(proc.returncode, 2)

    def test_examples_do_not_count_as_evidence(self):
        body = self.body().replace("[Evidence](../../../sources/evidence.txt)", "```md\n[Evidence](../../../sources/evidence.txt)\n```")
        result = self.result(self.drift(body=body))
        self.assertTrue(any("Verification" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
