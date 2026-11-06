# Unified knowledge archive: isolated real-source rehearsal

Date: 2026-11-06. Reproduction: [fixed pilot script](../../scripts/benchmark/knowledge_archive_pilot.py).
This is an engineering rehearsal, not an independent Owner/Agent trial, production acceptance or whole-project migration.

## Inputs and isolation

The local `gaokao_zx` source is pinned to `d7f6bdf014ac67b99666f322f872e3b16524da8c`.
The script uses a shallow `file://` clone with `--no-hardlinks`, no shared object alternates and a detached checkout. Source Git commands are read-only with optional locks disabled. It never adds a worktree to the original repository, commits, stages, pushes, deploys, copies ignored environment files, starts the application or changes personal configuration.

The successful run is retained locally at `.pact/tmp/knowledge-archive-pilot-20261106-r7/`. Its `result.json`, `clone-tracked.patch`, `clone-diff-stat.txt`, explicit untracked-path/hash inventory and complete `checkout/` permit review without a commit. The two independent branch worktrees and synthetic fixtures are retained too. Reusing an existing output directory fails before any Git command; interrupted trees are never erased or replayed.

Original HEAD, porcelain status, tracked binary diff and four declared source-file hashes are compared before and after. This is a scoped state observation, not a claim to have hashed all ignored/untracked files or attributed concurrent authorship. The existing dirty/untracked plans were excluded from the clone and left in the source. Original credentials, data, browser sessions and running services were not used.

```bash
python3 scripts/benchmark/knowledge_archive_pilot.py \
  --source /path/to/gaokao_zx \
  --revision d7f6bdf014ac67b99666f322f872e3b16524da8c \
  --output .pact/tmp/a-new-knowledge-pilot-run \
  --project-python /path/to/gaokao_zx/backend/venv/bin/python \
  --upgrade
```

The source must already have the pinned HEAD. No network repository, global interpreter configuration or project environment is provisioned. The approved project interpreter is used only for its document guard. The script is deliberately one frozen source/mapping experiment, with no migration protocol, generic executor, journal or recovery feature.

## Declared migration and evidence

One independent, code-derived explanation was moved:

| Disposition | Source / target | Authority treatment |
| --- | --- | --- |
| Migrated | `docs/01-业务说明书/03-考制与填报形态标准模型/考制模型-3+3综合改革体系.md` → `docs/product/specs/考制模型-3+3综合改革体系.md` | Ordinary Markdown before and after; no `spec` type, stable ID or confirmed status added |
| Held whole | `docs/01-业务说明书/02-招考通用引擎与基准流程/志愿方案管理、预览与导出规范.md` | Current acceptance and historical stage evidence remain byte-identical; whole-file cutover was outside this review |
| Reused unchanged | `docs/product/rules/result-semantics.md` | Existing confirmed Rule and its source evidence retained |
| Reused unchanged | `docs/product/rules/candidates/reference-recommendation.md` | Existing candidate stays candidate |

Before retiring the old explanation, the clone successfully read its exact original bytes with `git show <pinned-revision>:<source-path>`. The source SHA256 is `aca48d2418f6f6a926008ced0047d7a27c5b1d67353b6492cd8522a60a9e9c6f`. Only seven explicit relative-link substitutions change the transferred document; all other prose, conditions, exceptions, historical code baselines and evidence limitations match. The old path is an updated short redirect with neither a stable ID nor a second business body. It is not declared removed.

Six declared incoming links were individually mapped to the new body. Their surrounding source prose is unchanged. The domain router links to the ordinary explanation without confirming it. The shared product and business entry pages are updated last. The existing Change mechanism records migration scope, source revision, hashes, target, held/excluded material and verification boundaries inside the clone; no permanent knowledge ledger or per-plan summary is created.

File-target checks cover the eleven changed Markdown files. The transferred explanation's single fragment is checked against the actual explicit alias in its unchanged target. The frozen six incoming links have no fragments. These checks do **not** cover every repository link, special syntax, host import or rendering implementation. Unknown forms cause this fixed pilot to stop for review rather than silently rewrite them.

## Source-backed usability review

Nine fixed questions are labelled from the original sources, then checked against the migrated or retained bodies. The same nine pass before and after, with their artifact type and lifecycle preserved. They cover subject-selection scope, an explicit provincial exception, source-parser limitations, batch/filling-form independence, historical baseline evidence, confirmed result semantics, candidate status and the distinction between historical stage records and current acceptance.

The author also compared the complete original and transferred explanation, including its conditions and caveats, rather than relying only on successful string probes. The independent engineering reviewer separately verified the original-plus-link-substitutions relationship, the six incoming-link changes and unchanged held/formal/candidate bytes. This is source-preservation review; neither reviewer reconfirmed education policy or represented the project Owner.

The automated probes are exact source-text/status checks, not independent semantic oracles. Cold knowledge discovery recalls the original source; post-migration discovery recalls the new target. The preferred navigation continues to reach one body directly; the compatibility redirect remains available for undeclared external consumers. There is no measured long-term retrieval, comprehension or Agent-obedience improvement claim.

