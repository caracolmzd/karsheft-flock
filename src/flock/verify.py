import hashlib
from pathlib import Path
from typing import Optional

VERIFY_LEVELS = ("checksum", "full", "none")


class VerificationError(Exception):
    """Raised when package verification fails."""
    pass


def verify_checksum(path: Path, expected_sha256: str) -> None:
    """
    Verify SHA256 checksum of a file.

    Raises VerificationError if the computed hash does not match expected_sha256.
    """
    sha256 = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
    except OSError as e:
        raise VerificationError(f"Cannot read file for checksum verification: {path}: {e}") from e

    computed = sha256.hexdigest()
    if computed != expected_sha256:
        raise VerificationError(
            f"SHA256 checksum mismatch for {path.name}:\n"
            f"  expected: {expected_sha256}\n"
            f"  computed: {computed}"
        )


def verify_gpg(
    path: Path,
    key_fingerprint: str,
    keyring_path: Optional[Path] = None,
) -> None:
    """
    Verify GPG signature of a file against a known key fingerprint.

    Raises VerificationError if verification fails or gnupg is unavailable.
    """
    try:
        import gnupg
    except ImportError as e:
        raise VerificationError(
            "python-gnupg is required for GPG verification. "
            "Install it with: pip install python-gnupg"
        ) from e

    gpg_kwargs = {}
    if keyring_path is not None:
        gpg_kwargs["gnupghome"] = str(keyring_path)

    gpg = gnupg.GPG(**gpg_kwargs)

    sig_path = Path(str(path) + ".sig")
    if sig_path.exists():
        with open(sig_path, "rb") as sig_file:
            result = gpg.verify_file(sig_file, str(path))
    else:
        # Try detached verification — file may be self-signed
        with open(path, "rb") as f:
            result = gpg.verify_file(f)

    if not result:
        raise VerificationError(
            f"GPG verification failed for {path.name}. "
            f"Expected fingerprint: {key_fingerprint}"
        )

    actual_fingerprint = result.fingerprint or ""
    if key_fingerprint and actual_fingerprint.upper() != key_fingerprint.upper():
        raise VerificationError(
            f"GPG key fingerprint mismatch for {path.name}:\n"
            f"  expected: {key_fingerprint}\n"
            f"  actual:   {actual_fingerprint}"
        )
