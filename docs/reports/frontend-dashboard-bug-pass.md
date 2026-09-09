# Frontend dashboard bug pass

Date: 2026-09-10

Scope: `apps/web` public site and dashboard UI only. No backend, eval, or redeploy.

## Audit coverage

| Area | Desktop 1440 | Mobile 390 | Console | Links | Tab order |
| --- | --- | --- | --- | --- | --- |
| Landing `/` | yes | yes | clean | 200 | focusable |
| Docs `/docs`, `/docs/agents` | yes | n/a | clean | 200 | n/a |
| Scorecard `/scorecard` | yes | yes | clean | 200 | n/a |
| Connect `/connect` | yes | yes | clean | 200 | n/a |
| Dashboard logged-out `/dashboard` | yes | yes | clean | 200 | n/a |
| Dashboard logged-in | blocked | blocked | n/a | n/a | n/a |

Playwright: `apps/web/tests/frontend-dashboard-bug-pass.spec.ts` (5 tests, all pass).

## Bugs fixed

### 1. Webpack crash after landing then dashboard

**Symptom:** `TypeError: __webpack_require__.n is not a function` when visiting a server-only page first, then `/dashboard`.

**Fix:** `apps/web/src/components/ClientRuntime.tsx` client child in root layout imports `next/link` so webpack keeps the helper.

**Evidence:** before screenshots show broken state at HEAD; after pass includes landing-to-dashboard navigation test with zero webpack errors.

### 2. Dev and production sharing one `.next` folder

**Symptom:** `TypeError: __webpack_modules__[moduleId] is not a function` after running `next build` then `next dev`.

**Fix:** `apps/web/next.config.ts` uses `.next-dev` in development; `.gitignore` ignores it.

### 3. Logged-out dashboard showed load error without control plane

**Symptom:** `/dashboard` with no session cookie showed "Could not load your reviews" when the control plane on port 8000 was not running (common in local Playwright).

**Fix:** `apps/web/src/lib/session.ts` short-circuits `fetchReviews` / `fetchProfile` to `unauthenticated` when `gh_live_sign_in` is absent.

## Blocked

**Dashboard logged-in (390px and 1440px):** needs a real `gh_live_sign_in` cookie tied to the hosted control plane. This VPS Playwright run has no owner session export, so authenticated layout, reviews list, and runner heartbeat UI were not re-screenshot here. Logged-out paths and sign-in gate were verified.

## Screenshots

Before (HEAD before fixes): `docs/reports/frontend-dashboard-bug-pass-screenshots/before/`

After (with fixes): `docs/reports/frontend-dashboard-bug-pass-screenshots/after-*.png`

| Route | Before | After |
| --- | --- | --- |
| Landing desktop | `before/desktop-landing.png` | `after-desktop-landing.png` |
| Docs desktop | `before/desktop-docs.png` | `after-desktop-docs.png` |
| Scorecard desktop | `before/desktop-scorecard.png` | `after-desktop-scorecard.png` |
| Connect desktop | `before/desktop-connect.png` | `after-desktop-connect.png` |
| Dashboard desktop | `before/desktop-dashboard.png` | `after-desktop-dashboard.png` |
| Landing mobile | `before/mobile-landing.png` | `after-mobile-landing.png` |
| Scorecard mobile | `before/mobile-scorecard.png` | `after-mobile-scorecard.png` |
| Dashboard mobile | `before/mobile-dashboard.png` | `after-mobile-dashboard.png` |

## Tests added

- `apps/web/tests/frontend-dashboard-bug-pass.spec.ts` - Playwright audit
- `tests/test_web_root_client_runtime.py` - ClientRuntime guard
- `tests/test_web_next_dev_dist_dir.py` - separate dev distDir guard
- `tests/test_web_dashboard_sign_in_without_cookie.py` - sign-in short-circuit guard

## Gates

- `bunx tsc --noEmit` in `apps/web`: pass
- Targeted pytest (7 tests above): pass
- `bun run build`: not run (not required by goal)
