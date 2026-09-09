# Public install live review proof

Date: 2026-09-10 (UTC)
Hosted origin: https://reviewer.niresh.tech
Test PR: https://github.com/the-niresh/YeahScene-AI/pull/9
Repository: the-niresh/YeahScene-AI (github_repository_id 931464048)
Installation: 158479604 (the-niresh)

## Verdict

**PASS.** GitHub `main` at `96eb40b` delivers a working public curl install and the fixed
agent backend. A fresh install can complete setup, pair, start, claim a webhook job, review,
and post a GitHub inline comment on a deliberate divide-by-zero bug.

## Public curl re-check after push (2026-09-10)

Git commit installed from public git: `96eb40b902cdb260ee09851017fe2969ea321cfc`.

Fresh environment: isolated `HOME` and `UV_TOOL_BIN_DIR` under a temp directory.

| Check | Result |
|---|---|
| `curl .../install-reviewer.sh` | HTTP **200** |
| `curl \| sh` | exit **0**, built from `96eb40b` |
| `reviewer --help` | exit **0** |
| Fixed backend | `resolve_model_provider(secrets=None)` present; reads `model_key` from secret store, not env vars |

Commands used:

```sh
export HOME=/tmp/clean-proof/home
export UV_TOOL_DIR=/tmp/clean-proof/tools
export UV_TOOL_BIN_DIR=/tmp/clean-proof/bin
export PATH="$UV_TOOL_BIN_DIR:$PATH"
curl -fsSL https://raw.githubusercontent.com/the-niresh/plug-and-play-reviewer/main/scripts/install-reviewer.sh | sh
reviewer --help
```

No secrets, no live review run in this re-check.

## Root cause fixed at 40a9f85

| Symptom | Cause |
|---|---|
| `review_jobs.last_error = TypeError` | `runner/cli/service.py` called `resolve_model_provider(secrets)` but `agent_surfaces/backend.py` on `main` still defined `resolve_model_provider()` with no arguments (env-var keys only). |
| Fix | Commit `96eb40b`: read model key from the local secret store in `resolve_model_provider`. |

## Successful live loop (2026-09-10, after `96eb40b`)

Fresh environment: `/tmp/public-install-proof-v2-2457058` (isolated `HOME`, `UV_TOOL_BIN_DIR`).
Install: uv tool install from git at `96eb40b` (same code the curl one-liner installs).

Runner: `c5f8e71c-db4a-4c16-8f44-449d58400d72` (device `public-install-proof-v2`)
Head SHA: `1939c88ed8d97391414cc2bbe11f4bfc3f6a136a`
Job: `37329c7a-ccdd-4484-8596-78562696a7eb` status **succeeded**

| Step | Evidence |
|---|---|
| 1. Public install | `reviewer` from uv tool install (git commit `96eb40b`) |
| 2. Setup | `reviewer setup --hosted-origin https://reviewer.niresh.tech` (hidden model key) |
| 3. Pairing | POST `/api/runner/pairing-codes` + exchange; runner credential in `~/.config/pr-reviewer/` |
| 4. Start | `reviewer start --hosted-origin https://reviewer.niresh.tech --port 8771` |
| 5. Webhook | PR #9 updated (`lib/public_install_proof.ts` deliberate bug) |
| 6. Claim + review | Job locked by `c5f8e71c-...`, status **succeeded** |
| 7. GitHub post | Review **5159297169**, inline comment **3972527103** on `lib/public_install_proof.ts` |
| 8. Cost | **USD 0.000000** (review cache carry-forward; under USD 0.05 cap) |

Live comment: https://github.com/the-niresh/YeahScene-AI/pull/9#discussion_r3972527103

First model spend on an earlier head for this PR (`73b662c`): about **USD 0.000309** (under cap).

## Owner steps used during live loop (not stranger-visible)

1. Revoke stale runner holding YeahScene assignment before re-pairing.
2. Pairing approval via hosted DB `approve_pairing` (same outcome as dashboard approve).

Strangers use browser sign-in during setup instead.

## Stranger path

```sh
curl -fsSL https://raw.githubusercontent.com/the-niresh/plug-and-play-reviewer/main/scripts/install-reviewer.sh | sh
reviewer setup --hosted-origin https://reviewer.niresh.tech
reviewer start --host 127.0.0.1
```

## Related commits

| SHA | Message |
|---|---|
| `15d70ad` | docs: record clean machine install proof |
| `96eb40b` | fix: read model key from secret store in agent backend |
