# Historical upgrade compatibility repair — implementation gate (2026-10-20)

**PACT only.** Source main `9c6a529ca4500ebb9bf9b30c459c38f82f335c4c`. Do not change other repositories, invoke Codex, tag or release.

Verified historical *commit* source snapshots (none is inferred from a current release tag):

- 0.1.0: `101ccb91e1b312b3e061c012b1c167003260c749`. Original `.pact/config.example.yaml`, `.pact/baseline.example.yaml`; historical manifest/upgrade logic already exists here but older untracked installs may predate it. Plain-text Decision headers can have **no machine ID**, so guessing one is prohibited.
- 0.2.0: `8ef8228340cd22e668e898128b33bafde5b047d7`. YAML config/baseline/fitness seeds. Config includes paths/risk/discovery/convergence *defaults* no longer accepted by the modern Owner schema.
- 0.3.0: `f8690a64f7d6bc448092919cfb71411567041fc5`. New TOML seeds with compatibility for prior YAML; legacy documents/records might remain.
- Current 0.4.0-rc.1 main: runtime is TOML-only. `pact upgrade` currently ignores project-owned YAML seeds and historical YAML metadata in authoritative Markdown. This could misleadingly succeed while Owner configuration/Decision discovery disappears.

## Fixed safety contract

1. Normal `upgrade` dry-run must detect legacy seed/authoritative document metadata in the actual downstream target **before** allowing `--apply`. Do not pretend retained YAML is readable by modern runtime.
2. An explicit opt-in `--migrate-legacy` should convert only a well-defined stdlib-only YAML subset into TOML, preserving every supported Owner setting, review status and known metadata field. Historical removed config keys may be dropped **only when byte/semantic values equal the verified historic defaults**; custom old routing/authority values must block and require a manual decision. An older baseline lacks `agent_bootstrap` by design; add it as **pending**, never pretend review.
3. Original project-owned authority prose and metadata are critical. Preserve original Markdown body byte-for-byte. Parse and convert YAML front matter only if the parsed metadata identity/status/lifecycle is verified. Missing stable ID, unexpected metadata, ambiguous/duplicate YAML, symlink or overlarge file is a blocking conflict, never silently indexed as generic text. Non-PACT markdown with no PACT metadata is not rewritten.
4. Use the existing plan/stage/check/backup/publish/manifest-last/rollback upgrade transaction for these opt-in changes. Original project YAML seeds remain on disk as non-active historical sources; the new TOML is project-owned (seed), not overwritten by future upgrades. No blanket rewriting/renaming of legacy Decision prose.
5. Missing `.pact/install.json` or incompatible active task receipts must NOT be represented as a safe automated upgrade. Provide actionable manual upgrade instructions and keep original data intact. Do not silently invalidate outstanding Owner decisions or task work.
6. Test current-to-current no-op, source-pinned old 0.1/0.2/0.3 installs or deterministic fixtures, changed Owner preferences/review status, old decision retrieval by ID after migration, customized legacy settings fail closed, corrupted YAML, conflicting TOML, symlinks, stale plans and injected mid-apply rollback. Validate that `--apply` without opt-in refuses legacy targets, and that refused upgrades leave hashes unchanged.
7. Run PACT Check, schema/workflow lint, 9 OS×Python matrix and two real-source benchmark workflows at the exact PR head. If any unexpected authority loss or regression occurs, keep the PR Draft and do not merge. After successful source-first self-review, only merge PACT and verify exact-main CI.

No release GO, no GitHub Release and no Owner/independent Agent result is inferred by green engineering CI.
