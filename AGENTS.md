# AGENTS.md

Standing rules for any agent working in this repository. Cursor reads this in both the IDE and
the CLI. Read it once at the start of a session. It replaces having the rules pasted into every
prompt.

Project index and architecture live in `CLAUDE.md` and `docs/ARCHITECTURE.md`. Read those for
what the code is. This file is only how to work.

## The stack

Python 3.12, `uv` (never `pip` or `poetry` directly), Postgres with pgvector, Textual for the
terminal, FastAPI-shaped control plane, Next.js for the web.

```bash
uv sync
uv run ruff check <files>
uv run mypy src
flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q
```

## Track ownership is absolute

During a phase you own a set of directories and touch nothing else. A task that seems to need a
file outside your track is a **blocker to report**, not a file to edit. Two agents editing one
file is how this repo lost a commit once already.

Current tracks are listed in the active plan under `docs/phases/`.

`docs/phases/master-spec.md` has one owner and it is not you. Never rewrite it. A hand-rewrite
already deleted a whole phase from the index once.

## Before you write code

Write the failing test first. Run it. Watch it fail. Keep the real failure text, because you
have to paste it in your report. A test that has never been red proves nothing.

A test must fail when the **idea** is removed, not merely when the code is deleted. Asserting
that a function was called is not a test of what it does.

## The gate, before every commit

Scoped to the files you are staging:

```bash
uv run ruff check <your staged files>              # 0
uv run mypy src                                    # 0
grep -Pn '[\x{2013}\x{2014}]' <your staged files>  # no output
flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q
```

The suite must be at or above the count you recorded when you started, with 0 failed. Never run
pytest without the flock: several agents share this machine and the lock is single holder. While
iterating use a targeted `uv run pytest -q tests/test_your_file.py`, and run the full suite only
in the gate.

Full-repo ruff may be red in files you did not touch. That is not yours. Scope ruff to what you
stage and say so in your report.

## Commits

One line. A single `-m`. No body, no trailers, no AI attribution of any kind: no
`Co-Authored-By`, no tool names, no session links.

Stay on the default branch. Do not push. Do not open a pull request unless asked.

Never stage `docs/phases/` or `datasets/private/`.

Do not mark a task done before its commit exists.

## Writing style, in code and in docs

No em dash and no en dash anywhere. U+2014 and U+2013 are banned in code, comments, commits and
documentation. Use a plain hyphen. The grep above is the check.

**User-facing text and documentation is plain, simple English.** Short sentences. One idea each.
Everyday words. Define a term the first time it appears. No marketing language, no buzzwords, no
long words where a short one works. Write for someone setting this up for the first time who has
never read our code. If a sentence sounds like a brochure, delete it and say the thing plainly.

## Rules that bite in this codebase

- Source code, diffs, findings and model keys never reach the hosted plane. `boundary.py`
  enforces it and `HOSTED_EXEMPTIONS` stays empty. If a task seems to need an exemption, the
  task is wrong.
- Secrets never enter `os.environ` and never enter SQLite. Use the keyring store, or the
  mode-0600 file store on a host with no OS keychain.
- Never edit generated directories or generated documentation by hand. Regenerate them.
- `finish_completion` in `models/provider.py` validates on `schema_name` with an else that
  raises. Every new schema name needs a branch there in the same commit.
- Anything that starts a thread must shut it down explicitly, with a timeout on every future.
  A leaked executor thread cost this repo 300 seconds per occurrence and turned a 5 minute
  suite into 28 minutes.
- The reviewer reads text written by strangers. Untrusted input is wrapped, never interpolated
  raw into a prompt.

## Cost

Every model call is costed and recorded. A stage with no recorded cost is not finished. The
per-review target is about four cents; see the active spec for the budget table and where it
goes. If you add a call, say what it costs.

## Be frugal with tokens

Quota is the scarce resource on this project, not time. Every rule here exists because
something wasted it before.

**Read narrowly.** `grep -n` to find the line, then `sed -n '120,160p'` to read around it. Do not
open a 500-line file to change one function, and never dump a directory to see what is in it.

**Do not re-read what you have already read.** Read the spec and the plan once when your track
starts. On later tasks read only your own task section and `git log --oneline -20` to see what
has landed. A loop on this repo once re-read a 403-line index, a 91-line requirements file, a
spec and a plan on every single tick.

**Reuse before you write.** Look for a helper, type or pattern that already exists here before
adding one. This repo has 1,240 lines of retrieval, a finding matcher, a budget module and a
sandbox that were all written and then left unused because nobody looked. Re-implementing what
is three files away is the most expensive mistake available.

**Run tests narrowly while iterating.** `uv run pytest -q tests/test_your_file.py` costs seconds.
The full suite costs five minutes and a shared lock, and belongs only in the gate.

**Cite, do not paste.** In your report write `models/provider.py:161`, not the function body. The
person reading it can open the file.

**Smallest change that works.** No abstraction with one implementation, no configuration for a
value that never changes, no scaffolding for a feature nobody asked for. If the explanation is
longer than the code, delete the explanation.

**Say when you are stuck.** A blocker reported in one line costs almost nothing. Three attempts
at guessing around it costs a lot, and usually lands in the wrong place anyway.

## Reporting

Append one block to the end of `cursor-comm.md`, timestamped from `date -Is`:

```
## <timestamp> | <phase> | <task>
status: DONE or BLOCKED
commit sha: the sha and its message
red proof: the real failure text you saw before writing the code
gate numbers: ruff, mypy and pytest results
what I did: plain English
blockers: named exactly, or None
```

If you cannot finish, say BLOCKED with the specific reason and stop. Do not skip ahead to the
next task, and do not invent a workaround for a blocker that needs a human.
