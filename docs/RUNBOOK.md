# Runbook

This is the operator page. It says what is live and what still needs the
owner. It is not a launch scorecard.

## What is proved

`https://reviewer.niresh.tech` answers today.

- `GET /health` returns `200` and `{"status":"ok"}`.
- `GET /ready` returns `200` and `{"status":"ok"}`. That check talks to
  Postgres.

Recorded proofs (2026-09-10):

| Proof | Report |
|---|---|
| Public curl install | [clean-machine-install-proof.md](reports/clean-machine-install-proof.md) |
| Install from curl through live review | [public-install-live-review-proof.md](reports/public-install-live-review-proof.md) |
| GitHub webhook to bot review comment | [live-github-loop-proof.md](reports/live-github-loop-proof.md) |
| Holdout quality baseline (7 Zod cases) | [holdout-quality-baseline.md](reports/holdout-quality-baseline.md) |

The health checks alone do not prove a GitHub webhook or a model call. The
reports above do.

The hosted schema still must not hold source, diffs, or model keys. Finding
titles and rationale may sit on Neon so the dashboard can show them. See
[DATA_BOUNDARIES.md](DATA_BOUNDARIES.md).

## What still needs the owner

- Point the GitHub App homepage, callback, and webhook at
  `https://reviewer.niresh.tech` if they still use another origin.
- Install the App on a repository you own.
- Install a runner on a machine you control. Pair it. Store the model key
  there. See [INSTALL.md](INSTALL.md).
- Open a pull request and approve a finding before a comment can post.
- A new Render or Railway URL. That needs your account, a Neon
  `DATABASE_URL`, and GitHub App secrets. See [DEPLOY.md](DEPLOY.md).
- A published GitHub Release on GitHub (local build + checksum path is ready;
  see [RELEASE.md](RELEASE.md)).

Do not invent those values.

## GitHub App URLs

When the owner is ready, set:

- Homepage: `https://reviewer.niresh.tech`
- Callback: `https://reviewer.niresh.tech/api/auth/github/callback`
- Webhook: `https://reviewer.niresh.tech/api/github/webhook`

Until those match, live events will not reach this instance.

## Rollback

1. Stop the hosted overlay:
   `docker compose -f compose.release.yml -f docker-compose.hosted.yml down`.
2. Point the three App URLs back if you changed them.
3. Keep Neon data unless you mean to delete it.

## What this runbook does not claim

- The published scorecard is 7 Zod holdout cases only. It is not broad proof
  on every repository.
- It does not set prices for the later team paid path.
- It does not prove a cold stranger path with no owner help at pairing time.
