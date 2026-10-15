# S0 replayable negative fixtures and explicit historical blockers (2026-10-15)

> **PACT-only S0 engineering inventory.** The negative test inputs below are **controlled RED cases**, intentionally rejected by current PACT code. They are not claims that the named tests failed at the original historical snapshot. An actual historical failure must have its own offending commit, command, failing log and source bytes before it can be called **historical RED**. No external repository is cloned or changed.

## Source and run keys

- Historical owner-provided starting snapshot: `28d8a77e8bbc4fca6db320b4e1a95ac62079385b`; original offending commits for some examples remain **unknown**, not copied from this convenient snapshot.
- Eight-stage frozen main/base: `b67d7a725774d8404ad253b43cfca3dd35874fdf`; plan PR [#185](https://github.com/ningcol/PACT/pull/185) and staged PRs #186–#193 are distinct.
- Current source/installed fixed engineering corpus at `c8516ae31659bdae28598ae971ebd272a3e229fa`: [PACT Check #38687324164](https://github.com/ningcol/PACT/actions/runs/38687324164) **386 unit tests success**; [OS×Python selected matrix #38687324172](https://github.com/ningcol/PACT/actions/runs/38687324172) **9/9 success**, all nine raw logs inspected with no suppressed test failures.
- Every command below is a **PACT repository** command and creates only disposable `tempfile` targets or ignored PACT test state. A successful test means PACT blocked its bad fixture, not that the real-world incident was replayed at the historical commit.

## Reproduction syntax

From the pinned PACT implementation checkout, rerun a whole focused test module:

```sh
python -m unittest discover -s scripts/pact/tests -p 'test_FILE.py'
```

Replace `test_FILE.py` with the precise module shown below, or run the full corpus:

```sh
python -m unittest discover -s scripts/pact/tests -p 'test_*.py'
```

On Windows PowerShell and POSIX GitHub Actions the same Python entry point is used; literal quote parsing depends on the shell. The full 3×3 matrix runs a selected portability subset while PACT Check runs the entire unit corpus.

## S0-required issue-by-issue negative inventory

| S0 counterexample | Current executable PACT fixture (source module and exact test entry) | Required negative / expected observable outcome | Original-RED / external-data limitation |
| --- | --- | --- | --- |
| New implementation competes with obsolete architecture, mislocating a remembered feature | `test_historical_replay_metrics.py::test_aggregate_compares_direct_expanded_and_multi_query_without_gate`; `benchmarks/brownfield/cases.json` | Historical source-file retrieval metrics keep explicit denominators and expose direct-vs-expanded gap; benchmark success alone does not assert recall benefit | **Independent new old/new-architecture task oracle blocked**: previous answers/case targets were already used; an unseen held-out case cannot be retroactively reconstructed |
| Candidate Domain with no confirmed Product Rule | `test_synthetic_domain_host.py::test_candidate_rule_remains_non_normative_and_host_check_read_only`, `test_mixed_authority.py::test_candidate_document_is_not_promoted_or_reclassified` | Candidate Rule may be retrieved as context but must not appear in normative `applicable_rules`; explicitly required candidate Rule must refuse Context publication | Fictional PACT school-domain fixture is not a source-verified real `zx-zsb` task or Owner-approved Product Truth |
| Rejected Decision reason reused as permanently binding Rule | `test_audit_retention.py::test_rejected_rationale_retrievable_without_permanent_prohibition`, `test_task_handoff.py::test_changed_decision_premise_requires_re_review_on_resume` | Rejected alternative is discoverable with revisit conditions, not normative; changed referenced Decision bytes force re-review on resumed Task | Truly changed product/design premise without a file change and real Agent semantic misreading remain **unverified**; no confirmed Owner choice is assumed |
| Removal falsely labeled Convergence `updated` | `test_convergence_deletion_semantics.py::test_deletion_is_never_a_verified_update`, `::test_completion_gate_accepts_removal_but_rejects_deleted_update` | Deletion may be `removed` only under the valid prepared SHA and missing-file guard; a deletion reported `updated` **fails**; recreated/symlink path is not counted removed | Original offending-code SHA and failing log not revalidated from the old history; current negative fixture is a replayable regression, **not an invented original RED** |
| Interrupted task resumed without the original conversation | `test_task_handoff.py::test_checkpoint_resume_recover_without_inventing_completion`, `::test_run_receipt_is_revalidated_after_workspace_change` | Independent process receives prepared contract/digest, remaining tasks and stale receipt warning; checkpoint does not auto-complete Owner or rewrite frozen SHA | Actual interrupted Codex/Claude/OpenCode real-runner trace remains **blocked** until an authorized runner is available |
| Stale or false passing execution Evidence | `test_run_input_origins.py::test_required_medium_high_pass_rejects_run_that_changed_managed_files`, `test_task_workflow.py::test_pass_cannot_hide_unverified_required_claim_for_same_ac`, `::test_generated_acceptance_is_retracted_after_later_required_fail` | High/medium required pass on changed-workspace receipt fails; failed/unverified required sibling blocks AC; only unchanged PACT-generated acceptance may be retracted, manual drafts preserved | Before/after snapshot cannot detect write-and-restore *during* a command; signed attestation of local receipts unavailable |
| Concurrent ephemeral discovery inputs or disappearing probe | `test_cache_publishing_safety.py::test_transient_parse_failure_retries_without_partial_index`, `::test_permanent_source_failure_does_not_publish_map`, `::test_two_writers_one_reader_never_observe_partial_json` | A changed source set must retry/fail, never publish a success index mixing generations; atomic writers never expose partial JSON; Windows sharing conflicts retry within a cap and persistent errors fail | **Atomic, adversary-proof repository source snapshot is not provided**; polling cannot guarantee no change between checks; do not relabel this limitation as solved |
| File-origin/verification source from outside repository | `test_run_input_origins.py::test_external_script_is_rejected_by_default_without_receipt`, `::test_external_script_requires_opt_in_and_cannot_complete_medium_risk` | Unapproved external source is rejected before a passing receipt; explicit external-opt-in receipt alone cannot satisfy required medium/high Claim | Indirect subprocesses, network dependencies and opaque shell expansions are outside the declared-file attestation boundary |
| Host instruction routing, CI whitelist and include cycles | `test_host_wiring.py::test_missing_host_route_is_manual_review_not_false_pass`, `::test_filtering_host_ci_is_not_automatically_declared_compatible`, `::test_direct_markdown_include_cycle_is_rejected`, `test_init_readiness.py::test_existing_claude_and_opencode_host_configs_survive_repeated_init` | Static doctor flags missing/filtered/looping route for manual review or error; existing AGENTS/CLAUDE/OpenCode host configs remain intact and host CI is **not executed** | Real host CI allowlist policy and actual Agent instruction-loading behavior remain **blocked** without approved live runner/host setup |
| Mixed confirmed/pending material in one file | `test_mixed_authority.py::test_initialized_project_keeps_mixed_rule_non_normative`, `::test_explicit_pending_headings_are_detected` | Pending headings in a nominally confirmed Rule become review warnings; whole mixed file is **not** silently a confirmed applicable Rule | Section-level authority is not a PACT schema feature; split files/manual Owner confirmation remain necessary |

## Exactly what this closes—and does not close

**AC-S0-02 (E) mechanically covered:** every named S0 threat has either an existing PACT negative test callable through a stable source entry point or a case-specific **explicit blocking explanation**. No existing test has been duplicated as a second permanent fixture merely to inflate coverage. The above source paths, commands, expected rejection and historical/source limitations are frozen in one visible place, anchored to an actual successful test SHA.

**AC-S0-01 (E) remains unverified:** the table is *not* a per-incident historical original-offending-SHA log with both actual historical RED and current GREEN, nor proof of all original failure invocations. Do not assign the generic `28d8a77...` snapshot as the original defect commit without verifying it.

**S0-04, S0-05 and S7-01/S7-04 remain blocked/unverified:** the old/new architecture historical case was already inspected; no independently withheld task/oracle or authorized repeated real Agent/Owner A/B has been supplied. The PACT synthetic fixtures are author-constructed, not an unseen unbiased evaluation set.
