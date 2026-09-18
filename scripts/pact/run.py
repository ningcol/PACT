#!/usr/bin/env python3
"""Execute a command and write a PACT source-backed run receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

from schema_validate import load_schema, validate_instance


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = ROOT / ".pact" / "schema" / "run-receipt.schema.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_state(cwd: pathlib.Path) -> tuple[str | None, bool | None]:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if head.returncode != 0:
            return None, None

        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if dirty.returncode != 0:
            return head.stdout.strip(), None
        return head.stdout.strip(), bool(dirty.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        return None, None


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
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

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

    started = now_iso()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            shell=False,
        )
    except OSError as exc:
        print(f"PACT run: cannot execute command: {exc}", file=sys.stderr)
        return 2
    finished = now_iso()

    if not args.quiet:
        if completed.stdout:
            sys.stdout.buffer.write(completed.stdout)
            sys.stdout.buffer.flush()
        if completed.stderr:
            sys.stderr.buffer.write(completed.stderr)
            sys.stderr.buffer.flush()

    git_head, git_dirty = git_state(cwd)
    receipt = {
        "version": 1,
        "task_id": args.task_id,
        "argv": command,
        "cwd": str(cwd),
        "started_at": started,
        "finished_at": finished,
        "exit_code": int(completed.returncode),
        "status": "pass" if completed.returncode == 0 else "fail",
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
        "git_head": git_head,
        "git_dirty": git_dirty,
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

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
