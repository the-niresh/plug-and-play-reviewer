# Deploy the hosted control plane

This guide is for a first hosted instance. It covers Vercel for the Next.js UI,
and Render or Railway for the hosted API. For Render and Railway steps with
screenshot placeholders, see [SELF_HOST_CONTROL_PLANE.md](SELF_HOST_CONTROL_PLANE.md). It does
not put model keys or diffs
on the hosted plane. Those stay on the runner. Finding titles and rationale
may be stored so the dashboard can show them.

There is already a live compose instance at `https://reviewer.niresh.tech`.
`GET /health` and `GET /ready` return `200` with `{"status":"ok"}`. Use that
URL if you only need a working control plane today. Use the steps below when
you want a Vercel UI, or a Render or Railway API instance of your own.

## What you need before you start

You must have these. This repository does not contain them, and they must not
be committed.

1. A Vercel account for the web UI.
2. A Render account or a Railway account for the hosted API. Pick one. Free web
   tiers are enough. Do not add a persistent disk. Hosted GitHub App secrets go
   in the dashboard env vars, not a volume.
3. A Neon Postgres database. Copy the connection string. Add
   `sslmode=verify-full` if it is not already there.
4. A GitHub App. You need the App id, the PEM private key, the OAuth client
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
| `PR_REVIEWER_HOSTED_ORIGIN` | public app origin users open, no trailing slash |

Do not set `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `MODEL_KEY` on this
service. The runner owns model keys.

After the first deploy, copy the public URL. Set `PR_REVIEWER_HOSTED_ORIGIN`
to that https origin and redeploy once.

## Vercel web UI

Import the repository, then set **Root Directory to `apps/web`** and leave
every build setting on the Vercel default:

- install command: default (`bun install`)
- build command: default (`next build`)
- output directory: default (`.next`)

Do not add a `vercel.json` at the repository root. Vercel resolves the
framework from the Root Directory's `package.json`, and the repo root is a
Python project with none, so the import fails with `No Next.js version
detected`. A checked-in `vercel.json` also greys out the Build and
Development Settings in the dashboard, so wrong values cannot be cleared
from the UI.

Set these Vercel environment variables:

| Name | What to paste |
|---|---|
| `NEXT_PUBLIC_SITE_ORIGIN` | public Vercel or custom domain for the UI |
| `NEXT_PUBLIC_CONTROL_PLANE_ORIGIN` | public origin of the hosted API |
| `NEXT_PUBLIC_GITHUB_APP_SLUG` | GitHub App slug, for example `pr-reviewer-niresh` |

The web app proxies `/api/*` to `NEXT_PUBLIC_CONTROL_PLANE_ORIGIN`. That keeps
GitHub OAuth callbacks, dashboard API calls, and sign-out on the same browser
origin as the UI. Without that proxy, a Vercel frontend would show the page but
GitHub sign-in would not work.

When Vercel owns the web hostname, `NEXT_PUBLIC_CONTROL_PLANE_ORIGIN` must point
to a separate hosted API origin. For example, use
`NEXT_PUBLIC_SITE_ORIGIN=https://pr-reviewer-web.vercel.app` and
`NEXT_PUBLIC_CONTROL_PLANE_ORIGIN=https://reviewer.niresh.tech`. If you later
move `reviewer.niresh.tech` to Vercel, keep the API on another hostname such as
`https://api.reviewer.niresh.tech`.

In that split setup, set the hosted API's `PR_REVIEWER_HOSTED_ORIGIN` to the
Vercel web origin, not the API origin. The API uses it to build the GitHub OAuth
callback URL and GitHub App manifest. The browser still reaches the API through
the Vercel `/api/*` proxy.

For a Vercel UI, point the GitHub App URLs at the web origin:

- Homepage: `https://<vercel-or-custom-web-origin>`
- Callback: `https://<vercel-or-custom-web-origin>/api/auth/github/callback`
- Webhook: `https://<vercel-or-custom-web-origin>/api/github/webhook`

Enable Vercel Web Analytics and Speed Insights in the Vercel dashboard after
the project is created. The packages are already installed and mounted in the
root layout. These tools collect frontend traffic and performance data only.
They do not receive source code, diffs, model prompts, model replies, or model
keys from the runner.

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

1. In Railway, create a service from a repo import of this repository. It
   reads `deploy/railway.json`. There is no public Railway template id yet.
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
- The local runner UI. The public Next.js UI can run on Vercel. The Render
  blueprint and Railway repo-import files start the hosted API image only.
- Source, diffs, or model keys. The hosted schema must not hold those.
  Finding titles and rationale are allowlisted dashboard text. See
  [DATA_BOUNDARIES.md](DATA_BOUNDARIES.md).

## If something fails

- Process up, database down: `/health` is `200`, `/ready` is not.
- Wrong port: the service never becomes healthy. The API reads `PORT` from
  the environment and defaults to `8000`.
- Migrations missing: `/ready` may pass (`select 1`) while later routes
  fail. Check that `preDeployCommand` ran `pr-reviewer-db-migrate`.
