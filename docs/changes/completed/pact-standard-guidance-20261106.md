+++
[pact]
type = "change"
status = "completed"
+++

# Version-matched standard agent guidance

The Owner authorized this implementation on 2026-11-06 after parallel research
and evaluation. Standard instructions currently live in generated project-owned
guides. Those guides are absent from the upgrader's desired source entries and
lack a source hash, so normal seed-update notices cannot alert their owners.
Projects must otherwise keep reconciling copied standard procedures manually.

## Intended outcome and scope

- Supply one standard instruction source inside the existing compact runtime,
  with a bounded, read-only `guidance` command and content identity.
- Generate stable short entries; preserve existing project guides, custom
  READMEs, knowledge homes, stricter permissions and checks.
- Notify legacy/indirect entry owners to review routing without overwriting,
  appending, or claiming that a host actually loaded the new instructions.
- Keep standard content availability, static entry references, actual session
  loading, behavioral compliance and OS write protection distinct.
- Retain existing upgrade transactions, evidence requirements and runtime
  dependencies. No plugin marketplace, generic override engine, new approval
  register, automatic host policy edits or per-task completion scan is added.

The new read primitive is needed because existing `init` creates project files,
`doctor` checks foundation and `inspect` searches project knowledge; none exposes
the exact standard instructions shipped with the running archive. Standard
instructions remain about the same size as the previous copied guide. The short
entry is read once per session and after upgrades; no measured reduction in
Agent overhead or increase in obedience is claimed before a real-host pilot.

## Verification and review

Use temporary source/installed/legacy upgrade fixtures to check content identity,
read-only behavior, preservation, idempotence, warning boundaries and rollback.
Run required schema/workflow/check/unittest gates and independent code review.
An isolated gaokao_zx-shaped fixture may copy only its agent-entry documents;
do not upgrade or modify that project, execute its tests, or change host policy.

## Delivered behavior

`guidance.py` owns standard instructions, the minimal project entry and bootstrap
advice. The existing builder includes it in the same pyz as the protocol. The
reader exposes content identity, local runtime identity and explicit unverified
loading/compliance/protection fields, without running project discovery or Git.
Text output also surfaces known identity errors without turning a read into a
new completion gate. Source-mode reads suppress bytecode cache writes.

Init remains create-only and avoids another bootstrap when a direct reference
is already recognized. Upgrade inspects the actual selected archive, including
compact sources, before recommending its new command. Missing/unreadable/old
entries produce a bounded advisory, never an instruction rewrite. Concurrent
project-guide edits do not invalidate framework transaction decisions; successful
apply refreshes that advisory from the current installed archive and entry.

Doctor's opt-in host diagnostics report static references separately from actual
loading. Root overrides and unreadable/symbolic/oversize guides require review.
No source-copy checksum, text reference or local manifest match is promoted to
an OS lock, release attestation or verified product behavior.

## Independent review resolutions

Two implementers reviewed each other's boundaries; an independent reviewer
examined the integrated implementation in two rounds. Resolved findings:

- Display known runtime integrity errors in default guidance output.
- Bound actual host reads, not just a pre-read file size.
- Keep root override precedence wording conditional, without inferring loading.
- Preserve concurrent project entry edits and refresh stale advisory output.
- Inspect the effective archive rather than leftover source modules.
- Treat a genuinely corrupt DEFLATE stream as unknown capability instead of
  letting a best-effort advisory throw after a successful transaction.

All findings have independent or executable regression coverage. No unresolved
P1/P2 was reported after review.

## Verification results

- `python3 pact.py --help`: the new read primitive is discoverable under setup.
- `python3 scripts/pact/pact.py schema-lint`: 16 schemas supported.
- `python3 scripts/pact/pact.py workflow-lint`: 16 workflow/templates pinned.
- `python3 scripts/pact/pact.py check`: deterministic checks passed.
- Final `python3 -m unittest discover -s scripts/pact/tests -p 'test_*.py' -v`:
  **765 tests, OK, one environment-dependent skip** (this filesystem refused a
  non-UTF-8 filename). Final runtime-module hashes stayed unchanged throughout.
- Standard-guidance, upgrade and host-wiring subsets contain 7, 13 and 10 tests
  respectively, all passing. These include genuine corrupt DEFLATE data, known
  identity errors, cp1252 JSON transport and source-mode no-bytecode writes.
- An initial broad run exposed a stale assertion tied to the old guide wording;
  it was corrected to test optional workflow semantics in the runtime-supplied
  guide. The final full run above includes the correction and every review fix.
- The isolated gaokao_zx rc.2 installation/entry replay passed preview, injected
  failure rollback, upgrade, read-only guide access, static diagnostics and
  repeated-upgrade preservation. Its project-approved interpreter ran only
  PACT commands in the temporary copy.

Local stdout/stderr, exact fixture identities, final source hashes and result
JSON are retained under `.pact/tmp/standard-guidance-20261106/`; reproducible
regressions live in the repository test files. No cross-OS CI or real-host
obedience result is inferred from these local checks.

## Verification limits

The gaokao_zx simulation copies its rc.2 installation surface and entry documents
only. It verifies exact rollback after an injected failure, project-file
preservation, read-only guidance, no host-map generation, repeat-upgrade
idempotence and direct-reference recognition. The original project is unchanged;
no application tests or host configurations were executed. Its project-owned
source record and usage text still require reconciliation during a real upgrade.

OS enforcement and real-host session activation remain unverified. No new
runtime was committed, published, or installed in gaokao_zx by this change.
