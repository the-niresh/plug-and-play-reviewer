# Release checksum install proof

Date: 2026-09-10
Version: 0.1.0 (from pyproject.toml)
GitHub Release published: **no** (gh not authenticated on this VPS)

## What was proved locally

| Step | Result |
|---|---|
| `sh scripts/build-local-release.sh dist` | PASS |
| `dist/SHA256SUMS` written | PASS |
| `sh scripts/install-from-release.sh --dist dist --prefix /tmp/pr-reviewer-release-proof` | PASS |
| sha256sum verify output | `pr-reviewer-0.1.0-compose.release.yml: OK` |
| Installed file present | `/tmp/pr-reviewer-release-proof/pr-reviewer-0.1.0-compose.release.yml` |

## SHA256SUMS (2026-09-10 build)

```
393de36c6c0f1f3fc337582ceb02b206e782e859c05dd335ba269330dda63f9e  pr-reviewer-0.1.0-compose.release.yml
```

Digest changes when `compose.release.yml` or rendered config changes. Do not
treat this line as permanent.

## What still needs the owner

Publishing the release on GitHub requires authenticated `gh` or a pushed `v*`
tag to trigger `.github/workflows/release.yml`.

```sh
git push origin main
git tag v0.1.0
git push origin v0.1.0
gh release view v0.1.0 --repo the-niresh/plug-and-play-reviewer
```

Manual fallback:

```sh
sh scripts/build-local-release.sh dist
gh auth login
gh release create v0.1.0 dist/* --repo the-niresh/plug-and-play-reviewer --title "v0.1.0"
```

After publish, strangers can run:

```sh
sh scripts/install-from-release.sh --version 0.1.0 --prefix /tmp/pr-reviewer-release-prefix
```

## Scope

This path verifies and installs the **hosted deploy compose file**. The
`reviewer` CLI still installs via `install-reviewer.sh` or `uv tool install`.
