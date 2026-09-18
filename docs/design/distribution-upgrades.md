# Distribution and Safe Upgrades

PACT must be easy to update without turning framework distribution into a second source of project truth.

## Ownership classes

Every file created by PACT is treated as one of two classes.

### Framework-managed

Examples:

- `scripts/pact/` runtime;
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

Seed files are never overwritten. Template/framework changes affecting a seed are reported for manual reconciliation.

## No hidden package copy

Distribution packaging must not duplicate PACT governance/templates into a separately maintained source tree.

A future `uvx` / package wrapper may expose the CLI, but canonical framework content remains single-owned and versioned.
