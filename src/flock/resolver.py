import gzip
import io
import sys
from typing import Optional

import requests

from .verify import VERIFY_LEVELS


class PackageNotFoundError(Exception):
    """Raised when a requested package cannot be found in the mirror."""
    pass


def _parse_packages_file(content: str) -> dict[str, dict]:
    """Parse a Debian Packages control file into a dict keyed by package name."""
    packages: dict[str, dict] = {}
    current: dict[str, str] = {}
    current_key: Optional[str] = None

    for line in content.splitlines():
        if line == "":
            if current and "Package" in current:
                packages[current["Package"]] = current
            current = {}
            current_key = None
            continue

        if line.startswith(" ") or line.startswith("\t"):
            # Continuation line
            if current_key:
                current[current_key] = current.get(current_key, "") + "\n" + line.strip()
            continue

        if ":" in line:
            key, _, value = line.partition(":")
            current_key = key.strip()
            current[current_key] = value.strip()

    if current and "Package" in current:
        packages[current["Package"]] = current

    return packages


def resolve_packages(
    packages: list[str],
    mirror_url: str,
    verify_level: str,
) -> list[dict]:
    """
    Resolve package metadata from a Debian-compatible mirror.

    Downloads and parses the Packages.gz index from:
        mirror_url/dists/stable/main/binary-amd64/Packages.gz

    Returns a list of dicts with package metadata suitable for writing to flock.lock.
    Raises PackageNotFoundError if any requested package is not found.
    Raises requests.RequestException on network errors.
    """
    if verify_level not in VERIFY_LEVELS:
        raise ValueError(f"Invalid verify_level '{verify_level}'. Must be one of: {VERIFY_LEVELS}")

    packages_url = f"{mirror_url.rstrip('/')}/dists/stable/main/binary-amd64/Packages.gz"

    try:
        response = requests.get(packages_url, timeout=60)
        response.raise_for_status()
    except requests.ConnectionError as e:
        raise requests.RequestException(
            f"Cannot connect to mirror at {mirror_url}: {e}"
        ) from e
    except requests.HTTPError as e:
        raise requests.RequestException(
            f"Mirror returned HTTP error fetching package index: {e}"
        ) from e
    except requests.Timeout as e:
        raise requests.RequestException(
            f"Timed out fetching package index from {mirror_url}"
        ) from e

    try:
        decompressed = gzip.decompress(response.content)
        content = decompressed.decode("utf-8", errors="replace")
    except Exception as e:
        raise ValueError(f"Failed to decompress Packages.gz from mirror: {e}") from e

    index = _parse_packages_file(content)

    results: list[dict] = []
    missing: list[str] = []

    for pkg_name in packages:
        if pkg_name not in index:
            missing.append(pkg_name)
            continue

        entry = index[pkg_name]
        filename = entry.get("Filename", "")
        pkg_url = f"{mirror_url.rstrip('/')}/{filename}"
        sha256 = entry.get("SHA256", "")
        version = entry.get("Version", "unknown")
        architecture = entry.get("Architecture", "amd64")

        pkg_record: dict = {
            "name": pkg_name,
            "version": version,
            "architecture": architecture,
            "sha256": sha256,
            "url": pkg_url,
        }

        if verify_level == "full":
            # Include GPG key fingerprint placeholder — actual signing verification
            # happens at install time via verify_gpg()
            pkg_record["gpg_key_fingerprint"] = entry.get("GPG-Fingerprint", "")

        results.append(pkg_record)

    if missing:
        raise PackageNotFoundError(
            f"The following packages were not found in the mirror index: {', '.join(missing)}\n"
            f"Mirror: {mirror_url}"
        )

    return results
