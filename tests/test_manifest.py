import pytest
from pathlib import Path

from flock.manifest import init_manifest, read_manifest, write_manifest


def test_init_manifest_creates_file(tmp_path):
    manifest_path = tmp_path / "flock.toml"
    assert not manifest_path.exists()
    init_manifest(manifest_path)
    assert manifest_path.exists()


def test_init_manifest_has_flock_section(tmp_path):
    manifest_path = tmp_path / "flock.toml"
    init_manifest(manifest_path)
    data = read_manifest(manifest_path)
    assert "flock" in data
    assert data["flock"]["version"] == "1"


def test_read_manifest_missing_file(tmp_path):
    manifest_path = tmp_path / "flock.toml"
    with pytest.raises(FileNotFoundError, match="flock init"):
        read_manifest(manifest_path)


def test_write_and_read_manifest_roundtrip(tmp_path):
    manifest_path = tmp_path / "flock.toml"
    data = {
        "flock": {"version": "1"},
        "package": [{"name": "curl"}, {"name": "wget"}],
    }
    write_manifest(manifest_path, data)
    loaded = read_manifest(manifest_path)
    assert loaded["flock"]["version"] == "1"
    assert len(loaded["package"]) == 2
    assert loaded["package"][0]["name"] == "curl"
    assert loaded["package"][1]["name"] == "wget"
