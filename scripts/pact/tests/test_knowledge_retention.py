"""No-model regression tests for the task-close knowledge retention review."""

from __future__ import annotations

import hashlib
import json
import pathlib
import tempfile
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))

from knowledge_retention import review
from convergence_coverage import review as review_context_coverage
from schema_validate import load_schema, validate_instance
from converge import outcome as converge_outcome
from report import convergence_outcome as report_outcome


def retention(disposition="none", updated=None, created=None, removed=None):
    entry = {
        "disposition": disposition,
        "rationale": "Reviewed task intent and durable knowledge sources.",
        "updated": [] if updated is None else updated,
        "created": [] if created is None else created,
    }
    if removed is not None:
        entry["removed"] = removed
    return entry


class KnowledgeRetentionTests(unittest.TestCase):
    def test_legacy_is_readable_and_opt_in_requires_review(self):
        self.assertEqual(review({})[0], [])
        self.assertEqual(review({})[1]["status"], "unreviewed")
        self.assertTrue(review({}, require=True)[0])

    def test_no_new_knowledge_for_code_only_change(self):
        errors, result = review(
            {"knowledge_retention": retention()},
            changed_files=["src/order.py", "tests/test_order.py"],
            require=True,
        )
        self.assertEqual(errors, [])
        self.assertEqual(result["disposition"], "none")
        self.assertTrue(result["changed_paths_checked"])
        self.assertFalse(result["semantic_verification"])

    def test_update_create_and_both_require_matching_paths(self):
        old = "docs/product/rules/order.md"
        new = ".agents/decisions/implemented/stock.md"
        for disp, updated, created in [
            ("update", [old], []),
            ("create", [], [new]),
            ("update-and-create", [old], [new]),
        ]:
            with self.subTest(disp=disp):
                problems, summary = review(
                    {"knowledge_retention": retention(disp, updated, created)},
                    changed_files=updated + created,
                    require=True,
                )
                self.assertEqual(problems, [])
                self.assertEqual(summary["status"], "reviewed")

    def test_legacy_review_without_removed_field_still_passes(self):
        data = {"knowledge_retention": retention("none")}
        errors, report = review(data, changed_files=[], require=True)
        self.assertEqual(errors, [])
        self.assertEqual(report["removed"], [])

    def test_source_verified_removal_is_existing_knowledge_maintenance(self):
        path = "docs/product/rules/retired.md"
        data = {
            "knowledge_retention": retention("update", removed=[path]),
            "coverage": [{
                "path": path, "disposition": "removed",
                "rationale": "Verified source-backed retirement",
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            errors, outcome = review(
                data, changed_files=[path], root=root, require=True,
                verified_removed_paths=[path],
            )
            self.assertEqual(errors, [])
            self.assertEqual(outcome["removed"], [path])
            self.assertTrue(outcome["removed_source_verified"])

    def test_source_verified_rename_covers_both_old_and_new_paths(self):
        old = "docs/product/rules/old.md"
        new = "docs/product/rules/new.md"
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / new).parent.mkdir(parents=True)
            (root / new).write_text("# Revised canonical rule\n", "utf-8")
            data = {
                "knowledge_retention": retention(
                    "update-and-create", created=[new], removed=[old]),
                "coverage": [{
                    "path": old, "disposition": "removed",
                    "rationale": "Source-verified path retirement",
                }],
            }
            errors, outcome = review(
                data, changed_files=[old, new], root=root,
                verified_removed_paths=[old], require=True,
            )
            self.assertEqual(errors, [])
            self.assertEqual(outcome["created"], [new])
            self.assertEqual(outcome["removed"], [old])

    def test_removed_proof_comes_from_prepared_task_context(self):
        """The remover cannot invent a Convergence receipt for an unknown Rule."""
        path = "docs/product/rules/old.md"
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            source = root / path
            source.parent.mkdir(parents=True)
            source.write_text("# Original confirmed Rule\\n", "utf-8")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            context = {
                "artifacts": [{
                    "path": path, "sha256": digest,
                    "id": "RULE-OLD", "artifact_type": "rule",
                }],
            }
            context_path = root / "context.json"
            context_path.write_text(json.dumps(context), "utf-8")
            context_digest = hashlib.sha256(context_path.read_bytes()).hexdigest()
            convergence = {
                "context_sha256": context_digest,
                "coverage": [{
                    "path": path, "disposition": "removed",
                    "rationale": "Explicit reviewed retirement",
                }],
                "findings": [],
                "knowledge_retention": retention("update", removed=[path]),
            }
            source.unlink()
            coverage_errors, stats = review_context_coverage(
                context, convergence, root=root, context_path=context_path,
                expected_context_sha256=context_digest,
            )
            self.assertEqual(coverage_errors, [])
            self.assertEqual(stats["removed_verified"], [path])
            errors, report = review(
                convergence, root=root, changed_files=[path],
                require=True, verified_removed_paths=stats["removed_verified"],
            )
            self.assertEqual(errors, [])
            self.assertEqual(report["removed"], [path])

            # The same Convergence cannot bless a path whose exact original
            # bytes were never part of the prepared Context.
            forged = "docs/product/rules/never-prepared.md"
            convergence["coverage"].append({
                "path": forged, "disposition": "removed",
                "rationale": "Not in prepared Context",
            })
            convergence["knowledge_retention"] = retention(
                "update", removed=[path, forged],
            )
            coverage_errors, stats = review_context_coverage(
                context, convergence, root=root, context_path=context_path,
                expected_context_sha256=context_digest,
            )
            self.assertTrue(coverage_errors)
            errors, _ = review(
                convergence, root=root, changed_files=[path, forged],
                require=True, verified_removed_paths=stats["removed_verified"],
            )
            self.assertIn("not source-verified", " ".join(errors))

    def test_removal_without_original_convergence_proof_is_rejected(self):
        path = ".agents/decisions/implemented/retired.md"
        base = retention("update", removed=[path])
        for covered, verified in [
            ([], [path]),  # no explicit Convergence coverage
            ([{"path": path, "disposition": "aligned"}], [path]),
            ([{"path": path, "disposition": "removed"}], None),  # no Context
            ([{"path": path, "disposition": "removed"}], []),  # unverified
        ]:
            with self.subTest(covered=covered, verified=verified):
                data = {"knowledge_retention": base, "coverage": covered}
                errors, _ = review(
                    data, changed_files=[path], require=True,
                    verified_removed_paths=verified,
                )
                self.assertTrue(errors)
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            f = root / path
            f.parent.mkdir(parents=True)
            f.write_text("# Still exists\n", "utf-8")
            data = {
                "knowledge_retention": base,
                "coverage": [{"path": path, "disposition": "removed"}],
            }
            errors, _ = review(
                data, changed_files=[path], root=root, require=True,
                verified_removed_paths=[path],
            )
            self.assertIn("missing or unsafe", " ".join(errors))

    def test_removed_paths_cannot_be_duplicated_or_disguised_as_none(self):
        path = "docs/product/rules/old.md"
        for entry in [
            retention("none", removed=[path]),
            retention("create", created=["docs/product/rules/new.md"], removed=[path]),
            retention("update", updated=[path], removed=[path]),
            retention("update", removed=[path, path]),
            retention("update", removed=["../escape.md"]),
        ]:
            with self.subTest(entry=entry):
                self.assertTrue(review({"knowledge_retention": entry})[0])

    def test_pending_always_blocks_completion(self):
        data = {"knowledge_retention": retention("pending")}
        self.assertTrue(review(data)[0])
        report = {"findings": [], "coverage": [], **data}
        self.assertEqual(converge_outcome(report), "needs-reconciliation")
        self.assertEqual(report_outcome(report), "needs-reconciliation")

    def test_reject_empty_or_inconsistent_dispositions(self):
        for item in [
            retention("create"),
            retention("none", updated=["docs/product/rules/order.md"]),
            retention("update-and-create", updated=["docs/product/rules/order.md"]),
            retention("update", updated=["docs/product/rules/order.md"], created=["x.md"]),
            retention("create", created=["x.md", "x.md"]),
            retention("update", updated=["../escape.md"]),
            retention("update", updated=["docs\\rule.md"]),
            retention("update", updated=["/etc/passwd"]),
            retention("create", created=["src/main.py"]),
            retention("create", created=["docs/product/rules/line\nfeed.md"]),
            retention("create", created=["docs/product/rules/nul\x00byte.md"]),
        ]:
            with self.subTest(item=item):
                self.assertTrue(review({"knowledge_retention": item})[0])

    def test_existing_project_requirements_document_is_allowed(self):
        errors, _ = review(
            {"knowledge_retention": retention(
                "create", created=["docs/requirements/checkout.md"])},
            changed_files=["docs/requirements/checkout.md"], require=True,
        )
        self.assertEqual(errors, [])

    def test_existing_business_document_outside_docs_is_allowed(self):
        for path in ("README.md", "requirements/checkout.md", "product/terms.md"):
            with self.subTest(path=path):
                errors, _ = review(
                    {"knowledge_retention": retention("update", updated=[path])},
                    changed_files=[path], require=True,
                )
                self.assertEqual(errors, [])

    def test_declared_paths_must_be_changed(self):
        doc = "docs/product/rules/order.md"
        errors, _ = review(
            {"knowledge_retention": retention("update", updated=[doc])},
            changed_files=["src/order.py"],
        )
        self.assertIn("not changed by task", " ".join(errors))

    def test_no_changes_claim_conflicts_with_changed_durable_source(self):
        errors, _ = review(
            {"knowledge_retention": retention()},
            changed_files=["docs/product/rules/order.md"],
        )
        self.assertIn("'none' conflicts", " ".join(errors))

    def test_omitted_second_canonical_rule_is_rejected(self):
        first = "docs/product/rules/first.md"
        second = "docs/product/rules/second.md"
        problems, _ = review(
            {"knowledge_retention": retention("update", updated=[first])},
            changed_files=[first, second],
            require=True,
        )
        self.assertIn(second, " ".join(problems))
        self.assertIn("not included in review", " ".join(problems))

    def test_none_does_not_mistake_ordinary_readme_for_normative_truth(self):
        problems, _ = review(
            {"knowledge_retention": retention("none")},
            changed_files=["README.md", "docs/changes/completed/task.md"],
            require=True,
        )
        self.assertEqual(problems, [])

    def test_business_document_attachments_are_not_normative_rules(self):
        problems, stats = review(
            {"knowledge_retention": retention("none")},
            changed_files=[
                "docs/product/assets/order-flow.png",
                "docs/product/prds/specification.pdf",
                "docs/architecture/diagram.svg",
                "src/order.py",
            ],
            require=True,
        )
        self.assertEqual(problems, [])
        self.assertEqual(stats["status"], "reviewed")

    def test_all_changed_markdown_rules_still_require_coverage(self):
        problems, _ = review(
            {"knowledge_retention": retention("none")},
            changed_files=[
                "docs/product/assets/screenshot.png",
                "docs/product/rules/order.md",
            ],
            require=True,
        )
        self.assertIn("docs/product/rules/order.md", " ".join(problems))

    def test_canonical_governance_change_requires_review(self):
        problems, _ = review(
            {"knowledge_retention": retention("none")},
            changed_files=["docs/governance/authority.md"],
        )
        self.assertIn("'none' conflicts", " ".join(problems))

    def test_created_document_must_exist_in_repo_if_root_is_known(self):
        path = "docs/product/domains/order.md"
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            entry = {"knowledge_retention": retention("create", created=[path])}
            bad, _ = review(entry, changed_files=[path], root=root, require=True)
            self.assertIn("knowledge file missing", " ".join(bad))
            target = root / path
            target.parent.mkdir(parents=True)
            target.write_text("# Orders\n", encoding="utf-8")
            good, stats = review(entry, changed_files=[path], root=root, require=True)
            self.assertEqual(good, [])
            self.assertTrue(stats["created_paths_checked"])
            self.assertFalse(stats["kind_of_change_verified"])

    def test_deleted_file_cannot_masquerade_as_updated_knowledge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            path = "docs/product/rules/order.md"
            declared = {"knowledge_retention": retention("update", updated=[path])}
            problems, _ = review(
                declared, changed_files=[path], root=root, require=True,
            )
            self.assertIn("declared knowledge file missing", " ".join(problems))
            source = root / path
            source.parent.mkdir(parents=True)
            source.write_text("# Reviewed order rule\n", encoding="utf-8")
            problems, _ = review(
                declared, changed_files=[path], root=root, require=True,
            )
            self.assertEqual(problems, [])

    def test_symlink_created_knowledge_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            p = root / "docs/product/rules/rule.md"
            p.parent.mkdir(parents=True)
            (root / "real.md").write_text("# data\n", encoding="utf-8")
            try:
                p.symlink_to(root / "real.md")
            except OSError:
                self.skipTest("symlink not supported")
            errors, _ = review(
                {"knowledge_retention": retention("create", created=[
                    "docs/product/rules/rule.md"])},
                changed_files=["docs/product/rules/rule.md"],
                root=root,
            )
            self.assertIn("missing or unsafe", " ".join(errors))

    def test_parent_symlink_alias_is_not_valid_retained_knowledge(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            real = root / "actual"
            real.mkdir()
            (real / "order.md").write_text("# Orders\n", encoding="utf-8")
            parent = root / "docs/product/rules"
            parent.parent.mkdir(parents=True)
            try:
                parent.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlink not supported")
            path = "docs/product/rules/order.md"
            errors, _ = review(
                {"knowledge_retention": retention("create", created=[path])},
                changed_files=[path], root=root, require=True,
            )
            self.assertIn("missing or unsafe", " ".join(errors))

    def test_schema_accepts_retention_but_not_unknown_fields(self):
        schema = load_schema(ROOT / ".pact/schema/convergence-report.schema.json")
        example = json.loads(
            (ROOT / ".pact/examples/convergence-report.example.json").read_text("utf-8")
        )
        self.assertEqual(validate_instance(example, schema), [])
        example["knowledge_retention"]["removed"] = [
            "docs/product/rules/old.md",
        ]
        self.assertEqual(validate_instance(example, schema), [])
        example["knowledge_retention"]["unknown"] = 1
        self.assertTrue(validate_instance(example, schema))

    def test_existing_command_surfaces_expose_opt_in(self):
        for command in [
            [sys.executable, str(ROOT / "scripts/pact/complete.py"), "--help"],
            [sys.executable, str(ROOT / "scripts/pact/pact.py"), "task", "finish", "--help"],
        ]:
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--require-knowledge-retention", result.stdout)


if __name__ == "__main__":
    unittest.main()
