# Launch readiness audit

Date: 2026-09-10 (UTC)
Hosted origin: https://reviewer.niresh.tech
GitHub repo: the-niresh/plug-and-play-reviewer
Audited commit on `origin/main`: `96eb40b` (local `main` also has `04c56bf`, `15d70ad` docs not pushed)

## Executive summary

**Ready now for an owner-operated beta** on `reviewer.niresh.tech`: public curl install,
hosted health, GitHub webhook loop, runner pairing, live PR review comments, human reply
feedback, and free-tier enforcement are all proved.

**Still blocks a stranger-only public launch** without owner help: no measured review quality
baseline, no GitHub Release checksum asset, docs commits not on GitHub `main`, no verified
stranger end-to-end run (browser pairing only), and marketing/findability gaps (OG image,
repo topics, naming).

## Area verdicts

| # | Area | Verdict | Evidence |
|---|---|---|---|
| 1 | Public install | **PASS** | [clean-machine-install-proof.md](clean-machine-install-proof.md); [public-install-live-review-proof.md](public-install-live-review-proof.md); curl HTTP 200 installs `96eb40b`; `reviewer --help` exit 0 |
| 2 | Hosted health/ready | **PASS** | Live `GET /health` and `GET /ready` return `200` and `{"status":"ok"}`; dashboard `200` |
| 3 | GitHub App live webhook path | **PASS** | [live-github-loop-proof.md](live-github-loop-proof.md) PR #8; public-install proof PR #9 webhook enqueue |
| 4 | Local runner pairing/start/status | **PASS** | Live proofs paired runners and `reviewer start`; `tests/test_runner_pairing.py`, `tests/test_tui_connect_device_login.py` pass |
| 5 | Live PR review comment | **PASS** | PR #8 review **5158722711**; PR #9 review **5159297169** with inline comments |
| 6 | Human reply feedback capture | **PASS** | Live `review_comment_feedback` on PR #8 ([live-github-loop-proof.md](live-github-loop-proof.md)); `tests/test_review_comment_feedback.py` covers path (see product risks for shared-DB flakes) |
| 7 | One-user-one-repo free tier | **PASS** | `tests/test_free_tier_access.py` pass; `access_policy.py` enforces at approve/exchange/enqueue |
| 8 | Docs accuracy | **PARTIAL** | README/INSTALL/DEPLOY/RUNBOOK match live host; INSTALL still documents curl **404 fallback** (stale after push); DEMO/RUNBOOK omit newest public-install proofs; local doc commits `15d70ad`/`04c56bf` not on `origin/main` |
| 9 | Landing/share metadata | **PARTIAL** | `apps/web/src/app/layout.tsx` sets `metadataBase`, Open Graph, Twitter card; `sitemap.ts` exists; no OG image asset; GitHub repo topics not verified (`gh` not authed on this host) |
| 10 | Repo hygiene | **PASS** | `tests/test_repo_hygiene.py` pass; root `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue/PR templates, `docs/REPO_TOPICS.md` |
| 11 | Remaining owner actions | **BLOCKED** | See owner actions below |
| 12 | Remaining product risks | **BLOCKED** | See product risks below |

## What is ready now

- Stranger can run the public curl one-liner against GitHub `main` at `96eb40b` and get a
  working `reviewer` command with the fixed secret-store backend.
- Live hosted plane at `reviewer.niresh.tech` is up; health and ready checks pass.
- Full GitHub loop works on real PRs when a paired runner with a model key is running.
- Free tier limits one GitHub user and one repository per installation.
- Human reply feedback is captured on live PR threads.
- Review context cache is implemented locally (`tests/test_review_context_cache.py` pass;
  cache hits observed in live proofs at USD 0 incremental).
- Repo hygiene files for open source are in place.

## What still blocks public launch

1. **No published quality baseline.** Holdout precision/recall are not measured or published.
   Internal `TODO.md` section 1 still marks this as blocking everything public.
2. **Docs on GitHub lag local.** Push `15d70ad`, `04c56bf`, and this audit commit to
   `origin/main`.
3. **No GitHub Release checksum asset** for offline/pinned install (`docs/INSTALL.md`,
   `README.md`).
4. **No stranger-only end-to-end proof.** Live proofs used owner-side pairing approval and
   model key on a known VPS. A true cold stranger still needs browser GitHub sign-in during
   setup (documented, not re-proved here).
5. **Findability/marketing incomplete.** No OG image, repo topics unset (unverified), naming
   across repo/site/domain not unified (`TODO.md` section 6).
6. **One-click Render/Railway deploy** documented but not run as a stranger path (`DEMO.md`).

## Owner actions

| Action | Why |
|---|---|
| Push local commits through `04c56bf` and this audit to `origin/main` | Public docs and proof reports match what strangers read on GitHub |
| Run `gh repo edit` topics from `docs/REPO_TOPICS.md` | Findability on GitHub |
| Publish GitHub Release + checksum asset | Offline install path in INSTALL/RUNBOOK |
| Add Open Graph image (1200x630) and wire in layout metadata | Social share cards |
| Run holdout diagnosis and publish honest numbers | Quality claim for README/marketing |
| Optional: stranger-only install test on a machine with no repo checkout | Confirms pairing UX without owner DB shortcuts |

## Product risks (not launch blockers for private beta)

| Risk | Notes |
|---|---|
| Review quality unknown publicly | Dev eval notes exist; no holdout scorecard published |
| `tests/test_review_comment_feedback.py` failed on shared Postgres during this audit run | Live capture on PR #8 succeeded; treat as CI/VPS isolation risk |
| Free tier one repo | Strangers with two repos hit `free_tier_one_repository` |
| Human gate required | Comments do not post until a person approves (by design) |
| Finding title/rationale on hosted plane | Documented in DATA_BOUNDARIES; landing privacy copy still TODO |
| Retrieval/specialists/consensus | Wired in code paths; not part of published baseline |

## Proof index

| Report | Verdict |
|---|---|
| [clean-machine-install-proof.md](clean-machine-install-proof.md) | PASS |
| [public-install-live-review-proof.md](public-install-live-review-proof.md) | PASS |
| [live-github-loop-proof.md](live-github-loop-proof.md) | PASS |

## Next task list (ordered)

1. Push `origin/main` through latest docs commits (`15d70ad`, `04c56bf`, this audit).
2. Run holdout per-case report (`TODO.md` section 1). Publish or defer public marketing until numbers exist.
3. Stranger-only install + pairing test (no repo checkout, no DB approve shortcut).
4. Publish GitHub Release checksum asset; update INSTALL/RUNBOOK.
5. Add OG image; run `gh repo edit` topics; unify product name across README and site title.
6. Update `docs/INSTALL.md` to remove stale curl 404 fallback; add public-install proof links to `DEMO.md` and `RUNBOOK.md`.
7. Decide go/no-go for public announcement vs owner-operated beta invite only.

## Audit commands run

```sh
curl -fsS https://reviewer.niresh.tech/health
curl -fsS https://reviewer.niresh.tech/ready
curl -fsS -o /dev/null -w '%{http_code}\n' https://raw.githubusercontent.com/the-niresh/plug-and-play-reviewer/main/scripts/install-reviewer.sh
uv run pytest -q tests/test_repo_hygiene.py tests/test_installer.py tests/test_free_tier_access.py tests/test_review_context_cache.py tests/test_docs_product_polish.py tests/test_runner_pairing.py tests/test_hosted_boundary_enforcement.py tests/test_package_boundaries.py
```

No evals, ablates, or scorecard writes were run for this audit.
