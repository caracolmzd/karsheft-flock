# Flock Trust Model

Flock provides three verification tiers for installing Debian packages. The default tier balances security and practicality for most use cases.

---

## Verification Tiers

### 1. `checksum` (Default)

**What it does:** Verifies the SHA256 hash of each downloaded `.deb` file against the hash recorded in `flock.lock`.

**How it works:**
- During `flock resolve`, the SHA256 hash is fetched from the mirror's `Packages.gz` index and written into `flock.lock`.
- During `flock install`, the downloaded `.deb` is hashed locally and compared to the stored value.
- If the hashes differ, installation is aborted with a `VerificationError`.

**Source of truth:** `flock.lock` is the authoritative record of expected hashes. It should be committed to version control and treated as read-only at install time.

**When to use:**
- CI/CD pipelines where you control the mirror and trust the resolution step.
- Development environments where speed matters and the mirror is known-good.
- Any environment where you need reproducibility but not full cryptographic chain-of-custody.

**Limitations:**
- Trusts that the mirror was not compromised *at resolution time*.
- Does not verify the package publisher's identity.

---

### 2. `full` (GPG + SHA256)

**What it does:** Verifies both SHA256 checksum and GPG signature against a known key fingerprint.

**How it works:**
- During `flock resolve --verify=full`, the package index entry's `GPG-Fingerprint` field (if present) is stored in `flock.lock` alongside the SHA256.
- During `flock install --verify=full`:
  1. SHA256 checksum is verified first.
  2. GPG signature is verified using `python-gnupg` against the stored fingerprint.
  3. The actual signing key fingerprint is compared to the expected fingerprint. Any mismatch aborts installation.

**When to use:**
- Production systems where package authenticity must be cryptographically proven.
- Air-gapped or regulated environments requiring audit trails.
- Situations where the package supply chain must be fully verified end-to-end.

**Requirements:**
- `python-gnupg` must be installed (`pip install python-gnupg`).
- GPG must be available on the system (`gpg` binary).
- The mirror must include `GPG-Fingerprint` metadata or provide `.sig` sidecar files.

---

### 3. `none` (Emergency Only)

**What it does:** Skips all cryptographic verification. Packages are downloaded and installed without any integrity checks.

**How it works:**
- No SHA256 or GPG verification is performed.
- Packages are passed directly to `dpkg -i`.

**Safety gate:** Using `--verify=none` requires explicitly passing `--i-understand-the-risk` on the command line. This flag cannot be set via configuration — it must be a deliberate human action.

```bash
flock install --verify=none --i-understand-the-risk
```

**When to use:**
- Emergency recovery scenarios where the mirror index is unavailable.
- Internal trusted networks where the packages have been pre-screened by other means.
- Never in production CI/CD without compensating controls.

**WARNING:** `--verify=none` removes all security guarantees. A compromised mirror or man-in-the-middle attack will go undetected. Use only as a last resort.

---

## The Lockfile as Source of Truth

`flock.lock` is the cryptographic anchor of the Flock trust model:

- **Generated once** by `flock resolve` and committed to version control.
- **Never modified** at install time. The constant `LOCKFILE_IS_READ_ONLY_AT_INSTALL_TIME = True` documents this contract in code.
- **Auditable**: Contains package names, versions, architectures, SHA256 hashes, mirror URLs, and (in `full` mode) GPG key fingerprints.
- **Deterministic**: Given the same `flock.lock`, every `flock install` produces the same set of packages.

If `flock.lock` is modified between resolution and installation (e.g., by a malicious CI step), `assert_lockfile_not_modified()` can detect tampering by comparing the in-memory snapshot taken at read time against the current state.

---

## Trust Hierarchy Summary

| Tier       | SHA256 | GPG | Risk Flag Required | Recommended For         |
|------------|--------|-----|--------------------|-------------------------|
| `checksum` | ✅     | ❌  | No                 | CI/CD, development      |
| `full`     | ✅     | ✅  | No                 | Production, regulated   |
| `none`     | ❌     | ❌  | **Yes**            | Emergency only          |

---

## Security Recommendations

1. **Commit `flock.lock` to version control.** It is a security artifact, not a build artifact.
2. **Use `--verify=full` in production.** Configure your mirror to expose GPG fingerprints.
3. **Pin your mirror URL.** Changing mirrors mid-project can silently introduce different packages.
4. **Rotate GPG keys carefully.** Update `flock.lock` by re-running `flock resolve` after a key rotation.
5. **Treat `--i-understand-the-risk` as an alarm.** Any use of this flag should trigger a security review.
