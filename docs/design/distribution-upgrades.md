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

### Maintenance authority

In adopted projects ordinary business tasks may read and execute PACT, but must
not patch framework-managed files or embedded schemas. Only an explicitly
authorized PACT maintenance/upgrade task replaces them through the supported
upgrade procedure. Generic defects belong upstream with reproductions. The
upstream source itself remains editable under normal review and compatibility
testing; this is not a permanent freeze of PACT's implementation.

Project seeds, governance, skills, business documents and custom checks stay
project-owned. Agents maintain them within task authority; confirmed product
meaning, permissions and material risk still follow the Owner decision boundary.
An explicit Owner decision may revise product truth; code alone may not.
Generated receipts, task state and installation bookkeeping must not be edited
to manufacture passing hashes, results or ownership. These are collaboration
and integrity boundaries, not OS locks or tamper-proof attestations. Location
under `.pact/` alone does not make a project extension framework-managed.

Every installed file is one of two classes.

### Framework-managed

Examples:

- repository-root `pact.py`;
- `.pact/pact.pyz`, including embedded protocol schemas and standard agent guidance;
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

Business explanations, Rules, conflict decisions and other project knowledge
are not framework install targets. Standard routes for new knowledge and a
reviewed migration do not authorize upgrades to relocate or overwrite business
content. Projects reference version-matched framework guidance instead of
maintaining rewritten copies; keep only necessary project-specific additions.
See [knowledge maintenance](knowledge-maintenance.md) for pre-cutover, deferred
and post-cutover authority.

## Version-matched agent guidance

`python3 pact.py guidance` reads the standard instructions carried by the running
runtime. `--json` includes their content SHA256, runtime identity and source kind.
In source checkouts the content lives in `scripts/pact/guidance.py`; installed
projects read that same module inside `pact.pyz`. There is no separately editable
installed standard manual, new configuration layer or plugin dependency.

This command is read-only: no Git scan, discovery map, business verification,
task state or host configuration is produced. Use the project-approved Python
interpreter. Read in a new session and after an upgrade, not at every finish.

Fresh projects receive a short, stable `AGENTS.md` reference. Existing guides
and custom READMEs remain project-owned; init provides merge advice instead of
overwriting them. Projects keep necessary additions at their existing
authoritative locations: interpreter, commands, knowledge routing and stricter
permissions. Default knowledge paths do not override an established project
router. Project additions cannot manufacture confirmed truth or bypass runtime
Evidence checks. No generic replace/prepend/append/wrap engine is introduced.

When the selected upgrade source supports the command, upgrade reports an
`agent-guidance-review` notice if it cannot recognize a direct reference in the
project entry. This includes old generated guides which had no source hash and
could not receive ordinary seed-template notices. The notice preserves every
project byte; indirect routing may already work and requires manual review.
Repeated init/upgrade does not append instructions. A configured direct reference
is only a static observation, not a claim that it was executed or obeyed.

`doctor --host-wiring-only --json` separates available standard content and
bounded project-reference observations from session loading, behavioral
compliance and write protection, which remain unverified. It also surfaces root
`AGENTS.override.md` because a non-empty override can shadow `AGENTS.md` for
Codex at that directory. No global host configuration or nested rule tree is scanned.

Instruction/package integrity, actual host loading and verified task outcomes
are different assertions. Local manifest/hash matching is not a trusted release
attestation. A Markdown prohibition or a managed block in a writable guide is
not OS isolation; file permissions cannot protect only one Markdown block.
Optional host/OS protection must cover entire framework files, including the
root launcher, and both file tools and Shell execution paths. Its policy must
itself be protected. PACT neither changes that policy nor claims it is active.
An authorized upgrade uses the maintenance context; ordinary business tasks
cannot patch framework files to work around defects.

An optional [outer-sandbox sample and probe coverage](../evaluation/framework-protection-2026-11-06.md)
keeps configuration delivery separate from actual host protection. It changes no
global settings and certifies neither native file tools nor external MCP/plugins.

Project knowledge/configuration and tool-generated execution state retain their
existing ownership. Do not make all of `.pact/` read-only. A future host-native
file import may use a runtime-derived managed projection, but must not introduce
a second independent standard or silently enable global auto-updates.

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

Select a fixed source, preview operations/conflicts, apply within explicit
maintenance authority, then verify integrity and relevant project compatibility.
Updating an upstream clone never updates an adopted project automatically.
`doctor`/`status` expose runtime version, archive SHA256, integrity and declared
capabilities. Equal version strings can identify different builds; source mode
has no archive digest. Capabilities mean supported interfaces, not configured
policy, checks executed, rule loading or business acceptance.

Runtime replacement and reconciliation of project-owned guidance are separate
results. Review relevant upstream seed/template/usage differences and merge only
applicable guidance into existing authoritative files. Preserve customizations;
never invent baseline reviews, add CI, or run business-wide tests merely because
of an upgrade. Record actual results and outstanding guidance in the existing
maintenance record, without another approval register. Unknown source stays unknown.

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
