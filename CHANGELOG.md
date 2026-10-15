# Changelog

PACT runtime versions track the distributable framework/runtime files used by `pact init` and `pact upgrade`.

They do **not** version a project's Product Truth, Architecture, Decisions, Owner Profile, or other project-owned seed artifacts.

## Unreleased

No changes yet.

## 0.4.0-rc.1 (release candidate; validation pending) — 2026-10-15

### Semantic Knowledge Gardening

- Audit now surfaces explicitly superseded Decisions as
  `decision_retention_candidates` for **review only**, alongside existing
  active Change, known Drift, and mixed-Rule review targets.
- A replaceable Knowledge Gardening skill guides scoped, evidence-led cleanup
  without automatic Product Truth edits, archive-by-age, or a new CLI/gate.
- Add regressions that ensure active/rejected/archived Decisions are not
  silently reclassified or auto-archived.

### File-scoped Rule authority and mixed-confirmation warnings

- Explicit pending/unconfirmed headings in a `confirmed` Product Rule are
  flagged by `audit` and Discovery instead of silently expanding the whole
  page's normative scope.
- Task Context carries `mixed_authority` candidate metadata; mixed files do
  not populate `applicable_rules` or provide automatically applicable
  verification targets. The warning is intentionally review-only and bounded
  to explicit headings; no new section-level protocol or automatic product
  truth classification is introduced.
- Product guidance recommends separate confirmed/candidate Rule files.

### Verification input origin guard

- `pact run` rejects direct external script/config source paths by default;
  `--allow-external-inputs` records an explicit non-portable exception.
- `--source` records/rechecks repository-relative verification input hashes;
  stale or escaped sources cannot back a valid receipt.
- Medium/high-risk required Evidence cannot rely solely on external-opt-in
  receipts. Legacy v2 receipts remain valid. Source-path checks do **not**
  attest shell expansions, subprocess descendants, interpreters or network
  dependencies, and do not add a portable `--replay` guarantee.

### Prepared-task Evidence helpers

- `pact task draft` creates non-overwriting, structurally incomplete completion
  review templates; it never asserts alignment or completion.
- `pact task verify` runs a concrete check via `pact run` and appends a
  real pass/fail receipt associated with caller-chosen acceptance criteria.
  Stale Task Contracts/Contexts, invalid Evidence and external completion
  destinations block before running.
- Explicit semantic review remains mandatory; no automatic success
  interpretation or new mandatory step was introduced.

### Durable Decision retention and focused retrieval

- Decision Records are now guidance for genuinely long-lived, non-derivable
  engineering rationale, not default notes for every substantial change.
  Plans and progress remain in Change/Task artifacts.
- Generic discovery queries softly downrank decisions marked `archived` or
  `superseded`, without hiding historical records or degrading exact
  ID/title/alias lookups. Rejected alternatives retain their search weight.
  Lifecycle status is still advisory, not proof of current product truth.
- Agent bootstrap no longer recommends a fixed number of query expansions.
  Extra hypotheses are used only when they improve retrieval.
- Focused regressions cover search budgets, history lookups and rejected
  decisions; this change adds no CLI commands, schemas or mandatory gate.

### Explicit Convergence removal disposition (R05)

- `updated` now requires an existing, hash-changed Context artifact; a missing file can no longer pass as an update.
- Add `removed` coverage disposition for an artifact with a prepared content SHA256 that is now truly absent. Recreated files, directories and symlinks are not considered removed.
- A missing prepared artifact cannot be hidden as `aligned`, `stale` or `not-applicable`. Unresolved deletion belongs in blocking `owner-decision`; actual authorization remains a semantic review obligation, not a filesystem claim.
- Include focused regression tests in ordinary CI and the Linux/macOS/Windows × Python 3.11/3.12/3.13 portability/release matrices. The existing Convergence report schema version remains 1.

### Disposable cache validation and atomic publication (PR-08)

