# Distribution and Safe Upgrades

PACT must be easy to update without turning framework distribution into a second source of project truth.

## Ownership classes

Every file created by PACT is treated as one of two classes.

### Framework-managed

Examples:

- `.pact/pact.pyz` compact runtime, including framework protocol schemas;
- repository-root `pact.py` / runtime version marker;
- optional project CI integration;
- legacy/full-profile framework templates and compatibility files.

PACT may update these automatically **only when the target file is unchanged since the prior PACT install**.

### Project seed

Examples:

- `.pact/config.toml`;
- `.pact/baseline.toml`;
- `.pact/fitness.toml`;
- generated/merged `AGENTS.md`;
- project knowledge artifacts once they are materialized.

These become project-owned immediately after creation.

PACT upgrade never silently overwrites them.

## Install manifest

`pact init --apply` records:

```text
.pact/install.json
```

For each file it actually created, the manifest stores:

- ownership class;
- source path;
- source SHA256;
- installed SHA256.

The manifest is bookkeeping, not project truth.

## Install profiles

Fresh brownfield adoption uses `install_profile = "minimal"`.

The minimal profile installs the executable/control-plane nucleus only:

- root `pact.py`;
- `.pact/pact.pyz`;
- `.pact/VERSION`;
- Owner config, baseline, and fitness seeds;
- `AGENTS.md` when the project does not already have one, or merge guidance under `.pact/` when it does;
- `.gitignore` only when PACT must create one.

Product Truth, Architecture, Decision, Change, Drift, and Skill directories are not materialized merely to represent an empty taxonomy. They appear only when real project knowledge needs a durable repository owner.

This is a physical-layout optimization only. The runtime protocol, Task Contract, Context, Evidence, Convergence, Owner Report, and completion gates are unchanged.

### Upgrade compatibility

The install profile is sticky:

- a `minimal` manifest continues using the minimal desired distribution surface on upgrade;
- an explicit `full` manifest uses the historical/full surface;
- manifests created before install profiles existed are treated as legacy/full for upgrade planning.

PACT does **not** automatically convert an existing full/legacy installation to minimal. That would reinterpret existing project layout and could remove compatibility material the project has already referenced. A future explicit migration may do so only with its own reviewable safety contract.

## Upgrade safety

A future PACT source may plan an upgrade against an adopted project.

For framework-managed files:

- unchanged target + changed framework → safe update;
- missing target → safe create;
- locally modified target + changed framework → conflict;
- existing but untracked file → conflict.

If any framework conflict exists, `--apply` refuses the entire automatic update. PACT does not create a mixed partial runtime version.

When a newer distribution makes an old framework-managed path obsolete, upgrade may delete it only when the current file is still byte-identical to the prior install manifest. Locally modified obsolete framework files are preserved and detached from framework management.

Seed files are never overwritten. Template/framework changes affecting a seed are reported for manual reconciliation.

## Transactional apply

Automatic framework upgrade uses:

```text
plan
→ stage all replacement files
→ verify staged hashes
→ backup every target that will change
→ atomic file replacement
→ build/validate new install manifest
→ commit manifest
→ validate final hashes/version
```

If any mutation or validation fails, PACT restores all replaced files and the previous install manifest. Files created only by the failed upgrade are removed.

This is separate from conflict detection: conflicts prevent mutation before staging/apply; rollback protects against filesystem/process failure during apply.

## Single-file bootstrap

The repository root `bootstrap.py` is intentionally tiny and contains no governance/template truth.

It:

1. downloads an explicitly selected PACT GitHub ref/commit to a temporary directory;
2. optionally validates the source archive SHA256;
3. safely rejects archive traversal/symlinks;
4. invokes that downloaded source's real `init` or `upgrade` runtime;
5. deletes the temporary source afterward.

This enables adoption/update without a local PACT checkout while keeping canonical framework content single-owned.

## No hidden package copy

Distribution packaging must not duplicate PACT governance/templates into a separately maintained source tree.

A future `uvx` / package wrapper may improve invocation, but canonical framework content remains single-owned and versioned.


## Embedded protocol schemas

The canonical editable schema sources remain in the PACT source repository under `.pact/schema/`.

Adopted projects do not receive framework schema files. The compact runtime embeds the schema set as internal resources and treats those resources as authoritative when executing from `pact.pyz`.

During migration, unchanged old framework schema files are removed transactionally. Locally modified old schema files are preserved and detached, but they do not override the embedded runtime protocol.