An initial negative run exposed an important review error: a historical “not implemented / not verified” label had been mistaken for current state, although the pinned source explicitly records final acceptance. The oracle was corrected to preserve this distinction. The large mixed-history file was held because its whole-file cutover was not reviewed; it is **not** reported as a newly discovered unresolved business dispute.

## Sequential and independent-plan rehearsals

Plan A performs the one declared migration. Plan B reads/references the same target and uses existing `knowledge_retention: none`; it creates zero additional knowledge bodies. A patched subprocess boundary proves this ordinary no-output review invokes neither Git nor retrieval. Candidate assistance is skipped with zero source reads and no persisted register.

Two real Git branch worktrees are created from the isolated clone's pinned base, never from the original repository. They emit explicitly synthetic candidate policies with different IDs. Their uncommitted outputs are integrated by an explicit path copy into the local final-tree fixture, then passed to the same bounded helper used by `task assist`:

- Different titles and paraphrased bodies for the same synthetic scope produce an advisory review candidate.
- Identical titles with different year/role scopes remain separate, byte-identical candidate files. A hint is not a merge, deletion, rejection or confirmation.
- The helper reports source identity, status, explicit scope, hint reason and incomplete coverage.
- A source changed after Context preparation cannot pass an `aligned` Convergence claim; the existing source binding rejects it.

No commits or Git merge commits are created. This demonstrates independent workspace output and final-tree review, not committed-branch merge behavior, independent Agent judgment or actual business approval.

A separate tiny manual-procedure fixture has one synthetic known Drift associated with two conflicting source files and two plans. Both complete source files, including their non-conflicting chapters, stay unchanged; the real independent explanation can still migrate. A source lacking a retrievable Git version is deliberately not retired. The explicit local closure check rejects the open record. These are authored demonstrations of the documented manual choices, **not** automatic conflict classification, duplicate-dispute discovery, user consent or a migration executor. No real Owner choice or new business Decision is fabricated. Decided-versus-implemented closure constraints are exercised by the separate Drift fixture suite, not inferred from this source migration.

## Verification and remaining boundaries

The isolated project's PACT artifact check passes. Its stricter project knowledge guard reports the same three findings before and after: references to ignored `backend/venv` paths omitted from the credential-free clone. There are no new findings. The report preserves the nonzero guard result; it does not manufacture a virtual environment or claim the entire project guard passed.

The authorized framework upgrade succeeds inside the clone. All 230 project-owned Markdown files in the declared snapshot retain their pre-upgrade bytes, including the migrated explanation and existing decision/confirmation sources. The migrated business body is absent from `.pact/install.json` framework ownership. The snapshot includes real project knowledge even though the clone's parent path contains `.pact/tmp`; a regression test prevents an empty preservation corpus. The upgrade's advisory project-entry review notice remains visible. Framework installation, project routing, actual host loading, behavioral obedience and write protection remain separate claims.

The source HEAD/status/diff and declared source hashes remain unchanged. The fixed pilot and safety fixtures pass. Application, browser, database, official-policy revalidation, production, independent Owner acceptance and cross-OS execution are not performed by this pilot. Ordinary task completion and PACT `task finish` are not claimed for the cloned project's rehearsals. Host protection is reported separately in the [protection coverage report](framework-protection-2026-11-06.md).

## Cost and promotion boundary

`result.json` records actual total elapsed time, subprocess calls, explicit script read bytes, cold knowledge discovery, bounded candidate reads/comparisons and ordinary `none` time. These are instrumented scopes, not all OS/process I/O or human reading effort; helper counters are separate from script counters. The real candidate inventory hits the per-file budget on two linked large documents and reports truncation/unread sources. It does not claim there are no duplicates outside its read set.

| Successful local run measure | Observation |
| --- | --- |
| Complete clone/migration/branches/guards/upgrade rehearsal | 24.416 s; 27 instrumented subprocess calls |
| Explicit script reads | 28 reads; 743,459 bytes, excluding helper/internal-process reads |
| Cold knowledge discovery | 4.803 s; one top-level invocation; code search not requested |
| B ordinary `none` | 0.000862 s; zero additional subprocesses, source reads or knowledge bodies |
| Bounded candidate assistance | 0.030335 s; 12 files / 97,367 bytes; 11 comparisons; no retrieval or repository scan |
| Candidate coverage | Truncated: two directly linked documents exceed the per-file budget; reported unread |
| Framework upgrade preservation | 230 project Markdown files unchanged; migrated body absent from framework manifest |

These single-machine timings are observations, not a performance threshold or controlled before/after benchmark. The full cold-start byte count is unknown because internal discovery/OS reads were not instrumented.

The migration creates one new file for one existing body, retires the old body to a short redirect and creates one scoped Change; B adds no body. Synthetic negative candidates live only in the dedicated test worktrees/fixture. The local run includes clone/upgrade/guard costs, which are not imposed on ordinary maintenance.

The fixture study supports the bounded guidance, local closure interface and optional reuse hints. It does not establish the value of a generic multi-file migration executor. Full-project cutover, real disputed-business decisions, longer independent Agent trials and untested host/cross-platform claims remain separate work. Stop promotion if preservation, status separation, scope handling or ordinary-task cost regresses; no automatic release is performed here.
