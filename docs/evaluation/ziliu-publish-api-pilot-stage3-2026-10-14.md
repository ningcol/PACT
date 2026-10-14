# ziliu Publishing API Pilot — Stage 3 RED/GREEN and PACT Completion (2026-10-14)

**Scope:** Owner-approved, bounded correctness fix: keep authenticated server `POST /api/publish`, but no longer claim actual publication from unimplemented platform handlers. This is a real source change with two Draft PRs; neither repository main has been modified. This note is NOT a release or a user-efficiency result.

## Immutable references

| Artifact | Exact reference |
| --- | --- |
| ziliu pre-change source | `61af579266848ee50d12a0b658d1e32a49dabfde` |
| ziliu proposed correction | `6463b2a315d3619f8427c8ff83c1fe57e0385322` |
| ziliu code and tests | [Draft PR #1](https://github.com/ningcol/ziliu/pull/1) |
| PACT framework | main `28d8a77e8bbc4fca6db320b4e1a95ac62079385b` |
| PACT ephemeral lifecycle | [Draft PR #176](https://github.com/ningcol/PACT/pull/176) |
| Previous owner-value baseline / knowledge | [Draft PR #174](https://github.com/ningcol/PACT/pull/174), [Draft PR #175](https://github.com/ningcol/PACT/pull/175) |

## 1. Source-level call chain and approved decision

At the frozen base SHA, the NextAuth-protected server route parses a Zod request, dispatches to server-local stub functions for WeChat, Zhihu, Juejin and Knowledge Planet, then returns outer `success:true`. The three TODO providers return synthetic success; the Knowledge Planet branch constructs group success and a URL without provider acknowledgement. The editor-side `platform-preview.tsx` separately copies data to clipboard, opens the third-party website and interacts with the browser extension. Earlier Stage 2 audited 132 tracked JS/TS/Markdown sources without finding a literal `/api/publish` consumer; external/dynamic consumers and actual production traffic remain **unknown**.

The accepted scope is **Option A** of Stage 2: preserve the route and its authentication/validation, but return a truthful non-success for valid requests until a separately scoped provider integration exists. The correction returns HTTP **501** with `success:false`, an explanatory `error`, and **no fabricated provider result**. Invalid requests still fail Zod with 400; unauthenticated requests still return 401. The release/compatibility choice for outside callers remains a deployment concern, not permission to remove this API or auto-publish.

Exact product diff includes **only three paths**: `src/app/api/publish/route.ts`, new `scripts/tests/publish-api-contract.test.cjs`, and new `.github/workflows/publish-api-contract.yml`. No editor/extension file, data migration, credential, provider integration, or business database change.

## 2. Business RED/GREEN acceptance (actual runner evidence)

[Final ziliu PR CI run](https://github.com/ningcol/ziliu/actions/runs/38524211329): **completed/success** on exact fix SHA.

| Check | Frozen old source (RED) | Proposed source (GREEN) |
| --- | --- | --- |
| Auth/validation (401/400) | 4 pass | 4 pass |
| Four provider-placeholder success checks | 4 fail as expected | 4 pass |
| Knowledge Planet missing-group non-success | 1 fail as expected | 1 pass |
| Local loopback HTTP response using controlled NextAuth stub | 1 fail as expected | 1 pass |
| Total | **4 pass, 6 fail** | **10 pass, 0 fail** |

The test loads the **actual TypeScript handler source**, transpiles it using the project's locked TypeScript compiler, uses the real NextRequest/NextResponse and Zod implementations, and replaces only the NextAuth session dependency. The local loopback bridge sends a real HTTP request over `127.0.0.1` into that controlled handler. This is not the full deployed Next.js router, not genuine NextAuth login, and not platform E2E. Network-provider requests are not made.

`npm ci --ignore-scripts --no-audit --no-fund`, `npx tsc --noEmit`, and `npm run build` all passed with a synthetic CI-only session secret and local SQLite setting. Installation scripts are disabled to avoid repository hook side effects. **Build PASS does not mean any third-party article was published.**

## 3. PACT medium-risk trust-loop result

[Successful isolated PACT completion workflow](https://github.com/ningcol/PACT/actions/runs/38525315177) cloned the two frozen ziliu SHAs, installed current PACT into a disposable local checkout, created candidate/proposed/current/known project knowledge, committed that local-only bootstrap, prepared a Task Contract and then applied the **exact** three-path source patch. It executed four PACT workspace-bound `run` receipts for source scope, 10 contract tests, TypeScript and build.

| Machine observation | Verified result |
| --- | --- |
| Prepared task | `REAL-ZILIU-PUBLISH-FIX-001`, risk medium |
| Acceptance criteria | **4**, including one explicit constraint |
| Task acceptance | **4/4** Evidence-backed and Owner-Report-covered |
| Selected Context | **6 knowledge artifacts**, **12 code artifacts** |
| Context estimated selected tokens | **31,646** (medium-risk limit 40,000) |
| Target route in Context | **Materialized** for this task wording; also independently inspected |
| Convergence selected knowledge coverage | **6/6**, aligned |
| Task changed-path attribution | **3/3**, exactly route/test/CI |
| PACT run receipts bound to current workspace | **4** |
| Final Impact | Generated |
| `task finish` | **complete:true**, Convergence aligned, no trust warnings |
| `pact eval --task` | Successfully executed; task completed |

The initial Stage 3 PACT trial failed while constructing Evidence because its script incorrectly assumed **three** acceptance criteria. The actual prepared Task Contract also counts `--constraint` as **AC-4**. The harness was corrected to read all acceptance IDs/kinds from the real contract and bind each to passing run-backed Evidence. The corrected isolated workflow passed; the original failed run remains visible in the PR's CI history. This is **a pilot harness defect, not a PACT runtime defect**. Avoid hardcoded acceptance numbering in later pilots.

Stage 2 had identified a separate Context-quality limitation: under its original task wording, the target route was relegated to fallback hint #2 rather than selected among 12 code files. The Stage 3 wording/query produced a direct materialized route and explicit inspection. This result does not prove recall is universally reliable or that unattended Agents would always follow fallback hints.

## 4. Independent-review boundaries

- The user authorized the bounded technical correction, **not** real provider integrations, deletion of the API, or automatic release. The candidate Product Rule and proposed Decision created in disposable PACT remained non-authoritative; the prepared Task Contract carried the task-scoped intent.
- The new non-success response is a **breaking contract change for any unobserved caller that relied on synthetic `success:true`**. Source caller search cannot rule out deployed/remote consumers. A production release requires separate compatibility/release review.
- No real provider delivery, provider credentials, production authentication session, external publication, browser E2E, or live production database operations were executed.
- Owner comprehension, clarification rounds, real interruptions, relative time saved, and additional PACT process cost remain **NOT MEASURED**; CI durations alone are not a controlled value comparison.
- These facts validate the exact API correction and PACT machine loop; they are not claims about PACT's general economic or human value.

**Stage 3 result:** implementation and targeted regressions **PASS**; PACT evidence-backed lifecycle **PASS** on immutable commits. **Stop after independent review**, leave both PRs Draft/unmerged, no release/tag/deployment. Track human and external-client limits separately under PACT #28/#32.
