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

The disposable `.pact/cache/project-map.json` is generated and integrity
checked from these source records. It never overrides them. Adding a Domain
does **not** automatically confirm every linked Rule or Decision.

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
  Rule or exact ID/title/alias from this Domain is still selectable. The Agent
  must read the authentic Rule/Decision and judge actual task applicability
  before editing behavior.
- No Domain or multiple Domains: original lexical Context remains intact,
  with an explicit `scope_route.status` and a warning that none of those
  lexical hits is a semantically verified constraint.
- High-risk or explicit history/decision lookup: retain unrestricted Context
  to avoid silently omitting cross-domain safety constraints.
- Caller-declared `--require-rule` remains authoritative: it must be
  materialized and confirmed even if its Domain differs from the task's.
- Capped route hints (12 maximum) always disclose a dropped-hint count and
  unknown-applicability status. A short list is **not** proof that everything
  applicable has been found. When cross-domain or renamed code is plausible,
  manually check additional Domains/Git history or rerun without the option.

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
