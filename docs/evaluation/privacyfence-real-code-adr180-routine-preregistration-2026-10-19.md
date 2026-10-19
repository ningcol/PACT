# Supplemental real-source routine code task — pre-run protocol

**2026-10-19, written before running this second task.** Same public pinned PrivacyFence commit `6a03856a6e1819b2eacd3963154ebc7d02923296` and pristine 971 tracked files. Original test source `tests/unit/test_export_files.py` Git blob `61471e28fe1c907e958a13666e2507185b238ac5`. Scope of committed modifications: **PACT only**; test edits occur solely in disposable A/B local clones.

## Source-only task — no behavior change

> Rename the local `data` variable used by the CSV comma-and-newline rendering unit test to `csv_data` for clarity. Do not change its assertion, expected CSV bytes, runtime behavior, exports, or existing architectural decisions. Run the original test suite and preserve every original tracked file outside this one test file.

The task is written by this assistant after seeing the original unit test, not independently held out; it includes no Decision ID or ADR path. The user approved testing in a real open-source project; this is a **local trial only**, not a proposed PrivacyFence upstream PR.

## Exact pre-run criteria

1. Start with source-identical separate ephemeral A (unadapted) and B (installed source-identical PACT + test-only source-faithful Decision projections). Do not copy benchmark oracle, Task Contract evaluator source or PACT checkout into B. Verify original SHA, original test blob, original source manifest and absence of any tracked modifications.
2. B runs actual `pact context` for the no-ID task in explicitly requested `--nonfunctional --risk low --intent work` mode; record selected and deferred Decision counts, candidate paths/hashes, Context estimate and warnings. Confirm every visible Decision hint is source-bound and **not** incorrectly asserted as applicable current Decision. Do not infer task risk automatically. If code change were to alter production meaning, rerun normal Context instead.
3. B runs `pact task prepare` with a real Task Contract under the same opt-in mode before changing source. This validates high-level forwarding and persisted context. Do not manufacture Owner approval.
4. Edit exactly two local-variable identifier occurrences within the named unit test, in both A and B. The single-file diffs must match exactly, no source ADR or application code changed. Run the original `tests/unit/test_export_files.py` offline tests in A and B. Preserve the exact exit codes and test counts.
5. On B, generate a normal incomplete `pact task draft` and then attempt `pact task finish` **without inventing completion Evidence or an Owner Report**. The completion must be rejected, even if code tests pass, and the recorded incomplete task state must remain truthful. This is a negative completion-control test, not proof of Agent correctness or genuine Owner involvement.
6. Any failed subprocess, mismatched source/version, non-identical diff, unexpectedly accepted false-done attempt, missing PACT hint integrity or tracked-source modification outside the one test file forces **FAIL**. Report failures, not only passing cases. The original PrivacyFence repo remains read-only; no upstream write/push, no external paid model call, no Codex and no release.
7. This is a second developer-authored test on previously seen source, not an independent blind positive/negative holdout. Keep five original open Issues, default routing and Release HOLD unchanged. Estimated Context bytes are not model-billed tokens; no Owner benefit is measured.
