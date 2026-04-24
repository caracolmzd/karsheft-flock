# Mirror Protocol

Flock is compatible with the standard Debian APT repository format. Any mirror that follows the Debian repository layout can be used as a Flock mirror.

---

## Debian Repository Layout

Flock reads the binary package index from the following path relative to the mirror base URL:

```
{mirror_url}/dists/{suite}/main/binary-{arch}/Packages.gz
```

Default values used by `flock resolve`:
- `suite`: `stable`
- `arch`: `amd64`
- `mirror_url`: `https://deb.debian.org/debian`

The full default URL for the package index is:

```
https://deb.debian.org/debian/dists/stable/main/binary-amd64/Packages.gz
```

---

## Package Index Format

`Packages.gz` is a gzip-compressed file containing RFC-2822-style control paragraphs, one per package, separated by blank lines. Flock parses the following fields:

| Field          | Used For                              |
|----------------|---------------------------------------|
| `Package`      | Package name (index key)              |
| `Version`      | Version string stored in lockfile     |
| `Architecture` | Architecture stored in lockfile       |
| `Filename`     | Relative path to `.deb` file          |
| `SHA256`       | Checksum stored in lockfile           |
| `GPG-Fingerprint` | Key fingerprint (for `full` mode)  |

Example Packages entry:

```
Package: curl
Version: 7.88.1-10+deb12u5
Architecture: amd64
Filename: pool/main/c/curl/curl_7.88.1-10+deb12u5_amd64.deb
SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
Description: command line tool for transferring data with URL syntax
```

---

## Mirror URL Configuration

Specify a custom mirror with `--mirror`:

```bash
flock resolve --pkg curl --mirror https://mirror.example.com/debian
```

The mirror URL must:
1. Be reachable over HTTPS.
2. Serve `dists/stable/main/binary-amd64/Packages.gz` at the specified base URL.
3. Serve `.deb` files at the paths listed in `Filename` fields of the package index.

### Using a Regional Mirror

```bash
flock resolve --pkg curl --mirror https://ftp.us.debian.org/debian
```

For a full list of official Debian mirrors: https://www.debian.org/mirror/list

---

## GitHub Pages Hosting

You can host a Flock-compatible mirror on GitHub Pages. This is useful for:
- Private internal package registries
- Curated subsets of Debian packages
- Air-gapped environments with a sync mechanism

### Directory Structure

```
docs/                          # GitHub Pages root
├── dists/
│   └── stable/
│       └── main/
│           └── binary-amd64/
│               ├── Packages       # Uncompressed index
│               └── Packages.gz    # Gzip-compressed index
└── pool/
    └── main/
        └── c/
            └── curl/
                └── curl_7.88.1-10+deb12u5_amd64.deb
```

### Creating a GitHub Pages Mirror

1. **Create a repository** on GitHub for your mirror.

2. **Enable GitHub Pages** from repository settings, serving from the `docs/` directory or `gh-pages` branch.

3. **Create the package index:**

```bash
# Create directory structure
mkdir -p docs/dists/stable/main/binary-amd64
mkdir -p docs/pool/main/c/curl

# Copy .deb files
cp curl_7.88.1-10+deb12u5_amd64.deb docs/pool/main/c/curl/

# Generate Packages index
cat > docs/dists/stable/main/binary-amd64/Packages << 'EOF'
Package: curl
Version: 7.88.1-10+deb12u5
Architecture: amd64
Filename: pool/main/c/curl/curl_7.88.1-10+deb12u5_amd64.deb
SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
Description: command line tool for transferring data with URL syntax

EOF

# Compress
gzip -k docs/dists/stable/main/binary-amd64/Packages
```

4. **Configure Flock to use your mirror:**

```bash
flock resolve --pkg curl --mirror https://myorg.github.io/my-mirror
```

---

## Keeping Mirrors in Sync

For automated mirror synchronization, use the `apt-mirror` tool or a custom GitHub Actions workflow:

```yaml
name: Sync Mirror
on:
  schedule:
    - cron: "0 2 * * *"  # Daily at 02:00 UTC

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Sync packages
        run: |
          apt-get install -y apt-mirror
          apt-mirror /etc/apt/mirror.list
      - name: Regenerate index
        run: |
          gzip -k docs/dists/stable/main/binary-amd64/Packages
      - name: Commit and push
        run: |
          git add docs/
          git commit -m "chore: sync mirror $(date -u +%Y-%m-%d)"
          git push
```

---

## Security Considerations

- Always use HTTPS for mirror URLs. HTTP mirrors are vulnerable to MITM attacks.
- With `--verify=checksum`, a compromised mirror at resolution time is undetected at install time. Use `--verify=full` to mitigate this.
- When hosting a GitHub Pages mirror, enable branch protection on `main` to prevent unauthorized index modifications.
- Consider signing your `Packages` index with GPG and storing the signing key in GitHub Actions Secrets.
