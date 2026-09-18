#!/usr/bin/env python3
"""PACT single-file bootstrap.

This file contains no PACT project templates or governance truth. It only fetches
an explicitly selected PACT source archive into a temporary directory and invokes
that source's real init/upgrade runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile


DEFAULT_REPO = "ningcol/PACT"
DEFAULT_REF = "main"
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_archive(
    repo: str,
    ref: str,
    destination: pathlib.Path,
    *,
    archive_override: pathlib.Path | None = None,
) -> None:
    if archive_override is not None:
        shutil.copy2(archive_override, destination)
        return

    encoded_ref = urllib.parse.quote(ref, safe="")
    url = f"https://api.github.com/repos/{repo}/zipball/{encoded_ref}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PACT-bootstrap",
            "Accept": "application/vnd.github+json",
        },
    )

    total = 0
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_ARCHIVE_BYTES:
                raise RuntimeError(
                    f"PACT source archive exceeds {MAX_ARCHIVE_BYTES} bytes"
                )
            output.write(chunk)


def safe_extract(archive_path: pathlib.Path, destination: pathlib.Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            name = info.filename
            if not name:
                continue

            # Reject absolute paths, traversal, and Unix symlink entries.
            pure = pathlib.PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts:
                raise RuntimeError(f"unsafe archive path: {name!r}")

            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise RuntimeError(f"archive symlink is not allowed: {name!r}")

            target = (destination / pathlib.Path(*pure.parts)).resolve()
            if target != destination and destination not in target.parents:
                raise RuntimeError(f"archive entry escapes destination: {name!r}")

        archive.extractall(destination)


def find_source_root(extracted: pathlib.Path) -> pathlib.Path:
    candidates = [
        path.parent.parent.parent
        for path in extracted.glob("*/scripts/pact/pact.py")
        if path.is_file()
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected exactly one PACT source root in archive, found {len(candidates)}"
        )
    return candidates[0].resolve()


def invoke_source(
    source_root: pathlib.Path,
    command: str,
    target: pathlib.Path,
    *,
    apply: bool,
    github_actions: bool = False,
) -> int:
    runtime = source_root / "scripts" / "pact" / "pact.py"
    if not runtime.is_file():
        raise RuntimeError(f"downloaded source is missing PACT runtime: {runtime}")

    argv = [
        sys.executable,
        str(runtime),
        command,
        "--target",
        str(target),
    ]

    if command == "upgrade":
        argv.extend(["--source", str(source_root)])

    if apply:
        argv.append("--apply")

    if command == "init" and github_actions:
        argv.append("--github-actions")

    return subprocess.run(argv).returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap PACT without cloning the repository"
    )
    parser.add_argument("command", choices=["init", "upgrade"])
    parser.add_argument("--target", default=".")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument(
        "--archive",
        help="local source ZIP override (testing/offline use); skips network download",
    )
    parser.add_argument(
        "--sha256",
        help="optional expected SHA256 for the downloaded/local source ZIP",
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--github-actions", action="store_true")
    args = parser.parse_args()

    if sys.version_info < (3, 11):
        print("PACT bootstrap requires Python 3.11+.", file=sys.stderr)
        return 2

    if args.command == "upgrade" and args.github_actions:
        print("--github-actions applies only to init", file=sys.stderr)
        return 2

    target = pathlib.Path(args.target).expanduser().resolve()
    archive_override = (
        pathlib.Path(args.archive).expanduser().resolve()
        if args.archive
        else None
    )

    print(f"PACT bootstrap source: {args.repo}@{args.ref}", file=sys.stderr)
    if args.ref == "main" and archive_override is None:
        print(
            "PACT bootstrap note: 'main' is a moving ref; use an exact commit/tag "
            "for reproducible adoption or upgrade.",
            file=sys.stderr,
        )

    try:
        with tempfile.TemporaryDirectory(prefix="pact-bootstrap-") as tmp:
            tmp_root = pathlib.Path(tmp)
            archive_path = tmp_root / "pact-source.zip"
            extract_root = tmp_root / "source"

            download_archive(
                args.repo,
                args.ref,
                archive_path,
                archive_override=archive_override,
            )

            if args.sha256:
                actual = sha256_file(archive_path)
                if actual.lower() != args.sha256.lower():
                    raise RuntimeError(
                        f"source archive SHA256 mismatch: expected {args.sha256}, got {actual}"
                    )

            extract_root.mkdir(parents=True)
            safe_extract(archive_path, extract_root)
            source_root = find_source_root(extract_root)

            return invoke_source(
                source_root,
                args.command,
                target,
                apply=args.apply,
                github_actions=args.github_actions,
            )
    except Exception as exc:
        print(f"PACT bootstrap: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
