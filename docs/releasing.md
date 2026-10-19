# Releasing PACT

PACT runtime versions describe distributable framework/runtime behavior. They do not version a downstream project's Product Truth, Architecture, Decisions, Owner Profile, or other project-owned knowledge.

The `main` branch may carry a prerelease development version such as `0.4.0-dev.1`. That is a moving development identifier, not a published release.

## Before tagging

1. Replace any `-dev.*` runtime version in `.pact/VERSION` with the exact release version.
2. Move/finalize relevant `CHANGELOG.md` entries under that release heading.
3. Ensure `PACT Check` and the actual **fail-fast** 3 OS × 3 Python `PACT Core Matrix` are green for the **exact main commit intended for tagging**. Never count a Windows PowerShell step as passing if an earlier native command may have failed but a later command overwrote its exit status.
4. Run and document the relevant authorized external Agent/Owner pilots when release changes installation, Discovery, code mapping, Evidence or completion semantics. A source-level synthetic fixture or Linux/macOS/Windows Python unit test does **not** substitute for actual Agent-host use or measured Owner benefit. If these required evidence gates remain unresolved, record **Release HOLD** under #63 rather than manufacturing a passing release claim.
5. Resolve or explicitly document compatibility/migration behavior.
6. Confirm `LICENSE` is present and release assets/checksums include the Apache-2.0 license file.

## Enforced release approval (current default: HOLD)

The tag-triggered workflow will **fail before publishing** unless **all**
of these independently authorized inputs are present for the exact HEAD:

1. A protected GitHub Actions environment named `pact-release-approval`
   with **required reviewers** configured by the repository owner (GitHub
   settings are outside version-controlled workflow files and must be checked
   manually). Without an actual reviewer requirement, the environment name
   alone is not a human authorization.
2. An explicit environment/repository variable `PACT_RELEASE_GO=GO`.
3. An explicit variable `PACT_AGENT_OWNER_GATES_APPROVED=true` only after
   authentic real Agent/Owner gates #214/#28/#32 are independently accepted.
4. A variable `PACT_RELEASE_APPROVED_SHA` equal to the **full approved
   commit SHA**, which must also equal the current `main` HEAD and pushed
   tag commit.

The variables are deliberately **unset** during Release HOLD and CI cannot
set them automatically. A passing unit test or source-level benchmark is NOT
an Owner sign-off. The required-reviewer protection is a repository
administration setting; don't assert it is configured without checking it.
This controls the automated publishing path but cannot prevent administrators
from creating releases by other authorized GitHub interfaces.

## Tagging

Use an immutable semantic-version tag matching `.pact/VERSION` exactly:

```text
v0.4.0
v0.4.1
```

Do not publish a release tag whose version differs from `.pact/VERSION`.

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
- marks versions with a prerelease suffix (for example `0.4.0-rc.1` or `0.4.0-dev.1`) as GitHub prereleases rather than stable releases.

Users should prefer a release tag or exact commit over moving `main` for reproducible bootstrap/install.

## Runtime packaging

PACT already uses the single-file compact runtime in adopted projects:

```text
pact.py
└── .pact/pact.pyz
```

The canonical editable runtime and schemas remain in the source repository. `pact.pyz` is built from that source; it is not a separately maintained copy of project truth.

The small release bootstrap asset downloads/executes an explicitly selected source ref and the release also publishes the matching prebuilt `pact.pyz` plus checksums.
