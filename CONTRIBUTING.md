# Contributing

Thanks for looking. This page tells you how to set the project up, how to get a change accepted,
and the few rules that will get a pull request sent back.

## Set up

You need Python 3.12, [uv](https://docs.astral.sh/uv/), Docker, and Bun if you touch the web app.

```bash
git clone https://github.com/the-niresh/plug-and-play-reviewer.git
cd plug-and-play-reviewer
uv sync
docker compose up -d postgres
```

Copy `.env.example` to `.env` and fill in what you need. A model key is only required if you want
to run a real review; the test suite never calls a model.

## Run the tests

```bash
flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q
```

The `flock` matters. The tests share one Postgres, so two runs at once produce foreign key and
deadlock errors in tests that have nothing to do with your change. Always use it, even for a
single file.

Two files shell out to a frontend build and need a lot of memory. Skip them unless you are working
on the web app:

```
tests/test_landing_performance.py
tests/test_dashboard_performance.py
```

## Before you open a pull request

```bash
uv run ruff check <the files you changed>
uv run mypy src
flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q
```

All three must be clean, and the test count must not go down.

## How to write a change

**Write the failing test first.** Run it. Watch it fail. Keep the failure text; put it in the pull
request description. A test that has never been red proves nothing.

**A test must fail when the idea is removed, not only when the code is deleted.** Asserting that a
function was called is not a test of what it does. Before you open the pull request, delete the
behaviour you just added and confirm your test goes red. If it still passes, the test is not
finished.

**Do not use a stub to test the thing the stub replaces.** This project once had 1400 passing
tests while its central feature had never worked, because every test used a fake reviewer that
returned the right answer by construction. If your test never exercises the real path or a
faithful equivalent, say so in the description.

**Smallest change that works.** No abstraction with one implementation. No configuration for a
value that never changes.

## Rules that will get a change sent back

1. **The hosted control plane cannot hold private review data.** `control_plane/` must never import
   `runner/`. Source, diffs and model keys never reach the hosted plane.
   `control_plane/boundary.py` enforces this against the live schema, and
   `docs/DATA_BOUNDARIES.md` is generated from it. If your change seems to need an exemption, the
   design is wrong.
2. **The human gate is not negotiable.** No code path lets a model set `verified`,
   `allow_public_post`, or routing. A finding is never posted to a pull request without a person
   approving it.
3. **Secrets stay out of `os.environ` and out of SQLite.** Use the keyring store, or the mode-0600
   file store on a host with no OS keychain.
4. **Prompts are insert-only.** `PromptRegistry.register` raises on an existing name and version.
   Versions are derived from a hash of the prompt text, so editing the text bumps the version by
   itself. Never hand-write a version.
5. **Anything that starts a thread shuts it down explicitly, with a timeout on every future.** A
   leaked executor thread once turned a 5 minute test suite into 28 minutes.
6. **Untrusted input is wrapped, never interpolated raw into a prompt.** The reviewer reads text
   written by strangers.
7. **No em dash and no en dash**, anywhere: code, comments, commits, docs.
   `grep -Pn '[\x{2013}\x{2014}]' <file>` must return nothing. Use a plain hyphen.

## Commits and pull requests

Commit messages are one line, in the form `type: short description`, using `feat`, `fix`,
`refactor`, `docs`, `test`, `chore`, `perf` or `ci`. No body, no trailers.

In the pull request description, include:

- what changed, in plain English
- the failure text you saw before the fix
- your ruff, mypy and pytest results

## Writing style

Plain, simple English. Short sentences, one idea each, everyday words. Define a term the first
time it appears. Precise technical terms are welcome; marketing language is not. This applies to
documentation, error messages and anything a user reads.

## Reporting a bug

Open an issue with what you did, what you expected, and what happened, including the real error
text. If it involves a review, say which model and provider you used.

## Security

If you find prompt injection or a data-boundary bug, report it privately. See
[SECURITY.md](SECURITY.md). Do not open a public issue for those reports.
