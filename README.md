# PR Reviewer

Private AI code review. A hosted control plane takes GitHub events. A local
runner reads the diff, retrieves repo context, and calls your model.

Source, diffs, and model keys stay on the runner. Finding titles and rationale
may sit on the hosted dashboard so you can read them. A review comment does
not post until a human approves.

This is an open source PR reviewer. Use it for AI code review self hosted on
a laptop or a server you run.

## What it does

- The GitHub App receives the pull request event.
- The hosted plane stores job metadata only.
- The runner claims the job and keeps the patch local.
- Retrieval adds repo chunks to the packed diff before the model call.
- Findings that cannot point at the packed hunk are dropped.
- An optional suggested fix can post as a GitHub suggestion when it applies.
- Extra specialist reviewers are opt-in per repository. They are off by default.
- Custom agents and prompts stay private to that repository.

A single person running a local reviewer can stay on a simple path. Team
controls, shared prompts, and extra repositories are the paid path later.
There are no prices in this repository.

## What you need

- Python 3.12, [uv](https://docs.astral.sh/uv/), and Docker for full mode
- A model key on the runner. It never goes to the hosted database.
- A hosted origin. `https://reviewer.niresh.tech` answers `/health` and
  `/ready` today.
- A GitHub App pointed at that origin if you want live pull request events

One-click Render or Railway still needs your own secrets and database. A
Install the runner with [docs/INSTALL.md](docs/INSTALL.md) (`scripts/install-reviewer.sh`). A GitHub Release checksum asset is not published yet.

Start here: [Install](docs/INSTALL.md). Then [Deploy](docs/DEPLOY.md) if you
want your own hosted instance. [Runbook](docs/RUNBOOK.md) says what is proved
and what still needs the owner.

## What is proved

| Claim | Where |
|---|---|
| Hosted `/health` and `/ready` on `reviewer.niresh.tech` | [docs/DEPLOY.md](docs/DEPLOY.md) |
| Hosted schema cannot hold source, diffs, or model keys | `uv run python scripts/generate_data_boundaries_doc.py --check` |
| Finding title and rationale are allowlisted hosted text | [docs/DATA_BOUNDARIES.md](docs/DATA_BOUNDARIES.md) |
| Backend tests | `flock -w 3600 /tmp/pr-reviewer-pytest.lock uv run pytest -q` |
| Lint | `uv run ruff check .` |
| Types | `uv run mypy src` |

Run those commands on this checkout. Do not treat an old count in a README as
a result.

## What is not proved

- There is no published eval baseline. Dev notes exist. They are not a
  baseline. The scorecard page refuses a number until a measured run exists.
- A GitHub-hosted release asset is not published. Local checksum install is
  documented in [docs/INSTALL.md](docs/INSTALL.md).
- A new Render or Railway URL was not created. That needs the owner's
  account, Neon `DATABASE_URL`, and GitHub App secrets.
- A first live comment on a real pull request still needs the App URLs, a
  paired runner, a model key, and a human approve.

The reviewer does not learn from human replies yet.

## Local setup

```bash
uv sync
docker compose up -d postgres
DATABASE_URL=postgresql://pr_reviewer:pr_reviewer@localhost:54329/pr_reviewer uv run pr-reviewer-db-migrate
flock -w 3600 /tmp/pr-reviewer-pytest.lock uv run pytest -q
```

Installer and doctor: [docs/INSTALL.md](docs/INSTALL.md).
Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Security: [docs/SECURITY.md](docs/SECURITY.md).
Demo: [docs/DEMO.md](docs/DEMO.md).

## License

MIT. See [LICENSE](LICENSE).

