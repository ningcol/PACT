#!/usr/bin/env python3
"""Execute a command and write a PACT source-backed run receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import threading
from datetime import datetime, timezone

from schema_validate import load_schema, validate_instance
from security import redact_argv
from workspace import workspace_snapshot
from protocol_ids import validate_task_id


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = ROOT / ".pact" / "schema" / "run-receipt.schema.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pump_stream(
    stream,
    digest,
    output,
) -> None:
    try:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
            if output is not None:
                output.write(chunk)
                output.flush()
    finally:
        stream.close()


def run_streamed(
    command: list[str],
    *,
    cwd: pathlib.Path,
    quiet: bool,
) -> tuple[int, str, str]:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    assert process.stdout is not None
    assert process.stderr is not None

    stdout_digest = hashlib.sha256()
    stderr_digest = hashlib.sha256()
    stdout_target = None if quiet else sys.stdout.buffer
    stderr_target = None if quiet else sys.stderr.buffer

    threads = [
        threading.Thread(
            target=_pump_stream,
            args=(process.stdout, stdout_digest, stdout_target),
            daemon=True,
        ),
        threading.Thread(
            target=_pump_stream,
            args=(process.stderr, stderr_digest, stderr_target),
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()

    returncode = process.wait()
    for thread in threads:
        thread.join()

    return (
        int(returncode),
        stdout_digest.hexdigest(),
        stderr_digest.hexdigest(),
    )


def ci_provenance() -> dict | None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return None

    required = {
        "repository": "GITHUB_REPOSITORY",
        "run_id": "GITHUB_RUN_ID",
        "run_attempt": "GITHUB_RUN_ATTEMPT",
        "job": "GITHUB_JOB",
        "workflow": "GITHUB_WORKFLOW",
        "sha": "GITHUB_SHA",
        "ref": "GITHUB_REF",
        "server_url": "GITHUB_SERVER_URL",
    }
    values = {}
    for key, env_name in required.items():
        value = os.environ.get(env_name)
        if not value:
            return None
        values[key] = value

    return {
        "provider": "github-actions",
        **values,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a command and create a PACT execution receipt"
    )
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--cwd", help="command working directory; defaults to repository root")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="do not replay captured command stdout/stderr to the terminal",
    )
    parser.add_argument(
        "--redact-value",
        action="append",
        default=[],
        help="additional literal to redact from persisted argv; repeatable",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    try:
        validate_task_id(args.task_id)
    except ValueError as exc:
        print(f"PACT run: invalid task id: {exc}", file=sys.stderr)
        return 2

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("PACT run: command is required after --", file=sys.stderr)
        return 2

    cwd = pathlib.Path(args.cwd).expanduser().resolve() if args.cwd else ROOT
    output = pathlib.Path(args.output)
    if not output.is_absolute():
        output = ROOT / output

    try:
        workspace_before = workspace_snapshot(cwd)
    except Exception as exc:
        print(f"PACT run: cannot fingerprint workspace before command: {exc}", file=sys.stderr)
        return 2

    started = now_iso()
    try:
        returncode, stdout_sha256, stderr_sha256 = run_streamed(
            command,
            cwd=cwd,
            quiet=args.quiet,
        )
    except OSError as exc:
        print(f"PACT run: cannot execute command: {exc}", file=sys.stderr)
        return 2
    finished = now_iso()

    try:
        workspace_after = workspace_snapshot(cwd)
    except Exception as exc:
        print(f"PACT run: cannot fingerprint workspace after command: {exc}", file=sys.stderr)
        return 2

    persisted_argv, redacted_count = redact_argv(
        command,
        extra_values=args.redact_value,
    )

    receipt = {
        "version": 2,
        "task_id": args.task_id,
        "argv": persisted_argv,
        "argv_redacted": True,
        "redacted_argument_count": redacted_count,
        "cwd": str(cwd),
        "started_at": started,
        "finished_at": finished,
        "exit_code": returncode,
        "status": "pass" if returncode == 0 else "fail",
        "stdout_sha256": stdout_sha256,
        "stderr_sha256": stderr_sha256,
        "git_head": workspace_after.get("git_head"),
        "git_dirty": workspace_after.get("dirty"),
        "workspace_before": workspace_before,
        "workspace_after": workspace_after,
        "workspace_changed": (
            workspace_before.get("sha256") != workspace_after.get("sha256")
        ),
        "ci": ci_provenance(),
    }

    errors = validate_instance(receipt, load_schema(SCHEMA))
    if errors:
        print("PACT run: generated invalid receipt", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"PACT run receipt: {output}", file=sys.stderr)

    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
