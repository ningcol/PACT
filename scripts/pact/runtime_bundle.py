"""Build the deterministic single-file PACT runtime archive."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
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
    temporary = output.with_name(f".{output.name}.tmp")
    if temporary.exists():
        temporary.unlink()

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

        temporary.replace(output)
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
