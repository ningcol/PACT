#!/usr/bin/env python3
"""Build and smoke-test the exact assets published by PACT releases."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile


SCRIPT_PATH = pathlib.Path(__file__).resolve()
DEFAULT_ROOT = SCRIPT_PATH.parents[2]
ASSET_NAMES = ("pact-bootstrap.py", "pact.pyz")


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def runtime_builder(source_root: pathlib.Path):
    runtime_dir = source_root / "scripts" / "pact"
    sys.path.insert(0, str(runtime_dir))
    try:
        from runtime_bundle import build_runtime_bundle
    finally:
        try:
            sys.path.remove(str(runtime_dir))
        except ValueError:
            pass
    return build_runtime_bundle


def write_checksums(output_dir: pathlib.Path) -> pathlib.Path:
    lines = [
        f"{sha256_file(output_dir / name)}  {name}"
        for name in ASSET_NAMES
    ]
    target = output_dir / "SHA256SUMS"
    temporary = output_dir / ".SHA256SUMS.tmp"
    try:
        temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
        temporary.replace(target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def verify_checksums(output_dir: pathlib.Path) -> None:
    checksum_file = output_dir / "SHA256SUMS"
    seen: dict[str, str] = {}
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        digest, separator, name = line.partition("  ")
        if not separator or not digest or not name:
            raise RuntimeError(f"invalid SHA256SUMS line: {line!r}")
        seen[name] = digest

    if set(seen) != set(ASSET_NAMES):
        raise RuntimeError(
            f"SHA256SUMS asset set mismatch: {sorted(seen)} != {sorted(ASSET_NAMES)}"
        )

    for name in ASSET_NAMES:
        actual = sha256_file(output_dir / name)
        if seen[name] != actual:
            raise RuntimeError(
                f"SHA256SUMS mismatch for {name}: {seen[name]} != {actual}"
            )


def build_assets(source_root: pathlib.Path, output_dir: pathlib.Path) -> dict:
    source_root = source_root.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bootstrap = source_root / "bootstrap.py"
    if not bootstrap.is_file():
        raise FileNotFoundError(f"missing release bootstrap source: {bootstrap}")

    shutil.copy2(bootstrap, output_dir / "pact-bootstrap.py")
    build_runtime_bundle = runtime_builder(source_root)
    build_runtime_bundle(source_root, output_dir / "pact.pyz")
    write_checksums(output_dir)
    verify_checksums(output_dir)

    return {
        "output_dir": str(output_dir),
        "assets": {
            name: sha256_file(output_dir / name)
            for name in ASSET_NAMES
        },
        "checksums": str(output_dir / "SHA256SUMS"),
    }


def release_source_paths(source_root: pathlib.Path) -> list[pathlib.Path]:
    relative_files = [
        pathlib.Path("pact.py"),
        pathlib.Path(".pact/VERSION"),
        pathlib.Path(".pact/config.example.toml"),
        pathlib.Path(".pact/baseline.example.toml"),
        pathlib.Path(".pact/fitness.example.toml"),
    ]
    paths = [source_root / relative for relative in relative_files]
    paths.extend(sorted((source_root / "scripts" / "pact").glob("*.py")))
    paths.extend(sorted((source_root / ".pact" / "schema").glob("*.json")))
    paths.extend(
        sorted(
            path
            for path in (source_root / ".pact" / "templates").rglob("*")
            if path.is_file()
        )
    )

    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "release smoke source is incomplete: "
            + ", ".join(str(path) for path in missing)
        )
    return sorted(set(paths), key=lambda path: path.relative_to(source_root).as_posix())


def create_source_archive(
    source_root: pathlib.Path,
    archive_path: pathlib.Path,
) -> pathlib.Path:
    prefix = "PACT-release-smoke"
    with zipfile.ZipFile(
        archive_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for path in release_source_paths(source_root):
            relative = path.relative_to(source_root).as_posix()
            archive.write(path, f"{prefix}/{relative}")
    return archive_path


def run_checked(argv: list[str], *, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "release smoke command failed: "
            + " ".join(argv)
            + f"\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def smoke_install(source_root: pathlib.Path, output_dir: pathlib.Path) -> dict:
    verify_checksums(output_dir)

    run_checked([sys.executable, str(output_dir / "pact.pyz"), "--help"])

    with tempfile.TemporaryDirectory(prefix="pact-release-smoke-") as tmp:
        temp_root = pathlib.Path(tmp)
        archive = create_source_archive(source_root, temp_root / "source.zip")
        archive_sha = sha256_file(archive)
        target = temp_root / "adopted"

        run_checked(
            [
                sys.executable,
                str(output_dir / "pact-bootstrap.py"),
                "init",
                "--target",
                str(target),
                "--archive",
                str(archive),
                "--sha256",
                archive_sha,
                "--apply",
            ]
        )

        run_checked(
            [sys.executable, str(target / "pact.py"), "doctor", "--strict"],
            cwd=target,
        )
        status = run_checked(
            [sys.executable, str(target / "pact.py"), "status", "--strict", "--json"],
            cwd=target,
        )
        run_checked(
            [sys.executable, str(target / "pact.py"), "schema-lint"],
            cwd=target,
        )

        installed_runtime = target / ".pact" / "pact.pyz"
        release_runtime = output_dir / "pact.pyz"
        installed_sha = sha256_file(installed_runtime)
        release_sha = sha256_file(release_runtime)
        if installed_sha != release_sha:
            raise RuntimeError(
                "fresh bootstrap installed a compact runtime different from the "
                f"release asset: {installed_sha} != {release_sha}"
            )

        installed_version = (target / ".pact" / "VERSION").read_text(
            encoding="utf-8"
        ).strip()
        source_version = (source_root / ".pact" / "VERSION").read_text(
            encoding="utf-8"
        ).strip()
        if installed_version != source_version:
            raise RuntimeError(
                f"fresh bootstrap version mismatch: {installed_version} != {source_version}"
            )

        status_data = json.loads(status.stdout)
        if status_data.get("overall") != "pass":
            raise RuntimeError(
                f"fresh bootstrap status did not pass: {status_data!r}"
            )

        return {
            "archive_sha256": archive_sha,
            "release_runtime_sha256": release_sha,
            "installed_runtime_sha256": installed_sha,
            "runtime_version": installed_version,
            "status": status_data.get("overall"),
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and optionally smoke-test PACT release assets"
    )
    parser.add_argument("--source-root", default=str(DEFAULT_ROOT))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    source_root = pathlib.Path(args.source_root).expanduser().resolve()
    output_dir = pathlib.Path(args.output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = pathlib.Path.cwd() / output_dir

    try:
        result = build_assets(source_root, output_dir)
        if args.smoke:
            result["smoke"] = smoke_install(source_root, output_dir)
    except Exception as exc:
        print(f"PACT release assets: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"PACT release assets: {output_dir}")
        for name, digest in result["assets"].items():
            print(f"- {name}: {digest}")
        if args.smoke:
            print(
                "- smoke: fresh bootstrap PASS "
                f"(runtime={result['smoke']['runtime_version']}, "
                f"sha256={result['smoke']['installed_runtime_sha256']})"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
