# Flock Package Format

Flock packages (`.flock`) are thin metadata wrappers around standard Debian `.deb` files. They add provenance, signing, and mirror-hosting metadata without modifying the underlying package.

---

## Overview

A `.flock` file is a TOML document that describes:
- Where to download the underlying `.deb` file
- How to verify its integrity (SHA256 checksum)
- Who signed it (GPG fingerprint)
- Provenance metadata (source, version, architecture)

Flock does **not** repackage or modify `.deb` files. The `.deb` itself remains the canonical artifact; Flock adds a verifiable metadata layer.

---

## File Format

A `.flock` metadata file uses TOML syntax:

```toml
[package]
name = "curl"
version = "7.88.1-10+deb12u5"
architecture = "amd64"
description = "command line tool for transferring data with URL syntax"

[provenance]
mirror = "https://deb.debian.org/debian"
path = "pool/main/c/curl/curl_7.88.1-10+deb12u5_amd64.deb"
url = "https://deb.debian.org/debian/pool/main/c/curl/curl_7.88.1-10+deb12u5_amd64.deb"
source_package = "curl"
source_version = "7.88.1-10+deb12u5"
component = "main"
suite = "stable"

[signing]
sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
gpg_key_fingerprint = "A2166B8DE8BDC3367D1901C11EE2FF37CA8DA16B"
gpg_key_server = "keyserver.ubuntu.com"
signature_url = "https://example.com/packages/curl_7.88.1-10+deb12u5_amd64.deb.sig"
```

---

## Fields Reference

### `[package]` — Core Package Identity

| Field          | Type   | Required | Description                                      |
|----------------|--------|----------|--------------------------------------------------|
| `name`         | string | Yes      | Debian package name (e.g., `curl`)               |
| `version`      | string | Yes      | Full Debian version string                       |
| `architecture` | string | Yes      | Target architecture (e.g., `amd64`, `arm64`)     |
| `description`  | string | No       | Short package description from control file      |

### `[provenance]` — Origin and Location

| Field            | Type   | Required | Description                                         |
|------------------|--------|----------|-----------------------------------------------------|
| `mirror`         | string | Yes      | Base URL of the Debian-compatible mirror             |
| `path`           | string | Yes      | Relative path within the mirror (from `Filename:`)  |
| `url`            | string | Yes      | Full download URL (`mirror` + `/` + `path`)         |
| `source_package` | string | No       | Source package name (from `Source:` field)          |
| `source_version` | string | No       | Source package version                              |
| `component`      | string | No       | Repository component (`main`, `contrib`, `non-free`)|
| `suite`          | string | No       | Distribution suite (e.g., `stable`, `bookworm`)     |

### `[signing]` — Integrity and Authentication

| Field                | Type   | Required             | Description                                    |
|----------------------|--------|----------------------|------------------------------------------------|
| `sha256`             | string | Yes                  | SHA256 hex digest of the `.deb` file           |
| `gpg_key_fingerprint`| string | For `verify=full`    | Full 40-character GPG key fingerprint          |
| `gpg_key_server`     | string | No                   | Key server URL for fingerprint lookup          |
| `signature_url`      | string | No                   | URL to detached `.sig` file                    |

---

## Relationship to `flock.lock`

`flock.lock` aggregates the fields from multiple `.flock` descriptors into a single TOML file managed by the `flock resolve` command. The lockfile format mirrors the `.flock` schema but uses TOML arrays:

```toml
[meta]
generated_by = "flock resolve"
verify_level = "checksum"
timestamp = "2026-04-24T11:00:00Z"

[[package]]
name = "curl"
version = "7.88.1-10+deb12u5"
architecture = "amd64"
sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
url = "https://deb.debian.org/debian/pool/main/c/curl/curl_7.88.1-10+deb12u5_amd64.deb"
```

---

## Hosting on GitHub Pages

`.flock` metadata files can be hosted on GitHub Pages to create a lightweight, auditable package registry:

```
https://<org>.github.io/<repo>/packages/
├── curl/
│   └── curl_7.88.1-10+deb12u5_amd64.flock
├── wget/
│   └── wget_1.21.3-1+b1_amd64.flock
└── index.toml
```

`index.toml` lists all available packages for machine consumption:

```toml
[[package]]
name = "curl"
latest = "7.88.1-10+deb12u5"
flock_url = "https://example.github.io/packages/curl/curl_7.88.1-10+deb12u5_amd64.flock"

[[package]]
name = "wget"
latest = "1.21.3-1+b1"
flock_url = "https://example.github.io/packages/wget/wget_1.21.3-1+b1_amd64.flock"
```

---

## Versioning

The `.flock` format is versioned. A `format_version` field at the top level indicates compatibility:

```toml
format_version = "1"
```

Future versions will increment this field. Flock will refuse to install packages from an unsupported format version with a clear error message.

---

## Design Principles

1. **Non-destructive**: `.deb` files are never modified. Flock only adds metadata.
2. **Auditable**: All fields map to verifiable facts (checksums, fingerprints, URLs).
3. **Mirror-agnostic**: The provenance section records the original mirror, enabling mirror fallback.
4. **Human-readable**: TOML format is easy to review in pull requests and audit logs.
