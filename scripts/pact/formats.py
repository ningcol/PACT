"""PACT stdlib-only TOML configuration and metadata parsing."""

from __future__ import annotations

import pathlib
import re
import tomllib


TOML_FRONT_MATTER = re.compile(
    r"\A\+\+\+\s*\n(.*?)\n\+\+\+\s*(?:\n|\Z)",
    re.DOTALL,
)


class FormatError(ValueError):
    pass


def load_toml(path: pathlib.Path) -> dict:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise FormatError(f"{path}: TOML root must be a table")
    return data


def parse_markdown_metadata(raw: str) -> tuple[dict, str, str | None]:
    match = TOML_FRONT_MATTER.match(raw)
    if not match:
        return {}, raw, None

    try:
        data = tomllib.loads(match.group(1))
    except tomllib.TOMLDecodeError as exc:
        raise FormatError(f"invalid TOML front matter: {exc}") from exc

    return data if isinstance(data, dict) else {}, raw[match.end():], "toml"
