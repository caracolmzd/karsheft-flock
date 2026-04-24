# CI/CD Integration Guide

This guide covers integrating Flock into GitHub Actions workflows for reproducible, verified Debian package installation.

---

## Quick Start

```yaml
- name: Install packages with Flock
  run: |
    pip install karsheft-flock
    flock install --verify=checksum
```

Assumes `flock.lock` is committed to the repository.

---

## Recommended Verify Levels by Environment

| Environment       | Recommended Level | Rationale                                              |
|-------------------|-------------------|--------------------------------------------------------|
| Production        | `full`            | Maximum security; GPG + SHA256 verification            |
| Staging           | `checksum`        | Reproducibility without GPG infrastructure overhead    |
| Development CI    | `checksum`        | Fast, reproducible, minimal setup                      |
| Emergency hotfix  | `none` + flag     | Only when lockfile is stale and time is critical       |

---

## Complete GitHub Actions Workflow

```yaml
name: Build and Install

on:
  push:
    branches: [main]
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Flock
        run: pip install karsheft-flock

      - name: Cache downloaded .deb files
        uses: actions/cache@v4
        with:
          path: ~/.cache/flock
          key: flock-${{ runner.os }}-${{ hashFiles('flock.lock') }}
          restore-keys: |
            flock-${{ runner.os }}-

      - name: Install system packages
        run: sudo flock install --verify=checksum

      - name: Build application
        run: make build
```

---

## Production Workflow with Full GPG Verification

```yaml
name: Production Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Flock
        run: pip install karsheft-flock

      - name: Import GPG signing key
        run: |
          echo "${{ secrets.MIRROR_GPG_PUBLIC_KEY }}" | gpg --import
        env:
          GNUPGHOME: ${{ runner.temp }}/.gnupg

      - name: Install packages with full verification
        run: sudo flock install --verify=full
        env:
          GNUPGHOME: ${{ runner.temp }}/.gnupg

      - name: Deploy
        run: ./deploy.sh
```

Store the mirror's public GPG key in a GitHub Actions secret named `MIRROR_GPG_PUBLIC_KEY`.

---

## Caching Strategies

### Cache by Lockfile Hash (Recommended)

Cache downloaded `.deb` files keyed by the lockfile content. Any change to `flock.lock` (new package version or new package) invalidates the cache:

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/flock
    key: flock-${{ runner.os }}-${{ hashFiles('flock.lock') }}
    restore-keys: |
      flock-${{ runner.os }}-
```

### Cache by Week (Rotating)

For large dependency sets, cache by ISO week to limit cache size growth:

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/flock
    key: flock-${{ runner.os }}-${{ hashFiles('flock.lock') }}-${{ env.WEEK }}
    restore-keys: |
      flock-${{ runner.os }}-${{ hashFiles('flock.lock') }}-
      flock-${{ runner.os }}-
  env:
    WEEK: ${{ steps.date.outputs.week }}

- id: date
  run: echo "week=$(date +%Y-W%V)" >> $GITHUB_OUTPUT
```

### No Cache (Security-Sensitive Builds)

For maximum security, disable caching entirely so every build re-downloads and re-verifies:

```yaml
- name: Install packages (no cache)
  run: sudo flock install --verify=full
# No cache step — always fresh download + verification
```

---

## Resolving Packages in CI

Run `flock resolve` as part of a dependency update workflow, not on every build:

```yaml
name: Update Lockfile

on:
  schedule:
    - cron: "0 6 * * 1"  # Every Monday at 06:00 UTC
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Flock
        run: pip install karsheft-flock

      - name: Re-resolve packages
        run: |
          flock resolve \
            --pkg curl \
            --pkg wget \
            --pkg jq \
            --verify checksum \
            --mirror https://deb.debian.org/debian

      - name: Create pull request
        uses: peter-evans/create-pull-request@v6
        with:
          title: "chore: update flock.lock"
          body: |
            Automated lockfile update from `flock resolve`.

            Review the diff to confirm version changes are expected.
          branch: "chore/update-flock-lock"
          commit-message: "chore: update flock.lock"
```

---

## Reusable Workflow

Define a reusable workflow for consistent package installation across multiple repositories:

```yaml
# .github/workflows/flock-install.yml
name: Flock Install (Reusable)

on:
  workflow_call:
    inputs:
      verify_level:
        description: "Verification level"
        required: false
        default: "checksum"
        type: string
      mirror:
        description: "Mirror URL"
        required: false
        default: "https://deb.debian.org/debian"
        type: string

jobs:
  install:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install karsheft-flock
      - uses: actions/cache@v4
        with:
          path: ~/.cache/flock
          key: flock-${{ runner.os }}-${{ hashFiles('flock.lock') }}
      - run: sudo flock install --verify=${{ inputs.verify_level }}
```

Call it from other workflows:

```yaml
jobs:
  install-packages:
    uses: ./.github/workflows/flock-install.yml
    with:
      verify_level: full
```

---

## Security Hardening

### Pin Flock Version

Always pin the `karsheft-flock` version in CI/CD to avoid supply chain risks from upstream updates.

### Verify Flock Itself

In high-security environments, verify the integrity of the `karsheft-flock` distribution artifact before use by comparing its checksum against a known-good hash stored in the repository.

### Use Read-Only Tokens

When `flock resolve` runs in CI, it only needs read access to the mirror. Ensure the GitHub Actions token has minimal permissions:

```yaml
permissions:
  contents: read
```

### Audit Lockfile Changes

Require PR review for any `flock.lock` changes by adding it to `CODEOWNERS`:

```
# .github/CODEOWNERS
flock.lock @security-team
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `dpkg: error: requested operation requires superuser privilege` | Run with `sudo flock install` |
| `GPG verification failed` | Import the mirror signing key before running `flock install --verify=full` |
| `Lockfile not found` | Ensure `flock.lock` is committed to the repository |
| `Package not found in mirror index` | Check package name spelling; mirror may not have the package |
| Cache not restored | Verify the cache key matches between save and restore steps |
| `dpkg exited with code 1` | Run `sudo apt-get install -f` to fix broken dependencies |
