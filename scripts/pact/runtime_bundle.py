"""Build the deterministic single-file PACT runtime archive."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import tempfile
import time
import zipfile


FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
RUNTIME_DIR = pathlib.Path("scripts/pact")
BUNDLE_REL = pathlib.Path(".pact/cache/distribution/pact.pyz")


def runtime_sources(source_root: pathlib.Path) -> list[pathlib.Path]:
    runtime_dir = source_root / RUNTIME_DIR
    if not runtime_dir.is_dir():
        return []

    return sorted(
        path
        for path in runtime_dir.iterdir()
        if path.is_file()
        and path.suffix == ".py"
        and path.name != "__main__.py"
    )


def _write_entry(
    archive: zipfile.ZipFile,
    name: str,
    content: bytes,
) -> None:
    info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o100644 << 16
    info.create_system = 3
    archive.writestr(info, content)


WINDOWS_RUNTIME_REPLACE_RETRIES = 15
WINDOWS_RUNTIME_RETRY_BASE_SECONDS = 0.01


def _retryable_windows_runtime_replace(error: OSError) -> bool:
    """Only transient Windows sharing denials merit a bounded retry."""
    return (
        os.name == "nt"
        and isinstance(error, PermissionError)
        and getattr(error, "winerror", None) in {5, 32}
    )


def _publish_runtime(temporary: pathlib.Path, output: pathlib.Path) -> None:
    """Atomically replace complete ZIP under short-lived Windows sharing locks."""
    for attempt in range(WINDOWS_RUNTIME_REPLACE_RETRIES):
        try:
            os.replace(temporary, output)
            return
        except OSError as exc:
            if (
                attempt + 1 >= WINDOWS_RUNTIME_REPLACE_RETRIES
                or not _retryable_windows_runtime_replace(exc)
            ):
                raise
            time.sleep(WINDOWS_RUNTIME_RETRY_BASE_SECONDS * (attempt + 1))


def build_runtime_bundle(
    source_root: pathlib.Path,
    output: pathlib.Path,
) -> pathlib.Path:
    source_root = source_root.resolve()
    sources = runtime_sources(source_root)
    if not sources:
        raise FileNotFoundError(
            f"PACT runtime sources not found under {source_root / RUNTIME_DIR}"
        )

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Concurrent source installs/upgrades can both need a compact runtime.
    # Never share or unlink another build's staged ZIP filename.
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.pact-runtime-",
        suffix=".tmp",
        dir=output.parent,
    )
    os.close(fd)
    temporary = pathlib.Path(temporary_name)

    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_STORED,
        ) as archive:
            _write_entry(
                archive,
                "__main__.py",
                (
                    "from pact import main\n"
                    "raise SystemExit(main())\n"
                ).encode("utf-8"),
            )
            for path in sources:
                _write_entry(
                    archive,
                    path.name,
                    path.read_text(encoding="utf-8")
                    .replace("\r\n", "\n")
                    .replace("\r", "\n")
                    .encode("utf-8"),
                )

            _write_entry(
                archive,
                "pact_resources/__init__.py",
                b'"""Embedded PACT runtime resources."""\n',
            )
            schema_dir = source_root / ".pact" / "schema"
            for path in sorted(schema_dir.glob("*.json")):
                _write_entry(
                    archive,
                    f"pact_resources/schema/{path.name}",
                    path.read_text(encoding="utf-8")
                    .replace("\r\n", "\n")
                    .replace("\r", "\n")
                    .encode("utf-8"),
                )

        # Keep mkstemp's restrictive creation mode. Chmod'ing 0644 based
        # only on the source's permissions would override a caller's umask
        # (such as 077) and expose an adopted runtime to other OS users.
        # An administrator can explicitly grant wider access after install.
        _publish_runtime(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()

    return output


def ensure_runtime_bundle(source_root: pathlib.Path) -> pathlib.Path:
    source_root = source_root.resolve()

    installed = source_root / ".pact" / "pact.pyz"
    runtime_dir = source_root / RUNTIME_DIR

    # Adopted projects may retain only scripts/pact/pact.py as a compatibility
    # shim for project-owned guidance written before compact runtime existed.
    # That directory is not a source checkout and must never be used to rebuild
    # the runtime archive.
    source_builder = runtime_dir / "runtime_bundle.py"
    if installed.is_file() and not source_builder.is_file():
        return installed

    output = source_root / BUNDLE_REL
    return build_runtime_bundle(source_root, output)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic single-file PACT runtime"
    )
    parser.add_argument("--source-root", default=str(pathlib.Path(__file__).resolve().parents[2]))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source_root = pathlib.Path(args.source_root).expanduser().resolve()
    output = pathlib.Path(args.output).expanduser()
    if not output.is_absolute():
        output = pathlib.Path.cwd() / output
    output = build_runtime_bundle(source_root, output)
    print(f"PACT compact runtime: {output} sha256={sha256(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
