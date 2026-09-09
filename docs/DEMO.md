# Demo

| Mark | Means |
|---|---|
| ⬜ | Not done yet |
| ✅ | Runs on this checkout today |
| ❌ | Needs a deployment or a human |
| ❓ | Open |

Walk a signed webhook through to a human decision using commands that run
on this machine. The hosted origin `https://reviewer.niresh.tech` answers
`/health` and `/ready`. A first live comment on a real pull request still
needs the owner to point the GitHub App, pair a runner, and approve.

## Screenshots captured today - ✅

Playwright drives the live Task 21 API, then writes:

- `docs/assets/dashboard-desktop.png`
- `docs/assets/dashboard-mobile.png`

Command:

```bash
cd apps/web && bunx playwright test tests/dashboard.spec.ts -g "desktop and mobile screenshots"
```

The test asserts the approval titles that came over the wire, then captures
both viewports. It fails if the dashboard API is down.

## Signed webhook to a queued job - ✅ local

HMAC verification and enqueue are tested without a public hostname.

```bash
flock -w 3600 /tmp/pr-reviewer-pytest.lock uv run pytest -q tests/test_webhook.py
```

That suite proves missing headers, bad signatures, draft ignore, enqueue of
an opened pull request, and cancel of a closed one. It does not send a
payload to GitHub.

## Loopback dashboard and a human decision - ✅ local

Start the seeded dashboard API, the Next app, and the loopback onboarding
process the same way Playwright does (`apps/web/playwright.config.ts`).

```bash
cd apps/web && bunx playwright test tests/dashboard.spec.ts
```

That run:

1. Hits `/dashboard/health` on `127.0.0.1:8742`.
2. Opens a local session and shows the paired runner id.
3. Lists jobs the live API returned.
4. Approves `Null check on widget.value` with CSRF.
5. Rejects `Reject this queued finding`.

The dashboard has no webhook route
(`tests/test_dashboard_auth.py::test_dashboard_exposes_no_webhook_route`).
GitHub never posts to the user's machine.

## Local webhook to human decision - ✅ local

One test drives the hops that do not need DNS:

```bash
flock -w 3600 /tmp/pr-reviewer-pytest.lock uv run pytest -q tests/test_local_webhook_to_human_path.py
```

It asserts: a signed webhook creates one installation-scoped job, a paired
runner claims it over `/api/runner/jobs/claim`, analysis-only forces human
approval, the gate holds the finding so mock GitHub stays empty, a human
`allow_public_post` posts once, and a newer head SHA supersedes the job so a
stale post does not fire. Runtime Task 10 is still not done.

## Hosted health on reviewer.niresh.tech - ✅ live

`GET https://reviewer.niresh.tech/health` and
`GET https://reviewer.niresh.tech/ready` return `200` and `{"status":"ok"}`.
That is the hosted control plane and its database check.

A signed GitHub delivery still needs the App webhook pointed at
`https://reviewer.niresh.tech/api/github/webhook`. That App setting is owner
work. See [RUNBOOK.md](RUNBOOK.md).

## Posting to a real pull request - ❌ needs owner setup and a human

`post_review` is tested for stale head and duplicate keys. Posting onto a
real PR still needs the App URLs, a paired runner, a model key, and a human
approval. Retrieval, an optional suggested fix, and opt-in specialists can
run on that path. They are not a published baseline.

## What this demo is not

- It is not a 14-day FoodSpector shadow.
- It does not report precision, recall, or cost per PR. Dev eval notes are
  not a baseline.
- It does not use Redis.

## Settled - ✅

- ✅ Local webhook tests and the Playwright approval path run today.
- ✅ Hosted `/health` and `/ready` on `reviewer.niresh.tech` answer today.
- ❌ A live GitHub comment still needs owner App URLs, a runner, and a human.
