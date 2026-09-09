# Live GitHub loop proof

Date: 2026-09-09 (UTC)
Hosted origin: https://reviewer.niresh.tech
Test PR: https://github.com/the-niresh/YeahScene-AI/pull/8
Repository: the-niresh/YeahScene-AI (github_repository_id 931464048)
Installation: 158479604 (the-niresh)

## Verdict

**Partial proof.** Webhook, enqueue, runner claim, and local review completed under budget.
GitHub review posting and human reply feedback capture are **blocked** on an owner GitHub App
installation step. Three code bugs that prevented a fair live run were fixed in this repo.

## GitHub App preflight

| Check | Expected | Observed |
|---|---|---|
| Homepage | https://reviewer.niresh.tech | https://reviewer.niresh.tech |
| OAuth callback | https://reviewer.niresh.tech/api/auth/github/callback | Live sign-in redirect_uri matches |
| Webhook URL | https://reviewer.niresh.tech/api/github/webhook | Matches app hook config |
| Webhook secret | Matches hosted GITHUB_WEBHOOK_SECRET | Deliveries accepted (202/200) |
| Permissions (app manifest) | metadata read, contents read, pull_requests write | App manifest has write |
| Events (app manifest) | pull_request, pull_request_review_comment | App lists both |
| Installation permissions | pull_requests write effective | **read only on installation** |
| Installation events | both PR events | **pull_request only on installation** |

## Loop evidence

### 1. Webhook delivery observed

- `f66878c0-ac7c-11f1-8a79-5b14025a9599` pull_request opened (2026-09-09T18:33:35Z)
- `7d72c8c0-ac7d-11f1-9de8-ec146846efc5` pull_request synchronize (2026-09-09T18:37:24Z)

Both rows in `github_deliveries`.

### 2. Review job enqueued

- First job `3e064158-685c-4718-ae9d-39985805c784` was wrongly marked succeeded in ~2s (see bugs).
- Second job `02f88384-c5d5-41be-8c1d-b24b8767bd05` for head `26f3a80434007d423ee93fdc4a3d8cbeaf5cdda9`.

### 3. Runner claimed the job

Job `02f88384-c5d5-41be-8c1d-b24b8767bd05` locked_by runner `1f901404-5c8c-4614-a9a8-263908698e1d`.

### 4. Review completed (local runner)

Finding cached locally:

- Title: Division by zero potential
- File: lib/live_loop_proof.ts line 9
- Concern: correctness, severity high

### 5. Human gate path

Daemon routing (`runner/cli/service.py:_findings_with_route_decisions`) set `allow_public_post=True`
and `verified=True` for this correctness finding (non-security). Post was attempted; gate did not
block. Security findings would remain `allow_public_post=False`.

### 6. GitHub review comment posted

**Not achieved.** Post failed with `HTTPStatusError` (GitHub 403: Resource not accessible by
integration). Root cause: installation grants only `pull_requests: read`. Minting a write token
returns HTTP 422 from GitHub.

### 7. Human reply feedback capture

**Not achieved.** Depends on a posted review comment and `pull_request_review_comment` webhook.

### 8. Exact API cost

From `review_cache_heads` for this PR head:

- **USD 0.00030869999999999997** (~0.031 cents), well under the $0.05 budget.

Model: gpt-4o-mini via OpenAI key (repo_config for repository 931464048).

## Bugs found and fixed (this session)

1. **Hosted worker stole runner jobs.** `claim_review_job` claimed full PR jobs and the worker stub
   marked them succeeded without running a review. Fixed: worker only claims jobs missing PR identity.
2. **Runner used Anthropic hard-coded with an OpenAI key.** Fixed: `resolve_model_provider` +
   per-repo `repo_config` model choice (gpt-4o-mini).
3. **Post step reused read-only job token.** Fixed: new `/api/runner/jobs/{id}/post-token` mints
   `pull_requests: write` for `submit_review_to_github` only.

## Owner steps to finish the loop

1. Open https://github.com/settings/installations/158479604
2. Approve the pending permission upgrade so the installation grants **Pull requests: Read and write**
   (GitHub API currently returns 422 when requesting write).
3. Confirm the installation subscribes to **Pull request review comments** (app manifest already does;
   installation events currently list only `pull_request`).
4. Redeploy hosted api/worker images with this commit (worker claim fix + post-token route).
5. Re-run: push an empty commit on PR #8 (or open a fresh PR), ensure local `reviewer start` is
   running, approve/post if needed, reply to the bot comment, confirm `review_comment_feedback`.

## Re-run checklist

```bash
docker stop pr-reviewer-worker-1   # until redeployed with worker fix
cd plug-and-play-reviewer && set -a && source .env && set +a
uv run reviewer start --host 127.0.0.1 --port 8765
# push to PR branch, watch review_jobs and GitHub PR reviews
```
