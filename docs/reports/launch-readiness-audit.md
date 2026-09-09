# Launch readiness audit

Date: 2026-09-10 (UTC), updated after final launch polish
Hosted origin: https://reviewer.niresh.tech
GitHub repo: the-niresh/plug-and-play-reviewer
Audited commits: `7dc7abf` (holdout baseline), `c3039e4` (scorecard test fix), plus polish commit pending push

## Executive summary

**Ready now for an owner-operated beta** on `reviewer.niresh.tech`: public curl install,
hosted health, GitHub webhook loop, runner pairing, live PR review comments, human reply
feedback, free-tier enforcement, and a published holdout scorecard are all proved.

**Still blocks a stranger-only public launch** without owner help: no GitHub Release
checksum asset, no verified stranger-only end-to-end run (browser pairing only), and
repo topics not set on GitHub (requires admin `gh` access).

## Naming (public-facing)

| Surface | Name |
|---|---|
| Product (site title, README heading, OG) | **PR Reviewer** |
| GitHub repository | **plug-and-play-reviewer** |
| uv package / tool name | **plug-and-play-reviewer** |
| Live domain | **reviewer.niresh.tech** |
| Product Hunt (recommended) | **PR Reviewer** (owner picks at listing time) |

## Area verdicts

| # | Area | Verdict | Evidence |
|---|---|---|---|
| 1 | Public install | **PASS** | [clean-machine-install-proof.md](clean-machine-install-proof.md); [public-install-live-review-proof.md](public-install-live-review-proof.md); curl HTTP 200 on GitHub `main` |
| 2 | Hosted health/ready | **PASS** | Live `GET /health` and `GET /ready` return `200` and `{"status":"ok"}` |
| 3 | GitHub App live webhook path | **PASS** | [live-github-loop-proof.md](live-github-loop-proof.md) PR #8; [public-install-live-review-proof.md](public-install-live-review-proof.md) PR #9 |
| 4 | Local runner pairing/start/status | **PASS** | Live proofs; `tests/test_runner_pairing.py` pass |
| 5 | Live PR review comment | **PASS** | PR #8 review **5158722711**; PR #9 review **5159297169** |
| 6 | Human reply feedback capture | **PASS** | Live `review_comment_feedback` on PR #8 |
| 7 | One-user-one-repo free tier | **PASS** | `tests/test_free_tier_access.py`; README and landing state the limit plainly |
| 8 | Docs accuracy | **PASS** | INSTALL curl 404 fallback removed; DEMO/RUNBOOK link all live proofs; README names narrow Zod baseline |
| 9 | Landing/share metadata | **PASS** | `layout.tsx` metadataBase + OG/Twitter; `opengraph-image.tsx` 1200x630; sitemap/robots present. Card validator not run on this host |
| 10 | Repo hygiene | **PASS** | `tests/test_repo_hygiene.py`; SECURITY.md, templates, [REPO_TOPICS.md](../REPO_TOPICS.md) |
| 11 | Remaining owner actions | **BLOCKED** | See owner actions below |
| 12 | Remaining product risks | **PARTIAL** | See product risks below |

## What is ready now

- Stranger can run the public curl one-liner against GitHub `main` and get a working
  `reviewer` command.
- Live hosted plane at `reviewer.niresh.tech` is up.
- Full GitHub loop works on real PRs when a paired runner with a model key is running.
- Free tier limits one GitHub user and one repository per installation (no fake billing copy).
- Published holdout baseline: 7 Zod cases, gpt-4o-mini, precision 0.667 / recall 0.571.
  See [holdout-quality-baseline.md](holdout-quality-baseline.md) and `/scorecard`.
- Human reply feedback is captured on live PR threads (not self-improvement).
- Review context cache implemented and observed at USD 0 on cache hits in live proofs.

## What still blocks public launch

1. **GitHub Release not published yet.** Checksum install path is built and proved locally
   ([release-checksum-install-proof.md](release-checksum-install-proof.md)). Owner must push `v0.1.0`.
2. **No stranger-only end-to-end proof.** Live proofs used owner-side pairing approval
   and a model key on a known VPS. A cold stranger still needs browser GitHub sign-in
   during setup (documented, not re-proved here).
3. **GitHub repo topics unset.** `gh` is not authenticated on this VPS. Owner must run
   the command in [REPO_TOPICS.md](../REPO_TOPICS.md).
4. **One-click Render/Railway deploy** documented but not run as a stranger path (`DEMO.md`).
5. **Push local commits** (`7dc7abf`, `c3039e4`, polish) to `origin/main` so GitHub
   matches what strangers read.

## Owner actions

| Action | Why |
|---|---|
| `git push origin main` through baseline, scorecard test fix, and polish commits | Public GitHub matches local docs and proofs |
| Run `gh auth login` then `gh repo edit` topics from [REPO_TOPICS.md](../REPO_TOPICS.md) | Findability on GitHub (requires repo admin) |
| Push `v0.1.0` tag to trigger release workflow (or `gh release create`) | Publishes SHA256SUMS + compose asset on GitHub |
| Optional: run og card validator on `https://reviewer.niresh.tech/opengraph-image` | Confirms social preview outside this VPS |
| Optional: stranger-only install test on a machine with no repo checkout | Confirms pairing UX without owner DB shortcuts |
| Product Hunt listing under **PR Reviewer** when ready | Matches site/README product name |

## Product risks (not launch blockers for private beta)

| Risk | Notes |
|---|---|
| Narrow quality sample | 7 Zod holdout cases only; not proof on Flask, TypeScript apps, or your repo |
| `tests/test_review_comment_feedback.py` may flake on shared Postgres | Live capture on PR #8 succeeded |
| Free tier one repo | Strangers with two repos hit `free_tier_one_repository` |
| Human gate required | Comments do not post until a person approves (by design) |
| Finding title/rationale on hosted plane | Documented in DATA_BOUNDARIES; landing states it plainly |
| Retrieval/specialists | Wired in code paths; not part of published baseline |

## Proof index

| Report | Verdict |
|---|---|
| [clean-machine-install-proof.md](clean-machine-install-proof.md) | PASS |
| [public-install-live-review-proof.md](public-install-live-review-proof.md) | PASS |
| [live-github-loop-proof.md](live-github-loop-proof.md) | PASS |
| [holdout-quality-baseline.md](holdout-quality-baseline.md) | PASS (published, narrow sample) |

## Next task list (ordered)

1. Owner pushes `origin/main` through latest commits.
2. Owner runs `gh repo edit` topics from REPO_TOPICS.md.
3. Publish GitHub Release checksum asset; update INSTALL/RUNBOOK.
4. Stranger-only install + pairing test (no repo checkout, no DB approve shortcut).
5. Decide go/no-go for public announcement vs owner-operated beta invite only.

No evals, ablates, or scorecard number changes were run for this polish pass.