- Project Map and Code Map no longer treat a matching format version and source fingerprint as sufficient: cached required structure and indexed path coverage are checked, with Code Map reusing its existing JSON Schema and cross-checking its generated edges against resolved imports. An invalid or incomplete cached map is rebuilt from source instead of creating false empty search results.
- Incremental per-file parse caches now verify a self-integrity SHA256 of their cached parse payload before reuse. Older entries without this digest are safely reparsed once, with no change to source files or public index formats.
- Project Map, Code Map and per-file parse cache writers now publish complete JSON via unique same-directory temporary files, flush/fsync and atomic `os.replace`. A failed publication preserves the prior target; concurrent readers see complete old or new JSON, never a partially-written version from these writers.
- This is disposable cache damage detection, **not** signed attestation, cross-file transactionality, or a guarantee against a writer intentionally changing both cached content and its self-digest. Git HEAD remains descriptive metadata; unchanged source content does not trigger needless rebuilds solely because HEAD moved.

### Upgrade plan freshness and target preservation (PR-07)

- `upgrade --apply` rechecks the current install Manifest and regenerates the source/target plan before staging any replacements; a stale plan aborts rather than applying decisions made against outdated files.
- Planned create, update, refresh-manifest and remove operations recheck their expected target existence/type/content. Destructive operations verify each target again immediately before replacement or removal; unexpected user edits are never treated as safe unchanged framework files.
- Manifest publication detects concurrent changes. Rollback checks the content PACT actually wrote before restoring a file, and avoids replacing externally edited targets or the install Manifest with older backup data. Staged source digests and per-file source metadata are cross-checked with planned hashes.
- Simulated stale-plan, post-backup local edits and rollback tests cover safe refusal and preservation of project-owned changes. These are optimistic checks, not filesystem locks: changes between a final check and an OS write remain a documented TOCTOU limitation.

### Discovery and Markdown Impact correctness (PR-06)

- Code-aware discovery always preserves the strongest direct lexical code match when `--code-limit` leaves only one final result slot; generated import-neighbor context may use only the remaining budget. Existing ranking/scoring, multiple-query fusion, and larger-budget neighbor shares remain unchanged.
- Impact Analysis now resolves explicit Markdown links **relative to their source document's directory**, while links beginning with `/` use the repository root consistently with PACT's Markdown link checker.
- Markdown link fragments/query strings and percent-encoded destination paths are handled before deterministic file matching; links escaping the repository and external URLs cannot silently impersonate a project file.
- `pact.verification` metadata continues to use repository-relative paths. Project Map retains its existing raw-link index format and cache version; the fix is confined to deterministic Impact matching.
- Regression tests cover direct-vs-neighbor limits, nested links, anchors, encoded spaces, root links, false positives, and repository boundaries across the normal CI and 3×3 portability/release matrix.

### Completion Bundle retry path consistency (PR-05)

- `task finish` without an explicit `--bundle` now resolves the persisted `completion_bundle` in the prepared Task Manifest, matching `task status` and machine task observations, instead of blindly resetting to `.pact/completions/<TASK-ID>`.
- Explicit `--bundle` retains precedence, and successful completion persists that selected path for subsequent retries; both custom relative and absolute bundle locations remain supported.
- A malformed stored Bundle path, including explicit `null`, now fails with a clear path error before Final Impact, task state or completion history writes. A missing Bundle field retains the existing default fallback.
- The Convergence `updated` vs. intentionally deleted artifact classification (R05) has not been changed: the present design and schema do not explicitly settle that semantic distinction, so no unreviewed policy was introduced.

### Task state path confinement and completion preflight (PR-04)

- `task prepare`, `task finish`, `task status` and task-backed `eval` reject symlinked, non-directory, or escaped PACT task-state roots instead of resolving an untrusted `.pact/tasks` alias; preparation also validates its completion and temporary state roots before any staging work.
- `task finish` now validates the prepared Task Context repository path, existence and original content digest **before** changed-file attribution, Final Impact publishing or task state writes. A missing, escaped, or modified Context exits with code 2 without recording a completion attempt.
- `task status` and contract-backed `eval` use the same prepared Context checks; the default completion root is guarded on status and finish without changing the existing explicit/custom bundle policy.
- Existing task IDs, normal valid task completion, atomic writes and historical minimal evaluation observations retain their previous behavior. These checks guard preflight boundaries; they do not provide an inter-process lock against a concurrent filesystem adversary.

