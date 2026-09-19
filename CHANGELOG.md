# Changelog

PACT runtime versions track the distributable framework/runtime files used by `pact init` and `pact upgrade`.

They do **not** version a project's Product Truth, Architecture, Decisions, Owner Profile, or other project-owned seed artifacts.

## Unreleased

### Minimal Adoption / Lazy Materialization

- fresh brownfield installs use one compact control-plane surface;
- initial adoption installs only the executable/control-plane nucleus instead of empty Product/Architecture/Decision/Change/Drift/Skill scaffold;
- optional durable knowledge locations may remain absent until real project knowledge needs to be preserved;
- adopted-project Doctor validates the minimal executable nucleus without treating absent lazy knowledge directories as broken;
- the default Agent task trust loop remains in compact `AGENTS.md` / merge guidance, so removing empty Skill scaffold does not weaken Task Contract, Evidence, Convergence, Owner Report, or completion requirements;
- upgrades preserve the compact installed surface without alternate legacy/full profiles;
- existing `AGENTS.md` remains untouched and receives merge guidance under `.pact/`;
- real DouBaoFreeImageGen historical fresh-adoption validation reduced the install from the original 97 managed files to 8 managed files (9 physical files including `.pact/install.json`) while strict Doctor, Status, schema-lint, and code-aware Task Context still passed.

### Pre-release simplification

- removed unreleased legacy YAML config/front-matter parsing;
- removed alternate legacy/full install profiles and runtime compatibility shims;
- run receipts now use only the current workspace-bound format;
- prepared tasks must carry the current Context SHA contract;
- upgrade tests now cover current-runtime update/conflict/rollback/seed safety instead of unreleased migration paths.

### Evidence trust hardening

- repository file provenance is static/source evidence and no longer counts as executed verification;
- medium/high required pass claims need a passing `pact-run` receipt bound to the current workspace;
- Evidence refs are confined to the repository root after path/symlink resolution;
- low-risk claims may still use static repository evidence when that level of proof is appropriate.

### Daily status / readiness UX

- normal `status` treats pending repository-wide baseline review as advisory instead of permanent warning state;
- `readiness --require-ready` remains the explicit opt-in full-baseline governance gate;
- malformed/invalid baseline readiness now blocks `status` rather than being silently downgraded;
- `status` reuses its Doctor result when evaluating readiness instead of invoking Doctor twice.

### Retrieval / Context

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

- prepared Task Contexts now carry SHA256 binding into high-level completion;
- selected knowledge artifacts carry prepared content fingerprints when available;
- Convergence Reports can explicitly dispose every Task Context knowledge artifact;
- `task finish` blocks silent Context omission and stale prepared Context reuse;
- `updated` artifact dispositions are rejected when the prepared artifact content did not actually change;
- machine task observations record Convergence coverage blockers.

### Evaluation / proof of value

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
