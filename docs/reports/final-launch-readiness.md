# Final launch readiness

Date: 2026-09-10 (UTC)
Hosted origin: https://reviewer.niresh.tech
Local HEAD: `410dc4b` (`docs: record three-real-pr production demo`)
GitHub `origin/main`: `463edc9` (5 commits behind local; see check 1)

## Executive verdict

**PARTIAL.** The live product on `reviewer.niresh.tech` passes production smoke checks,
published scorecard, release assets, install script, and the full proof chain through the
three-real-pr demo. **Owner-operated beta and demo storytelling are ready.**

**Public launch is still blocked** until `origin/main` is pushed through the five local
commits (demo report, dashboard PR links, sitemap dockerignore fix, and two earlier fixes).

## Check table

| # | Check | Verdict | Evidence |
|---|---|---|---|
| 1 | `origin/main` has latest commits including 3 PR demo report | **BLOCKED** | Local `410dc4b`; `origin/main` at `463edc9`. Unpushed: `505da25`, `55dc0dc`, `51b53c3`, `2903d7f`, `410dc4b` |
| 2 | Production routes return 200 | **PASS** | 2026-09-10 curl: `/`, `/connect`, `/dashboard`, `/scorecard`, `/sitemap.xml`, `/robots.txt`, `/opengraph-image` all **200** |
| 3 | `/connect` has GitHub App install link | **PASS** | `https://github.com/apps/pr-reviewer-niresh/installations/new` in live HTML |
| 4 | `/scorecard` shows gpt-4o-mini and 7 Zod holdout | **PASS** | Live HTML: Model `gpt-4o-mini`, Sample `7 holdout cases, all from the Zod repository`, 7 PRs reviewed |
| 5 | `/api/reviews` includes `pull_request_url` when signed in | **PASS** | Live API + DB: PR 10 and 11 return `https://github.com/the-niresh/YeahScene-AI/pull/{n}` (deployed UI/API from `2903d7f`) |
| 6 | Release `v0.1.0` has both assets | **PASS** | `pr-reviewer-0.1.0-compose.release.yml` and `SHA256SUMS` on GitHub Release (published 2026-09-09) |
| 7 | Public curl install script returns 200 | **PASS** | `curl` on `raw.githubusercontent.com/.../scripts/install-reviewer.sh` returns **200** |
| 8 | Proof reports linked below | **PASS** | All eight reports exist and are cited in this document |

## Proof reports

| Report | Verdict | Link |
|---|---|---|
| Clean machine install | PASS | [clean-machine-install-proof.md](clean-machine-install-proof.md) |
| Public install live review | PASS | [public-install-live-review-proof.md](public-install-live-review-proof.md) |
| Release checksum install | PASS | [release-checksum-install-proof.md](release-checksum-install-proof.md) |
| Live GitHub loop | PASS | [live-github-loop-proof.md](live-github-loop-proof.md) |
| Stranger UAT | PASS | [stranger-only-uat.md](stranger-only-uat.md) |
| Frontend launch QA | PASS | [frontend-launch-qa.md](frontend-launch-qa.md) |
| Holdout quality baseline | PASS | [holdout-quality-baseline.md](holdout-quality-baseline.md) |
| Three real PR demo | PASS | [three-real-pr-demo.md](three-real-pr-demo.md) |

## Demo links (production, 2026-09-10)

| Demo | URL |
|---|---|
| Correctness PR (#10) | https://github.com/the-niresh/YeahScene-AI/pull/10 |
| Bot comment with suggested fix | https://github.com/the-niresh/YeahScene-AI/pull/10#discussion_r3978266924 |
| Security PR (#11, gate blocked post) | https://github.com/the-niresh/YeahScene-AI/pull/11 |
| Human feedback reply | https://github.com/the-niresh/YeahScene-AI/pull/10#discussion_r3978320561 |
| Earlier live loop (PR #8) | https://github.com/the-niresh/YeahScene-AI/pull/8 |
| Public install proof (PR #9) | https://github.com/the-niresh/YeahScene-AI/pull/9 |
| Stranger UAT PR | https://github.com/yeahscenevisionary/social-media-vault/pull/1 |
| Live scorecard | https://reviewer.niresh.tech/scorecard |
| GitHub Release v0.1.0 | https://github.com/the-niresh/plug-and-play-reviewer/releases/tag/v0.1.0 |

## Exact known limits

- Holdout baseline is **7 cases, all TypeScript from the Zod repo**. It is not a broad
  multi-language benchmark.
- `v0.1.0` is a **proof release**, not a marketed public launch (see frontend launch QA).
- Security findings are **held from public GitHub post** by the human gate (demo PR #11).
- Suggested fix blocks can be **malformed** on GitHub (duplicate return line). Known from
  stranger UAT and three-real-pr demo.
- Hosted dashboard lists review jobs with Open PR links even when hosted `review_findings`
  is empty for runner-only reviews (findings stay on the runner; public text on GitHub).
- Retrieval, code graph, specialists, and LangGraph are **off** on the public scorecard.
- Human reply feedback is **captured**, not applied as automatic self-improvement.
- Free tier: **one GitHub user, one repository** per installation.
- Signed-in production dashboard was not re-screenshot on this VPS without a live session
  cookie; API shape for `pull_request_url` is verified.

## What we do not claim

- We do not claim production-scale multi-tenant SaaS readiness.
- We do not claim measured quality beyond the published 7-case Zod holdout.
- We do not claim CodeRabbit, Qodo, or other tool parity without same-PR comparisons.
- We do not claim every stranger path works with zero owner involvement (pairing approval,
  model key, and runner uptime still matter).
- We do not claim Open Graph card validation on third-party preview tools (not run here).
- We do not claim GitHub repo topics are set (owner action still open).

## Owner actions left

| Priority | Action | Why |
|---|---|---|
| **Required** | `git push origin main` through `410dc4b` | Public GitHub must match local proofs (demo report, PR links, sitemap fix) |
| Recommended | Set GitHub repo topics per [REPO_TOPICS.md](../REPO_TOPICS.md) | Findability |
| Recommended | Fix suggested-fix placement (next product goal) | Bot comments can show malformed suggestions |
| Optional | Run og card validator on `/opengraph-image` | Third-party social preview check |
| Optional | Product Hunt / announcement when owner chooses | Not part of this proof release |

## Verification commands (2026-09-10)

```sh
# Production smoke
for r in / /connect /dashboard /scorecard /sitemap.xml /robots.txt /opengraph-image; do
  curl -sS -o /dev/null -w "$r:%{http_code}\n" "https://reviewer.niresh.tech$r"
done

# Install script
curl -sS -o /dev/null -w "%{http_code}\n" \
  https://raw.githubusercontent.com/the-niresh/plug-and-play-reviewer/main/scripts/install-reviewer.sh

# Release assets
gh release view v0.1.0 --repo the-niresh/plug-and-play-reviewer --json assets

# Git sync
git fetch origin && git log origin/main..HEAD --oneline
```