### Execution pipe and interruption reliability (PR-03)

- The streamed verifier waits for stdout/stderr reader threads using one bounded 3-second drain deadline after its direct child exits, rather than joining indefinitely if a descendant inherited an output handle.
- A direct child exit without output-pipe EOF cannot produce a run receipt: output digests may be incomplete, so `pact run` exits with an execution error instead of claiming a verified pass.
- On an interrupt delivered to PACT alone, direct-child terminate-then-kill behavior is retained and output reader joins cannot block forever; the existing interrupt return code (130) and no-receipt behavior are preserved.
- This change deliberately does not kill arbitrary descendant process trees. Noncooperating descendants may remain running and are outside this direct-child cleanup boundary; verification still fails closed.
- The positive short-lived descendant and both inherited-pipe regressions now run as part of PACT Check and the 3-OS × 3-Python portability/release matrix.

### Contract and acceptance trust fixes (PR-01)

- High-level `task finish` rejects prepared Task Contracts whose bytes no longer match the original digest before task-change/Impact side effects. `task status` and contract-backed `eval --task` reject that drift as well; minimal historical eval observations without a tracked Contract remain readable.
- Acceptance coverage now requires passing `required=true` Evidence claims, closing the optional-claim bypass for medium/high-risk completion while preserving low-risk static-file evidence when legitimately required.
- Duplicate Evidence claim identifiers, Owner acceptance entries outside the Task Contract, and unrelated/unknown evidence references inside an acceptance entry are rejected.
- These checks validate local recorded state; they do not establish remote/tamper-proof attestations when a writer can modify the prepared manifest and its dependent artifacts together.

### Git workspace identity and attribution hardening (PR-02)

- Git working-tree snapshots now reject dirty, uninitialized, moved, or uninspectable tracked submodules rather than assigning the same stable fingerprint to different unverified source states. A clean, initialized submodule remains represented by its Git gitlink object.
- Final task change attribution compares committed and working file state using consistent type, executable-bit and content encodings. It no longer reports a file as changed solely because it was committed and then restored to its original bytes.
- POSIX Git -z filenames preserve literal backslashes instead of converting them to directory separators, preventing path collisions and incorrect generated-state exclusions.
- Git workspace fingerprint domain is now V3. Older V2 run receipts intentionally become stale and must be regenerated under the newer verification rule; existing pre-V3 prepared dirty-file baseline strings remain readable for final change attribution.
- New temporary-Git regression cases also run in the portability/release matrix. The boundary still excludes Git ignored input files, environment variables and remote services from workspace fingerprint guarantees.

Development runtime on `main`: `0.4.0-dev.1`. No `v0.4.0` release has been published by this change.

### Minimal Adoption / Lazy Materialization

- fresh brownfield installs use one compact control-plane surface;
- initial adoption installs only the executable/control-plane nucleus instead of empty Product/Architecture/Decision/Change/Drift/Skill scaffold;
- optional durable knowledge locations may remain absent until real project knowledge needs to be preserved;
- adopted-project Doctor validates the minimal executable nucleus without treating absent lazy knowledge directories as broken;
- the default Agent task trust loop remains in compact `AGENTS.md` / merge guidance, so removing empty Skill scaffold does not weaken Task Contract, Evidence, Convergence, Owner Report, or completion requirements;
- upgrades preserve the compact installed surface without alternate legacy/full profiles;
- existing `AGENTS.md` remains untouched and receives merge guidance under `.pact/`;
- real DouBaoFreeImageGen historical fresh-adoption validation reduced the install from the original 97 managed files to 9 managed files (10 physical files including `.pact/install.json`) after retaining the PACT license under `.pact/LICENSE` while strict Doctor, Status, schema-lint, and code-aware Task Context still passed.

### CI efficiency

