#!/usr/bin/env python3
"""Fail-closed, human-reviewed PACT RC/stable release policy.

The tag workflow fetches GitHub's actual per-run environment approval history
and exact-main CI results using an Actions-read token. An environment name or
a repository variable on its own is NOT proof that reviewers are configured.
This module neither creates tags nor publishes releases.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from collections.abc import Mapping

SEMVER = re.compile(
    r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:(-rc\.(?:0|[1-9][0-9]*)))?$"
)
SHA = re.compile(r"^[0-9a-f]{40}$")
ENVIRONMENT = {
    "rc": "pact-rc-approval",
    "stable": "pact-release-approval",
}
CI_WORKFLOWS = {
    "pact-check": "PACT Check",
    "core-matrix": "PACT Core Matrix",
}


class ReleaseHold(ValueError):
    """Missing approval or mismatched exact-source evidence."""


def classify(tag: str, runtime_version: str) -> str:
    if not isinstance(tag, str) or SEMVER.fullmatch(tag) is None:
        raise ReleaseHold(
            "release tag must be vMAJOR.MINOR.PATCH or vMAJOR.MINOR.PATCH-rc.N; "
            "development, alpha, arbitrary prerelease and moving refs cannot publish"
        )
    if tag[1:] != runtime_version.strip():
        raise ReleaseHold(
            f"tag {tag!r} must exactly equal .pact/VERSION "
            f"{runtime_version.strip()!r}"
        )
    return "rc" if "-rc." in tag else "stable"


def require_sha(tag_sha: str, main_sha: str) -> None:
    if not isinstance(tag_sha, str) or SHA.fullmatch(tag_sha) is None:
        raise ReleaseHold("tag must resolve to a full 40-character commit SHA")
    if not isinstance(main_sha, str) or SHA.fullmatch(main_sha) is None:
        raise ReleaseHold("main HEAD must be a full 40-character commit SHA")
    if tag_sha != main_sha:
        raise ReleaseHold(
            "tag commit differs from currently reviewed main HEAD; "
            "never publish a tag from a stale or unrelated commit"
        )


def require_ci_receipts(reports: Mapping[str, object], sha: str) -> None:
    if set(reports) != set(CI_WORKFLOWS):
        raise ReleaseHold("both PACT Check and Core Matrix receipts are required")
    for key, workflow_name in CI_WORKFLOWS.items():
        collection = reports[key]
        if not isinstance(collection, dict):
            raise ReleaseHold(f"{workflow_name}: missing GitHub Actions response")
        entries = collection.get("workflow_runs")
        if not isinstance(entries, list) or not any(
            isinstance(run, dict)
            and run.get("name") == workflow_name
            and run.get("head_sha") == sha
            and run.get("head_branch") == "main"
            and run.get("event") == "push"
            and run.get("status") == "completed"
            and run.get("conclusion") == "success"
            for run in entries
        ):
            raise ReleaseHold(
                f"{workflow_name}: no successful exact-main push workflow "
                "receipt for this tag commit"
            )


def has_real_environment_approval(records: object, environment: str) -> bool:
    """Review history is fetched from this *exact* workflow run, never PR text."""
    if not isinstance(records, list):
        return False
    return any(
        isinstance(entry, dict)
        and entry.get("state") == "approved"
        and isinstance(entry.get("user"), dict)
        and entry["user"].get("type") == "User"
        and isinstance(entry["user"].get("login"), str)
        and bool(entry["user"]["login"])
        and isinstance(entry.get("environments"), list)
        and any(
            isinstance(env, dict) and env.get("name") == environment
            for env in entry["environments"]
        )
        for entry in records
    )


def require_release_approval(
    channel: str,
    tag_sha: str,
    main_sha: str,
    *,
    env: Mapping[str, str],
    approvals: object,
    ci_reports: Mapping[str, object],
    event: str = "push",
) -> None:
    if channel not in ENVIRONMENT:
        raise ReleaseHold("invalid release channel")
    if event != "push":
        raise ReleaseHold("only an immutable version-tag push can publish")
    require_sha(tag_sha, main_sha)
    require_ci_receipts(ci_reports, tag_sha)

    expected_env = ENVIRONMENT[channel]
    if not has_real_environment_approval(approvals, expected_env):
        raise ReleaseHold(
            f"{expected_env}: missing authenticated approved environment review "
            "in GitHub's per-run audit history; an unprotected environment "
            "or a bypass cannot release"
        )
    if channel == "rc":
        go = env.get("PACT_RC_RELEASE_GO")
        approved = env.get("PACT_RC_RELEASE_APPROVED_SHA")
        if go != "GO" or approved != tag_sha:
            raise ReleaseHold(
                "RC requires explicit PACT_RC_RELEASE_GO=GO and "
                "PACT_RC_RELEASE_APPROVED_SHA equal to the exact tag commit"
            )
        # RC engineering trial is permitted without falsely claiming real
        # Agent/Owner efficacy. This does not relax the stable gate below.
    else:
        if (
            env.get("PACT_RELEASE_GO") != "GO"
            or env.get("PACT_RELEASE_APPROVED_SHA") != tag_sha
            or env.get("PACT_AGENT_OWNER_GATES_APPROVED") != "true"
        ):
            raise ReleaseHold(
                "stable release requires protected GO, exact approved SHA, "
                "and genuine PACT_AGENT_OWNER_GATES_APPROVED=true; "
                "developer engineering trials do not meet this gate"
            )


def read_json(path: str) -> object:
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseHold(f"missing/malformed authenticated GitHub evidence: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PACT gated RC/stable release")
    sub = parser.add_subparsers(dest="command", required=True)
    cl = sub.add_parser("classify")
    cl.add_argument("--tag", required=True)
    cl.add_argument("--version-file", required=True)
    cl.add_argument("--github-output")
    gate = sub.add_parser("gate")
    gate.add_argument("--tag", required=True)
    gate.add_argument("--version-file", required=True)
    gate.add_argument("--tag-sha", required=True)
    gate.add_argument("--main-sha", required=True)
    gate.add_argument("--event", default="push")
    gate.add_argument("--approvals-file", required=True)
    gate.add_argument("--check-runs-file", required=True)
    gate.add_argument("--matrix-runs-file", required=True)
    args = parser.parse_args(argv)
    try:
        version = pathlib.Path(args.version_file).read_text(encoding="utf-8").strip()
        channel = classify(args.tag, version)
        if args.command == "classify":
            data = {
                "channel": channel,
                "environment": ENVIRONMENT[channel],
                "prerelease": "true" if channel == "rc" else "false",
            }
            if args.github_output:
                with open(args.github_output, "a", encoding="utf-8") as output:
                    for key, value in data.items():
                        output.write(f"{key}={value}\n")
            print(json.dumps(data, sort_keys=True))
        else:
            require_release_approval(
                channel, args.tag_sha, args.main_sha,
                env=os.environ,
                approvals=read_json(args.approvals_file),
                ci_reports={
                    "pact-check": read_json(args.check_runs_file),
                    "core-matrix": read_json(args.matrix_runs_file),
                },
                event=args.event,
            )
            print(json.dumps({
                "release_gate": "AUTHORIZED",
                "channel": channel, "commit": args.tag_sha,
                "reviewed_environment": ENVIRONMENT[channel],
                "main_ci_verified": ["PACT Check", "PACT Core Matrix"],
            }))
        return 0
    except (ReleaseHold, OSError, UnicodeError) as exc:
        print(f"Release HOLD: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
