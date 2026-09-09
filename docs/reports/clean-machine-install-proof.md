# Clean machine install proof

Date: 2026-09-10 (UTC)
Docs followed: public `README.md` and `docs/INSTALL.md` on GitHub `main`.
Fresh environment: isolated `HOME`, `XDG_*`, `UV_TOOL_DIR`, and `UV_TOOL_BIN_DIR` under a temp directory.

## Verdict

**PASS.** After `main` was pushed to GitHub, a stranger can install with the public
`curl` one-liner and run `reviewer --help` and `reviewer doctor` with no secrets.

## Re-run after push (2026-09-10T00:59+05:30)

Git commit installed from public git: `40a9f85b01b0733bc08f3a9d3c9b2ab6af7c9b16`.

| Step | Command | Result |
|---|---|---|
| 0 | `curl -fsSL .../install-reviewer.sh` on public GitHub `main` | **200** |
| 1 | `curl ... \| sh` with fresh temp `HOME` and `UV_TOOL_BIN_DIR` | OK (exit 0) |
| 2 | `reviewer --help` | OK (exit 0) |
| 3 | `reviewer doctor --yes` | OK (exit 0, full Docker mode) |

Commands used:

```sh
export HOME=/tmp/clean-proof/home
export UV_TOOL_DIR=/tmp/clean-proof/tools
export UV_TOOL_BIN_DIR=/tmp/clean-proof/bin
export PATH="$UV_TOOL_BIN_DIR:$PATH"
curl -fsSL https://raw.githubusercontent.com/the-niresh/plug-and-play-reviewer/main/scripts/install-reviewer.sh | sh
reviewer --help
reviewer doctor --yes
```

No model key, runner credential, or `.env` was used. No live review was run.

## First run before push (historical)

| Step | Result |
|---|---|
| `curl .../install-reviewer.sh` | **404** (script not on remote yet) |
| Manual `uv tool install --from git+...` | OK |

That partial result is kept for history. Push to `origin/main` cleared the blocker.

## Setup path (documented, not executed)

```sh
reviewer setup --hosted-origin https://reviewer.niresh.tech
```

Hidden input stores the model key locally. Pairing and `reviewer start` follow
`docs/INSTALL.md`. Those steps need owner-supplied model key and GitHub pairing.

## Remaining stranger notes

1. **`uv` prerequisite.** Documented in `docs/INSTALL.md`. The install script exits
   with a clear message if `uv` is missing.
2. **PATH.** Default install uses `~/.local/bin`. The script prints a PATH hint.
   This proof used an isolated `UV_TOOL_BIN_DIR` under temp.

## Next product proof

Real user install plus live PR review from the public install path (no checkout
clone). That needs model key, GitHub pairing, and `reviewer start` on a machine
that used only the public curl install.
