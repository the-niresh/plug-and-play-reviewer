# Frontend launch QA

Date: 2026-09-10
Scope: Public frontend before any announcement (v0.1.0 is a **proof release**, not public launch)
Hosted origin: https://reviewer.niresh.tech
Repo commit deployed to UI: `7f55471`

## Executive verdict

| Surface | Verdict | Notes |
|---|---|---|
| **Production (`reviewer.niresh.tech`)** | **PASS** (re-checked 2026-09-10 after UI redeploy) | All launch QA blockers cleared |
| **Local preview (`main`)** | **PASS** | Matches production after redeploy |
| **Automated tests / typecheck** | **PASS** | 59 pytest + Playwright metadata test + `tsc --noEmit` |

## Production redeploy (2026-09-10)

**Root cause:** Traefik still routed UI traffic to stale `pr-reviewer-ui-1` (4 days old,
project `pr-reviewer`) while API had already moved to `plug-and-play-reviewer-api-1`.

**Action taken on host `76.13.243.12`:**

```sh
docker stop pr-reviewer-ui-1 && docker rm pr-reviewer-ui-1
cd /root/claude/projects/plug-and-play-reviewer
docker compose -f compose.release.yml -f docker-compose.hosted.yml build ui
docker compose -f compose.release.yml -f docker-compose.hosted.yml up -d ui
```

New container: `plug-and-play-reviewer-ui-1` (image built from `7f55471`).

No application code changes. No scorecard number changes.

## Production re-check (post-redeploy)

| Check | Result | Evidence |
|---|---|---|
| `/opengraph-image` | PASS 200 | [metadata-status.json](frontend-launch-qa-screenshots/live-post-redeploy/metadata-status.json) |
| `/sitemap.xml` | PASS 200 | same |
| `/robots.txt` | PASS 200 | same |
| `/scorecard` shows gpt-4o-mini + 7 Zod holdout | PASS | curl grep on live HTML |
| Landing: free tier, team, no self-improvement, baseline | PASS | curl grep on live HTML |
| `/dashboard` sign-in gate when logged out | PASS | "Sign in with GitHub" in HTML |
| `/connect` repository picker | PASS | "Choose repositories on GitHub" |

Post-redeploy screenshots: [live-post-redeploy/](frontend-launch-qa-screenshots/live-post-redeploy/)

```sh
curl -fsSL -o /dev/null -w "og:%{http_code} sitemap:%{http_code} robots:%{http_code}\n" \
  https://reviewer.niresh.tech/opengraph-image \
  https://reviewer.niresh.tech/sitemap.xml \
  https://reviewer.niresh.tech/robots.txt
# og:200 sitemap:200 robots:200
```

## Route checks (initial QA, pre-redeploy)

The first QA pass on 2026-09-10 found production **BLOCKED** because the UI container
was stale. Evidence kept under [live/](frontend-launch-qa-screenshots/live/) for comparison.

| Route | Pre-redeploy | Post-redeploy |
|---|---|---|
| Metadata routes | 404 | 200 |
| Scorecard | refusal strings | numeric baseline |
| Landing copy | stale | updated sections live |
| Docs / connect | PASS | PASS |

Local preview screenshots: [frontend-launch-qa-screenshots/](frontend-launch-qa-screenshots/)

## Copy and claims audit (production, post-redeploy)

| Check | Result |
|---|---|
| No stale "install/release/proof missing" copy | PASS |
| Holdout baseline honest (7 Zod cases only) | PASS on landing + scorecard |
| No unsupported self-improvement claim | PASS ("does not learn from human replies yet") |
| Team vs free-tier wording clear | PASS |
| v0.1.0 framed as proof release | PASS in repo docs |

## Auth / connect flow (no secrets)

| Step | Result |
|---|---|
| Sign-in link on landing | PASS |
| Full GitHub OAuth completion | **BLOCKED** for automated QA (needs human login; see owner-browser-uat) |
| `/connect` repository picker CTA | PASS |
| Dashboard without session | PASS (sign-in prompt only) |

## Tests run (initial QA)

```text
uv run pytest -q tests/test_site_metadata.py tests/test_docs_product_polish.py \
  tests/test_web_scorecard.py tests/test_web_landing_sign_in.py \
  tests/test_web_onboarding_sign_in.py tests/test_web_connect_asks_only_for_repositories.py \
  tests/test_web_agent_surfaces_docs.py tests/test_web_dashboard.py
# 59 passed

cd apps/web && bunx playwright test tests/launch-qa-screenshots.spec.ts
# 3 passed
```

Constraints honored: no evals, no ablate, no scorecard number changes, no backend code edits.

## Fixes and commits

| Fix | Commit / action |
|---|---|
| Frontend launch QA report + screenshots | `7f55471` |
| Production UI redeploy | Docker on host (no git commit) |
| Production re-check report update | this commit |

## Remaining launch blockers

1. ~~Published release install~~ verified in `428d0f4`
2. ~~Production web redeploy~~ done 2026-09-10
3. **Owner browser UAT** - login, dashboard, GitHub pairing, runner flow from real site
4. Stranger-only install + browser pairing (no owner DB shortcuts)
5. Optional OG card validator (route now live; external validator not run here)
6. Feedback-to-eval loop (optional product story)
