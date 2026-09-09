# Live GitHub loop proof

Date: 2026-09-09 / 2026-09-10 (UTC)
Hosted origin: https://reviewer.niresh.tech
Test PR: https://github.com/the-niresh/YeahScene-AI/pull/8
Repository: the-niresh/YeahScene-AI (github_repository_id 931464048)
Installation: 158479604 (the-niresh)

## Verdict

**Live GitHub smoke-test: PASS.** Full loop verified on the live hosted plane:

PR webhook -> job enqueue -> runner claim -> review -> human gate -> GitHub review comment ->
human reply -> `review_comment_feedback` row.

Budget for the first model call on this PR: **USD 0.000309** (well under the USD 0.05 cap).
Successful re-run heads used the local review cache (USD 0 incremental).

Commit with code fixes: `a20c026` (`fix: unblock live runner claim post and review model`).

## GitHub App preflight

| Check | Expected | Observed |
|---|---|---|
| Homepage | https://reviewer.niresh.tech | https://reviewer.niresh.tech |
| OAuth callback | https://reviewer.niresh.tech/api/auth/github/callback | Live sign-in redirect_uri matches |
| Webhook URL | https://reviewer.niresh.tech/api/github/webhook | Deliveries accepted |
| Permissions (installation) | pull_requests write | **write** (after owner approval) |
| Events (installation) | pull_request, pull_request_review_comment | **both subscribed** |
| Runner credential | claim succeeds on hosted | 200, not 401 |

## Successful loop run (2026-09-09T19:10Z)

Head SHA: `ca5bea07fb590d54f204de09cafb2891c0aa687b`
Job: `ad096d75-679d-4916-9e24-14dc0b1e9541`
Runner: `1f901404-5c8c-4614-a9a8-263908698e1d`

| Step | Evidence |
|---|---|
| 1. Webhook | `github_deliveries` `114eaa10-ac82-11f1-90bc-3afaab9480bb` event `pull_request` |
| 2. Enqueue | `review_jobs` row `ad096d75-679d-4916-9e24-14dc0b1e9541` status **succeeded** |
| 3. Runner claim | `locked_by` runner `1f901404-5c8c-4614-a9a8-263908698e1d` |
| 4. Review | Finding: Division by zero potential on `lib/live_loop_proof.ts` (cache carry-forward) |
| 5. Human gate | Non-security finding routed with `allow_public_post=True` |
| 6. GitHub post | Review id **5158722711**, inline comment **3972082930** by `pr-reviewer-niresh[bot]` |
| 7. Reply feedback | Human reply comment **3972088937**; webhook `3a534e20-ac82-11f1-9e72-44e72ea18866`; `review_comment_feedback` classification **wrong** for finding `ad096d75-679d-4916-9e24-14dc0b1e9541:1` |
| 8. Cost | First review head `26f3a804...`: USD **0.000309**; pass head used cache (USD 0) |

Live PR: https://github.com/the-niresh/YeahScene-AI/pull/8#discussion_r3972082937

## Bugs found and fixed (before pass)

1. **Hosted worker stole runner jobs.** Worker now claims only jobs missing PR identity.
2. **Runner hard-coded Anthropic with an OpenAI key.** Uses `resolve_model_provider` + repo_config.
3. **Post reused read-only job token.** Added `/api/runner/jobs/{id}/post-token` with `pull_requests: write`.

## Operational notes from re-run

- Stale long-lived `reviewer start` process did not call `post-token`; restarting the runner was required after deploy.
- Installation `pull_requests: write` had to be approved at https://github.com/settings/installations/158479604 before post-token mint returned 201.

## Earlier partial attempts (same PR)

| Head | Job | Result |
|---|---|---|
| `26f3a804...` | `02f88384-...` | Review OK; post failed (installation read-only) |
| `a2c20a2...` | `bc0e5c2b-...` | Review OK (cache); post failed (read-only + stale runner) |
| `9600f12...` | `55f5b17c-...` | Failed `HTTPStatusError` (stale runner, no post-token) |

## Re-run checklist

```bash
cd plug-and-play-reviewer && set -a && source .env && set +a
uv run reviewer start --host 127.0.0.1 --port 8765
# push to PR branch; confirm review_jobs succeeded and GitHub review appears
# reply to bot inline comment; confirm review_comment_feedback row
```
