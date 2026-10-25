# Releasing PACT

PACT runtime versions describe distributable framework/runtime behavior. They do not version a downstream project's Product Truth, Architecture, Decisions, Owner Profile, or other project-owned knowledge.

The `main` branch may carry a prerelease development version such as `0.4.0-dev.1`. That is a moving development identifier, not a published release.

## Before tagging

1. Replace any `-dev.*` runtime version in `.pact/VERSION` with the exact release version.
2. Move/finalize **all merged pre-tag runtime fixes** under the exact release heading in `CHANGELOG.md`; reserve `Unreleased` for subsequent changes.
3. Ensure `PACT Check` and the actual **fail-fast** 3 OS × 3 Python `PACT Core Matrix` are green for the **exact main commit intended for tagging, after the final documentation PR merge**. Never count a Windows PowerShell step as passing if an earlier native command may have failed but a later command overwrote its exit status.
4. For a **stable** release, run and independently accept the applicable real coding-Agent/Owner trials when installation, Discovery, code mapping, Evidence or completion semantics change. Source-level fixtures and OS×Python unit tests cannot substitute. For an explicitly marked **RC pilot**, those trials may be pending, but the dedicated RC Owner/reviewer approval, source integrity, installation/upgrade smoke and all automated checks still apply. Never describe an RC as stable or as proving Agent obedience/Owner benefit.
5. Resolve or explicitly document compatibility/migration behavior.
6. Confirm `LICENSE` is present and release assets/checksums include the Apache-2.0 license file.

## Two fail-closed channels (default: HOLD)

`v0.4.0-rc.1` is for **controlled real-project pilots**, not a stable or
independently approved Agent/Owner efficacy claim. The stable `v0.4.0`
keeps stronger acceptance gates. Neither channel is approved merely by a
passing test, an environment **name**, or a successful PR.

Both channels require the tag to equal the exact `.pact/VERSION`, identify
the **current main HEAD**, and have successful GitHub **main-push** PACT Check
and Core Matrix receipts for that same SHA. The tag workflow reruns all
9 OS×Python combinations and the full source/installation smoke tests.
It calls GitHub's per-workflow-run **environment approval history API** and
**fails closed unless it contains an actual human `approved` review for the
correct selected environment**. An empty history (including unconfigured
environments) or an API failure blocks publication even when variables are
set. The last publication step rechecks current main HEAD.

| Channel | Version / environment | Required Owner variables | Real Agent/Owner acceptance |
| --- | --- | --- | --- |
| RC pilot | `vX.Y.Z-rc.N` / `pact-rc-approval` | `PACT_RC_RELEASE_GO=GO` and `PACT_RC_RELEASE_APPROVED_SHA=<40-character exact main SHA>` | Not claimed; formal trial may still be pending |
| Stable | `vX.Y.Z` / `pact-release-approval` | `PACT_RELEASE_GO=GO`, `PACT_RELEASE_APPROVED_SHA=<40-character exact main SHA>`, `PACT_AGENT_OWNER_GATES_APPROVED=true` | Independently completed and accepted before GO |

Do **not** set `PACT_AGENT_OWNER_GATES_APPROVED=true` solely because the
engineering CI succeeded. Stable approval remains **HOLD** until genuine
Agent/Owner acceptance is authorized.

### Human setup still required in GitHub Settings

The repository administrator must create **both** GitHub Environments
(`pact-rc-approval`, `pact-release-approval`) as relevant under
**Settings → Environments** and configure **Required reviewers** for each.
For the RC, put the two `PACT_RC_*` values in the **RC environment's
variables**, not as a credential in code or a repository commit. Configure
required reviewers in the stable environment independently and do not set
its three GO/Owner acceptance variables until stable evidence exists.

A GitHub run waiting for review requires a real human to select
**Review deployments → Approve and deploy**. The selected reviewer should
be an authorized person, not an Agent or workflow. If prevention of
self-review is enabled, an independent authorized reviewer must approve.
GitHub environment restrictions and their reviewer lists are not
version-controlled; configuration **cannot** be inferred from these files.
This workflow verifies an actual approved event for its exact run after
that event occurs. Running `gh release create` outside this workflow is an
administrative action outside these automated gates and is not authorized
by passing CI.

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

The untagged `0.4.0-rc.1` candidate has a verified **four-version
source-pinned engineering upgrade matrix** from [PR #241](https://github.com/ningcol/PACT/pull/241),
using the original PACT installers in disposable GitHub Actions targets:

| Original PACT installation | Candidate upgrade path | Acceptance boundary |
| --- | --- | --- |
| `0.1.0` and `0.2.0`, with a valid `.pact/install.json` | Explicit `--migrate-legacy` preview, then reviewed apply for YAML Owner seeds / PACT Decision metadata | No silent YAML/TOML shadowing or invented Decision/Owner status |
| `0.3.0`, with a valid install manifest | Ordinary upgrade if fully modern; explicit `--migrate-legacy` if historical YAML/Decision sources are present | Original rationale and project-owned config remain authoritative |
| Early **unpublished** `0.4.0-rc.1` development install | Ordinary preview and apply | Existing TOML Decisions, including Windows CRLF frontmatter, stay byte-identical |
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
Owner decision. The published tag and downloadable assets do not exist
until human RC approval completes. **After publication**, repeat
checksum/installation and representative 0.1/0.2/0.3/0.4-to-tag upgrades
using the immutable `v0.4.0-rc.1` source, not moving `main`.

### How an existing pilot project upgrades after RC publication

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

**The RC release is still HOLD until** the administrator configures
`pact-rc-approval` with Required reviewers and environment-local
`PACT_RC_RELEASE_GO=GO` plus
`PACT_RC_RELEASE_APPROVED_SHA=<the final reviewed 40-character main SHA>`,
and a real authorized reviewer approves the exact release workflow.
These conditions cannot be satisfied by a PR, a CI badge or a note in
the repository. Do **not** set stable
`PACT_AGENT_OWNER_GATES_APPROVED=true` based on the RC tests.

## Tagging

Use an immutable semantic-version tag **matching `.pact/VERSION`
exactly**. Only stable `vMAJOR.MINOR.PATCH` and RC `vMAJOR.MINOR.PATCH-rc.N`
are publishable by this workflow; `-dev.N`, `-alpha` and arbitrary
suffixes are rejected. The current source version is `0.4.0-rc.1`.
No tag or GitHub Release is created by merely merging this workflow.

Once main Check + Core Matrix are green on its exact SHA, and the
appropriate human reviewer/environment variables are configured:

```bash
git fetch origin main
git switch main
git pull --ff-only
# Check this output is the intended RC, and record the full reviewed SHA.
cat .pact/VERSION
git rev-parse HEAD

# Only the authorized maintainer does this; the push triggers the guarded workflow.
git tag -a v0.4.0-rc.1 -m "PACT v0.4.0-rc.1 pilot prerelease"
git push origin refs/tags/v0.4.0-rc.1
```

Do not tag until `PACT_RC_RELEASE_APPROVED_SHA` equals the **final** main
commit being tagged (which changes when the release-documentation PR merges)
and a real reviewer is assigned. If review or CI is
missing, the run stays blocked or fails and publishes nothing. Never move
or force-push a release tag to work around a failure; fix the missing
evidence and use a new reviewed commit/version if necessary.

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
- verifies a real reviewer event for the selected environment, exact
  approved commit variables and successful main-branch CI via authenticated
  GitHub API before building/publishing;
- retains the existing independent Agent/Owner approval requirement for
  stable releases.

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
