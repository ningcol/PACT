# M1 frozen-input provenance amendment (no test input changes)

Date: 2026-10-17. Applies to frozen M1 task cards, oracle and original preregistration, whose original Git blob SHAs remain unchanged.

## Concrete instrument defect and preserved RED

The first PACT Core Matrix run for PR #219 on head \`990733f7e40fa86fef76d8f642bd5e3ffadebd86\` failed in M1 input validation **before any installed M1 predictions**. The developer had mistakenly recorded the Git blob SHA of \`scripts/benchmark/decision_memory_m0.py\` (\`14693c6b209b8ef734edbd9e3e9842efd5bca3cd\`) as the corpus blob SHA in the frozen task-card field and preregistration.

Authoritative, already-existing original M0 corpus: \`benchmarks/decision-memory/m0-inputs.json\`, Git blob SHA **\`753babf70317c6af1b292b1b031e0afaec503ec3\`** on both the baseline main and PR #219. These names were confused; the corpus contents were **not** modified.

Remediation is strictly provenance/instrument correctness:
- Preserve original \`m1-task-cards.json\`, \`m1-oracle.json\`, and M1 preregistration byte-for-byte with their pre-run Git history and all eight original tasks and expected IDs.
- Runner checks actual M0 corpus bytes against the corrected Git blob SHA.
- Runner separately checks that the frozen card still contains the original *mislabeled* blob field, rejecting unexpected changes.
- In every output print both the actual corpus blob and the mislabeled frozen card value; never silently edit the oracle, task wording, goals or denominator.
- Preserve the original CI failure as evidence of an **instrument defect**, not a PACT decision-memory retrieval failure. The first valid result can only be collected after this fix.

The original preregistration's statement naming \`14693c...\` the M0 corpus should be read with this correction; this amendment does not authorize tuning scores or reinterpretation of synthetic diagnostics as real Agent evidence. The full real-Agent/Owner and release gates remain HOLD.
