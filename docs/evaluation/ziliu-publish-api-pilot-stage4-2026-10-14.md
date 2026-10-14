# ziliu publish API Stage 4 — release compatibility and deployment-risk audit

**Status at creation:** temporary reproducible risk-audit workflow and evidence design, **not** a release authorization. Runtime findings are PENDING until the exact CI run finishes.

## Frozen inputs

- ziliu default branch: `61af579266848ee50d12a0b658d1e32a49dabfde`.
- Proposed ziliu correction Draft [PR #1](https://github.com/ningcol/ziliu/pull/1): `6463b2a315d3619f8427c8ff83c1fe57e0385322`.
- PACT main: `28d8a77e8bbc4fca6db320b4e1a95ac62079385b`; earlier full trust-loop Draft [PACT PR #176](https://github.com/ningcol/PACT/pull/176).
- Stage 3 source RED/GREEN, NextRequest/NextResponse + test-only auth stub, 10/10 green and PACT task finish are already recorded; this stage checks the **real Next.js server** compatibility boundary and deployability.

## Source-backed release risk inventory

| Review area | Confirmed source fact | Release implication |
| --- | --- | --- |
| Successful server request | `POST /api/publish` returned synthetic HTTP 200 `success:true` for four unimplemented providers; new Draft returns HTTP 501 `success:false` without a provider result | Intentional **breaking API response change** for any unknown caller expecting 200/data; not a provider rollout |
| Authentication | NextAuth `getServerSession(authOptions)` backed by JWT session strategy, local DB credentials provider | Preserve 401/400; real deployed session security/cookies need separate staging validation |
| Published UI | Editor `handlePublish` copies content, signals extension and opens provider website; no literal direct endpoint call in inspected tracked JS/TS/Markdown | Editor and extension code are unchanged; this alone cannot establish absence of external/dynamic clients |
| Extension API | `extension/core/api-service.js` routes named article/preset/config/conversion endpoints via background; no explicit publish helper was seen in that inspected service | Need inspect full shipped extension archive separately and still cannot prove installed client behavior |
| Deployment | README describes Vercel/Next.js; `vercel.json` sets API maxDuration 60 and generic security headers, no server publish route rewrite | Static routing source not altered, but actual Vercel build/deployment and environment config inaccessible |
| API CORS | The separately implemented `/api/articles/[id]` route sets extension CORS headers; `POST /api/publish` has no equivalent explicit handler | Do not claim external extension clients work; verify real OPTIONS/GET behavior and distinguish app-default from route-specific headers |

## Required isolated checks

1. Enumerate the **entire tracked repository**, scan relevant text files for literal `/api/publish`, and read-only scan the **shipped** `public/ziliu-extension-v1.3.3.zip` without executing plugin code. Record hits with file/member names, not an unsupported claim of zero outside traffic.
2. Freeze both exact SHAs; install project lockfile dependencies with hooks disabled. Build Next.js **twice** (base and proposed correction) with `TURSO_*` blank, temporary local SQLite, and non-production auth secret.
3. Start real `next start` bound only to `127.0.0.1`; create short-lived test-only NextAuth JWT in memory using the local package and no user/database credentials. Send real loopback HTTP requests to anonymous, malformed, unsupported platform, four valid providers, GET and OPTIONS.
4. Compare baseline and fixed HTTP status/JSON, preserving 401/400, verifying deliberate 200->501 for all four, unchanged GET/OPTIONS. Fail the CI on unexpected differences; never fake successful service execution.
5. Record the facts and unverified boundaries in this report; no product main mutations, third-party provider calls, real account cookie, Vercel deploy, production health probes, secrets or release.

## CI observations

**PENDING** at document creation. The PR must be updated from the actual immutable workflow run; never mark these checks as pass without the run evidence.

## Risk disposition and stop rule

Passing local tests and a clean tracked/ZIP caller scan is **insufficient to claim release safety**: unseen third-party clients may depend on HTTP 200, 5xx status may trigger automatic retries/alerts, and there is no accessible production request telemetry in this GitHub-only audit.

**Release gate: HOLD until** the owner reviews external consumers/usage telemetry in their staging/production operations and authorizes the changed response; a canary/rollback strategy exists; NextAuth cookie and browser-extension end-to-end paths are validated on real staging if release is intended. Those steps are outside this disposable read-only audit.

**Stop after independent Stage 4 review.** Keep ziliu PR #1 and PACT PRs #174–#176 Draft/unmerged, and keep this temporary workflow Draft/unmerged. No auto merge, deployment or tag.
