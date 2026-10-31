# Releasing PACT

PACT runtime versions describe distributable framework/runtime behavior. They do not version a downstream project's Product Truth, Architecture, Decisions, Owner Profile, or other project-owned knowledge.

**RC2 preparation status (2026-10-31):** `v0.4.0-rc.1` was
published on 2026-10-27 and remains an immutable experimental prerelease.
The source currently prepares **`v0.4.0-rc.2`**, which includes only the
reviewed `--scope-first` unmapped/ambiguous fallback correction from
[PR #246](https://github.com/ningcol/PACT/pull/246), plus release
metadata and upgrade checks. A version-file change or merged PR does **not**
publish RC2. Genuine real-Agent/Owner acceptance is still pending.

The `main` branch may carry a prerelease development version such as `0.4.0-dev.1`. That is a moving development identifier, not a published release.

## Before tagging

1. Replace any `-dev.*` runtime version in `.pact/VERSION` with the exact release version.
2. Move/finalize **all merged pre-tag runtime fixes** under the exact release heading in `CHANGELOG.md`; reserve `Unreleased` for subsequent changes.
3. Ensure `PACT Check` and the actual **fail-fast** 3 OS × 3 Python `PACT Core Matrix` are green for the **exact main commit intended for tagging, after the final documentation PR merge**. Never count a Windows PowerShell step as passing if an earlier native command may have failed but a later command overwrote its exit status.
4. For a **stable** release, run and independently accept the applicable real coding-Agent/Owner trials when installation, Discovery, code mapping, Evidence or completion semantics change. Source-level fixtures and OS×Python unit tests cannot substitute. For an explicitly marked **RC pilot**, those trials may be pending; a maintainer can publish a tagged prerelease after exact-main CI, release portability and asset smoke succeed, without an extra Environment approval. Source integrity and installation/upgrade checks still apply. Never describe an RC as stable or as proving Agent obedience/Owner benefit.
5. Resolve or explicitly document compatibility/migration behavior.
6. Confirm `LICENSE` is present and release assets/checksums include the Apache-2.0 license file.

## Two release channels: simple prerelease, protected stable

`v0.4.0-rc.1` is an **already published experimental controlled-pilot
prerelease**; `v0.4.0-rc.2` is its next proposed patch candidate. Neither
is a stable release or independently verified Agent/Owner efficacy claim.
The tag-pushing maintainer initiates RC publication; **no**
`pact-rc-approval` Environment, `PACT_RC_RELEASE_GO`, SHA-approval variable
or secondary human deployment review is required.

For **both** release channels the immutable tag must match
`.pact/VERSION` and point to the **current reviewed `main` HEAD**, with
successful *main-push* PACT Check and 3 OS × 3 Python Core Matrix runs
for that SHA. The release workflow additionally reruns the tagged
9-cell matrix, source/schema/unit checks, asset builds, bootstrap smoke
and checksums before publishing. A changed main commit, missing/failed
CI, invalid tag or failed smoke stops publication.

| Channel | Tag | Human setup | Additional release conditions |
| --- | --- | --- | --- |
| Experimental RC | `vX.Y.Z-rc.N` | Maintainer with tag-write permission; **no Environment or GO variables** | Exact-current-main CI, tagged matrix, source/build/asset validation; published as `prerelease`, **not latest** |
| Stable | `vX.Y.Z` | Protected `pact-release-approval` Environment with Required reviewers | Actual approved GitHub run review, `PACT_RELEASE_GO=GO`, `PACT_RELEASE_APPROVED_SHA=<exact-main-SHA>`, `PACT_AGENT_OWNER_GATES_APPROVED=true`, plus all RC-grade checks |

### Stable approval only

For the stable channel, a repository administrator must configure
**Settings → Environments → `pact-release-approval`** with real
Required reviewers and the three Environment-local variables above.
An authorized human must approve **Review deployments → Approve and
deploy** on the exact stable release workflow run. The policy verifies
GitHub's authenticated per-run Environment-approval history; a named
but unprotected environment, bypass, missing variables, malformed
approval response or unapproved run fails closed.

The stable-only approval Job must succeed before the common publisher
can run. RC intentionally **skips** that Job and cannot turn a skipped
stable approval into a stable release. Do **not** set
`PACT_AGENT_OWNER_GATES_APPROVED=true` based on synthetic/unit or
source-level checks; genuine real Agent/Owner acceptance remains open
under #214, #28, #32 and release decision #63.

### RC pilot limitations and follow-up

Every RC GitHub Release is explicitly marked **prerelease**, **not latest**,
and includes a warning: developer-authored fixed-case engineering evidence
does **not** establish independent coding-Agent obedience or measured Owner
benefit. The RC channel never auto-closes #214/#28/#32/#221/#63 or publishes
a stable release. The original Owner/Decision content remains project-owned;
legacy 0.1/0.2 YAML migrations are explicit `--migrate-legacy`, not automatic.
Use Git's immutable tag and the PACT Bootstrap pinned to that tag for
individual pilot repositories. Report real Agent/Owner outcomes separately
instead of relabeling old scripted engineering receipts.

## RC upgrade-compatibility handoff (engineering evidence, not universal migration)

The published `0.4.0-rc.1` candidate had a verified **four-version
source-pinned engineering upgrade matrix** from [PR #241](https://github.com/ningcol/PACT/pull/241),
using the original PACT installers in disposable GitHub Actions targets:

| Original PACT installation | Candidate upgrade path | Acceptance boundary |
| --- | --- | --- |
| `0.1.0` and `0.2.0`, with a valid `.pact/install.json` | Explicit `--migrate-legacy` preview, then reviewed apply for YAML Owner seeds / PACT Decision metadata | No silent YAML/TOML shadowing or invented Decision/Owner status |
| `0.3.0`, with a valid install manifest | Ordinary upgrade if fully modern; explicit `--migrate-legacy` if historical YAML/Decision sources are present | Original rationale and project-owned config remain authoritative |
| Early **unpublished** `0.4.0-rc.1` development install | Ordinary preview and apply | Existing TOML Decisions, including Windows CRLF frontmatter, stay byte-identical |
| Published `v0.4.0-rc.1` at exact source SHA `7592efd` | RC2 preview and apply; repeat and fault-injected rollback | Current Owner preferences, Decisions and custom AGENTS guidance remain byte-identical; only unchanged framework-managed files may update |
| No trustworthy `.pact/install.json`, incompatible custom YAML, conflicting local framework edits or incomplete historical Task state | **Do not auto-upgrade**; review a backed-up isolated copy manually | Fail closed instead of inventing ownership or rewriting policy |

[Four pinned original installations, Bootstrap and failure/rollback checks](https://github.com/ningcol/PACT/actions/runs/40153967276)
passed on the reviewed source. The checks include source ZIP SHA256,
original Owner/Decision meaning and ID/status, repeated upgrade,
simulated mid-apply failure with byte-for-byte rollback and retry,
and local framework-edit conflict refusal. [Exact merged main
PACT Check](https://github.com/ningcol/PACT/actions/runs/40154561902)
and [3×3 Core Matrix](https://github.com/ningcol/PACT/actions/runs/40154561904)
also passed **before this documentation update**. The last documentation
commit must get its own main-push CI.

These are test fixtures and sampled historical installations, **not a
promise that every manually customized install will upgrade without
intervention**, nor evidence that a real coding Agent honored a migrated
Owner decision. Changing the release workflow or merging documentation
never creates a tag or downloadable assets: an authorized maintainer must
push the RC tag after exact-main CI succeeds. **After publication**, repeat
checksum/installation and representative 0.1/0.2/0.3/0.4-to-tag upgrades
using the immutable `v0.4.0-rc.1` source, not moving `main`.

### RC1 → RC2 pilot upgrade (once RC2 is published)

Check the actual published `v0.4.0-rc.2` GitHub Release assets and their
`SHA256SUMS` first; work from a **backed-up/disposable project copy**.
Normal tracked RC1 installations with intact `.pact/install.json` use
dry-run preview, inspect the planned managed files and ensure project-owned
Owner/Decision sources are untouched, then apply deliberately:

```bash
python pact-bootstrap.py upgrade --ref v0.4.0-rc.2 --target ../rc1-pilot-project
python pact-bootstrap.py upgrade --ref v0.4.0-rc.2 --target ../rc1-pilot-project --apply
```

Never supply `--migrate-legacy` automatically for a modern RC1 project.
For projects still containing actual legacy YAML, inspect a separate
`--migrate-legacy` preview and apply only after Owner review.
After the upgrade rerun `doctor --strict`, `owner --strict`,
`readiness`, `check` and exact-ID `discover` on the critical Decisions.
The project-owned content must not silently change; conflicts or absent
ownership manifests require manual recovery rather than bypass.

The historical upgrade matrix checks four old source generations and also
the **published RC1** original source `7592efd3393ff568758400ff06d7e2e5b3315a2f`
against the new RC2 source, including rollback/retry, idempotence, SHA256
Bootstrap and Owner/Decision/guide preservation. Its CI evidence must be
observed rather than presumed.

### Previously published RC1 upgrade examples (historical)



Obtain the approved `pact-bootstrap.py` and `SHA256SUMS` from the
**actual GitHub Release**, verify the downloaded asset digests, and
back up the old project (or work in a disposable copy). The following
commands are **post-publication examples**, not commands to run before
`v0.4.0-rc.1` is released:

```bash
# Modern tracked installation: preview first; then apply only with no conflicts.
python pact-bootstrap.py upgrade --ref v0.4.0-rc.1 --target ../existing-project
python pact-bootstrap.py upgrade --ref v0.4.0-rc.1 --target ../existing-project --apply

# Historical YAML sources: inspect an explicit migration preview FIRST.
python pact-bootstrap.py upgrade --ref v0.4.0-rc.1 --target ../existing-project --migrate-legacy
python pact-bootstrap.py upgrade --ref v0.4.0-rc.1 --target ../existing-project --migrate-legacy --apply
```

Use the ordinary **or** legacy path as appropriate; do not apply both
paths indiscriminately. A preview reports conflicts without changing
project files. Resolve an unsafe conflict with explicit Owner review
before re-running; never bypass provenance by `init --apply` in place.
The historical `AGENTS.md` is project-owned and is not silently
rewritten even when it contains obsolete YAML references. After apply,
verify `pact.py doctor --strict`, `owner --strict`, `readiness`,
`check`, and exact-ID `discover` of the important Decisions in that
project. See [Distribution and Safe Upgrades](design/distribution-upgrades.md).

**RC2 publication boundary:** a maintainer must push a new valid
`v0.4.0-rc.2` tag pointing to the exact, fully tested `main` commit.
Do **not** retag or overwrite the published `v0.4.0-rc.1`.
The tagged GitHub Actions workflow validates the same-source push CI,
repeats the 9-cell matrix and builds/smokes assets automatically; it
must finish **successfully** before the prerelease is considered
published. There is **no additional RC Environment/GO approval**.
Stable `v0.4.0` retains the independent human Agent/Owner gates.

## Tagging

Use an immutable semantic-version tag **matching `.pact/VERSION`
exactly**. Only stable `vMAJOR.MINOR.PATCH` and RC `vMAJOR.MINOR.PATCH-rc.N`
are publishable by this workflow; `-dev.N`, `-alpha` and arbitrary
suffixes are rejected. The RC2 preparation source version is `0.4.0-rc.2` (unpublished until the tagged release workflow succeeds).
No tag or GitHub Release is created by merely merging this workflow.

Once main Check + Core Matrix are green on the exact intended SHA,
the authorized maintainer can create and push the RC tag:

```bash
git fetch origin main
git switch main
git pull --ff-only
# Check this output is the intended RC, and record the full reviewed SHA.
cat .pact/VERSION
git rev-parse HEAD

# Only the authorized maintainer does this; the push triggers the guarded workflow.
git tag -a v0.4.0-rc.2 -m "PACT v0.4.0-rc.2 pilot prerelease"
git push origin refs/tags/v0.4.0-rc.2
```

Do not tag a stale or unrelated commit: the tag **must** resolve to
the final `main` SHA with green main-push CI for that same commit.
No extra RC reviewer/GO setup is needed. If the tag or CI gate fails,
the workflow publishes nothing. Never move or force-push a release tag
to work around a failure; fix the source/evidence first and select a
new version if an immutable tag already exists.

## Automated GitHub Release

Pushing a `v*` tag triggers the release workflow.

The workflow:

- verifies the tag/version match and semantic-version shape;
- runs the 3 OS × 3 Python portability matrix on the tag commit and blocks publication unless all nine cells pass;
- runs schema/check/full-unit validation;
- builds the compact `pact.pyz` runtime from the tagged source;
- publishes `pact-bootstrap.py`;
- publishes `pact.pyz`;
- publishes `LICENSE` with the release assets;
- publishes `SHA256SUMS` covering `pact-bootstrap.py`, `pact.pyz`, and `LICENSE`;
- creates the GitHub Release with generated notes;
- marks only `-rc.N` versions as experimental GitHub prereleases
  (not latest) with an explicit no-Agent/Owner-efficacy warning; `-dev.N`
  cannot publish;
- for RC, verifies **exact-main CI and tag identity**, with no human
  Environment approval or `GO` variables;
- for stable, requires an actual approved event for `pact-release-approval`,
  exact approved SHA, Owner `GO` and genuine Agent/Owner acceptance
  **before** the common publishing job can run.

After an RC is actually published, verify its `prerelease` flag, attached
`pact-bootstrap.py`, `pact.pyz`, `LICENSE`, `SHA256SUMS` and hashes
using `gh release view`, `gh release download` and
`sha256sum -c SHA256SUMS`. Test installation and the 0.1/0.2/0.3 plus early 0.4
upgrade paths again from the immutable tag before declaring external
adoption ready.

Users should prefer a release tag or exact commit over moving `main` for reproducible bootstrap/install.

## Runtime packaging

PACT already uses the single-file compact runtime in adopted projects:

```text
pact.py
└── .pact/pact.pyz
```

The canonical editable runtime and schemas remain in the source repository. `pact.pyz` is built from that source; it is not a separately maintained copy of project truth.

The small release bootstrap asset downloads/executes an explicitly selected source ref and the release also publishes the matching prebuilt `pact.pyz` plus checksums.
