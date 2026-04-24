import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w


def read_manifest(path: Path) -> dict:
    """Read flock.toml manifest file."""
    if not path.exists():
        raise FileNotFoundError(
            f"Manifest file not found: {path}\n"
            "Run 'flock init' to create a new manifest."
        )
    with open(path, "rb") as f:
        return tomllib.load(f)


def write_manifest(path: Path, data: dict) -> None:
    """Write manifest data to flock.toml using TOML format."""
    with open(path, "wb") as f:
        tomli_w.dump(data, f)


def init_manifest(path: Path) -> None:
    """Create a default flock.toml manifest with version and empty package list."""
    data = {
        "flock": {"version": "1"},
        "package": [],
    }
    write_manifest(path, data)
