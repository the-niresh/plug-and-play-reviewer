# One-click deploy of the hosted control plane

This guide deploys the **hosted control plane only**. It does not deploy the
local runner. Source, diffs, and model keys must stay on a machine you control.

Both one-click targets start `pr-reviewer-api`:

- Render reads `deploy/render.yaml` and runs
  `/app/.venv/bin/pr-reviewer-api`.
- Railway reads `deploy/railway.json` and runs the same command.

Neither file starts the runner. Do not add a runner service to these platforms.

The live instance today is `https://reviewer.niresh.tech`. The product domain
will be `plugandplayreviewer.online`, but it is not pointed yet.

## What you need before you start

1. A Render account or a Railway account.
2. A Neon Postgres database. Copy the connection string.
3. A GitHub App with:
   - App id (`GITHUB_APP_ID`)
   - PEM private key (`GITHUB_APP_PRIVATE_KEY`)
   - OAuth client id and secret (`GITHUB_OAUTH_CLIENT_ID`,
     `GITHUB_OAUTH_CLIENT_SECRET`)
   - Webhook secret (`GITHUB_WEBHOOK_SECRET`)

Do not commit any of these values.

## Environment variables

Set every name below in the Render or Railway dashboard. The repo files list
the names only. Values come from your accounts.

| Name | Where to get the value |
|---|---|
| `DATABASE_URL` | Neon dashboard. Use the Postgres connection string. Add `sslmode=verify-full` if it is not already there. |
| `GITHUB_APP_ID` | GitHub App settings page. Numeric id. |
| `GITHUB_APP_PRIVATE_KEY` | GitHub App settings. Generate or download the PEM. Paste the full text including `BEGIN` and `END` lines. |
| `GITHUB_OAUTH_CLIENT_ID` | GitHub App settings, OAuth credentials section. |
| `GITHUB_OAUTH_CLIENT_SECRET` | Same section as the client id. |
| `GITHUB_WEBHOOK_SECRET` | GitHub App settings, webhook section. You choose this secret when you create the App. |
| `PR_REVIEWER_HOSTED_ORIGIN` | The public https origin users open in a browser, no trailing slash. Set this after the first deploy when you know the hostname. |

Do **not** set `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or any model key on this
service. Model keys belong on the runner only.

## Render

### Step 1. Create a Blueprint

1. Open [Render](https://render.com) and sign in.
2. Choose **New** then **Blueprint**.
3. Connect the `the-niresh/plug-and-play-reviewer` repository.
4. Render reads `deploy/render.yaml` and proposes a web service named `reviewer`.

<!-- SCREENSHOT: Render Blueprint screen showing the reviewer web service from deploy/render.yaml -->

### Step 2. Fill environment variables

In the Blueprint or service **Environment** tab, add every variable from the
table above. For the first pass you can set `PR_REVIEWER_HOSTED_ORIGIN` to a
placeholder such as `https://reviewer.onrender.com` until Render assigns the
real hostname.

<!-- SCREENSHOT: Render environment variable form with DATABASE_URL and GitHub App secrets filled (values blurred) -->

### Step 3. Deploy

Deploy the Blueprint. Render runs:

```
/app/.venv/bin/pr-reviewer-db-migrate
```

as `preDeployCommand`, then starts:

```
/app/.venv/bin/pr-reviewer-api
```

Health check path: `/health`.

<!-- SCREENSHOT: Render deploy log showing preDeployCommand migrate and pr-reviewer-api start -->

### Step 4. Set the public origin and redeploy

Copy the assigned hostname, for example `reviewer-xxxx.onrender.com`. Set
`PR_REVIEWER_HOSTED_ORIGIN` to `https://reviewer-xxxx.onrender.com` and
redeploy once.

### Step 5. Verify

```sh
curl -sS "https://<your-hostname>/health"
curl -sS "https://<your-hostname>/ready"
```

Both should return `200` and `{"status":"ok"}`. `/ready` runs `select 1` on
Neon. If it fails, check `DATABASE_URL` and that migrations ran.

<!-- SCREENSHOT: curl or browser showing /health JSON response -->

## Railway

### Step 1. Import the repository

1. Open [Railway](https://railway.com) and sign in.
2. Create a **New Project** from a GitHub repo import of
   `the-niresh/plug-and-play-reviewer`.
3. Railway reads `deploy/railway.json`. There is no public template id yet.

<!-- SCREENSHOT: Railway new service from GitHub repo import -->

### Step 2. Add environment variables

Open the service **Variables** tab. Railway does not read secrets from
`railway.json`. Add every name from the environment table manually.

<!-- SCREENSHOT: Railway variables tab with the seven required names -->

### Step 3. Deploy

Railway runs the same pre-deploy migrate and start commands as Render:

- `preDeployCommand`: `/app/.venv/bin/pr-reviewer-db-migrate`
- `startCommand`: `/app/.venv/bin/pr-reviewer-api`
- `healthcheckPath`: `/health`

<!-- SCREENSHOT: Railway deployment details showing start command and health check -->

### Step 4. Set the public origin and redeploy

Copy the public Railway URL. Set `PR_REVIEWER_HOSTED_ORIGIN` to that https
origin and redeploy.

### Step 5. Verify

Same `/health` and `/ready` checks as Render.

## Point the GitHub App at the new origin

In GitHub App settings, set:

- Homepage: `https://<origin>`
- Callback: `https://<origin>/api/auth/github/callback`
- Webhook: `https://<origin>/api/github/webhook`

Until all three match, OAuth and webhooks will not reach this instance.

## What this does not deploy

| Not deployed | What to do instead |
|---|---|
| Local runner | Install on your machine. See [SELF_HOSTING.md](SELF_HOSTING.md). |
| Next.js web UI | Deploy `apps/web` on Vercel. See [DEPLOY.md](DEPLOY.md). |
| Model keys | Run `reviewer setup` on the runner. |

## If something fails

- Process up, database down: `/health` is `200`, `/ready` is not.
- Wrong port: the API reads `PORT` from the environment and defaults to `8000`.
- Migrations missing: check that `preDeployCommand` ran `pr-reviewer-db-migrate`.

See also [DEPLOY.md](DEPLOY.md) for the Vercel UI and a combined picture.
