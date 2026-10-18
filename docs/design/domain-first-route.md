# Opt-in Domain-first Task Context (experimental)

PACT keeps exactly one authority for each durable fact: a Domain page routes,
confirmed Product Rules define product behavior, Decision records explain
durable trade-offs, code/tests describe and verify implementation. **No per-code
Markdown shadow copy or handwritten central index.** Git stores revision
history; stable PACT IDs and status/replacement references preserve business
identity and current authority.

## Fixed source homes

- `docs/product/domains/<domain>.md`: lightweight confirmed Domain router;
  document canonical name, bounded aliases, optional stable `paths` globs,
  and links/IDs of related existing Rules and Decisions.
- `docs/product/rules/<name>.md`: independently confirmed normative Rule.
  Candidate and confirmed requirements are in separate files.
- `.agents/decisions/implemented/<name>.md`: only durable, non-derivable
  rationale and invariants; historical and rejected records keep their own
  lifecycle and supersession links.
- `src/` and tests: actual current implementation; optional nearby README
  may link to its Domain, but no mandatory source-file Markdown duplicate.

The disposable `.pact/cache/project-map.json` is generated from repository
Markdown. Domain/Rule/Decision **routing fields are freshly reparsed from
the authoritative source files** on every scoped lookup; a matching cache
fingerprint or syntactically valid index is not enough to trust aliases,
paths or Owner authority. A tampered/stale authority cache causes a hard
failure, not a silent new Domain. Adding a Domain does **not** automatically
confirm every linked Rule or Decision.

## Opt-in route (without changing default retrieval)

```shell
python pact.py context "Rename src/auth/login.py parameter without changing authentication" \
  --success "Authentication behavior unchanged" --risk low \
  --no-code --scope-first

python pact.py task prepare "Change login session expiration" \
  --success "Existing auth constraints are preserved" \
  --risk medium --scope-first
```

The router first matches only **declared, confirmed** Domain IDs, full
titles/aliases or a code file named in the task against a Domain's `paths`
globs. It never infers an authoritative match from arbitrary code comments or
a random body-text substring.

- Exactly one Domain: Domain router is materialized. Its linked Rules and
  Decisions become **metadata-only candidate hints**, NOT automatically
  `decisions` or `applicable_rules`; only an explicitly requested stable
  Rule or exact ID/title/alias from this Domain is still selectable. Each
  linked candidate is pinned to the source file SHA256 and **must receive an
  explicit, reasoned Convergence coverage disposition** before Task Finish
  can pass, even when the candidate was only metadata and not materialized.
  Agents should inspect the cited source before declaring it `not-applicable`.
  The convergence check can verify presence, status, source hashes and coverage,
  but cannot mechanically prove that a semantic rationale is true.
- No Domain or multiple Domains: original lexical Context remains intact,
  with an explicit `scope_route.status` and a warning that none of those
  lexical hits is a semantically verified constraint.
- High-risk or explicit history/decision lookup: retain unrestricted Context
  to avoid silently omitting cross-domain safety constraints.
- Caller-declared `--require-rule` remains authoritative: it must be
  materialized and confirmed even if its Domain differs from the task's.
- Metadata hints are capped at 12, but this display limit never truncates the
  internal linked source-path set. A Domain with **more than 12** linked
  authorities keeps **unrestricted** lexical Context instead of hiding the
  thirteenth exact ID; it warns that the hint list is incomplete. Its scoped
  Task Finish is deliberately blocked until the full Domain is inspected and
  the task is reprepared **without** `--scope-first` (or a smaller, approved
  scope is documented). Similarly, missing/ambiguous Domains and any
  pathless/cross-domain authority require targeted broad follow-up. A short
  list can never certify semantic completeness.

## Verification and deployment gate

The option is **experimental, disabled by default**. Domain metadata creates
routing evidence, not a semantic proof. A renamed or relocated implementation
may invalidate a `paths` route even when the owner-facing behavior remains
identical. A changed business concept, shared security constraint, global
requirement, or weakly named Domain can therefore require a broader investigation.

Never mark automatic Owner permission or semantic decision adherence as
verified based on `scope_route`. Before default adoption, compare against
the frozen baseline on pathless decisions, code rename/move, missing/multiple
Domains, cross-Domain confirmed Rules, routine negatives and real Agent
behavior. Developer-authored retrieval benchmarks are useful *engineering*
evidence only. Issues #221/#214 and release remain HOLD pending independent
Agent/Owner findings.
