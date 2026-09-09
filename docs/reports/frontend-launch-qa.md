# Frontend launch QA

Date: 2026-09-10
Scope: Public frontend before any announcement (v0.1.0 is a **proof release**, not public launch)
Hosted origin checked: https://reviewer.niresh.tech
Local preview: `main` branch via `next dev` and Playwright on http://127.0.0.1:3000

## Executive verdict

| Surface | Verdict | Notes |
|---|---|---|
| **Production (`reviewer.niresh.tech`)** | **BLOCKED** | Deploy is behind `main`. Metadata routes 404, scorecard still refuses, landing copy stale |
| **Local preview (`main`)** | **PASS** | Routes, copy, scorecard numbers, metadata, keyboard nav, mobile layout all good |
| **Automated tests / typecheck** | **PASS** | 59 pytest + Playwright metadata test + `tsc --noEmit` |

**No frontend code fixes were required.** The blocker is redeploying the web app so production matches `main` (through at least `428d0f4`).

## Route checks

| Route | Live HTTP | Live QA | Local QA | Screenshot |
|---|---|---|---|---|
| `/` landing | 200 | **BLOCKED** stale copy | PASS | [live](frontend-launch-qa-screenshots/live/desktop-landing.png) · [local](frontend-launch-qa-screenshots/desktop-landing.png) |
| `/` mobile | 200 | **BLOCKED** stale copy | PASS (no overlap) | [live](frontend-launch-qa-screenshots/live/mobile-landing.png) · [local](frontend-launch-qa-screenshots/mobile-landing.png) |
| `/docs` | 200 | PASS | PASS | [live](frontend-launch-qa-screenshots/live/desktop-docs.png) · [local](frontend-launch-qa-screenshots/desktop-docs.png) |
| `/docs/agents` | 200 | PASS | PASS | [live](frontend-launch-qa-screenshots/live/desktop-docs-agents.png) · [local](frontend-launch-qa-screenshots/desktop-docs-agents.png) |
| `/scorecard` | 200 | **BLOCKED** refusal strings | PASS numeric baseline | [live](frontend-launch-qa-screenshots/live/desktop-scorecard.png) · [local](frontend-launch-qa-screenshots/desktop-scorecard.png) |
| `/connect` | 200 | PASS (install CTA present) | PASS | [live](frontend-launch-qa-screenshots/live/desktop-connect.png) · [local](frontend-launch-qa-screenshots/desktop-connect.png) |
| `/dashboard` auth | 200 | **BLOCKED** sign-in only (expected without OAuth) | PASS sign-in gate | [live](frontend-launch-qa-screenshots/live/desktop-dashboard.png) · [local](frontend-launch-qa-screenshots/desktop-dashboard.png) |
| `/opengraph-image` | **404** | **BLOCKED** | PASS 200 | n/a (live 404) |
| `/sitemap.xml` | **404** | **BLOCKED** | PASS 200 | [live status](frontend-launch-qa-screenshots/live/metadata-status.json) |
| `/robots.txt` | **404** | **BLOCKED** | PASS 200 | same |

## Copy and claims audit (local `main`)

| Check | Result |
|---|---|
| No stale "install/release/proof missing" copy | PASS |
| Holdout baseline honest (7 Zod cases only) | PASS on landing + scorecard sample line |
| No unsupported self-improvement claim | PASS ("does not learn from human replies yet") |
| Team vs free-tier wording clear | PASS (one GitHub user, one repo; team path described) |
| v0.1.0 framed as proof release | PASS in repo docs; live landing not yet updated |

Live landing is missing sections present on `main` (for example "What the evals show", "What teams can change", holdout honesty block). Live scorecard still shows `holdout is empty; refusing to report`.

## Auth / connect flow (no secrets)

| Step | Result |
|---|---|
| Sign-in link on landing | PASS live + local (`/api/auth/github/sign-in?return_to=/dashboard`) |
| Full GitHub OAuth completion | **BLOCKED** (needs human GitHub login; not run) |
| `/connect` repository picker CTA | PASS live (GitHub App install link renders) |
| Dashboard without session | PASS (sign-in prompt; no data leak in HTML) |

## Keyboard navigation

Local tab order reaches skip link, site nav (Docs, Scorecard, Dashboard), deploy link, and sign-in. See [keyboard-tab-order-local.json](frontend-launch-qa-screenshots/keyboard-tab-order-local.json).

Live tab order on current deploy only cycles sign-in and body ([keyboard-tab-order-live.json](frontend-launch-qa-screenshots/keyboard-tab-order-live.json)). This matches the older landing without full nav focus targets.

## Mobile layout

Playwright overlap scan at 390px width on local landing: **0 overlapping text nodes**. Screenshots at 390px for landing and scorecard captured.

## Tests run

```text
uv run pytest -q tests/test_site_metadata.py tests/test_docs_product_polish.py \
  tests/test_web_scorecard.py tests/test_web_landing_sign_in.py \
  tests/test_web_onboarding_sign_in.py tests/test_web_connect_asks_only_for_repositories.py \
  tests/test_web_agent_surfaces_docs.py tests/test_web_dashboard.py
# 59 passed

cd apps/web && bunx tsc --noEmit -p tsconfig.json
# exit 0

cd apps/web && bunx playwright test tests/launch-qa-screenshots.spec.ts
# 3 passed (desktop routes, mobile, metadata routes on local dev)
```

Constraints honored: no evals, no ablate, no scorecard number changes, no backend edits.

## Fixes and commits

| Fix | Commit |
|---|---|
| None (production redeploy required) | n/a |

This QA commit adds the report, screenshots, and a Playwright spec for local regression.

## Owner action to clear production BLOCKED items

Redeploy the web app on `reviewer.niresh.tech` from current `main` so production includes:

- `sitemap.ts`, `robots.ts`, `opengraph-image.tsx`
- Updated landing copy (holdout honesty, free tier, no self-improvement)
- Published `docs/reports/scorecard.json` on `/scorecard`

After redeploy, re-check:

```sh
curl -fsSL -o /dev/null -w "og:%{http_code}\n" https://reviewer.niresh.tech/opengraph-image
curl -fsSL https://reviewer.niresh.tech/sitemap.xml | head
curl -fsSL https://reviewer.niresh.tech/scorecard | grep -E "gpt-4o-mini|7 holdout"
```

## Remaining launch blockers (unchanged)

1. ~~Published release install~~ verified in `428d0f4`
2. Stranger-only install + browser pairing (no owner DB shortcuts)
3. Optional OG card validator (after redeploy makes `/opengraph-image` live)
4. Feedback-to-eval loop (optional product story)
5. **Production web redeploy** (new from this QA)
