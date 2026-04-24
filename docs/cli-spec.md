# Flock CLI Reference

Complete reference for the `flock` command-line interface.

---

## Global Options

```
flock [OPTIONS] COMMAND [ARGS]...
```

| Option          | Description                              |
|-----------------|------------------------------------------|
| `--version`     | Show version and exit                    |
| `--help`        | Show help message and exit               |

---

## Commands

### `flock init`

Initialize a `flock.toml` manifest in the current directory.

**Usage:**
```bash
flock init
```

**Description:**

Creates a new `flock.toml` file in the current working directory with a minimal scaffold:

```toml
[flock]
version = "1"

[[package]]
```

Fails with an error if `flock.toml` already exists. Remove or rename the existing file before reinitializing.

**Options:** None.

**Exit codes:**
| Code | Meaning                                  |
|------|------------------------------------------|
| 0    | Success — `flock.toml` created           |
| 1    | `flock.toml` already exists              |

**Examples:**

```bash
# Initialize a new manifest
flock init

# Force reinitialize (remove existing first)
rm flock.toml && flock init
```

---

### `flock resolve`

Resolve package metadata from a Debian mirror and write `flock.lock`.

**Usage:**
```bash
flock resolve [OPTIONS]
```

**Description:**

Downloads the `Packages.gz` index from the specified Debian mirror, looks up each requested package, and writes a `flock.lock` file containing:
- Package name, version, architecture
- SHA256 checksum
- Download URL
- (If `--verify=full`) GPG key fingerprint

The generated `flock.lock` should be committed to version control.

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--pkg NAME` | | string (multiple) | *required* | Package name to resolve. May be specified multiple times. |
| `--verify LEVEL` | | choice | `checksum` | Verification level: `checksum`, `full`, or `none`. |
| `--mirror URL` | | string | `https://deb.debian.org/debian` | Debian mirror base URL. |
| `--help` | | | | Show help and exit. |

**Verification levels:**

| Level      | Effect at resolve time                        |
|------------|-----------------------------------------------|
| `checksum` | Records SHA256 from mirror index              |
| `full`     | Records SHA256 and GPG fingerprint            |
| `none`     | Records URL only — no integrity metadata      |

**Exit codes:**
| Code | Meaning                                            |
|------|----------------------------------------------------|
| 0    | Success — `flock.lock` written                     |
| 1    | Package not found, network error, or invalid input |

**Examples:**

```bash
# Resolve a single package
flock resolve --pkg curl

# Resolve multiple packages
flock resolve --pkg curl --pkg wget --pkg jq

# Use a custom mirror
flock resolve --pkg curl --mirror https://ftp.us.debian.org/debian

# Enable full GPG verification in the lockfile
flock resolve --pkg curl --verify full

# Use a GitHub Pages mirror
flock resolve --pkg curl --mirror https://myorg.github.io/my-mirror
```

**Output format:**

```
Resolving 2 package(s) from https://deb.debian.org/debian ...
Wrote flock.lock with 2 package(s).
  curl 7.88.1-10+deb12u5 (amd64)
  wget 1.21.3-1+b1 (amd64)
```

---

### `flock install`

Install packages from `flock.lock`.

**Usage:**
```bash
flock install [OPTIONS]
```

**Description:**

Reads `flock.lock` from the current directory, downloads each listed package, verifies integrity (according to `--verify`), and installs using `dpkg -i`.

Requires a Debian-based system with `dpkg` installed. May require root privileges for `dpkg` to succeed.

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--verify LEVEL` | choice | `checksum` | Verification level: `checksum`, `full`, or `none`. |
| `--i-understand-the-risk` | flag | false | Required when `--verify=none`. Explicitly acknowledges disabled verification. |
| `--help` | | | Show help and exit. |

**Verification behavior:**

| Level      | SHA256 check | GPG check | Risk flag required |
|------------|--------------|-----------|--------------------|
| `checksum` | Yes          | No        | No                 |
| `full`     | Yes          | Yes       | No                 |
| `none`     | No           | No        | **Yes**            |

**Exit codes:**
| Code | Meaning                                              |
|------|------------------------------------------------------|
| 0    | All packages installed successfully                  |
| 1    | Verification failed, download error, or dpkg error   |

**Examples:**

```bash
# Install with default checksum verification
flock install

# Install with full GPG + checksum verification
flock install --verify full

# Emergency install (no verification — dangerous)
flock install --verify none --i-understand-the-risk

# Run as root (often required for dpkg)
sudo flock install --verify full
```

**Output format:**

```
Installing 2 package(s) [verify=checksum]...
  Downloading curl (7.88.1-10+deb12u5)...
  Verifying checksum for curl...
  OK: curl (7.88.1-10+deb12u5)
  Downloading wget (1.21.3-1+b1)...
  Verifying checksum for wget...
  OK: wget (1.21.3-1+b1)

Installing 2 package(s) with dpkg...
Installation complete.
All packages installed successfully.
```

---

## Error Reference

| Error Message | Cause | Resolution |
|---------------|-------|------------|
| `Manifest file not found` | `flock.toml` missing | Run `flock init` |
| `Lockfile not found` | `flock.lock` missing | Run `flock resolve` |
| `Package not found in mirror index` | Package name not in `Packages.gz` | Check spelling or try a different mirror |
| `SHA256 checksum mismatch` | Downloaded file differs from lockfile | Mirror may be compromised; re-resolve or use `--verify=full` |
| `GPG verification failed` | Signature invalid or fingerprint mismatch | Check key fingerprint in `flock.lock` |
| `--verify=none requires --i-understand-the-risk` | Safety gate | Add `--i-understand-the-risk` flag |
| `dpkg not found` | Not on a Debian-based system | Use a Debian/Ubuntu host |
| `dpkg exited with code 1` | Dependency issues | Run `apt-get install -f` |

---

## Configuration

Flock currently reads configuration from command-line flags only. A future version will support `flock.toml` configuration:

```toml
[flock]
version = "1"
mirror = "https://ftp.us.debian.org/debian"
verify = "checksum"
```

---

## Shell Completion

Generate shell completion scripts:

```bash
# Bash
_FLOCK_COMPLETE=bash_source flock > ~/.flock-complete.bash
echo ". ~/.flock-complete.bash" >> ~/.bashrc

# Zsh
_FLOCK_COMPLETE=zsh_source flock > ~/.flock-complete.zsh
echo ". ~/.flock-complete.zsh" >> ~/.zshrc

# Fish
_FLOCK_COMPLETE=fish_source flock > ~/.config/fish/completions/flock.fish
```
