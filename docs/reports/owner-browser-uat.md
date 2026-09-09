# Owner browser UAT

Date: 2026-09-10
Hosted origin: https://reviewer.niresh.tech
Browser: Playwright Chromium (headless) against live production
Runner: public install proof (`/tmp/public-install-proof-v2-2457058`, paired as `the-niresh`)

v0.1.0 is a **proof release**, not a public launch. This UAT is from the owner's
perspective on the real hosted product.

## Executive summary

| Area | Verdict |
|---|---|
| Public hosted pages (landing, docs, scorecard, connect) | **PASS** |
| GitHub OAuth sign-in starts correctly | **PASS** |
| Authenticated dashboard (reviews, settings, repo list) | **BLOCKED** (owner must finish GitHub login in browser) |
| Runner pairing + live reviews | **PASS** (proved via paired runner + GitHub API; see below) |

No code changes. No new PR opened.

## Checklist

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | Landing loads on reviewer.niresh.tech | **PASS** | [01-landing-desktop.png](owner-browser-uat-screenshots/01-landing-desktop.png), [01-landing-mobile.png](owner-browser-uat-screenshots/01-landing-mobile.png) |
| 2 | GitHub sign-in works (OAuth starts) | **PASS** | Clicking "Sign in with GitHub" on `/dashboard` redirects to `github.com/login` with `client_id` and `return_to` oauth authorize URL. [02-github-oauth-login.png](owner-browser-uat-screenshots/02-github-oauth-login.png) |
| 3 | Dashboard opens after sign-in | **BLOCKED** | [02-dashboard-logged-out.png](owner-browser-uat-screenshots/02-dashboard-logged-out.png). Automated browser has no GitHub session. Owner must complete login (steps below). |
| 4 | GitHub App install/connect flow | **PASS** | `/connect` shows "Choose repositories on GitHub" CTA. [04-connect.png](owner-browser-uat-screenshots/04-connect.png) |
| 5 | Free tier one-user-one-repo wording clear | **PASS** | Landing section 06: "The free tier allows one GitHub user and one repository per installation." |
| 6 | Pairing flow works with local runner | **PASS** | Paired runner credential returns 200 from `GET /api/runner/installation` as `the-niresh` with `the-niresh/YeahScene-AI`. Documented live loop in [public-install-live-review-proof.md](public-install-live-review-proof.md). |
| 7 | Runner status visible | **PARTIAL** | Hosted dashboard does not show runner heartbeat without login. Runner daemon process active on port 8771; `GET /onboarding/mode` returns `granted_mode: full`. CLI `reviewer status` reports onboarding server state separately. |
| 8 | Repo selection works | **PARTIAL** | Installation API lists 1 repo (`the-niresh/YeahScene-AI`). Browser `/dashboard/settings` requires sign-in (same blocker as #3). GitHub install URL works from `/connect`. |
| 9 | Existing live review proof visible/traceable | **PASS** | GitHub API: PR #9 reviews **5159297169** by `pr-reviewer-niresh[bot]`; inline comment **3972527103**. PR #8 review **5158722711** in [live-github-loop-proof.md](live-github-loop-proof.md). |
| 10 | New tiny PR | **N/A** | Not opened (not needed; existing PR #8/#9 proofs suffice). |

Additional public routes captured: [05-docs.png](owner-browser-uat-screenshots/05-docs.png), [06-docs-agents.png](owner-browser-uat-screenshots/06-docs-agents.png), [07-scorecard.png](owner-browser-uat-screenshots/07-scorecard.png).

Baseline honesty on landing: **PASS** ("does not learn from human replies yet", 7 Zod holdout wording).

## Owner steps to clear BLOCKED #3 and #8 (browser dashboard)

These are the exact clicks. No hidden commands.

1. Open https://reviewer.niresh.tech/dashboard
2. Click **Sign in with GitHub**
3. Log in to GitHub as `the-niresh` (or your install owner account)
4. Approve OAuth for the PR Reviewer App if prompted
5. You should land back on `/dashboard` with reviews listed (YeahScene-AI jobs from live proofs)
6. Open https://reviewer.niresh.tech/dashboard/settings to see connected repositories
7. Optional: click **Change repository permission on GitHub** to add/remove repos

If step 5 shows an empty dashboard, confirm the runner is started:

```sh
reviewer start --hosted-origin https://reviewer.niresh.tech --host 127.0.0.1 --port 8771
```

## Owner steps to re-run pairing (check #6, if needed)

From a machine with the public `reviewer` CLI installed:

```sh
curl -fsSL https://raw.githubusercontent.com/the-niresh/plug-and-play-reviewer/main/scripts/install-reviewer.sh | sh
reviewer setup --hosted-origin https://reviewer.niresh.tech
reviewer start --hosted-origin https://reviewer.niresh.tech --host 127.0.0.1 --port 8771
```

During `reviewer setup`, the browser opens hosted GitHub sign-in (same as dashboard step 2-4 above). Approve pairing in the terminal/TUI when prompted.

## Runner + installation evidence (2026-09-10)

```text
GET https://reviewer.niresh.tech/api/runner/installation
Authorization: Bearer <runner credential>
-> 200
github_login: the-niresh
installation_id: 158479604
repositories: the-niresh/YeahScene-AI (931464048)
```

Process: `reviewer start --hosted-origin https://reviewer.niresh.tech --port 8771` (PID active during UAT).

## Live review traceability

| PR | GitHub review id | Inline comment |
|---|---|---|
| [YeahScene-AI #8](https://github.com/the-niresh/YeahScene-AI/pull/8) | 5158722711 | [3972082930](https://github.com/the-niresh/YeahScene-AI/pull/8#discussion_r3972082937) |
| [YeahScene-AI #9](https://github.com/the-niresh/YeahScene-AI/pull/9) | 5159297169 | [3972527103](https://github.com/the-niresh/YeahScene-AI/pull/9#discussion_r3972527103) |

## Constraints honored

- No evals, no ablate, no scorecard number changes, no prompt/matcher/model default changes
- No application code changes
- No new PR opened

## Fixes and commits

| Item | Commit |
|---|---|
| UAT report + screenshots | this commit |

## Remaining after owner completes browser login

1. Re-screenshot `/dashboard` and `/dashboard/settings` while signed in
2. Confirm reviews list shows YeahScene-AI jobs
3. Optional: stranger-only UAT (cold machine, no owner DB shortcuts)
