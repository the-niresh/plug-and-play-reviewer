# Configuration

This page lists every setting you can change, split by where it lives. There
are two separate machines in this product, and they hold different things:

- **The control plane** (Render or Railway) only routes GitHub webhooks and
  stores job metadata. It never sees your source code, your diffs, or a model
  key.
- **The runner** (your own machine) holds your model key, reads your code, and
  runs the review.

Putting a model key on the control plane would not work anyway: nothing on
that side ever reads one. If you are looking for where to put your OpenAI or
Anthropic key, skip to Table B.

## Table A: control plane (Render or Railway)

Set these as environment variables in the Render or Railway dashboard. This is
the complete list. `Settings` in `src/pr_reviewer/config.py` has exactly these
seven fields, nothing else, so do not go looking for an eighth variable.

| Variable | What it does | What you get if you set it | What breaks if you do not |
|---|---|---|---|
| `DATABASE_URL` | Postgres connection string for job metadata. | The service can read and write jobs, installations, and findings. | The service never starts; nothing works. On Render this is filled in for you by the `reviewer-db` database in `deploy/render.yaml`. On Railway you must add it yourself. |
| `GITHUB_APP_ID` | The numeric id of your GitHub App. | The service can identify itself to GitHub's API. | Every GitHub API call fails. |
| `GITHUB_APP_PRIVATE_KEY` | The App's PEM private key, full text including the `BEGIN`/`END` lines. | The service can mint installation tokens to read PRs and post reviews. | The service cannot authenticate as the App; nothing GitHub-related works. |
| `GITHUB_OAUTH_CLIENT_ID` | The App's OAuth client id. | Users can start the GitHub sign-in flow. | Sign-in fails immediately. |
| `GITHUB_OAUTH_CLIENT_SECRET` | The App's OAuth client secret. | The sign-in flow can complete and issue a session. | Sign-in starts but never finishes. |
| `GITHUB_WEBHOOK_SECRET` | The secret you chose when creating the App's webhook. | Incoming webhook signatures are verified before a job is queued. | Every webhook is rejected; no review is ever queued. |
| `PR_REVIEWER_HOSTED_ORIGIN` | The public https origin this service is reachable at, no trailing slash. | The OAuth callback URL and GitHub App manifest are built with the right host. | OAuth callbacks and manifest URLs point at the wrong place, so sign-in and App installation both break. |

Nothing else belongs here. In particular, do not set `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `MODEL_KEY`, or `GITHUB_APP_SLUG` on the control plane.
None of that code runs on this side: a grep of `control_plane/` and `web/`
turns up zero references to a model key, and `GITHUB_APP_SLUG` is read only by
`src/pr_reviewer/tui/github_connect.py`, which is runner-side code that never
runs in the deploy image. Setting either would do nothing except leave a
secret sitting in a dashboard you do not need it in.

## Table B: runner (your own machine, `reviewer setup`)

These are not environment variables. `reviewer setup` writes most of them to
`setup.json` on your machine; the one secret value goes into your OS keyring
(or a mode-0600 file store where no OS keyring exists), never into a file you
could commit by accident and never into an env var. The field names below are
the real ones read by `src/pr_reviewer/runner/cli/setup_wizard.py`:
`provider_id`, `model_id`, `hosted_origin`, `prompt_name`, `prompt_version`,
`custom_base_url`, `custom_model_id`.

### Your LLM provider API key

Set this: pick a provider in `reviewer setup`, and paste its key when asked.
Get this: the review step can actually call a model.
Without this: `reviewer review` refuses with "no model key" and exit code `2`.

Which key you need depends on which provider you pick. Eleven providers are
built in today (`src/pr_reviewer/models/catalogue.py`): `openai`,
`anthropic`, `moonshot`, `qwen`, `openrouter`, `groq`, `xai`, `deepseek`,
`github-copilot`, `ollama`, `opencode`. Read that file for the current list
before assuming a provider exists; this list can grow.

The key itself is stored under the name `model_key` in your OS keyring (or the
file store), keyed to the `provider_id` you picked. It is never written to
`setup.json`, never printed back to you unmasked, and never read from an
environment variable.

### Custom endpoint and custom model

Set this: `custom_base_url` and `custom_model_id` in `reviewer setup`.
Get this: you can point the runner at any OpenAI-compatible endpoint that is
not in the catalogue above, for example a self-hosted model server.
Without this: the runner only offers the providers and models the catalogue
already lists.

### The agent prompt

Set this: `prompt_name` and `prompt_version`.
Get this: control over exactly which prompt text the runner sends.
Without this: the runner uses the built-in default prompt and version.

Prompts are insert-only. `PromptRegistry.register` raises if you try to
register a name and version that already exist
(`src/pr_reviewer/prompts/registry.py:27`). You cannot edit a prompt version
in place. To change the prompt text, register a new version under the same
name and bump `prompt_version` to point at it.

### Colour in the terminal

These are read from the environment by `src/pr_reviewer/runner/cli/style.py`,
so they are the one part of Table B you do set as env vars, not through
`reviewer setup`:

| Variable | Effect |
|---|---|
| `NO_COLOR` | Set (any value) to turn output colour off. |
| `PR_REVIEWER_NO_COLOR` | Same effect, project-specific name. |
| `FORCE_COLOR` | Set to force colour on even when output is not a terminal. |
| `TERM=dumb` | Also turns colour off, same as a real dumb terminal would. |

## Subscription-backed providers only run on the runner

`src/pr_reviewer/models/cli_provider.py` shells out to an external
command-line tool (for example a Codex-style CLI) and expects it to already be
logged in with a subscription, rather than sending a request with an API key.
That login is an interactive OAuth flow that needs a browser.

The Render and Railway deploy image is `python:3.12-slim` with only the Python
virtual environment installed: no Node, no CLI binaries, no browser, and no
way to complete that login inside a container. So a subscription-backed
provider cannot be selected through one-click deploy. There is no workaround
for this; it is a property of running headless in a container. This kind of
provider is a runner capability, chosen in `reviewer setup`, on a machine
where you have a real terminal and a browser to log in with.

## See also

- [ONE_CLICK_DEPLOY.md](ONE_CLICK_DEPLOY.md) - deploying the control plane
- [SELF_HOSTING.md](SELF_HOSTING.md) - installing and running the runner
