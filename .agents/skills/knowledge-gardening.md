# Skill: Knowledge Gardening

## Purpose

Keep current project knowledge **small, accurate and easy to find**. This is
a replaceable Agent procedure, not a PACT rule, autonomous truth editor, or
reason to write more Decision Records.

## When to run

During relevant maintenance, when a project explanation reveals stale knowledge,
or when a meaningful change closes. Do not mandate a full-repository pass for
every trivial implementation or introduce a new CLI.

## Inputs and discovery

Start with \`pact audit --json\` and the relevant \`pact inspect\`/Task Context.
Review only the targets relevant to the task:

- \`active_changes\`: determine if the actual work completed or was abandoned.
- \`known_drift\`: reconcile the observed mismatch against the correct
  authority; do not rewrite confirmed Product Truth merely to match code.
- \`mixed_rule_candidates\`: inspect explicit pending headings inside confirmed
  Rule files. Split into separate confirmed and candidate Rule Artifacts, linked
  from a neutral domain page. Do not invent which paragraphs were approved.
- \`decision_retention_candidates\`: review decisions **already explicitly
  superseded**, checking that their old rationale is historical, not a
  remaining current constraint. Preserve the supersession link and rationale.

Do not archive solely because a note is old, no longer referenced, or located
near deleted code. A missing file reference is a review clue, not permission
to rewrite design history. Preserve decisions with long-term maintenance value
not reliably recoverable from code, tests, current architecture or ordinary docs.

## Workflow

1. Identify the relevant source, scope and owner of truth (Product Rule,
   current architecture, Task Contract, code, or durable Decision rationale).
2. Read concrete affected code, tests, contracts and explicit references. Confirm
   what is current and what is historical. **Do not infer product approval**.
3. Propose the smallest patch: fix a stale route/link or current-state
   description, split mixed Rule authority, mark a Change completed/abandoned,
   or move a reviewed superseded Decision to \`archived/\` with its history intact.
4. Keep a brief evidence summary of which source established each conclusion.
   When authority is disputed, leave the relevant record candidate/blocked
   and surface the product consequence for owner resolution.
5. Run \`pact check\`, appropriate verification/fitness checks and Convergence
   against actual affected paths. A clean Audit is not proof of behavioral
   correctness. Record what remains unknown.

## Guardrails

- Never auto-delete or auto-archive the repository's normative/historical truth.
- Never set \`status = "confirmed"\` from parser output, passing tests, or code alone.
- Never turn an Audit \`semantic_review_target\` into a deterministic failure
  solely on semantic inference.
- Prefer references over copied rationale and remove stale duplicates only
  after checking their owner.
- No mandatory extra process when Audit has no relevant targets.

The resulting review can be delivered as an ordinary task patch/PR. The user
should see consequences, verification and remaining uncertainty by default.
