# Distribution and Safe Upgrades

PACT must be easy to adopt and update without turning framework distribution into a second source of project truth.

## One installed surface

PACT has one supported installed layout. Fresh adoption installs only the control-plane nucleus:

- repository-root `pact.py`;
- `.pact/pact.pyz`;
- `.pact/VERSION`;
- project-owned Owner config, baseline, and fitness seeds;
- `AGENTS.md` when the project does not already have one, or merge guidance under `.pact/`;
- `.pact/.gitignore` for local generated control-plane state;
- optional project CI workflow only when explicitly requested.

Product Truth, Architecture, Decision, Change, Drift, and Skill directories are materialized only when real project knowledge needs a durable owner.

There are no legacy/full install profiles or alternate runtime layouts in the supported protocol.

## Ownership classes

Every installed file is one of two classes.

### Framework-managed

Examples:

- repository-root `pact.py`;
- `.pact/pact.pyz`, including embedded protocol schemas;
- `.pact/VERSION`;
- optional project CI integration.

PACT may update these automatically only when the target remains unchanged since the prior install.

### Project seed

Examples:

- `.pact/config.toml`;
- `.pact/baseline.toml`;
- `.pact/fitness.toml`;
- generated `AGENTS.md` or merge guidance.

Seeds become project-owned immediately after creation and are never silently overwritten by upgrade.

## Install manifest

`pact init --apply` records `.pact/install.json`.

For every file PACT actually created, it stores:

- ownership class;
- source path;
- source SHA256 when applicable;
- installed SHA256.

The manifest is upgrade bookkeeping, not project truth.

## Transactional initialization

Fresh/repeated `pact init --apply` never overwrites existing project files.

For missing install targets it uses a create-only transaction:

```text
plan
→ render every new file into a transaction staging directory
→ publish each missing target atomically
→ build install provenance from the published bytes
→ commit .pact/install.json last
→ verify recorded hashes
```

If publishing, manifest construction, or final validation fails, PACT removes only files created by that init transaction and restores any prior install manifest. Existing project files are not part of the rollback set.

## Upgrade safety

For framework-managed files:

- unchanged target + changed framework → safe update;
- missing target → safe create;
- locally modified target + changed framework → conflict;
- existing but untracked framework path → conflict.

If any conflict exists, `--apply` refuses the entire automatic update.

When a future release makes a framework path obsolete, upgrade deletes it only when the current file is still byte-identical to the prior installed hash. A locally modified obsolete framework file is preserved and detached from framework management.

Seed files are never overwritten. A changed upstream seed template is reported for manual reconciliation.

## Stale-plan and concurrent-edit boundary

A dry-run plan is a snapshot, not a reservation of installed files. The CLI's `--apply` path creates its own plan, and the apply phase rechecks the installation Manifest, source version/content and planned operations before any target mutation.

Before create/update/remove/refresh, PACT verifies each planned destination still has the expected existence, regular-file type and SHA256. For destructive operations it also verifies the target just before the OS replacement/removal. A new user-created file, a locally edited framework file, a modified obsolete file or a stale manifest triggers an error instead of silent replacement or deletion. Unchanged files are still upgraded and the existing transaction rollback tests continue to apply.

The install Manifest is written last. PACT refuses to overwrite a concurrently altered Manifest. During rollback, it checks that a replaced file still has the exact bytes PACT wrote (or is still absent after removal) before restoring or deleting it. A file or install Manifest subsequently changed by another writer is preserved, and PACT reports incomplete rollback rather than asserting that all files were restored.

This is an **optimistic fail-closed check**, not a cross-process lock or a proof that every race is impossible. Non-cooperating writers can still change a file between the final comparison and an OS-level operation. Stronger protection would require coordination or platform-specific atomic conditional operations; do not claim that this phase provides either.

## Historical PACT 0.1/0.2/0.3 upgrades (explicit, no data loss)

