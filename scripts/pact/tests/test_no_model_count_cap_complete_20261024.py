"""Characterization of known count-cap authority omission at the actual completion CLI.

These are synthetic, no-model PACT-only cases.  No actual Owner/Agent is
involved. A known Context authority truncation must block task completion.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))
import context as pact_context
from discover import score_document
from map import parse_document
from schema_validate import load_schema, validate_instance


class OmittedAuthorityCompletionProbe(unittest.TestCase):
    def test_complete_blocks_known_count_omission_even_when_evidence_passes(self):
        with tempfile.TemporaryDirectory(prefix="pact-count-cap-complete-") as tmp:
            root = pathlib.Path(tmp)

            def save(name, content):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                return path

            # Parse real TOML-front-matter Markdown rather than inventing
            # metadata that Discover would never have found.
            task_query = "Review Rule 1 and Rule 2 applicability"
            records = []
            for n in (1, 2):
                relative = f"docs/product/rules/rule-{n}.md"
                source = save(
                    relative,
                    f'+++\n[pact]\ntype = "rule"\nid = "RULE-{n}"\n'
                    f'status = "confirmed"\n+++\n# Rule {n}\n'
                    f'This rule controls existing product policy {n}.\n',
                )
                doc = parse_document(source, root)
                score, reasons = score_document(doc, task_query)
                self.assertGreater(score, 0)
                doc.update({
                    "mixed_authority": False,
                    "score": score,
                    "reasons": reasons,
                })
                records.append(doc)
            with patch.object(pact_context, "ROOT", root):
                selected, _, budget = pact_context.select_context_candidates(
                    records, [], token_budget=0, knowledge_limit=1, code_limit=1,
                )
            self.assertEqual(budget["authority_candidates_dropped"], 1)
            self.assertEqual(len(selected), 1)

            source_rel = selected[0]["path"]
            source_sha = hashlib.sha256((root / source_rel).read_bytes()).hexdigest()
            # Reconstruct a schema-valid Context Envelope, not a permissive
            # hand-written fragment.  This mimics a prepared task source.
            selected_source = selected[0]
            ctx = {
                "version": 1, "status": "candidate",
                "task": "Check project policy without changing code",
                "goal": "Check project policy without changing code",
                "observable_success": "Check the project's existing policy",
                "risk_level": "low", "discovery_query": "project policy",
                "domains": [],
                "artifacts": [{
                    "path": source_rel, "sha256": source_sha,
                    "id": selected_source["id"],
                    "artifact_type": "rule", "title": "Rule 1",
                    "score": selected_source["score"],
                    "reasons": selected_source["reasons"],
                    "estimated_tokens": selected_source["estimated_tokens"],
                    "mixed_authority": False,
                }],
                "applicable_rules": [selected_source["id"]],
                "decisions": [],
                "verification_targets": [],
                "known_unknowns": [
                    "An otherwise eligible confirmed Rule candidate was "
                    "omitted by the hard knowledge-count cap."
                ],
                "risk_policy": {
                    "knowledge_limit": 1, "code_context": False,
                    "code_limit": 1, "completion": [],
                    "materialization_token_budget": 0,
                },
                "context_budget": budget,
            }
            errors = validate_instance(
                ctx, load_schema(ROOT / ".pact/schema/context-envelope.schema.json")
            )
            self.assertEqual(errors, [], errors)
            ctx_path = save("context.json", json.dumps(ctx))
            ctx_sha = hashlib.sha256(ctx_path.read_bytes()).hexdigest()

            contract = {
                "version": 1, "task_id": "TASK-CAP-REVIEW",
                "intent": "Check project policy without changing code",
                "acceptance_criteria": [
                    {"id": "AC-1", "kind": "outcome",
                     "text": "Check the project's existing policy"}
                ],
            }
            contract_path = save("contract.json", json.dumps(contract))
            contract_sha = hashlib.sha256(contract_path.read_bytes()).hexdigest()
            save("proof.txt", "Machine-readable sample proof fixture\n")
            claim_text = "The sample fixture exists."
            evidence = {
                "version": 1, "task_id": "TASK-CAP-REVIEW",
                "task": "Check project policy without changing code",
                "risk_level": "low",
                "task_contract_sha256": contract_sha,
                "claims": [{
                    "id": "EV-GREEN", "claim": claim_text,
                    "required": True, "status": "pass", "criteria": ["AC-1"],
                    "evidence": [
                        {"kind": "other", "provenance": "file", "ref": "proof.txt"}
                    ],
                }],
                "limitations": [],
            }
            converge = {
                "version": 1, "task_id": "TASK-CAP-REVIEW",
                "change": "Review existing rules", "owner_summary": "No changes made.",
                "context_sha256": ctx_sha, "evidence": ["EV-GREEN"],
                "coverage": [{
                    "path": source_rel, "disposition": "aligned",
                    "rationale": "Reviewed the selected source Rule",
                }],
                "change_coverage": [], "findings": [],
            }
            owner = {
                "version": 1, "task_id": "TASK-CAP-REVIEW",
                "status": "completed", "summary": "Reviewed",
                "before": "Existing policy", "after": "Policy unchanged",
                "verification": [
                    {"claim": claim_text, "evidence_ids": ["EV-GREEN"]}
                ],
                "acceptance": [{
                    "criterion_id": "AC-1",
                    "summary": "Check the project's existing policy",
                    "evidence_ids": ["EV-GREEN"],
                }],
                "consistency": {"status": "aligned", "summary": "No drift."},
                "owner_decisions": [],
            }
            bundle = root / "bundle"
            for key, data in {
                "evidence": evidence,
                "convergence": converge,
                "owner-report": owner,
            }.items():
                save(f"bundle/{key}.json", json.dumps(data))
            result = subprocess.run([
                sys.executable, str(ROOT / "scripts" / "pact" / "complete.py"),
                str(bundle), "--root", str(root),
                "--context", str(ctx_path),
                "--context-sha256", ctx_sha,
                "--contract", str(contract_path),
                "--expected-risk", "low",
                "--check-change-coverage", "--json",
            ], capture_output=True, text=True, cwd=root, timeout=90)
            # The omitted Rule is a candidate, not automatically applicable.
            # Since its source was never reviewed, mechanical completion must
            # fail closed and ask for a wider Context (no Owner GO invented).
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            parsed = json.loads(result.stdout)
            self.assertFalse(parsed["complete"], parsed)
            self.assertTrue(any("authority" in e.lower() and "limit" in e.lower()
                                for e in parsed["errors"]), parsed)
            self.assertEqual(parsed["convergence_coverage"]["required_artifacts"], 1)
            self.assertEqual(budget["authority_candidates_dropped"], 1)


if __name__ == "__main__":
    unittest.main()
