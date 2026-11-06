# Drift

PACT stores each durable drift item as one machine-readable artifact.

Lifecycle:

```text
known → resolved | accepted
```

Layout:

```text
docs/drift/
├── known/
├── resolved/
├── accepted/
└── TEMPLATE.md
```

## Why one file per drift

A single shared register becomes hard to reference, validate, move through lifecycle, and merge across worktrees.

One artifact per drift gives:

- stable ID;
- explicit status;
- independent lifecycle;
- Project Discovery visibility;
- Audit inventory;
- less merge conflict pressure.

## Policy

Known drift records a real unresolved inconsistency.

It is not permission to silently redefine Product Truth or leave high-risk ambiguity unresolved.

When resolved or explicitly accepted, move the artifact to the matching lifecycle directory and update its status.

## Decision and implementation are separate

Group the same business dispute into one Drift, linking every affected source
and plan. Record the source versions, confirmed facts, unknowns, scope, user
consequences, risks and the explicit question/options for the Owner. Agents
resolve questions already settled by existing authority themselves.

When the Owner chooses a business meaning, update its one canonical body and
record that decision's source. If implementation still disagrees, keep the
Drift `known`; a decision is not evidence of consistent behavior. `accepted`
requires explicit acceptance of the remaining deviation and a selected interim
authority. Merely postponing a decision is not acceptance. Only verified
implementation, relevant body and reference changes allow `resolved`.

Do not create an extra Decision artifact for every business decision. Apply the
existing admission threshold for durable, otherwise irrecoverable rationale.
During a migration, any unresolved chapter holds its entire source file in its
original authoritative location. Independent files may continue; do not change
a shared root navigation until the declared scope is ready.

## Optional local closure check

Use the structured headings in `TEMPLATE.md` for records whose closure you
want checked. This opt-in mode does not retroactively gate historical Drift
or ordinary task completion:

```bash
python3 pact.py check --root . --drift-closure docs/drift/resolved/example.md --json
# Repeat --drift-closure to check several explicitly selected records.
```

`--drift-closure` and `--artifact-only` are mutually exclusive. Paths are
repository-relative (or absolute paths inside that root). This mode reads the
explicit Drift files, the artifact schema and directly linked local files only;
it does not enumerate the repository or follow targets' outgoing links. Link
ID references (`domains`, `related`, etc.) directly in the Drift so they can be
located without an inventory. Unlinked ID-only references fail this local mode.
Duplicate IDs can only be detected within that explicitly visited set; use the
ordinary check for repository-wide ID integrity.

The six second-level headings are `Conflict sources`, `Scope`, `Decision
basis`, `Current authority`, `Implementation and verification`, and `Remaining
issues`. Closed records require nonempty content without template placeholders.
Conflict sources, decision basis and current authority each require a Markdown
source locator. A resolved record also requires `### Implementation` and
`### Verification` subsections with evidence links. An accepted record requires
a selected current authority and a description of the remaining deviation.
A `known` record cannot pass a requested closure check. The status must match
the lifecycle directory.

Common inline links (including angle-wrapped destinations and nested
parentheses) and reference-style Markdown links are supported. Local file
existence is checked; remote/special URLs, anchors/queries and unsupported
bracket/host-import syntax are reported as unverified. Directories, missing
files, root escapes and symlink aliases fail. Use explicit file links for
important closure evidence; separately review chapters and host-specific forms.
A checked file locator does not prove its linked chapter or recorded claim.

A passing result establishes only record structure and direct locators. JSON
explicitly leaves Owner-confirmation authenticity, business semantics, actual
implementation behavior, remote availability, anchors and host imports
unverified. Manual evidence review remains necessary; do not report that all
references or business behavior were verified from this check alone.
