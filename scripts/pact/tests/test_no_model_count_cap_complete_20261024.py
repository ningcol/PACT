"""Characterization of known count-cap authority omission at the actual completion CLI.

These are synthetic, no-model PACT-only cases.  No actual Owner/Agent is
involved, and the failing target is intentionally left unfixed in this PR.
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


class OmittedAuthorityCompletionProbe(unittest.TestCase):
    @unittest.expectedFailure
    def test_complete_must_block_known_count_omission_even_when_evidence_passes(self):
        with tempfile.TemporaryDirectory(prefix="pact-count-cap-complete-") as tmp:
            root = pathlib.Path(tmp)

            def save(name, content):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                return path

            records = []
            for n in (1, 2):
                relative = f"docs/product/rules/rule-{n}.md"
                save(relative, f"# Rule {n}\n")
                records.append({
                    "path": relative,
                    "id": f"RULE-{n}",
                    "artifact_type": "rule",
                    "status": "confirmed",
                    "mixed_authority": False,
                    "score": 20-n,
                })
            with patch.object(pact_context, "ROOT", root):
                selected, _, budget = pact_context.select_context_candidates(
                    records, [], token_budget=0, knowledge_limit=1, code_limit=1,
                )
            self.assertEqual(budget["authority_candidates_dropped"], 1)
            self.assertEqual(len(selected), 1)

            source_rel = selected[0]["path"]
            source_sha = hashlib.sha256((root / source_rel).read_bytes()).hexdigest()
            ctx = {
                "risk_level": "low",
                "artifacts": [{"path": source_rel, "sha256": source_sha}],
                "context_budget": budget,
            }
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
            self.assertEqual(result.returncode, 1,
                             "known truncated authority should block completion: "
                             + result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
