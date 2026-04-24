import hashlib
import pytest
from pathlib import Path

from flock.verify import VerificationError, verify_checksum
from flock.installer import install_packages


def test_verify_checksum_correct_hash(tmp_path):
    test_file = tmp_path / "test.deb"
    content = b"fake deb content for testing"
    test_file.write_bytes(content)

    expected_sha256 = hashlib.sha256(content).hexdigest()
    # Should not raise
    verify_checksum(test_file, expected_sha256)


def test_verify_checksum_wrong_hash(tmp_path):
    test_file = tmp_path / "test.deb"
    content = b"fake deb content for testing"
    test_file.write_bytes(content)

    wrong_hash = "0" * 64
    with pytest.raises(VerificationError, match="mismatch"):
        verify_checksum(test_file, wrong_hash)


def test_verify_checksum_missing_file(tmp_path):
    test_file = tmp_path / "nonexistent.deb"
    with pytest.raises(VerificationError, match="Cannot read"):
        verify_checksum(test_file, "abc123")


def test_install_packages_none_without_risk_raises():
    lockfile_data = {
        "meta": {"verify_level": "none"},
        "package": [
            {
                "name": "curl",
                "version": "7.88.1",
                "architecture": "amd64",
                "sha256": "abc123",
                "url": "https://example.com/curl.deb",
            }
        ],
    }
    with pytest.raises(VerificationError, match="--i-understand-the-risk"):
        install_packages(lockfile_data, verify_level="none", i_understand_the_risk=False)


def test_install_packages_empty_no_error():
    lockfile_data = {"meta": {}, "package": []}
    # Should complete without error (no packages to install)
    install_packages(lockfile_data, verify_level="checksum", i_understand_the_risk=False)
