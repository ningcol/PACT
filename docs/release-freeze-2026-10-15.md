# PACT v0.4.0 Release Freeze — Evidence Checklist (2026-10-15)

> Status: **HOLD / not a release approval**. This document records current known evidence and the exact checks needed to move from development to a release candidate. Scope: **ningcol/PACT only**. This checklist does not authorize modifying, merging, or deploying downstream repositories.

## Source identity

- Starting main SHA: `b67d7a725774d8404ad253b43cfca3dd35874fdf`.
- Runtime version at that SHA: `0.4.0-dev.1` (`.pact/VERSION`).
- `CHANGELOG.md` retains an `Unreleased` heading.
- Apache-2.0 `LICENSE` exists, including release packaging rules in `docs/releasing.md`.
- The tagged release workflow is `.github/workflows/release.yml`; it is not evidence that a final tag has already shipped.
- The newest main commit describes three review passes and passing PACT Check, a 9-cell portability matrix and a pinned real-owner evidence smoke. These are **reported past checks on their own source commits**; they must not be promoted into a fresh check of a future frozen release SHA.

## Gate A — freeze the intended artifact

- [ ] Confirm which of the accumulated `Unreleased` features and fixes belong in `0.4.0` (or whether a `0.4.0-rc.1` is preferable).
- [ ] Freeze the exact source commit. Do not merge unrelated changes into the release candidate during verification.
- [ ] Set `.pact/VERSION` to the selected release/RC version and move/finalize the corresponding `CHANGELOG.md` heading **in the same reviewed change**.
- [ ] Reconcile install/upgrade behavior and compatibility guidance with the selected scope.
- [ ] Verify no prohibited downstream/owner-project changes are part of this freeze.

## Gate B — run reproducible verification on the frozen SHA

Record **run URLs, exact SHA, executed commands, results and date**. Historical evidence does not count as a rerun.

- [ ] `python scripts/pact/pact.py schema-lint`
- [ ] `python scripts/pact/pact.py check`
- [ ] `python -m unittest discover -s scripts/pact/tests -p "test_*.py"`
- [ ] `python bootstrap.py --help`
- [ ] Linux/macOS/Windows × Python 3.11/3.12/3.13 portability 9/9 on the exact frozen commit.
- [ ] `python scripts/release/release_assets.py --output-dir dist --smoke`.
- [ ] Validate `pact-bootstrap.py`, `pact.pyz`, `LICENSE`, `SHA256SUMS` as an exact matching asset set.
- [ ] Complete source review against the frozen SHA for Discovery, mixed Rule authority, Task state, Evidence input origins, cache/upgrade safety, and release-workflow permissions.
- [ ] Triage any newly found P0/P1 issue and re-run affected checks after fixes.

## Gate C — keep empirical and semantic claims honest

- Existing public-pilot and owner-project cases are useful machine-side evidence, not proof of measured owner value.
- [ ] Link a relevant external pilot to the exact release candidate where installation/Discovery/Evidence/completion semantics changed.
- [ ] Preserve the separate release HOLD for the **ziliu product change** described in PACT issue #28: local API/compatibility checks cannot attest deployed third-party publishing or client compatibility.
- [ ] Keep missing human measurements in PACT issue #32 as **not measured**: owner interruptions, comprehension, technical escalation, overhead and subjective context precision. Do not record fabricated zero values.
- [ ] Decide whether unresolved #28/#32 dimensions block general-availability claims or are transparently disclosed as limitations. Do not silently close those issues.

## Gate D — publication, only after explicit release approval

- [ ] Review the frozen source diff and accept the release scope.
- [ ] Confirm green CI and artifacts against the *same* SHA that will be tagged.
- [ ] Create the immutable `v<version>` tag only when its version equals `.pact/VERSION`.
- [ ] Confirm `.github/workflows/release.yml` completes and publishes the exact assets and checksums.
- [ ] Verify the public release entry, download links and hashes; only then close issue #63 with evidence.

## Current verdict

**Release HOLD.** Source packaging and licensing infrastructure are present, and no P0/P1 blocker was established in the preceding narrow remote-source rechecks. Nevertheless, a frozen RC/release commit, exact-SHA fresh verification, and explicit release approval are not yet evidenced here. This document is a checklist, not a completed test receipt or an authorization to tag.

References: [#63](https://github.com/ningcol/PACT/issues/63), [#28](https://github.com/ningcol/PACT/issues/28), [#32](https://github.com/ningcol/PACT/issues/32), [release documentation](releasing.md).
