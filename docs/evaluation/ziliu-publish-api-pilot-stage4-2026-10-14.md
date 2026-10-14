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

**Observed exact audit run:** [GitHub Actions run 38529359870](https://github.com/ningcol/PACT/actions/runs/38529359870) completed **SUCCESS** on Stage 4 initial PR revision `1d5f4faea196d0afbc5c7c5975027c3645d9c72d`.

### Packaged artifact + caller inventory

- Git tracked **180 files**. Apart from the publishing route itself, **140 plain-text files** were scanned for literal `/api/publish` or `api/publish`: **zero matches**.
- The actual tracked `public/ziliu-extension-v1.3.3.zip` was opened **read-only**; **29 code/config/HTML text members** inspected: **zero literal endpoint matches**. ZIP member execution, extension browser startup and external network access did not occur.
- Scanned binary/oversize path exclusions are logged by name (mostly images and the ZIP itself); ZIP text members were separately scanned. This is still not evidence about older installed archives, dynamically composed URLs, private consumers, gateways or real request traffic.

### Real Next.js `next start` response comparison

Both immutable versions passed a production Next.js build and started on **127.0.0.1:31857**. The runner used the real NextAuth JWT encoding and session decoding with a short-lived **synthetic test JWT** and intentionally blank remote Turso configuration (local-only SQLite). This is materially stronger than a bare handler mock but not a genuine user login, browser session or Vercel deployment.

| Actual HTTP request | Old Git source | Patched source | Interpretation |
| --- | --- | --- | --- |
| Unauthenticated POST | 401 / `success:false` | 401 / `success:false` | Preserved |
| Authenticated POST, invalid title | 400 / `success:false` | 400 / `success:false` | Preserved |
| Authenticated POST, invalid platform enum | 400 / `success:false` | 400 / `success:false` | Preserved |
| Authorized valid POST to WeChat | 200 / `success:true`, `data` | 501 / `success:false`, `error` | Deliberately breaking response contract |
| Authorized valid POST to Zhihu | 200 / `success:true`, `data` | 501 / `success:false`, `error` | Deliberately breaking response contract |
| Authorized valid POST to Juejin | 200 / `success:true`, `data` | 501 / `success:false`, `error` | Deliberately breaking response contract |
| Authorized valid POST to Knowledge Planet | 200 / `success:true`, synthetic group `results` | 501 / `success:false`, `error` | Deliberately breaking response contract |
| GET | 405 | 405 | Preserved |
| OPTIONS | 204, `Allow: OPTIONS, POST` | 204, same `Allow` | Preserved |

`Content-Type: application/json` was observed on relevant POST responses. The cross-origin OPTIONS probe with a synthetic `chrome-extension://` Origin received **no Access-Control-Allow-Origin header on either version**. This appears to be a **pre-existing cross-origin limitation of this route**, not a regression introduced by PR #1. Raw Node clients do not enforce browser CORS, so the local probe does not establish whether a browser extension can invoke this API.

### Exact source/runner boundaries

- The runner verified the only three product patch paths: `src/app/api/publish/route.ts`, contract tests, and CI workflow; editor/extension code remains untouched.
- No production database, real account, Vercel project settings, provider token, publishing event, or external service was contacted. Source and ZIP static scans prove only absence of **literal** callers in the inspected artifacts.
- No PACT runtime changes were needed to run this audit. Stage 3 PACT acceptance remains independently backed by [complete:true](https://github.com/ningcol/PACT/actions/runs/38525315177).

### Release gates — technical audit versus actual deployment decision

| Gate | Stage 4 status | Next action outside this GitHub-only test |
| --- | --- | --- |
| Real Next.js unchanged 401/400/405/OPTIONS | **PASS** | Retain as build-time acceptance |
| Four platforms truthfully reject unimplemented provider calls | **PASS** | Keep 501/non-success contract explicit |
| Current tracked + released ZIP literal-caller census | **PASS within static scope** | Do not infer no outside callers |
| Inventory actual production/staging `/api/publish` use | **UNKNOWN — RELEASE HOLD** | Authorized operator reviews aggregate request telemetry and clients across a representative traffic period, without sharing credentials or personal request data |
| External SDK/client handling of new 501 and body | **UNKNOWN — RELEASE HOLD** | Confirm any known integration treats 501 as non-success, has bounded retries, and doesn't falsely mark published |
| Real staging NextAuth/browser extension end-to-end | **NOT RUN — RELEASE HOLD** | Check login/session and editor-to-extension path in approved isolated staging before public deploy |
| Monitoring and rollback plan | **NOT APPROVED — RELEASE HOLD** | Prepare 5xx/501 dashboards, safe abort/canary path; avoid rolling back silently to the old false-success behavior |
| PACT economic/human outcomes | **NOT MEASURED** | Continue #28/#32 real owner observations; CI speed isn't a before/after value result |

**Technical outcome: PASS for isolated compatibility verification. Operational decision: HOLD — do not deploy or merge based on this test alone.**

## Risk disposition and stop rule

Passing local tests and a clean tracked/ZIP caller scan is **insufficient to claim release safety**: unseen third-party clients may depend on HTTP 200, 5xx status may trigger automatic retries/alerts, and there is no accessible production request telemetry in this GitHub-only audit.

**Release gate: HOLD until** the owner reviews external consumers/usage telemetry in their staging/production operations and authorizes the changed response; a canary/rollback strategy exists; NextAuth cookie and browser-extension end-to-end paths are validated on real staging if release is intended. Those steps are outside this disposable read-only audit.

**Stop after independent Stage 4 review.** Keep ziliu PR #1 and PACT PRs #174–#176 Draft/unmerged, and keep this temporary workflow Draft/unmerged. No auto merge, deployment or tag.
