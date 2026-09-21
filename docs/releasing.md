# Releasing PACT

PACT runtime versions describe distributable framework/runtime behavior. They do not version a downstream project's Product Truth, Architecture, Decisions, Owner Profile, or other project-owned knowledge.

The `main` branch may carry a prerelease development version such as `0.4.0-dev.1`. That is a moving development identifier, not a published release.

## Before tagging

1. Replace any `-dev.*` runtime version in `.pact/VERSION` with the exact release version.
2. Move/finalize relevant `CHANGELOG.md` entries under that release heading.
3. Ensure `PACT Check` and `PACT Core Matrix` are green on `main`.
4. Run relevant manual external pilots when the release changes installation, Discovery, code mapping, Evidence, or completion semantics.
5. Resolve or explicitly document compatibility/migration behavior.
6. Confirm `LICENSE` is present and release assets/checksums include the Apache-2.0 license file.

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
