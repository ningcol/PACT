#!/usr/bin/env python3
"""Safe GitHub Actions preflight for a future REAL coding-Agent A/B pilot.

This is intentionally NOT a coding-Agent session. It builds two clean,
independent workspaces and validates source identity / PACT-only treatment.
It never reads model API keys, starts an inference client, or publishes an
answer key. All external project writes occur only in a disposable clone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import traceback

import brownfield_adr_viewer as pilot

PACT_ROOT = pathlib.Path(__file__).resolve().parents[2]
UPSTREAM = "https://github.com/privacyfence/privacyfence.git"
UPSTREAM_SHA = "6a03856a6e1819b2eacd3963154ebc7d02923296"
EVALUATION_ORACLE_PATH = "benchmarks/privacyfence/pilot-developer-oracle-v1.json"
RUNNER_KIND = "github-hosted-disposable-preflight"
TRIAL_STATUS = "NOT_RUN_MISSING_INDEPENDENT_INPUT_AND_MODEL_AUTHORIZATION"


def command(*args: str, cwd: pathlib.Path | None = None, seconds: int = 120) -> str:
    completed = subprocess.run(
        args, cwd=cwd, check=False, capture_output=True,
        text=True, timeout=seconds,
    )
    if completed.returncode:
        raise RuntimeError(
            f"command failed ({args[0]} {args[1] if len(args) > 1 else ''}): "
            f"returncode={completed.returncode}; stderr={completed.stderr[-400:]}"
        )
    return completed.stdout.strip()


def tracked_source(root: pathlib.Path) -> dict[str, str]:
    """Content-digest every tracked upstream source without traversing symlinks."""
    paths = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True, capture_output=True, timeout=40,
    ).stdout
    tracked: dict[str, str] = {}
    real_root = root.resolve()
    for raw in paths.split(b"\x00"):
        if not raw:
            continue
        rel = raw.decode("utf-8")
        pure = pathlib.PurePosixPath(rel)
        if pure.is_absolute() or ".." in pure.parts or "\\" in rel:
            raise ValueError(f"unsafe tracked source relative path: {rel!r}")
        candidate = root / rel
        if candidate.is_symlink():
            # Detect malicious/accidental links to host secrets; hash only the
            # link itself. It is never dereferenced in the snapshot.
            if not candidate.resolve().is_relative_to(real_root):
                raise ValueError(f"upstream tracked symlink escapes clone: {rel!r}")
            data = os.readlink(candidate).encode("utf-8")
        elif candidate.is_file():
            if not candidate.resolve().is_relative_to(real_root):
                raise ValueError(f"source file escapes clone: {rel!r}")
            data = candidate.read_bytes()
        else:
            raise ValueError(f"tracked file absent or unsupported: {rel!r}")
        tracked[rel] = hashlib.sha256(data).hexdigest()
    return dict(sorted(tracked.items()))


def manifest_digest(snapshot: dict[str, str]) -> str:
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def original_clean(root: pathlib.Path) -> bool:
    return not command(
        "git", "-C", str(root), "status",
        "--porcelain", "--untracked-files=no",
    )


def run_preflight(root: pathlib.Path) -> dict:
    """Prove Actions can prepare strict A/B workspaces, with NO model charge."""
    if not root.is_dir() or root.is_symlink():
        raise ValueError("temporary runner scratch directory is unavailable")
    with tempfile.TemporaryDirectory(prefix="pact-agent-runner-", dir=root) as tmp:
        work = pathlib.Path(tmp)
        source, a, b = (
            work / "pinned-upstream",
            work / "A-original",
            work / "B-pact",
        )
        command("git", "clone", "--quiet", UPSTREAM, str(source), seconds=210)
        command(
            "git", "-C", str(source), "checkout", "--detach", "--quiet",
            UPSTREAM_SHA, seconds=70,
        )
        if command("git", "-C", str(source), "rev-parse", "HEAD") != UPSTREAM_SHA:
            raise ValueError("upstream source commit is not the pinned SHA")
        if command("git", "-C", str(source), "remote", "get-url", "origin") != UPSTREAM:
            raise ValueError("unexpected upstream remote")
        if not original_clean(source):
            raise ValueError("upstream original source started dirty")
        inventory = source / "docs" / "adr"
        adr_count = len(list(inventory.glob("*.md")))
        if adr_count != 184:
            raise ValueError(f"upstream ADR inventory drift: {adr_count}")

        # Independently copied worktrees: no model session, code test, or
        # trial receives another arm's .git state or edits.
        shutil.copytree(source, a, symlinks=True)
        shutil.copytree(source, b, symlinks=True)
        base = tracked_source(source)
        if not base or not (a / "README.md").is_file():
            raise ValueError("missing expected original repository source")
        baseline_hash = manifest_digest(base)
        if tracked_source(a) != base or tracked_source(b) != base:
            raise ValueError("copied A/B worktrees differ before treatment")
        if (a / "pact.py").exists() or (a / ".pact").exists():
            raise ValueError("control arm unexpectedly already contains PACT")

        # Only B is treated. No oracle or benchmark task wording is copied.
        install = pilot.install_pact(b)
        if not install["installed_source_match"]:
            raise ValueError("installed PACT archive differs from checked-out source")
        if not (b / "pact.py").is_file():
            raise ValueError("B missing installed PACT CLI")
        if not (b / "AGENTS.md").is_file():
            raise ValueError("B missing the PACT-initialized Agent guide")
        if (b / EVALUATION_ORACLE_PATH).exists():
            raise ValueError("test oracle leaked into Agent-visible B workspace")
        if (a / EVALUATION_ORACLE_PATH).exists():
            raise ValueError("test oracle leaked into control workspace")
        if tracked_source(a) != base or tracked_source(b) != base:
            raise ValueError("PACT installation rewrote original upstream source")
        if not original_clean(a) or not original_clean(b):
            raise ValueError("upstream tracked files changed during preparation")

        return {
            "kind": RUNNER_KIND,
            "source": "privacyfence/privacyfence",
            "pinned_upstream_sha": UPSTREAM_SHA,
            "original_source_file_count": len(base),
            "original_source_tree_sha256": baseline_hash,
            "adr_file_count": adr_count,
            "A_unmodified_original_source": True,
            "B_unmodified_original_source": True,
            "A_has_no_PACT_runtime": True,
            "B_installed_source_identical_PACT": True,
            "B_installed_archive_sha256": install["installed_archive_sha256"],
            "same_upstream_source_on_both_arms": True,
            "answer_keys_exposed_to_agent": False,
            "real_agent_executed": False,
            "provider_billed_tokens": None,
            "owner_approval_authenticated": False,
            "independently_blinded": False,
            "trial_status": TRIAL_STATUS,
            "release_gate": "HOLD",
            "preflight_status": "PASS",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--temp-root", default=os.environ.get("RUNNER_TEMP", "/tmp"))
    args = parser.parse_args()
    output = pathlib.Path(args.output)
    if not output.parent.is_dir():
        parser.error("preflight output parent directory must already exist")

    result = {
        "kind": RUNNER_KIND,
        "source": "privacyfence/privacyfence",
        "pinned_upstream_sha": UPSTREAM_SHA,
        "preflight_status": "FAIL",
        "real_agent_executed": False,
        "independently_blinded": False,
        "release_gate": "HOLD",
    }
    try:
        result = run_preflight(pathlib.Path(args.temp_root))
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)[:1200]
        result["traceback"] = traceback.format_exc(limit=5)[:2400]
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Agent Actions preflight: {result['preflight_status']}; "
        f"model sessions NOT RUN; report written"
    )
    return 0 if result["preflight_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