- PACT Check remains the single full correctness gate and still runs every unit test;
- the 3×3 Core Matrix now focuses on cross-platform bootstrap/runtime/distribution/stdlib/init/Git-path portability instead of repeating the complete semantic test suite nine times;
- release validation still runs the full unit suite.

### Pre-release simplification

- removed unreleased legacy YAML config/front-matter parsing;
- removed alternate legacy/full install profiles and runtime compatibility shims;
- run receipts now use only the current workspace-bound format;
- prepared tasks must carry the current Context SHA contract;
- upgrade tests now cover current-runtime update/conflict/rollback/seed safety instead of unreleased migration paths.

### Release / distribution hardening

- adopted projects now retain Apache-2.0 at `.pact/LICENSE` as a framework-managed install artifact, so bootstrap/init/upgrade preserve the license without overwriting the host repository's root license;
- PACT is now licensed under Apache License 2.0; the repository and formal release assets include `LICENSE`, and `SHA256SUMS` covers the license alongside the executable release artifacts;
- bootstrap ZIP extraction now limits archive file count, per-file expanded size, total expanded size, local archive size, and suspicious compression ratios before extraction;
- tag releases are blocked on the same 3 OS × 3 Python portability coverage used for normal development;
- normal PR CI and tag publication now use the same release-asset builder and run a fresh offline bootstrap smoke against the exact `pact-bootstrap.py` / `pact.pyz` / `SHA256SUMS` package before publication;
- prerelease version suffixes publish as GitHub prereleases instead of stable releases while exact tag/VERSION equality remains required;
- non-Git high-level task completion now surfaces that exact changed-file attribution is unavailable instead of silently providing a weaker guarantee;
- stale version-specific Python requirement messages were replaced with the protocol-level Python 3.11+ requirement.

### Reliability hardening

- Doctor/Status/Version/Upgrade now share the canonical install-manifest reader and filesystem confinement rules, eliminating divergent trust decisions for unsafe tracked paths or symlinked provenance;
- maintained GitHub Actions workflows and the downstream CI template now pin Node 24-capable `actions/checkout@v7.0.1` and `actions/setup-python@v7.0.0`, removing the Node 20 deprecation path before formal release;
- external pilot workflows now pin Node 24-capable `actions/upload-artifact@v7.0.1`, completing the maintained JavaScript-action runtime migration away from deprecated Node 20 actions;
- prepared Task Contract/Context/Final Impact paths are now resolved through one repository-confinement primitive across finish/status/eval, preventing traversal or symlink escapes while preserving external custom completion bundles;
- `task finish` now validates prepared manifest path/digest/risk/workspace-baseline fields before any workspace, Impact, or completion-history side effects, so malformed durable task state fails closed at the lifecycle boundary;
- `task status` now validates manifest path fields and the prepared Task Contract before reporting recovery state, so malformed/missing durable task metadata fails closed instead of becoming a traceback or a misleading zero-acceptance task;
- `task status` now reports completion files from the task manifest's actual `completion_bundle`, including custom relative/absolute bundle paths, instead of always assuming the default `.pact/completions/<TASK-ID>` location;
- `task finish` now atomically publishes completion-attempt history and stages Final Impact before replacing its canonical path, so persistence failures preserve prior valid derived state and do not follow leaf symlinks;
- `pact init --apply` now rejects parent-directory symlink escapes and treats existing leaf symlinks, including broken symlinks, as occupied paths under no-overwrite semantics;
- `pact upgrade` now applies the same repository confinement during planning/provenance reads, rejecting symlinked install manifests and framework-managed leaf symlinks before hashing or mutation;
- non-Git workspace fingerprints now include directory symlink identity/target without traversing linked directories, so retargeting invalidates workspace-bound Evidence;
- Project Map / Code Map file enumeration now refuses file symlinks whose resolved content escapes the repository root, preventing external files from being indexed as project knowledge;
- `pact init --apply` now stages all would-be-created files before target mutation, publishes them atomically, commits install provenance last, and rolls back transaction-created files/manifest state on failure;
- Project Map and Code Map freshness fingerprints now include source-content SHA256 instead of relying on size/mtime;
- per-file parse cache reuse is content-hash bound, so equal-size content replacements with preserved mtimes are reparsed;
- `pact run` streams stdout/stderr while hashing instead of retaining full command output in memory;
- validated `pact run` receipts are staged in the destination directory, fsynced, and atomically published so interrupted/failed writes do not leave partial receipts or follow a pre-existing leaf symlink;
- interrupted `pact run` execution now terminates its direct verification child with bounded terminate/kill cleanup, returns controlled status 130, and avoids publishing a receipt or leaking a Python traceback;
- Git workspace fingerprint V2 hashes staged index state, current unstaged file state, and untracked contents instead of buffering full binary patches;
- large-output and large-binary workspace regressions now run in the cross-platform portability matrix.

