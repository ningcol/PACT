# Distribution and Safe Upgrades

PACT must be easy to update without turning framework distribution into a second source of project truth.

## Ownership classes

Every file created by PACT is treated as one of two classes.

### Framework-managed

Examples:

- `.pact/pact.pyz` compact runtime;
- `.pact/schema/`;
- generic lifecycle/readme/templates;
- PACT initialization guidance;
- the opt-in PACT project CI workflow.

PACT may update these automatically **only when the target file is unchanged since the prior PACT install**.

### Project seed

Examples:

- `.pact/config.toml`;
- `.pact/baseline.toml`;
- project governance documents;
- Agent Skills;
- generated/merged `AGENTS.md`.

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
