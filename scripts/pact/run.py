#!/usr/bin/env python3
"""Execute a command and write a PACT source-backed run receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone

from cache import file_sha256
from schema_validate import load_schema, validate_instance
from security import redact_argv
from workspace import git_root, workspace_snapshot
from protocol_ids import validate_task_id


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = ROOT / ".pact" / "schema" / "run-receipt.schema.json"
DIRECT_CHILD_TERMINATE_GRACE_SECONDS = 2.0
OUTPUT_DRAIN_GRACE_SECONDS = 3.0


VERIFICATION_SOURCE_EXTENSIONS = {
    ".py", ".sh", ".js", ".mjs", ".cjs", ".ts", ".json", ".toml",
    ".yaml", ".yml", ".sql", ".md", ".env", ".ps1",
}


def declared_source_hashes(root: pathlib.Path, sources: list[str]) -> list[dict]:
    """Hash explicitly declared project-local verification inputs."""
    root = root.resolve()
    recorded: list[dict] = []
    seen: set[str] = set()
    for raw in sources:
        relative = pathlib.Path(raw)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ValueError(f"verification source must be repository-relative: {raw!r}")
        candidate = root / relative
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"verification source escapes repository: {raw!r}") from exc
        if candidate.is_symlink() or not candidate.is_file():
            raise ValueError(f"verification source must be a regular repository file: {raw!r}")
        name = candidate.relative_to(root).as_posix()
        if name in seen:
            raise ValueError(f"duplicate declared verification source: {name}")
        seen.add(name)
        recorded.append({"path": name, "sha256": file_sha256(candidate)})
    return recorded


def external_source_count(
    root: pathlib.Path, cwd: pathlib.Path, command: list[str]
) -> int:
    """Conservatively detect direct external script/schema/config path arguments.

    This is a scope guard, not shell interpretation, process sandboxing or
    dependency attestation. An opaque script string or subprocess may still
    open external resources that argv does not declare.
    """
    root = root.resolve()
    cwd = cwd.resolve()
    found: set[str] = set()
    for arg in command:
        # argv items are already individual tokens: preserve a pathname
        # containing spaces, then additionally inspect simple shell fragments.
        tokens = [arg]
        if " " in arg:
            try:
                tokens.extend(shlex.split(arg))
            except ValueError:
                pass
        for token in tokens:
            candidate_text = token
            if token.startswith("--") and "=" in token:
                candidate_text = token.split("=", 1)[1]
            source = pathlib.Path(candidate_text).expanduser()
            if (
                source.suffix.lower() not in VERIFICATION_SOURCE_EXTENSIONS
                and not source.name.startswith(".env")
            ):
                continue
            if not (source.is_absolute() or candidate_text.startswith(("..", "~"))):
                continue
            resolved = source.resolve() if source.is_absolute() else (cwd / source).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                found.add(str(resolved))
    return len(found)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pump_stream(
    stream,
    digest,
    output,
    errors: list[BaseException],
) -> None:
    try:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
            if output is not None:
                output.write(chunk)
                output.flush()
    except BaseException as exc:
        errors.append(exc)
    finally:
        stream.close()


def _terminate_direct_child(
    process: subprocess.Popen,
    *,
    grace_seconds: float = DIRECT_CHILD_TERMINATE_GRACE_SECONDS,
) -> None:
    """Best-effort terminate-then-kill cleanup for the direct child."""
    if process.poll() is not None:
        return

    try:
        process.terminate()
    except OSError:
        if process.poll() is not None:
            return
        raise

    try:
        process.wait(timeout=grace_seconds)
        return
    except subprocess.TimeoutExpired:
        pass

    if process.poll() is None:
        process.kill()
    process.wait()


def _join_output_threads(
    threads: list[threading.Thread],
    *,
    grace_seconds: float = OUTPUT_DRAIN_GRACE_SECONDS,
) -> bool:
    """Return False if an inherited pipe prevents finite-time EOF.

    One shared monotonic deadline bounds the *whole* join, not each stream.
    Do not close buffered pipe wrappers from this thread while reader threads
    are blocked in read(): close() may wait on the buffered reader's lock.
    Their daemon threads/fds are reclaimed when this CLI process exits.
    """
    deadline = time.monotonic() + max(0.0, grace_seconds)
    for thread in threads:
        thread.join(timeout=max(0.0, deadline - time.monotonic()))
    return not any(thread.is_alive() for thread in threads)


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

    pump_errors: list[BaseException] = []
    threads = [
        threading.Thread(
            target=_pump_stream,
            args=(process.stdout, stdout_digest, stdout_target, pump_errors),
            daemon=True,
        ),
        threading.Thread(
            target=_pump_stream,
            args=(process.stderr, stderr_digest, stderr_target, pump_errors),
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()

    try:
        returncode = process.wait()
    except BaseException:
        try:
            _terminate_direct_child(process)
        finally:
            # Preserve the original interruption/exception. Descendants may
            # outlive the direct child while still holding its output pipes.
            _join_output_threads(threads)
        raise

    if not _join_output_threads(threads):
        # Without EOF the digests may be partial even when the command exited
        # successfully. Fail closed and do not publish a success receipt.
        raise OSError(
            "command output streams did not close within "
            f"{OUTPUT_DRAIN_GRACE_SECONDS:g}s after the direct child exited; "
            "a descendant may still hold stdout/stderr (no receipt published)"
        )
    if pump_errors:
        raise OSError(f"command output streaming failed: {pump_errors[0]}")

    return (
        int(returncode),
        stdout_digest.hexdigest(),
        stderr_digest.hexdigest(),
    )


def publish_receipt(output: pathlib.Path, receipt: dict) -> None:
    """Atomically publish a validated run receipt without following a leaf symlink."""
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.pact-run-",
        suffix=".tmp",
        dir=output.parent,
    )
    temporary = pathlib.Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        try:
            if temporary.exists():
                temporary.unlink()
        except OSError:
            pass


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
        "--source", action="append", default=[],
        help="repository-relative script/schema/config file used by verification; repeatable",
    )
    parser.add_argument(
        "--allow-external-inputs", action="store_true",
        help="explicitly allow external script/config paths; receipt records untrusted scope",
    )
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

    # The verified workspace may be a separately selected brownfield Git
    # repository; never bind source files to the PACT implementation checkout.
    source_root = git_root(cwd) or cwd
    try:
        verification_sources = declared_source_hashes(source_root, args.source)
        external_count = external_source_count(source_root, cwd, command)
    except (OSError, ValueError) as exc:
        print(f"PACT run: invalid verification input: {exc}", file=sys.stderr)
        return 2
    if external_count and not args.allow_external_inputs:
        print(
            "PACT run: external script/schema/config path detected; "
            "declare project-local sources or explicitly use --allow-external-inputs",
            file=sys.stderr,
        )
        return 2

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
    except KeyboardInterrupt:
        print("PACT run: interrupted", file=sys.stderr)
        return 130
    except OSError as exc:
        print(f"PACT run: cannot execute command: {exc}", file=sys.stderr)
        return 2
    finished = now_iso()

    try:
        if declared_source_hashes(source_root, args.source) != verification_sources:
            print(
                "PACT run: declared verification source changed during execution; "
                "no receipt published",
                file=sys.stderr,
            )
            return 2
    except (OSError, ValueError) as exc:
        print(f"PACT run: cannot recheck verification sources: {exc}", file=sys.stderr)
        return 2

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
        "verification_sources": verification_sources,
        "verification_input_scope": (
            "external-opt-in" if external_count
            else "declared-files" if verification_sources
            else "unattributed"
        ),
        "external_input_count": external_count,
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

    try:
        publish_receipt(output, receipt)
    except OSError as exc:
        print(f"PACT run: cannot publish receipt: {exc}", file=sys.stderr)
        return 2

    print(f"PACT run receipt: {output}", file=sys.stderr)
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
