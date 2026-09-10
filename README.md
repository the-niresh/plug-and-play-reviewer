# Plug and Play Reviewer

Private AI code review. A hosted control plane takes GitHub events. A local
runner reads the diff, retrieves repo context, and calls your model.

<p>
  <a href="https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fthe-niresh%2Fplug-and-play-reviewer&project-name=pr-reviewer-web&repository-name=plug-and-play-reviewer&env=NEXT_PUBLIC_SITE_ORIGIN,NEXT_PUBLIC_CONTROL_PLANE_ORIGIN,NEXT_PUBLIC_GITHUB_APP_SLUG&envDescription=Public%20web%20origin,%20hosted%20API%20origin,%20and%20GitHub%20App%20slug">
    <img alt="Deploy frontend to Vercel" src="https://img.shields.io/badge/Deploy%20frontend%20to%20Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white">
  </a>
  <a href="https://render.com/deploy?repo=https://github.com/the-niresh/plug-and-play-reviewer">
    <img alt="Deploy API on Render" src="https://render.com/images/deploy-to-render-button.svg">
  </a>
  <a href="https://railway.com/new/template?template=https://github.com/the-niresh/plug-and-play-reviewer">
    <img alt="Deploy API on Railway" src="https://railway.com/button.svg">
  </a>
</p>

The product domain will be `plugandplayreviewer.online`. The live control plane
today is `https://reviewer.niresh.tech`. That name is not pointed yet.

Source, diffs, and model keys stay on the runner. Finding titles and rationale
may sit on the hosted dashboard so you can read them. A review comment does
not post until a human approves.

This is an open source PR reviewer. Use it for AI code review self hosted on
a laptop or a server you run.

## Two boxes

| Box | Deploy | Sees |
|---|---|---|
| **Hosted control plane** | One-click on Render or Railway (`pr-reviewer-api` only) | Job metadata, finding titles, rationale |
| **Local runner** | Always on your machine (`reviewer start`) | Source, diffs, model key |

No deploy target in this repo runs the runner.

## What it does

- The GitHub App receives the pull request event.
- The hosted plane stores job metadata only.
- The runner claims the job and keeps the patch local.
- Retrieval adds repo chunks to the packed diff before the model call.
- Findings that cannot point at the packed hunk are dropped.
- An optional suggested fix can post as a GitHub suggestion when it applies.
- Extra specialist reviewers are opt-in per repository. They are off by default.
- Custom agents and prompts stay private to that repository.

A single person running a local reviewer can stay on a simple path. The free tier
allows one GitHub user and one repository per installation. Team controls,
shared prompts, and extra repositories are the paid path later. There are no
prices in this repository.

## What you need

- Python 3.12, [uv](https://docs.astral.sh/uv/), and Docker for full mode
- A model key on the runner. It never goes to the hosted database.
- A hosted origin. `https://reviewer.niresh.tech` answers `/health` and
  `/ready` today.
- A GitHub App pointed at that origin if you want live pull request events

One-click Render still needs your own secrets and database. Railway starts from a repo import until a public template id exists.
Install the runner with [docs/INSTALL.md](docs/INSTALL.md) (`scripts/install-reviewer.sh`).
The GitHub Release checksum path is documented in [docs/RELEASE.md](docs/RELEASE.md).

## Documentation

| Doc | What it covers |
|---|---|
| [SELF_HOSTING.md](docs/SELF_HOSTING.md) | End-to-end flow from install to a claimed job |
| [ONE_CLICK_DEPLOY.md](docs/ONE_CLICK_DEPLOY.md) | Render and Railway control plane deploy |
| [INSTALL.md](docs/INSTALL.md) | Install, setup, doctor, uninstall |
| [DEPLOY.md](docs/DEPLOY.md) | Vercel UI plus hosted API |
| [RUNBOOK.md](docs/RUNBOOK.md) | What is live and what needs the owner |
| [MCP.md](docs/MCP.md) | `reviewer mcp` over stdio |
| [CHANNELS.md](docs/CHANNELS.md) | Slack, Telegram, Discord, email |
| [AGENT_CONTRACT.md](docs/AGENT_CONTRACT.md) | JSON shapes, exit codes, agent prompt |

Start here: [Self-hosting](docs/SELF_HOSTING.md). Then [One-click deploy](docs/ONE_CLICK_DEPLOY.md) if you
want your own hosted instance.

## What is proved

| Claim | Where |
|---|---|
| Hosted `/health` and `/ready` on `reviewer.niresh.tech` | [docs/DEPLOY.md](docs/DEPLOY.md) |
| Public curl install on GitHub `main` | [docs/reports/clean-machine-install-proof.md](docs/reports/clean-machine-install-proof.md) |
| Live install plus review on a real PR | [docs/reports/public-install-live-review-proof.md](docs/reports/public-install-live-review-proof.md) |
| Live GitHub webhook to review comment | [docs/reports/live-github-loop-proof.md](docs/reports/live-github-loop-proof.md) |
| Published holdout scorecard (7 Zod cases, gpt-4o-mini) | [docs/reports/holdout-quality-baseline.md](docs/reports/holdout-quality-baseline.md), [/scorecard](https://reviewer.niresh.tech/scorecard) |
| Hosted schema cannot hold source, diffs, or model keys | `uv run python scripts/generate_data_boundaries_doc.py --check` |
| Finding title and rationale are allowlisted hosted text | [docs/DATA_BOUNDARIES.md](docs/DATA_BOUNDARIES.md) |
| Backend tests | `flock -w 3600 /tmp/pr-reviewer-pytest.lock uv run pytest -q` |
| Lint | `uv run ruff check .` |
| Types | `uv run mypy src` |

Run those commands on this checkout. Do not treat an old count in a README as
a result.

## What is not proved

- The published scorecard is **7 human-judged holdout cases from the Zod
  repository only**. It is not proof on every language, repo, or pull request.
  Dev eval notes are working notes, not a published baseline.
- GitHub Release checksum install is documented in [docs/RELEASE.md](docs/RELEASE.md).
  Assets build locally today; publishing `v*` on GitHub still needs the owner
  to push a tag (see RELEASE.md).
- A new Render or Railway URL was not created. That needs the owner's
  account, Neon `DATABASE_URL`, and GitHub App secrets.
- No stranger-only end-to-end proof without owner-side pairing shortcuts.

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
