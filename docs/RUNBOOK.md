# Runbook

This is the operator page. It says what is live and what still needs the
owner. It is not a launch scorecard.

## What is proved

`https://reviewer.niresh.tech` answers today.

- `GET /health` returns `200` and `{"status":"ok"}`.
- `GET /ready` returns `200` and `{"status":"ok"}`. That check talks to
  Postgres.

Those two checks prove the hosted control plane process and its database
path. They do not prove a GitHub webhook, a model call, or a posted
comment.

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
- A public GitHub Release install asset. Local checksum install is the
  path today.

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

- It does not publish an eval baseline.
- It does not prove a comment on a real pull request.
- It does not set prices for the later team paid path.
