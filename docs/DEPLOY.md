# Deploy the hosted control plane

This guide is for a first hosted instance. It covers Render and Railway. It
does not put model keys, diffs, or findings on the hosted plane. Those stay
on the runner.

There is already a live compose instance at `https://reviewer.niresh.tech`.
`GET /health` and `GET /ready` return `200` with `{"status":"ok"}`. Use that
URL if you only need a working control plane today. Use the steps below when
you want a Render or Railway instance of your own.

## What you need before you start

You must have these. This repository does not contain them, and they must not
be committed.

1. A Render account or a Railway account. Pick one. Free web tiers are
   enough. Do not add a persistent disk. Hosted GitHub App secrets go in the
   dashboard env vars, not a volume.
2. A Neon Postgres database. Copy the connection string. Add
   `sslmode=verify-full` if it is not already there.
3. A GitHub App. You need the App id, the PEM private key, the OAuth client
   id, the OAuth client secret, and the webhook secret. You can create the
   App first with placeholder URLs, deploy, then edit the App to the real
   origin.

If any of those are missing, stop. Do not invent values.

## What to fill in

Set these names in the Render or Railway dashboard. Leave them empty in the
repo.

| Name | What to paste |
|---|---|
| `DATABASE_URL` | Neon URL with `sslmode=verify-full` |
| `GITHUB_APP_ID` | GitHub App id, digits |
| `GITHUB_APP_PRIVATE_KEY` | full PEM text |
| `GITHUB_OAUTH_CLIENT_ID` | GitHub App OAuth client id |
| `GITHUB_OAUTH_CLIENT_SECRET` | GitHub App OAuth client secret |
| `GITHUB_WEBHOOK_SECRET` | GitHub App webhook secret |
| `PR_REVIEWER_HOSTED_ORIGIN` | public https origin, no trailing slash |

Do not set `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `MODEL_KEY` on this
service. The runner owns model keys.

After the first deploy, copy the public URL. Set `PR_REVIEWER_HOSTED_ORIGIN`
to that https origin and redeploy once.

## Render

1. In Render, create a Blueprint from this repository. It reads
   `deploy/render.yaml`.
2. Fill the env vars in the table above. For the first pass, set
   `PR_REVIEWER_HOSTED_ORIGIN` to `https://reviewer.onrender.com` as a
   placeholder if you do not have the assigned hostname yet.
3. Deploy. Render runs `/app/.venv/bin/pr-reviewer-db-migrate` before it
   starts `/app/.venv/bin/pr-reviewer-api`.
4. Copy the assigned hostname. Set `PR_REVIEWER_HOSTED_ORIGIN` to
   `https://<that-hostname>` and redeploy.
5. Expect `GET https://<that-hostname>/health` to return `200` and
   `{"status":"ok"}`. That check does not touch the database.
6. Expect `GET https://<that-hostname>/ready` to return `200` and
   `{"status":"ok"}`. That check runs `select 1` on Neon. If this fails, the
   database URL or migrations are wrong.

## Railway

1. In Railway, create a service from this repository. It reads
   `deploy/railway.json`.
2. In the service variables, add every name in the table above. Railway does
   not take those values from the JSON file.
3. Deploy. Railway runs `/app/.venv/bin/pr-reviewer-db-migrate` before it
   starts `/app/.venv/bin/pr-reviewer-api`.
4. Copy the public URL. Set `PR_REVIEWER_HOSTED_ORIGIN` and redeploy.
5. Expect the same `/health` and `/ready` results as Render.

## Point the GitHub App at the new origin

In the GitHub App settings, set:

- Homepage: `https://<origin>`
- Callback: `https://<origin>/api/auth/github/callback`
- Webhook: `https://<origin>/api/github/webhook`

Until those three match, OAuth and webhooks will not reach this instance.

## What this does not deploy

- The local runner. Install that on a machine you control. Pair it to this
  origin. Store model keys there.
- The Next.js UI. The one-click files start the API image only.
- Source, diffs, findings, or model keys. The hosted schema must not hold
  those.

## If something fails

- Process up, database down: `/health` is `200`, `/ready` is not.
- Wrong port: the service never becomes healthy. The API reads `PORT` from
  the environment and defaults to `8000`.
- Migrations missing: `/ready` may pass (`select 1`) while later routes
  fail. Check that `preDeployCommand` ran `pr-reviewer-db-migrate`.
