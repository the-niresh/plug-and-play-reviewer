# Self-hosting Plug and Play Reviewer

This guide walks through the full path from zero to a live review on your own
machine. It assumes the hosted control plane is already running at
`https://reviewer.niresh.tech`. The product domain will be
`plugandplayreviewer.online`, but that name is not pointed yet. Use the live
host above until it is.

## Two boxes

| Box | Where it runs | What it sees |
|---|---|---|
| **Hosted control plane** | Render, Railway, or similar. One-click deployable. | Job metadata, finding titles, rationale. Never source, diffs, or model keys. |
| **Local runner** | Your laptop or a machine you control. Always local. | Source, diffs, model key, webhook URLs for notifications. |

No deploy target in this repository runs the runner. `deploy/render.yaml` and
`deploy/railway.json` both start `pr-reviewer-api` only. Putting the runner on
Render would send your source to a remote host and break the privacy model.

## What you need

- A machine you control (laptop, desktop, or home server).
- [uv](https://docs.astral.sh/uv/) and the `reviewer` command. See
  [INSTALL.md](INSTALL.md).
- A model API key. It stays on the runner only.
- A GitHub account with permission to install Apps on at least one repository.

## End-to-end flow

### 1. Install the `reviewer` command

```sh
curl -fsSL https://raw.githubusercontent.com/the-niresh/plug-and-play-reviewer/main/scripts/install-reviewer.sh | sh
reviewer --help
```

### 2. Store your model key

```sh
reviewer setup --hosted-origin https://reviewer.niresh.tech
```

Hidden input collects the model key. It is stored in the OS secret store, or in
`~/.config/pr-reviewer` mode `0600` when no OS store exists. The command rejects
secret-bearing flags such as `--model-key`.

### 3. Sign in with GitHub

```sh
reviewer
```

Or:

```sh
reviewer login
```

Both open the terminal UI when stdin is a terminal. Signing in needs a browser.
There is no headless login path. The TUI walks you through GitHub device login
and pairs this machine with the hosted control plane.

To sign out later:

```sh
reviewer logout --yes
```

### 4. Install the GitHub App and grant repository access

During pairing, the TUI opens the hosted connect flow in your browser. Complete
these steps there:

1. Authorize the GitHub App for your account or organization.
2. Choose which repositories the App may access.
3. Confirm the installation.

The hosted plane receives webhook events for those repositories. It stores job
metadata only. It never receives your source or diffs.

### 5. Start the local runner

```sh
reviewer start --hosted-origin https://reviewer.niresh.tech --host 127.0.0.1
```

You can set `PR_REVIEWER_HOSTED_ORIGIN` instead of passing `--hosted-origin`
each time. Optional flags:

- `--port 8741` (default loopback port)
- `--mode full` or `--mode analysis_only`

Check status:

```sh
reviewer status
reviewer open
reviewer stop
```

On Windows, use autostart instead of a manual start:

```powershell
reviewer service install --hosted-origin https://reviewer.niresh.tech --host 127.0.0.1 --port 8799
reviewer service start
```

Run health checks before you rely on the runner:

```sh
reviewer doctor
```

### 6. Open a pull request on an allowed repository

Push a branch and open a PR on a repository you granted in step 4. The GitHub App
webhook reaches the hosted control plane, which enqueues a review job.

### 7. The runner claims the job

While `reviewer start` is running, the runner daemon polls the hosted plane,
claims the job with a Postgres lease, fetches the PR diff with a short-lived
installation token, runs the review locally, and stores findings. Nothing in
the diff or model prompt leaves your machine except allowlisted finding title
and rationale for the dashboard.

Approve a finding in the hosted dashboard before a public GitHub review comment
can post.

## One-off review from the terminal

You can also review a single PR without waiting for a webhook:

```sh
reviewer review owner/repo#12 --json
```

Exit codes:

- `0` review completed, no findings
- `1` review completed, findings present
- `2` refused (for example GitHub not connected or no model key)
- `3` failure

See [AGENT_CONTRACT.md](AGENT_CONTRACT.md) for JSON shapes and error codes.

## Related docs

- [INSTALL.md](INSTALL.md) - install, setup, doctor, uninstall
- [CONFIGURATION.md](CONFIGURATION.md) - every setting, control plane and runner
- [ONE_CLICK_DEPLOY.md](ONE_CLICK_DEPLOY.md) - deploy your own hosted control plane
- [CHANNELS.md](CHANNELS.md) - Slack, Telegram, Discord, and email notifications
- [MCP.md](MCP.md) - drive reviews from another agent over stdio
- [DEPLOY.md](DEPLOY.md) - Vercel UI plus Render or Railway API
