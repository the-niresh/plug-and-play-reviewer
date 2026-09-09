# Clean machine install proof

Date: 2026-09-10 (UTC)
Docs followed: local `README.md` and `docs/INSTALL.md` (same content intended for GitHub `main`).
Fresh environment: isolated `HOME`, `XDG_*`, `UV_TOOL_DIR`, and `UV_TOOL_BIN_DIR` under a temp directory.

## Verdict

**PARTIAL PASS.** A stranger can install and run `reviewer --help` and `reviewer doctor`
using the manual `uv tool install` command from `docs/INSTALL.md`. The public `curl`
one-liner is **blocked** until install commits are pushed to GitHub `main`.

## Steps run

| Step | Command | Result |
|---|---|---|
| 0 | `curl .../install-reviewer.sh` on public GitHub `main` | **404** (script not on remote yet) |
| 1 | Prerequisite `uv` | OK (`uv 0.10.12`) |
| 2 | `uv tool install --from git+https://github.com/the-niresh/plug-and-play-reviewer.git plug-and-play-reviewer` | OK (exit 0) |
| 3 | `reviewer --help` | OK (exit 0, lists `setup`, `doctor`, `start`) |
| 4 | `reviewer doctor --yes` | OK (exit 0, all Docker checks OK, full mode) |
| 5 | `reviewer setup --help` | OK (documents `--hosted-origin`, hidden model key) |

No model key, runner credential, or `.env` was used. No live review was run.

## Setup path (documented, not executed)

Public install docs say:

```sh
reviewer setup --hosted-origin https://reviewer.niresh.tech
```

Hidden input stores the model key locally. Pairing and `reviewer start` follow
`docs/INSTALL.md`. Those steps need owner-supplied model key and GitHub pairing;
they were not run in this proof.

## Hidden knowledge required today

1. **Push gap.** Local `main` is ahead of `origin/main`. Public `curl` install and
   updated `docs/INSTALL.md` are not on GitHub yet. A stranger reading only
   live GitHub docs still sees the old release-archive install path.
2. **`uv` prerequisite.** Documented in `docs/INSTALL.md`, but not installed by
   `install-reviewer.sh`. Expected.
3. **PATH.** After `uv tool install`, `~/.local/bin` must be on PATH. The install
   script prints a hint; strangers may miss it if they skip the script output.
4. **Live hosted origin.** `docs/INSTALL.md` must use `https://reviewer.niresh.tech`
   in the setup example, not a placeholder host only.

## Owner step to clear the curl blocker

Push `main` to GitHub so these commits are on `origin/main`:

- `7daad70` (`scripts/install-reviewer.sh`)
- Updated `docs/INSTALL.md` and `README.md` from this proof

Then re-run:

```sh
curl -fsSL https://raw.githubusercontent.com/the-niresh/plug-and-play-reviewer/main/scripts/install-reviewer.sh | sh
reviewer --help
```

## Doc fixes in this commit

- `docs/INSTALL.md`: note when `curl` returns 404; use live hosted origin in setup example.
- `README.md`: fix install sentence; point strangers to INSTALL for the runner command.
