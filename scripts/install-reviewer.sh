#!/bin/sh
set -eu

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install it from https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

if [ -n "${PR_REVIEWER_INSTALL_SOURCE:-}" ]; then
  SOURCE="$PR_REVIEWER_INSTALL_SOURCE"
else
  REF="${PR_REVIEWER_GIT_REF:-main}"
  SOURCE="git+https://github.com/the-niresh/plug-and-play-reviewer.git@${REF}"
fi

uv tool install --from "$SOURCE" plug-and-play-reviewer

BIN_DIR=$(uv tool dir --bin 2>/dev/null || true)
if [ -n "$BIN_DIR" ]; then
  echo "Installed reviewer into $BIN_DIR"
  echo "Add it to PATH if needed: export PATH=\"$BIN_DIR:\$PATH\""
else
  echo "Installed reviewer. Run: uv tool update-shell"
fi
