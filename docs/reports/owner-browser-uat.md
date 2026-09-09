# Owner browser UAT

Date: 2026-09-10 (updated after owner GitHub sign-in)
Hosted origin: https://reviewer.niresh.tech
Browser: Playwright Chromium (headless) for public routes; authenticated state verified by owner in real browser
Runner: public install proof (`/tmp/public-install-proof-v2-2457058`, paired as `the-niresh`)

v0.1.0 is a **proof release**, not a public launch. This UAT is from the owner's
perspective on the real hosted product.

## Executive summary

| Area | Verdict |
|---|---|
| Public hosted pages (landing, docs, scorecard, connect) | **PASS** |
| GitHub OAuth sign-in | **PASS** (owner completed login 2026-09-10) |
| Authenticated dashboard (reviews, settings, repo list) | **PASS** (non-empty dashboard; 3 repos on settings) |
| Runner pairing + live reviews | **PASS** (paired runner + GitHub review proofs) |

No code changes. No new PR opened.

## Checklist

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | Landing loads on reviewer.niresh.tech | **PASS** | [01-landing-desktop.png](owner-browser-uat-screenshots/01-landing-desktop.png), [01-landing-mobile.png](owner-browser-uat-screenshots/01-landing-mobile.png) |
| 2 | GitHub sign-in works | **PASS** | OAuth redirect proved in [02-github-oauth-login.png](owner-browser-uat-screenshots/02-github-oauth-login.png). Owner completed sign-in in browser 2026-09-10. |
| 3 | Dashboard opens after sign-in | **PASS** | Owner confirmed authenticated dashboard is **not empty** (reviews/findings visible). Pre-auth gate: [02-dashboard-logged-out.png](owner-browser-uat-screenshots/02-dashboard-logged-out.png). |
| 4 | GitHub App install/connect flow | **PASS** | `/connect` shows "Choose repositories on GitHub" CTA. [04-connect.png](owner-browser-uat-screenshots/04-connect.png) |
| 5 | Free tier one-user-one-repo wording clear | **PASS** | Landing section 06: "The free tier allows one GitHub user and one repository per installation." |
| 6 | Pairing flow works with local runner | **PASS** | Paired runner credential returns 200 from `GET /api/runner/installation` as `the-niresh`. Live loop in [public-install-live-review-proof.md](public-install-live-review-proof.md). |
| 7 | Runner status visible | **PARTIAL** | Hosted dashboard shows **review jobs and findings** (indirect proof the runner ran). There is no separate "runner online" heartbeat on the hosted UI. Local runner daemon was active on port 8771 during earlier proofs. |
| 8 | Repo selection works | **PASS** | Owner confirmed **3 repositories** listed on `/dashboard/settings` after sign-in. Install/change link also works from `/connect`. |
| 9 | Existing live review proof visible/traceable | **PASS** | GitHub: PR #9 review **5159297169**; PR #8 review **5158722711**. See [live-github-loop-proof.md](live-github-loop-proof.md). |
| 10 | New tiny PR | **N/A** | Not opened (existing PR #8/#9 proofs suffice). |

Additional public routes captured: [05-docs.png](owner-browser-uat-screenshots/05-docs.png), [06-docs-agents.png](owner-browser-uat-screenshots/06-docs-agents.png), [07-scorecard.png](owner-browser-uat-screenshots/07-scorecard.png).

Baseline honesty on landing: **PASS** ("does not learn from human replies yet", 7 Zod holdout wording).

## Authenticated dashboard (owner-verified 2026-09-10)

Owner completed GitHub sign-in on https://reviewer.niresh.tech and confirmed:

- `/dashboard` loads with review data (not empty)
- `/dashboard/settings` lists **3 connected repositories**
- Sign-out avatar/menu visible in dashboard shell

Automated Playwright on this VPS cannot reuse the owner's browser session cookie, so
authenticated screenshots were not captured by the agent. To capture them locally after
sign-in:

```sh
cd apps/web
node -e "
import { chromium } from '@playwright/test';
const b = await chromium.launch({ headless: false });
const p = await b.newPage();
await p.goto('https://reviewer.niresh.tech/dashboard');
console.log('Sign in manually, then press Enter');
await new Promise(r => process.stdin.once('data', r));
await p.screenshot({ path: '../docs/reports/owner-browser-uat-screenshots/03-dashboard-authenticated.png', fullPage: true });
await p.goto('https://reviewer.niresh.tech/dashboard/settings');
await p.screenshot({ path: '../docs/reports/owner-browser-uat-screenshots/08-settings-authenticated.png', fullPage: true });
await b.close();
"
```

## Owner reproduction steps (no hidden commands)

### Sign in and view dashboard

1. Open https://reviewer.niresh.tech/dashboard
2. Click **Sign in with GitHub**
3. Log in and approve OAuth
4. Confirm dashboard shows review summary and recent reviews
5. Open https://reviewer.niresh.tech/dashboard/settings and confirm repository list

### Pair and run reviews (CLI)

```sh
curl -fsSL https://raw.githubusercontent.com/the-niresh/plug-and-play-reviewer/main/scripts/install-reviewer.sh | sh
reviewer setup --hosted-origin https://reviewer.niresh.tech
reviewer start --hosted-origin https://reviewer.niresh.tech --host 127.0.0.1 --port 8771
```

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
| Initial UAT report + public screenshots | `6c8fd1d` |
| Post sign-in report update | this commit |
