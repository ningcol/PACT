# Revision 2 — corroborated source anchors after conservative trial failed (2026-10-20)

**Status:** The first fixed 8/16-point rule is a recorded partial failure: in privacyfence/privacyfence, it retained 10/10 positives but also retained all six irrelevant Decision selections across two routine negatives (2/2), failing the previously declared improvement criterion. The earlier preregistration and raw CI receipt are intentionally preserved. On mrwilson/adr-viewer, that same rule preserved 4/4 positives and reduced eight noisy routine cases to 0/8; it is not sufficient for both repositories.

This revision was proposed before running the second source-anchor rule against GitHub Actions. It is again developer-informed and cannot be called independent holdout evidence. It does not change frozen tasks, source Git SHAs or scoring oracle, and carries all previous safety gates unchanged.

## More robust source-grounded relevance rule

For the same single-task-query, low/medium-risk ordinary Context, a current Decision can have a large lexical score merely because many generic task words occur in a verbose ADR body. Replace absolute score as the sole weak test with an auditably source-backed corroboration test:

1. Any explicit source-score reason (including exact Decision ID/title/alias, quoted phrase or all query terms) preserves the full Decision.
2. Any distinctive task term appearing in the Decision's declared title (with actual Unicode token boundaries) preserves it. No title term means only weak body evidence so far, **not** semantic inapplicability.
3. Any distinctive compound task identifier/phrase such as an underscored code symbol or hyphenated domain phrase appearing intact in original Decision source preserves it. This protects pathless/opaque-titled code decisions and screen-reader-style source rationale. Long distinctive exact body terms also protect noncode domains.
4. With multiple queries, a non-ASCII unspaced script, high-risk, explicit Domain routing, history/decision intent, opt-in nonfunctional or --full-decisions, the original full selection remains. When the original Decision source cannot be verified, fail or preserve full context, never silently discard authority.
5. If none of the above corroborates the generic body match, defer only its full body into source-pinned, capped weak_decision_hints. User/Agent must inspect hints and required Convergence before completion; truncation blocks completion.

The rule is lexical/structural, not a new AI task classifier or Owner approval. A pathless Decision with no distinctive title may still be a true hidden constraint: it remains a source-hashed mandatory review hint and can always be fully reloaded. Semantic recall and coding obedience are still NOT established.

## Unchanged precommitted stop rules

PrivacyFence original 10/10 selected positive targets, fewer than six current Decision selections across its two developer-labelled routine negatives, unmodified 12 original ADR projections, source hashes, no hidden authority or fake task completion. Adr-viewer original 4/4 selected positive targets, fewer than eight routine negatives receiving current Decisions. All original tests, core 3x3 matrix and strict source-binding must pass. Any false negative, forged hint or fail-open task finish blocks merge. Do not tune the oracle, revise cases or redefine the denominator. No external repo writes, Codex, release tag or fabricated Owner metrics.