Old PACT 0.1/0.2 project seeds were YAML; 0.3 added TOML but could
continue consuming old YAML. The current compact 0.4 runtime is TOML-only.
Simply installing a new empty config or leaving an old YAML Decision
unchanged could otherwise erase *effective* Owner intent while preserving
the original bytes. The upgrader now scans legacy YAML seeds and
PACT-marked authoritative Markdown *before* any writes.

- Run `upgrade` with no flags for a dry-run; if legacy sources exist,
  ordinary `upgrade --apply` **refuses** instead of shadowing them.
- Use `upgrade --migrate-legacy` for an explicit **migration preview**.
  Only after reviewing its operations/conflicts, use
  `upgrade --migrate-legacy --apply`.
- The narrow, standard-library YAML converter is migration-only; runtime
  support for arbitrary legacy YAML does not return. It preserves the old
  `.pact/*.yaml` files, creates modern project-owned TOML seeds, and
  modifies only verified TOML-front-matter conversions in historical
  project-owned Markdown. The authoritative Markdown *body is unchanged*.
- Original Owner preferences, baseline reviews and supported Fitness
  checks must round-trip into the exact current schema. Old 0.2 did
  not record an `agent_bootstrap` review: it becomes **pending**, never
  invented as reviewed. Retired default path/risk/discovery/convergence
  settings are ignored only when equal to original historic defaults;
  custom legacy semantics are a hard conflict requiring Owner review.
- A historical Decision without an existing stable `DEC-*` ID and
  lifecycle status is a **manual conflict**. The converter never invents
  Decision identity, demotes Rule authority, reconstructs lost rationale,
  or promotes tentative business truth.
- Historical incomplete `.pact/tasks/*/task.json` state blocks upgrading
  until its state is genuinely completed or archived outside the project.
  No old Evidence/Convergence/Task Contract is silently reinterpreted by
  the newer trust contract.
- A pre-manifest install (no `.pact/install.json`) cannot use automatic
  tracked upgrade: preserve the old project and its documents, establish
  provenance by an explicit new installation in an isolated copy, then
  reconcile its project-owned notes manually.
- The old YAML files may remain after a successful migration as archive
  material; only TOML is active. Verify `owner --strict`,
  `readiness`, `check` and exact-ID `discover` of important
  Decisions after upgrading.

The new TOML seeds and authority metadata conversion are staged/backed
up/committed within the **existing upgrade transaction**. Any failure
rolls back bytes and the old install manifest where safe. This protects
the configured Owner meanings; it does not prove a real Agent will obey
them, or that every historical nonstandard YAML syntax is supported.

## Transactional apply

Automatic framework upgrade uses:

```text
plan
→ stage replacement files
→ verify staged hashes
→ backup every target that will change
→ atomic replacement/removal
→ build and validate new install manifest
→ commit manifest
→ validate final hashes/version
```

If mutation or validation fails, PACT restores replaced files and the previous manifest. Files created only by the failed upgrade are removed.

## Single-file bootstrap

The repository-root `bootstrap.py` contains no project truth.

It:

1. downloads an explicitly selected PACT GitHub ref/commit to a temporary directory;
2. optionally validates the source archive SHA256;
3. rejects archive traversal and symlink entries;
4. invokes that source's real `init` or `upgrade`;
5. deletes the temporary source afterward.

This keeps canonical framework content single-owned and versioned.

## Embedded protocol schemas

Canonical editable schemas live under `.pact/schema/` in the PACT source repository.

Adopted projects do not receive those schema files. The exact installed `pact.pyz` embeds the protocol schemas used by its runtime, so runtime and validation contract move together.

## No hidden package copy

Future wrappers such as `uvx` may improve invocation, but they must not introduce a separately maintained copy of PACT governance/templates or protocol truth.


## Local generated state

PACT keeps execution/process state local rather than turning it into durable project knowledge.

The nested `.pact/.gitignore` ignores:

- `cache/`;
- `tasks/`;
- `runs/`;
- `completions/`;
- `tmp/`;
- transient upgrade transaction directories.

These files remain available locally for task status, evaluation, Evidence, and completion checks, but they do not belong in normal project commits. Durable knowledge belongs in Product Truth, Architecture, Decisions, Changes, Drift, and ordinary Git history.
