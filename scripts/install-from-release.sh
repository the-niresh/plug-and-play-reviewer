#!/bin/sh
# Download a pinned hosted-deploy asset from a GitHub Release (or a local dist/
# directory), verify SHA256SUMS, and copy the compose file with install.sh.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
REPO="${PR_REVIEWER_RELEASE_REPO:-the-niresh/plug-and-play-reviewer}"
VERSION=""
DIST=""
PREFIX=""

usage() {
  echo "usage: install-from-release.sh --prefix DIR [--version VERSION | --dist DIR]" >&2
  echo "  --version VERSION   GitHub Release tag without v (default: pyproject.toml version)" >&2
  echo "  --dist DIR          Use SHA256SUMS and asset from a local build (offline proof)" >&2
  echo "  --prefix DIR        Destination directory for the verified compose file" >&2
  exit 2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --version)
      VERSION="$2"
      shift 2
      ;;
    --dist)
      DIST="$2"
      shift 2
      ;;
    --prefix)
      PREFIX="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "unknown option: $1" >&2
      usage
      ;;
  esac
done

if [ -z "$PREFIX" ]; then
  echo "--prefix is required" >&2
  usage
fi

if [ -z "$VERSION" ]; then
  VERSION=$(python3 -c "import tomllib, pathlib; print(tomllib.loads((pathlib.Path('$ROOT') / 'pyproject.toml').read_text())['project']['version'])")
fi

ASSET="pr-reviewer-${VERSION}-compose.release.yml"
WORKDIR="${TMPDIR:-/tmp}/pr-reviewer-release-$$"
mkdir -p "$WORKDIR"
trap 'rm -rf "$WORKDIR"' EXIT INT HUP TERM

if [ -n "$DIST" ]; then
  cp "$DIST/SHA256SUMS" "$WORKDIR/SHA256SUMS"
  cp "$DIST/$ASSET" "$WORKDIR/$ASSET"
else
  TAG="v${VERSION}"
  BASE="https://github.com/${REPO}/releases/download/${TAG}"
  curl -fsSL "${BASE}/SHA256SUMS" -o "$WORKDIR/SHA256SUMS"
  curl -fsSL "${BASE}/${ASSET}" -o "$WORKDIR/$ASSET"
fi

sh "$ROOT/scripts/install.sh" \
  --archive "$WORKDIR/$ASSET" \
  --checksum-file "$WORKDIR/SHA256SUMS" \
  --prefix "$PREFIX"

echo "Installed verified release asset to ${PREFIX}/${ASSET}"
