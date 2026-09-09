# Release checksum install proof

Date: 2026-09-10
Version: 0.1.0
Release: https://github.com/the-niresh/plug-and-play-reviewer/releases/tag/v0.1.0

## Published GitHub Release (2026-09-10 re-check)

| Check | Result | Evidence |
|---|---|---|
| GitHub Release `v0.1.0` | PASS | published 2026-09-09T20:44:34Z |
| Asset `pr-reviewer-0.1.0-compose.release.yml` | PASS | 2034 bytes on release |
| Asset `SHA256SUMS` | PASS | 104 bytes on release |
| `install-from-release.sh` from public main | PASS | shallow clone of `main`, script run exit 0 |
| SHA256SUMS verify during install | PASS | `pr-reviewer-0.1.0-compose.release.yml: OK` |
| Installed file under fresh temp prefix | PASS | `/tmp/pr-reviewer-pub-prefix-*/pr-reviewer-0.1.0-compose.release.yml` |
| No secrets used | PASS | public git clone + release download URLs only |
| Evals run | PASS (none) | |
| Scorecard changed | PASS (none) | `docs/reports/scorecard.json` untouched |

Public install proof (fresh clone + fresh prefix):

```sh
PROOF_DIR=$(mktemp -d /tmp/pr-reviewer-pub-verify-XXXXXX)
PREFIX=$(mktemp -d /tmp/pr-reviewer-pub-prefix-XXXXXX)
git clone --depth 1 https://github.com/the-niresh/plug-and-play-reviewer.git "$PROOF_DIR/repo"
sh "$PROOF_DIR/repo/scripts/install-from-release.sh" --version 0.1.0 --prefix "$PREFIX"
# pr-reviewer-0.1.0-compose.release.yml: OK
# Installed verified release asset to $PREFIX/pr-reviewer-0.1.0-compose.release.yml
# exit=0
```

**Verdict:** published release checksum install is verified end to end.

## Published SHA256SUMS

```
393de36c6c0f1f3fc337582ceb02b206e782e859c05dd335ba269330dda63f9e  pr-reviewer-0.1.0-compose.release.yml
```

Installed file hash matched the published digest on 2026-09-10.

## Local build proof (still PASS)

| Step | Result |
|---|---|
| `sh scripts/build-local-release.sh dist` | PASS |
| `sh scripts/install-from-release.sh --dist dist --prefix /tmp/pr-reviewer-pub-local-$$` | PASS |

## CI note

Tag push workflow [34402098194](https://github.com/the-niresh/plug-and-play-reviewer/actions/runs/34402098194)
failed at `build images`. Release assets were published manually by the owner.
Future tag releases should fix CI or continue manual publish per [RELEASE.md](../RELEASE.md).

## Scope

This path verifies and installs the **hosted deploy compose file**. The
`reviewer` CLI still installs via `install-reviewer.sh` or `uv tool install`.
