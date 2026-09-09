# Install

## What you need before you start

- A machine you control. The runner reads source and diffs there.
- [uv](https://docs.astral.sh/uv/) to install the `reviewer` command.
- Docker if you want full mode with sandbox checks.
- A model key. Enter it during `reviewer setup`. It stays on this machine.
- A hosted origin to pair with. `https://reviewer.niresh.tech` answers
  `/health` and `/ready` today. For your own instance see [DEPLOY.md](DEPLOY.md).
- GitHub connected through the App. Pairing uses a one-time browser or device
  code.

The installer never asks for hosted-plane credentials. Model keys are read with
hidden input and stored in the OS secret store, or in `~/.config/pr-reviewer`
mode `0600` when that store is missing.

## Install the reviewer command

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first, then
run:

```sh
curl -fsSL https://raw.githubusercontent.com/the-niresh/plug-and-play-reviewer/main/scripts/install-reviewer.sh | sh
```

That one-liner returns **HTTP 200** on GitHub `main` today (verified 2026-09-10).
See [clean-machine-install-proof.md](reports/clean-machine-install-proof.md).

Or, from a git checkout:

```sh
sh scripts/install-reviewer.sh
```

The script runs `uv tool install` from the public GitHub repository and puts
`reviewer` on your PATH (usually `~/.local/bin`). No model key or GitHub secret
is required for install.

Equivalent manual command:

```sh
uv tool install --from git+https://github.com/the-niresh/plug-and-play-reviewer.git plug-and-play-reviewer
```

After install:

```sh
reviewer --help
```

## Verified locally (2026-09-10)

From a clean temp directory on this machine, with isolated tool paths:

```sh
PR_REVIEWER_INSTALL_SOURCE=/path/to/plug-and-play-reviewer \
  UV_TOOL_DIR=/tmp/pr-reviewer-tools \
  UV_TOOL_BIN_DIR=/tmp/pr-reviewer-bin \
  sh scripts/install-reviewer.sh
/tmp/pr-reviewer-bin/reviewer --help
```

Exit code 0. The `reviewer setup` command appears in help output.

## Pinned install from a GitHub Release (checksum verified)

For a pinned hosted deploy compose file, or offline verification after download,
use [RELEASE.md](RELEASE.md).

Build assets locally:

```sh
sh scripts/build-local-release.sh dist
```

Install with checksum verification from a local build:

```sh
mkdir -p /tmp/pr-reviewer-release-prefix
sh scripts/install-from-release.sh --dist dist --prefix /tmp/pr-reviewer-release-prefix
```

After the owner publishes `v0.1.0` on GitHub:

```sh
sh scripts/install-from-release.sh --version 0.1.0 --prefix /tmp/pr-reviewer-release-prefix
```

Pin the runner CLI to the same tag (still needs network to git):

```sh
PR_REVIEWER_GIT_REF=v0.1.0 curl -fsSL https://raw.githubusercontent.com/the-niresh/plug-and-play-reviewer/main/scripts/install-reviewer.sh | sh
```

Publishing a release needs owner auth. See [RELEASE.md](RELEASE.md).

## Hosted deploy artifact (not the CLI)

To copy a pinned `compose.release.yml` with checksum verification, use
`scripts/build-local-release.sh`, `scripts/install-from-release.sh`, or
`scripts/install.sh` directly. That path is for hosted control-plane deploy,
not for installing the `reviewer` runner command.

## Setup

```sh
reviewer setup --hosted-origin https://reviewer.niresh.tech
```

`--hosted-origin` is the public control-plane site. Hidden input collects the model key. Slack secrets, if used, are also hidden. The command rejects secret-bearing flags.

Then:

```sh
reviewer doctor
reviewer start --host 127.0.0.1
reviewer status
reviewer stop
```

`reviewer doctor` checks control-plane reachability, pairing, model keys, port use, disk space, and Docker. Full mode requires Docker. Analysis-only is offered only after its limits are shown.

## Uninstall

Remove the uv tool install:

```sh
uv tool uninstall plug-and-play-reviewer
```

Remove local runner data only when you mean it:

```sh
sh scripts/uninstall.sh --delete-data --confirm-delete
```
