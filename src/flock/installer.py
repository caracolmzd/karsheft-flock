import subprocess
import sys
import tempfile
from pathlib import Path

import requests

from .verify import VerificationError, VERIFY_LEVELS, verify_checksum, verify_gpg


def install_packages(
    lockfile_data: dict,
    verify_level: str,
    i_understand_the_risk: bool = False,
) -> None:
    """
    Install packages from a parsed flock.lock data structure.

    For verify_level="none": requires i_understand_the_risk=True.
    Downloads each .deb to a temporary directory, verifies, then runs dpkg -i.
    """
    if verify_level not in VERIFY_LEVELS:
        raise ValueError(f"Invalid verify_level '{verify_level}'. Must be one of: {VERIFY_LEVELS}")

    if verify_level == "none":
        if not i_understand_the_risk:
            raise VerificationError(
                "verify_level='none' requires --i-understand-the-risk flag. "
                "This disables all verification and is dangerous."
            )
        print(
            "WARNING: Package verification is DISABLED. "
            "This is dangerous and should only be used in emergency situations.",
            file=sys.stderr,
        )

    packages = lockfile_data.get("package", [])
    if not packages:
        print("No packages to install.")
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        deb_paths: list[Path] = []

        for pkg in packages:
            name = pkg.get("name", "unknown")
            version = pkg.get("version", "unknown")
            url = pkg.get("url", "")
            expected_sha256 = pkg.get("sha256", "")
            gpg_fingerprint = pkg.get("gpg_key_fingerprint", "")

            print(f"  Downloading {name} ({version})...")

            deb_filename = f"{name}_{version}_amd64.deb"
            deb_path = tmp_path / deb_filename

            try:
                response = requests.get(url, timeout=120, stream=True)
                response.raise_for_status()
                with open(deb_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=65536):
                        f.write(chunk)
            except requests.RequestException as e:
                raise RuntimeError(f"Failed to download {name} from {url}: {e}") from e

            if verify_level in ("checksum", "full"):
                print(f"  Verifying checksum for {name}...")
                verify_checksum(deb_path, expected_sha256)

            if verify_level == "full":
                print(f"  Verifying GPG signature for {name}...")
                if not gpg_fingerprint:
                    raise VerificationError(
                        f"GPG fingerprint missing for package '{name}' "
                        "but verify_level='full' requires it."
                    )
                verify_gpg(deb_path, gpg_fingerprint)

            deb_paths.append(deb_path)
            print(f"  OK: {name} ({version})")

        print(f"\nInstalling {len(deb_paths)} package(s) with dpkg...")
        deb_strs = [str(p) for p in deb_paths]

        try:
            result = subprocess.run(
                ["dpkg", "-i"] + deb_strs,
                check=False,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            if result.returncode != 0:
                raise RuntimeError(
                    f"dpkg exited with code {result.returncode}. "
                    "You may need to run as root or fix dependencies with: apt-get install -f"
                )
        except FileNotFoundError:
            raise RuntimeError(
                "dpkg not found. Flock requires a Debian-based system with dpkg installed."
            )

        print("Installation complete.")
