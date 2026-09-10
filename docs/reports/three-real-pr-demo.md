# Three real PR demo

Date: 2026-09-10 (UTC)
Hosted origin: https://reviewer.niresh.tech
Repository: the-niresh/YeahScene-AI (github_repository_id 931464048)
Installation: 158479604 (the-niresh)
Runner: c5f8e71c-db4a-4c16-8f44-449d58400d72 (device `public-install-proof-v2`)

## Verdict

**PASS.** Three production pull requests ran on the live hosted plane with the real GitHub App
and the paired runner. Case 1 posted a bot comment with a suggested fix. Case 2 found security
findings but the human gate blocked public posting (no GitHub review). Case 3 captured human
reply feedback and surfaced a new task candidate in `reviewer feedback candidates`.

Total model spend on the two fresh review heads: **USD 0.00074895** (under the USD 0.05 cap).

## Demo cases

### 1. Simple correctness bug

| Item | Value |
|---|---|
| PR | https://github.com/the-niresh/YeahScene-AI/pull/10 |
| Branch | `demo-correctness-divzero` |
| Bug | `averagePositive` divides by `count` with no guard when every value is non-positive |
| Job id | `c334b788-f5d1-4fb8-9bdc-2cd6de191a17` |
| Head SHA | `701889476133f5350f4e32596392681e915b9054` |
| Finding | Potential divide by zero (`concern=correctness`, `severity=high`) |
| Bot review id | 5166131805 |
| Bot comment | https://github.com/the-niresh/YeahScene-AI/pull/10#discussion_r3978266924 |
| Suggested fix | **Posted** in the GitHub suggestion block (`return count > 0 ? sum / count : 0;`) |
| Model cost (this head) | USD **0.00031245** (local `review_cache_heads`; fresh call, not a zero-cost replay) |
| Dashboard Open PR | https://github.com/the-niresh/YeahScene-AI/pull/10 (via `/api/reviews` `pull_request_url`) |

### 2. Security-looking bug

| Item | Value |
|---|---|
| PR | https://github.com/the-niresh/YeahScene-AI/pull/11 |
| Branch | `demo-security-token-check` |
| Bug | Hardcoded demo token plus loose `==` authorization check in `lib/demo_security.ts` |
| Job id | `e64e4772-b2ed-4fc8-b1c7-44eb17efa1ac` |
| Head SHA | `7b12f7f79a8a7cccf1cdc350be8fb8e060fb54a5` |
| Findings (local cache) | `Hardcoded token in source code` and `Insecure token comparison` (`concern=security`, `severity=high`) |
| GitHub bot review | **None** (human gate blocked public post for security findings) |
| Suggested fix | **Not posted** (no public GitHub review comment) |
| Model cost (this head) | USD **0.00043650** (local `review_cache_heads`; fresh call) |
| Dashboard Open PR | https://github.com/the-niresh/YeahScene-AI/pull/11 (via `/api/reviews` `pull_request_url`) |

### 3. Feedback loop (on case 1)

| Item | Value |
|---|---|
| Human reply | https://github.com/the-niresh/YeahScene-AI/pull/10#discussion_r3978320561 |
| Reply text | "This is wrong: the function should throw when count is zero, not return zero." |
| Hosted feedback row | `4caa8f1c-ec37-4ecd-9365-fc5c7c695753` |
| Classification | **wrong** |
| Finding id | `c334b788-f5d1-4fb8-9bdc-2cd6de191a17:1` |
| Feedback CLI | `uv run reviewer feedback candidates` |

Task candidate output:

```
753e6c6d3d6f3e23: install=158479604 repo=931464048 pr=10 finding=c334b788-f5d1-4fb8-9bdc-2cd6de191a17:1 class=wrong count=1
```

## Cost summary

| Head | PR | cost_usd |
|---|---|---|
| `701889476133f5350f4e32596392681e915b9054` | 10 | 0.00031245 |
| `7b12f7f79a8a7cccf1cdc350be8fb8e060fb54a5` | 11 | 0.00043650 |
| **Total** | | **0.00074895** |

Both heads ran new model calls on new files. Neither was a zero-cost cache replay.

## Hosted storage check

| Check | Result |
|---|---|
| `review_findings` for demo jobs | 0 rows (findings stayed on the runner; public text only on GitHub for PR 10) |
| `model_calls` on hosted for demo jobs | 0 rows |
| `review_comment_feedback.reply_text` | Wrapped untrusted input only; no source, diff, or model key |
| Boundary tests | `tests/test_hosted_boundary_enforcement.py` pass |

## Commands used

```sh
# Runner already paired as public-install-proof-v2 on port 8771
gh pr create ...  # PR 10 and PR 11
gh api .../comments/3978266924/replies  # human reply on PR 10
uv run reviewer feedback candidates
curl https://reviewer.niresh.tech/health
```

## Known product notes (not demo blockers)

- PR 10 suggestion block adds a duplicate return line instead of replacing the division line.
  That matches the existing suggested-fix placement bug noted in stranger UAT.
- Hosted dashboard lists both review jobs with Open PR links even when hosted `review_findings`
  is empty for runner-only reviews.
