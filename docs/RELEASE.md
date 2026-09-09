# GitHub Release and checksum install

This path pins the hosted deploy compose file. It is not the `reviewer` CLI
installer. For the runner command see [INSTALL.md](INSTALL.md).

## What a release contains

Each tagged release publishes:

| File | Purpose |
|---|---|
| `pr-reviewer-<version>-compose.release.yml` | Rendered compose file for hosted deploy |
| `SHA256SUMS` | sha256 digest for the compose file |
| `sbom.spdx.json` | SPDX SBOM from syft (CI release workflow) |

Version comes from `pyproject.toml` (`project.version`). Tag names use a `v`
prefix (`v0.1.0` for version `0.1.0`).

## Build assets locally

Requires Docker (same as `scripts/build-local-release.sh`):

```sh
sh scripts/build-local-release.sh dist
cat dist/SHA256SUMS
```

## Install from a local build (offline proof)

```sh
mkdir -p /tmp/pr-reviewer-release-prefix
sh scripts/install-from-release.sh --dist dist --prefix /tmp/pr-reviewer-release-prefix
ls /tmp/pr-reviewer-release-prefix
```

The script verifies `SHA256SUMS` before copying the compose file.

## Install from a published GitHub Release

After a release exists on GitHub:

```sh
mkdir -p /tmp/pr-reviewer-release-prefix
sh scripts/install-from-release.sh --version 0.1.0 --prefix /tmp/pr-reviewer-release-prefix
```

Or download manually:

```sh
VERSION=0.1.0
TAG=v${VERSION}
ASSET=pr-reviewer-${VERSION}-compose.release.yml
curl -fsSL "https://github.com/the-niresh/plug-and-play-reviewer/releases/download/${TAG}/SHA256SUMS" -o SHA256SUMS
curl -fsSL "https://github.com/the-niresh/plug-and-play-reviewer/releases/download/${TAG}/${ASSET}" -o "${ASSET}"
sh scripts/install.sh --archive "${ASSET}" --checksum-file SHA256SUMS --prefix /tmp/prefix
```

Use the verified compose file with your env vars and `docker compose -f ...`.

## Publish a release (owner)

Prerequisites: push access, `gh auth login`, Docker on the runner.

1. Ensure `main` is ready and version in `pyproject.toml` is correct.
2. Commit and push.
3. Tag and push:

```sh
git tag v0.1.0
git push origin v0.1.0
```

4. GitHub Actions workflow `.github/workflows/release.yml` runs on `v*` tags,
   builds assets, and creates the Release with attachments.
5. Verify:

```sh
gh release view v0.1.0 --repo the-niresh/plug-and-play-reviewer
gh release download v0.1.0 --repo the-niresh/plug-and-play-reviewer -D /tmp/release-check
cat /tmp/release-check/SHA256SUMS
```

Manual fallback if CI is unavailable:

```sh
sh scripts/build-local-release.sh dist
gh release create v0.1.0 dist/* --repo the-niresh/plug-and-play-reviewer --title "v0.1.0"
```

Proof report: [reports/release-checksum-install-proof.md](reports/release-checksum-install-proof.md).