### Trust hardening batch

- prepared task risk is bound through Context/Evidence/completion so a high-risk task cannot be downgraded by editing Evidence risk;
- task IDs use one safe path-segment protocol and are confined before task/run/eval filesystem access;
- run receipts enforce exit-code/status consistency;
- local receipt terminology distinguishes execution-backed/workspace-bound provenance from tamper-proof attestation; GitHub Actions fields are CI metadata only;
- malformed or unsafe install manifests fail closed;
- locally modified framework-managed files block automatic upgrade instead of leaving stale framework ownership;
- high-level task preparation runs deterministic repository checks before Context creation;
- Owner verification claims cannot expand referenced Evidence claims, and Convergence Evidence IDs must resolve.

### Evidence trust hardening

- repository file provenance is static/source evidence and no longer counts as executed verification;
- medium/high required pass claims need a passing `pact-run` receipt bound to the current workspace;
- Evidence refs are confined to the repository root after path/symlink resolution;
- low-risk claims may still use static repository evidence when that level of proof is appropriate.

### Daily status / readiness UX

- normal `status` treats pending repository-wide baseline review as advisory instead of permanent warning state;
- `readiness --require-ready` remains the explicit opt-in full-baseline governance gate;
- malformed/invalid baseline readiness now blocks `status` rather than being silently downgraded;
- `status` reuses its Doctor result when evaluating readiness instead of invoking Doctor twice;
- Doctor persists the freshness-aware Project Map used for its check, and `status` reuses that same map/check result for the audit summary instead of rescanning the repository.

### Task-state UX / atomicity

- fresh init uses nested `.pact/.gitignore` instead of touching the project root `.gitignore`;
- cache/tasks/runs/completions/tmp are explicit local generated control-plane state;
- `task prepare` stages all preparation artifacts under `.pact/tmp` and atomically publishes the task only after Context/Impact succeed;
- task/completion state IDs must resolve to real direct children rather than symlink/junction aliases;
- canonical `task.json` reads reject leaf symlinks, and task manifest updates are staged, fsynced, and atomically replaced so interrupted finish writes preserve the previous recoverable state;
- failed preparation leaves no half-created visible task;
- `--force` preserves the old task/completion until replacement preparation succeeds, then invalidates stale completion state.

### Retrieval / Context

