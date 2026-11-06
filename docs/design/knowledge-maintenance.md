# Knowledge maintenance and bounded migration

The [product router](../product/README.md) owns placement and granularity. This
procedure uses existing Change, Drift, Context and Convergence records; it adds
no registry, global knowledge lock, per-plan summary or migration executor.

## Before, during and after a switch

Before migration, maintain the established authoritative locations. Declare the
inventory scope and exclusions in one existing Change, with source Git revision
and path, reviewed source-to-target mapping, migrated/deferred/excluded outcome,
reference mapping and verification results. Temporary inventory stays local;
its existence does not prove completion. Review only scoped files and their
direct references, classifying confirmed requirements, candidates, current
implementation, long-lived rationale and history without inferring authority
from code. Retain conditions, exceptions and real confirmation sources.

First move conflict-free, independently usable files. An unresolved business
conflict in any chapter defers the **whole source file**, unchanged; independent
files may proceed. One business dispute gets one Drift across sources/plans,
with exact source revisions, known/unknown facts, scope, visible consequences,
risk, the decision question/options and interim authority. Reuse an existing
Drift rather than opening one per source. Resolve questions from existing
authority autonomously; ask the Owner only across the existing decision boundary.

Retire a source body only when its original bytes can be recovered through an
existing Git revision and path. Uncommitted/untracked content needs a checkpoint
under the project's existing Git process; never auto-commit or require unrelated
work to be clean. Without a recoverable revision, defer retirement. Preserve
stable IDs during moves. Cross-type extraction records source links, never
cross-type `supersedes`. Historical Decision rationale and valid replacement
relations remain available. An old path may become a short redirect containing
neither another stable ID nor another effective business body. A redirect is an
`updated` file, not `removed`; actual canonical deletions still require the
prepared Context's source-bound removal evidence.

Review explicit reference mappings individually. Check file targets with existing
tools; separately inspect chapter anchors, encoded/parenthesized links, host
imports and special syntax. Disclose unverified references. Update root entries
and shared navigation **last**, after file-level cutovers. After the declared
switch, maintain the new canonical bodies; deferred files retain their original
authority and maintenance route. An interruption leaves the isolated Git tree
and diffs available for review, without automatic replay, overwrite or cleanup.

## Decision and implementation are separate

A genuine Owner decision identifies its source, choice and applicable scope.
Update the unique business authority accordingly. If implementation still
disagrees, retain the Drift and report the deviation; a decision alone is not
resolution. Postponement without an authority choice keeps the source deferred.
`accepted` requires explicit risk acceptance, an interim authority and remaining
deviations. `resolved` requires the body, references and necessary implementation
to be verified. Do not create a Decision for each business choice; its existing
two-condition admission rule still applies. The optional
`check --drift-closure PATH` validates only selected records' structure and direct
references, not the authenticity or semantics of a decision. It does not become
a default historic Drift or task-finish gate.

## Ordinary tasks and reuse

Use existing `knowledge_retention`: reuse without a body change is `none`, with
the existing source cited in the rationale; routine fixes may directly use
`none`. Updates explain the authority and delta; creations explain why existing
records are insufficient and identify the new fact and its source. No new `reuse`
enum or mandatory review table is needed. An `aligned` claim applies only to
unchanged sources actually bound in the original prepared Context. New authority
that changes constraints needs genuine scope/Evidence reconciliation; do not
force reprepare simply to remove warnings.

Assist offers bounded candidates from this task's outputs, prepared sources,
related Domains and explicit links, reusing Audit overlap heuristics. Specs
remain ordinary, unconfirmed documents. Truncated, unread or unreturned sources
mean incomplete recall, never “no duplicate exists.” Similarity, possible scope
conflicts and suspected misplacement require semantic review; they never justify
automatic merge, deletion or confirmation. Proven bad IDs/references/bindings may
fail mechanically. File-operation checks show only what preparation proves;
they establish neither first appearance of knowledge nor authorship.

## Multiple plans and agents

Sequential plans read the latest body and update or cite it at the same path.
Within one plan, designate one knowledge-page integrator in existing work
assignments; workers do not each need their own full Task, Change and summary.
Prefer isolated worktrees for independently accepted plans. This is a
collaboration convention, not a global scheduler or lock.

Review knowledge changes and related topics in the **final merged tree** and
record the result in the original PR/Change. Include same-meaning records with
different files and IDs, not just textual merge conflicts. Similar rules for
different years, roles, conditions or states remain distinct. Report migration
application, structural cutover, business behavior consistency and PACT Task
completion as separate outcomes.

## Framework ownership

Standard instructions, protocol and runtime have one managed source; projects
reference them and keep necessary environmental, verification and stricter
permission additions. Do not maintain rewritten framework-rule copies. Business
bodies and Owner decisions are project-owned, excluded from the framework
installation manifest and preserved during upgrades. See
[distribution ownership](distribution-upgrades.md).
