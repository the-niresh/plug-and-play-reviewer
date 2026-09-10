# Self-host the control plane

This guide deploys the **hosted control plane only**. It does not deploy the
local runner. Source, diffs, and model keys must stay on a machine you control.

This is a bootstrap, not a single click. Five of the seven variables below
only exist after you create a GitHub App by hand, and the deploy needs a
second pass once you know your own URL. Read the next section before you
press deploy.

Both deploy targets start `pr-reviewer-api`:

- Render reads `deploy/render.yaml` and runs
  `/app/.venv/bin/pr-reviewer-api`.
- Railway reads `deploy/railway.json` and runs the same command.

Neither file starts the runner. Do not add a runner service to these platforms.

The live instance today is `https://plugandplayreviewer.online`. The product domain
will be `plugandplayreviewer.online`, but it is not pointed yet.

See [CONFIGURATION.md](CONFIGURATION.md) for the full list of control-plane
variables and what each one does.

## Before you click: create a GitHub App

Deploying without a GitHub App does not fail loudly. The service boots
**healthy** and `/health` returns `200`. It just silently rejects every
webhook, because there is no App to sign them. You get a working-looking
service that reviews nothing, and nothing in the logs tells you that.

Create the GitHub App first, and collect five values from it before you
touch Render or Railway:

1. App id (`GITHUB_APP_ID`) - the GitHub App settings page, top of the page.
2. PEM private key (`GITHUB_APP_PRIVATE_KEY`) - GitHub App settings, generate
   and download the PEM. Paste the full text including the `BEGIN` and `END`
   lines.
3. OAuth client id (`GITHUB_OAUTH_CLIENT_ID`) - GitHub App settings, OAuth
   credentials section.
4. OAuth client secret (`GITHUB_OAUTH_CLIENT_SECRET`) - same section as the
   client id.
5. Webhook secret (`GITHUB_WEBHOOK_SECRET`) - GitHub App settings, webhook
   section. You choose this value yourself when you create the App.

Do not commit any of these values.

## The bootstrap sequence

The App's webhook URL and OAuth callback both need your deployed URL, which
does not exist until after the first deploy. So this takes two passes: deploy
once with a placeholder origin, then set the real one and redeploy.

1. Create the GitHub App and collect the five values above.
2. Deploy on Render or import on
   Railway.
3. Copy the deployed URL.
4. Set `PR_REVIEWER_HOSTED_ORIGIN` to that URL.
5. Set the App's webhook URL to `<url>/api/github/webhook`.
6. Set the App's callback URL to `<url>/api/auth/github/callback`.
7. Redeploy.
8. Verify: `curl <url>/health` returns 200, then open a pull request and
   confirm a job is queued.

Skipping step 5 is the mistake people actually make. It gives you a healthy
service that reviews nothing, because GitHub has nowhere to send events.

## Environment variables

Set every name below in the Render or Railway dashboard. The repo files list
the names only. Values come from your accounts.

| Name | Where to get the value |
|---|---|
| `DATABASE_URL` | Bring your own Postgres. Use Neon: its free tier does not expire, while a Render free database is deleted 30 days after it is created and takes every job record with it. Paste the pooled connection string from your Neon dashboard. Add `sslmode=verify-full` if it is not already there. |
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

Set `DATABASE_URL` to your Neon connection string. In
the Blueprint or service **Environment** tab, add the remaining six variables
from the table above. For the first pass you can set
`PR_REVIEWER_HOSTED_ORIGIN` to a placeholder such as
`https://reviewer.onrender.com` until Render assigns the real hostname.

<!-- SCREENSHOT: Render environment variable form with DATABASE_URL and GitHub App secrets filled (values blurred) -->

### Step 3. Deploy

Deploy the Blueprint. There is no start command and no pre-deploy command to set. The
image runs `pr-reviewer-serve`, which applies migrations and then serves:

```
Database migrations complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

The migration lives in the image on purpose. Render's separate pre-deploy step is a paid
feature, so a free-plan service that relied on it would skip the migration and come up
healthy against an empty schema. Health check path: `/health`.

The blueprint also pins `plan: free`. Leave that out and Render bills you for its
default instance size.

<!-- SCREENSHOT: Render deploy log showing the migrate and start command -->

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

Railway has a real pre-deploy step, so unlike the Render free plan it runs the
migration separately:

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

Until all three match, OAuth and webhooks will not reach this instance. A
service can look healthy while this step is still wrong: `/health` only
checks that the process is up, not that GitHub can reach it.

## What this does not deploy

| Not deployed | What to do instead |
|---|---|
| Local runner | Install on your machine. See [SELF_HOSTING.md](SELF_HOSTING.md). |
| Next.js web UI | Deploy `apps/web` on Vercel. See [DEPLOY.md](DEPLOY.md). |
| Model keys | Run `reviewer setup` on the runner. |

## If something fails

- Process up, database down: `/health` is `200`, `/ready` is not.
- Wrong port: the API reads `PORT` from the environment and defaults to `8000`.
- Migrations missing: check the deploy log for `Database migrations complete.`
  before the API starts. The start command runs the migration first.
- Healthy but no reviews: the webhook or callback URL does not match the
  deployed origin. Recheck the three settings in the section above.

See also [DEPLOY.md](DEPLOY.md) for the Vercel UI and a combined picture.
