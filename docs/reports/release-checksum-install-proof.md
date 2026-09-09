# Release checksum install proof

Date: 2026-09-10
Version: 0.1.0 (from pyproject.toml)

## Published GitHub Release (2026-09-10 check)

| Check | Result | Evidence |
|---|---|---|
| Tag `v0.1.0` on GitHub | PASS | `refs/tags/v0.1.0` -> `5198c25` |
| GitHub Release record | **FAIL** | `GET /releases/tags/v0.1.0` -> 404; release list count 0 |
| Asset `pr-reviewer-0.1.0-compose.release.yml` | **FAIL** | download URL -> 404 |
| Asset `SHA256SUMS` | **FAIL** | download URL -> 404 |
| `install-from-release.sh` from public main | **FAIL** | script fetch OK; install exits 22 on asset 404 |
| CI release workflow | **FAIL** | [run 34402098194](https://github.com/the-niresh/plug-and-play-reviewer/actions/runs/34402098194): `build images` failed; publish skipped |

Public install attempt (no secrets, fresh prefix):

```sh
PREFIX="/tmp/pr-reviewer-pub-proof-$$"
curl -fsSL https://raw.githubusercontent.com/the-niresh/plug-and-play-reviewer/main/scripts/install-from-release.sh \
  -o /tmp/install-from-release-pub.sh
sh /tmp/install-from-release-pub.sh --version 0.1.0 --prefix "$PREFIX"
# curl: (22) The requested URL returned error: 404
# exit=22
```

**Verdict:** checksum install path is implemented and proved locally, but **published
release install is not verified** because no release assets exist on GitHub yet.

## Local build proof (still PASS)

| Step | Result |
|---|---|
| `sh scripts/build-local-release.sh dist` | PASS |
| `dist/SHA256SUMS` written | PASS |
| `sh scripts/install-from-release.sh --dist dist --prefix /tmp/pr-reviewer-pub-local-$$` | PASS |
| sha256sum verify output | `pr-reviewer-0.1.0-compose.release.yml: OK` |
| Installed file under fresh prefix | PASS |

## SHA256SUMS (2026-09-10 local build)

```
393de36c6c0f1f3fc337582ceb02b206e782e859c05dd335ba269330dda63f9e  pr-reviewer-0.1.0-compose.release.yml
```

Digest changes when `compose.release.yml` or rendered config changes. Do not
treat this line as permanent.

## Owner action to unblock published proof

The tag exists but the release workflow failed before assets were uploaded.
Fix the workflow (likely `docker compose -f compose.release.yml build` in CI)
or publish manually:

```sh
sh scripts/build-local-release.sh dist
gh auth login
gh release create v0.1.0 dist/pr-reviewer-0.1.0-compose.release.yml dist/SHA256SUMS \
  --repo the-niresh/plug-and-play-reviewer --title "v0.1.0"
```

Re-run public proof after assets exist:

```sh
PREFIX="/tmp/pr-reviewer-pub-proof-$$"
curl -fsSL https://raw.githubusercontent.com/the-niresh/plug-and-play-reviewer/main/scripts/install-from-release.sh \
  | sh -s -- --version 0.1.0 --prefix "$PREFIX"
ls "$PREFIX/pr-reviewer-0.1.0-compose.release.yml"
```

## Scope and constraints

- No secrets used in this check (public API + curl only).
- No evals run.
- `docs/reports/scorecard.json` unchanged.
- This path verifies and installs the **hosted deploy compose file**. The
  `reviewer` CLI still installs via `install-reviewer.sh` or `uv tool install`.