- high-level `task prepare` now preserves the task wording as primary retrieval intent and treats repeatable `--query` values as additional search hypotheses, matching recommended `inspect` behavior;
- task-primary Context selection now preserves the files selected by the owner/task wording under the same count/token budgets before supplemental Agent queries fill remaining capacity; peer low-level multi-query fusion remains symmetric;
- task-primary Context may expose up to five metadata-only `code_candidate_hints` for high-ranked fallback code paths that did not fit the selected canonical Context; hints do not change selected artifacts, token accounting, or completion coverage;
- Python Code Map structured symbols now include direct class methods (without recursively indexing local nested functions), and generated Code Map/parse-cache versions are bumped so existing caches rebuild under the new retrieval semantics;
- Code Map adds a bounded `generic-lexical` fallback for Go, Swift, Kotlin, Java, Rust, C/C++, C#, Ruby, and PHP;
- generic fallback stores at most 256 lexical identifiers per file and creates no import/AST edges;
- generic identifier matches rank below structured top-level symbols and remain derived search evidence only;
- recommended `inspect` now accepts repeatable retrieval queries and forwards the same normalized query set to explanation knowledge and code discovery;
- `inspect --code-limit` provides a hard final code-candidate budget;
- Explanation Packets record the actual retrieval query set used;
- inspect/explain now propagate indexing/discovery failures instead of downgrading nonzero JSON child exits to empty results;
- `code_limit` is now a true final output budget for both single- and multi-query retrieval;
- query-diverse fusion prevents specialized query intents from being silently starved when the budget permits representation;
- historical retrieval comparison now enforces equal final code budgets across direct/expanded/multi-query modes;
- Context adds a soft risk-adaptive estimated materialization-token budget on top of hard artifact-count limits;
- token estimates use deterministic repository file size (`UTF-8 bytes / 4`) and never materialize file bodies into the Context envelope;
- confirmed Product Rules and implemented Decisions may explicitly exceed the soft token budget instead of being silently dropped;
- `discover`, `context`, and `task prepare` accept repeatable discovery queries;
- multi-query retrieval uses deterministic Reciprocal Rank Fusion across independent lexical/graph result lists;
- fused multi-query Context is capped by the existing risk-adaptive knowledge/code limits;
- Task Context records the actual `discovery_queries` used;
- Agent guidance now treats expanded queries as search hypotheses rather than project truth;
- the historical brownfield benchmark compares direct, single-expanded, and fused multi-query retrieval.

### Compact Runtime

- adopted projects use one `.pact/pact.pyz` runtime behind the stable repository-root `pact.py` entry point;
- framework JSON schemas are embedded in `pact.pyz` and no longer copied into adopted projects;
- compact runtime schema resources are authoritative over preserved obsolete local schema files;
- `schema-lint` validates the full embedded protocol set in compact installs;
- safe upgrade removes unchanged obsolete source-runtime/schema files with rollback, while preserving local modifications.

### Convergence Trust

- prepared tasks record a Git-aware workspace baseline without requiring a clean worktree;
- `task finish` derives the files whose final content changed relative to preparation, excluding generated PACT state;
- actual task-changed files automatically feed a final Impact report;
- Convergence `change_coverage` must review every task-changed path; missing/duplicate/stale coverage blocks completion;
- pre-existing dirty files are not attributed to the task unless their content changed after preparation;
- prepared Task Contexts now carry SHA256 binding into high-level completion;
- selected knowledge artifacts carry prepared content fingerprints when available;
- Convergence Reports can explicitly dispose every Task Context knowledge artifact;
- `task finish` blocks silent Context omission and stale prepared Context reuse;
- `updated` artifact dispositions are rejected when the prepared artifact content did not actually change;
- machine task observations record Convergence coverage blockers.

### Evaluation / proof of value

- machine task observations now include Context token-budget pressure, task changed-file attribution/final Impact, and changed-file coverage blockers;
- `pact eval --all-tasks --json` derives all valid local task observations and summarizes machine-only trust/context/verification metrics overall and by risk;
- malformed local task state is reported explicitly in the machine summary instead of being silently omitted;
- machine summaries deliberately do not infer owner interactions, comprehension, subjective overload, PACT overhead, or a single PACT score;
- high-level `task finish` persists completion-attempt outcomes for later evaluation;
- `pact eval --task <TASK-ID>` derives machine-observed task metrics without fabricating human-interaction values;
- added a real historical brownfield Context-retrieval benchmark using owner-maintained repositories;
- benchmark compares direct owner-language retrieval with Agent-expanded queries and treats low recall as data, not a CI failure.

### Owner Trust Loop

- `task prepare` now persists a machine-readable Task Contract;
- repeatable acceptance criteria receive stable `AC-*` IDs;
- Evidence claims can bind directly to acceptance criteria;
- `task finish` blocks completion when acceptance is unverified or omitted from the Owner Report;
- task-scoped constraints and acceptance coverage are visible through the high-level task surface.

## 0.3.0 — 2026-09-18

PACT 0.3 focuses on reducing adoption friction and hardening the trust boundary between AI claims and real project state.

### Zero-dependency runtime

