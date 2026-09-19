# Security Policy

PACT is project-control infrastructure: it reads repositories, executes project-owned verification commands, records local/CI provenance, and can update its own framework-managed files. Security reports should therefore avoid exposing secrets or private repository content publicly.

## Supported versions

Security fixes target:

- the latest published PACT runtime release;
- `main` when a fix is being prepared for the next release.

Older runtime lines may be asked to upgrade when the fix depends on current provenance/upgrade machinery.

## Reporting a vulnerability

Prefer GitHub **Private Vulnerability Reporting** for this repository when it is available.

Please include:

- affected PACT version/commit;
- affected command or workflow;
- reproduction steps;
- expected vs observed security boundary;
- whether secrets/private repository content may have been exposed.

Do **not** paste credentials, access tokens, private source, or exploit details into a public issue.

If private vulnerability reporting is unavailable, open a minimal public issue requesting a private security contact path, without sensitive technical details.

## Security boundaries

PACT aims to:

- remain zero-runtime-dependency in core;
- avoid persisting command stdout/stderr content in run receipts;
- redact common secret-like argv values;
- bind verification Evidence to exact workspace state;
- validate install provenance and framework file hashes;
- stage and rollback runtime upgrades;
- pin GitHub Actions used by PACT CI to immutable commit SHAs.

PACT local receipts are execution/provenance records, not tamper-proof cryptographic attestations. GitHub Actions metadata recorded in a receipt is provenance metadata only; local environment variables can imitate it and PACT does not remotely attest the run. Stronger assurance requires repository protections and an independent remote/signed attestation layer.
