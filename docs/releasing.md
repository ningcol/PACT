# Releasing PACT

PACT runtime versions describe distributable framework/runtime behavior. They do not version a downstream project's Product Truth, Architecture, Decisions, Owner Profile, or other project-owned knowledge.

## Before tagging

1. Update `.pact/VERSION`.
2. Update `CHANGELOG.md`.
3. Ensure `PACT Check` and `PACT Core Matrix` are green on `main`.
4. Run relevant manual external pilots when the release changes installation, Discovery, code mapping, Evidence, or completion semantics.
5. Resolve or explicitly document compatibility/migration behavior.

## Tagging

Use an immutable semantic-version tag matching `.pact/VERSION`:

```text
v0.3.1
v0.4.0
```

Do not publish a tag whose version differs from `.pact/VERSION`.

## Automated GitHub Release

Pushing a `v*` tag triggers the release workflow.

The workflow:

- verifies the tag/version match;
- runs schema/check/unit validation;
- publishes `bootstrap.py`;
- publishes `SHA256SUMS`;
- creates the GitHub Release with generated notes.

Users should prefer a tag or exact commit over moving `main` for reproducible bootstrap/install.

## Runtime packaging

The current release asset intentionally keeps `bootstrap.py` small and canonical project content in the tagged source tree.

A future single-file `pact.pyz` runtime should only be introduced after runtime/core refactoring makes path/schema access safe inside zipapp packaging; it must not become a separately maintained copy of project truth.