- removed PyYAML and jsonschema runtime dependencies;
- removed `scripts/pact/requirements.txt`;
- PACT core now requires only Python 3.11+ standard library;
- added internal validation for the JSON Schema subset used by PACT;
- added repository-root `pact.py` convenience entry point.

### TOML and compatibility

- new project config, baseline, and fitness files use TOML;
- new PACT Markdown artifacts use TOML front matter;
- PACT 0.2-generated YAML remains readable through a restricted compatibility parser;
- legacy Owner config and baseline state are normalized during 0.3 use;
- Domain aliases are now machine-readable and actually consumed by Discovery;
- Decision template is now a real machine-readable PACT Decision artifact;
- readiness now includes explicit `agent_bootstrap` review.

### Trusted completion

- added `pact run` command receipts with real argv, exit code, timestamps, Git state, and stdout/stderr hashes;
- Evidence now carries explicit provenance;
- medium/high-risk required pass claims need machine-backed evidence;
- Owner Reports cannot describe failed/unverified Evidence as verified;
- Evidence, Convergence, and Owner Report bind to the same task ID;
- added `pact complete` to validate the full completion bundle;
- high-risk completion blocks unresolved Evidence limitations and non-aligned Convergence.

### Risk and discovery freshness

- low/medium/high risk now changes default Context depth and code expansion;
- medium/high Impact Analysis enables code-neighbor analysis by default;
- Project Map and Code Map now use source fingerprints and rebuild only when stale;
- Explain/Context/Impact share freshness-aware caches;
- generated code relationships expose confidence instead of pretending all import resolution is equally certain.

### Deployment

- added stdlib-only single-file `bootstrap.py` for init/upgrade without cloning PACT;
- bootstrap supports pinned GitHub refs/commits and optional archive SHA256 verification;
- bootstrap rejects archive traversal and symlink entries;
- fixed mixed-version `init` behavior: tracked projects on another runtime must use upgrade;
- legacy YAML project seeds are preserved rather than shadowed by default TOML files;
- upgrades now stage/verify replacements, back up targets, atomically replace files, and rollback files + install manifest after apply/validation failure;
- strict Doctor validates framework-owned file hashes against install provenance.

### Still intentionally open

- real brownfield pilot (#28);
- evaluation using observed real-project task data (#32).

These remain open because framework implementation is not evidence that PACT improves real project work.

## 0.2.0 — 2026-09-18

### Added

- tracked installation provenance in `.pact/install.json`;
- transactional, conflict-aware framework upgrades;
- explicit framework-managed vs project-seed ownership;
- runtime version inspection;
- generated Python / JavaScript / TypeScript / Vue code maps;
- opt-in code-aware Project Discovery;
- opt-in code-aware Task Context;
- import-neighbor Impact candidates;
- pluggable project-owned Architecture Fitness Functions;
- optional real-task Pilot Evaluation records and summaries.

### Changed

- Context Resolution promotes only confirmed Product Rules and implemented Decisions into authoritative task constraints;
- Doctor validates install provenance and project Fitness configuration without implicitly running architecture checks;
- project CI can run Fitness explicitly while keeping application build/test/E2E commands project-owned;
- code relationships remain generated/disposable evidence rather than project truth.

### Safety

- project seed files are never silently overwritten by runtime upgrade;
- local/upstream conflicts in framework-managed files block automatic upgrade before any partial update;
- unresolved path aliases/framework magic are reported as unresolved rather than guessed;
- structural import relationships are treated as candidate behavioral impact, not hard product truth.

## 0.1.0 — 2026-09-18

Initial executable PACT v1 foundation:

- Governance / Truth Ownership / Decision Authority;
- brownfield-safe initialization;
- explicit baseline readiness;
- Owner Profile and Human Interface contracts;
- Project Discovery and Project Explanation;
- Context Resolution and conservative Impact Analysis;
- Evidence Receipts and evidence-backed Owner Reports;
- Convergence Reports;
- deterministic artifact/reference/lifecycle checks;
- Doctor / Audit;
- opt-in project GitHub Actions integration.
