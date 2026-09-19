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

## Upgrade safety

For framework-managed files:

- unchanged target + changed framework → safe update;
- missing target → safe create;
- locally modified target + changed framework → conflict;
- existing but untracked framework path → conflict.

If any conflict exists, `--apply` refuses the entire automatic update.

When a future release makes a framework path obsolete, upgrade deletes it only when the current file is still byte-identical to the prior installed hash. A locally modified obsolete framework file is preserved and detached from framework management.

Seed files are never overwritten. A changed upstream seed template is reported for manual reconciliation.

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
