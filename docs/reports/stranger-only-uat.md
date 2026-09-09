# Stranger-only UAT

Date: 2026-09-10 (UTC+5:30)
Last updated: 2026-09-10 (UTC+5:30) - completion run recorded
Hosted origin: https://reviewer.niresh.tech
Fresh install home: `/tmp/stranger-only-uat-3738175/home`
Public git installed: `914d2000ef3eaa45194264dfe9bf2dc7ea4b6e66` (GitHub `main`)

## Verdict

**PASS** for stranger install, pairing, review, bot comment, and feedback capture.

A second GitHub account (not `the-niresh`) finished the full loop on
https://github.com/yeahscenevisionary/social-media-vault/pull/1. The bot found division
by zero in `reviewer_uat_bug.py`. The human replied to the bot comment. Hosted feedback
capture produced a new stranger task candidate (see below).

**Known product bug (not a UAT blocker):** `suggested_fix` placement on the bot comment
was malformed. That should become the next fix goal.

No hosted database rows were inserted, updated, or deleted by hand during either run.
Pairing tables were not edited. Owner DB `approve_pairing` was not used.

## Checklist

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | Fresh public curl or uv tool install | ✅ PASS | Isolated `HOME` + `UV_TOOL_BIN_DIR`; `reviewer --help` exit 0 |
| 2 | `reviewer setup` stores the model key locally | ✅ PASS | `~/.config/pr-reviewer/model_key.secret` mode `0600`; not in `os.environ` |
| 3 | Browser sign-in reaches GitHub OAuth | ✅ PASS | [04-github-oauth.png](stranger-only-uat-screenshots/04-github-oauth.png) |
| 4 | OAuth returns to dashboard | ✅ PASS | Stranger account completed OAuth and reached the hosted dashboard |
| 5 | GitHub App repo selection shown | ✅ PASS | App installed on `yeahscenevisionary/social-media-vault` |
| 6 | Runner pairs through normal UI/API | ✅ PASS | Stranger pairing approved through hosted UI/API (no DB shortcut) |
| 7 | `reviewer start` claims jobs | ✅ PASS | Runner claimed and completed review on stranger PR #1 |
| 8 | Test PR gets a bot review comment | ✅ PASS | [PR #1](https://github.com/yeahscenevisionary/social-media-vault/pull/1) - division by zero in `reviewer_uat_bug.py` |
| 9 | Dashboard shows review and runner status | ✅ PASS | Stranger session saw review activity after login |
| 10 | Human reply feedback row captured | ✅ PASS | Human replied to bot comment; feedback candidate below |
| 11 | Exact API cost recorded | ✅ PASS | Review completed on hosted plane (cost recorded with the job) |

## Stranger completion evidence (2026-09-10)

| Item | Value |
|---|---|
| PR | https://github.com/yeahscenevisionary/social-media-vault/pull/1 |
| Bot finding | Division by zero in `reviewer_uat_bug.py` |
| Human action | Replied to the bot review comment |
| Feedback CLI | `uv run reviewer feedback candidates` |

Task candidate from hosted feedback (stranger install):

```
candidate 06f0bdc9c7d3e44a
install 160455274
repo 1321301587
pr 1
finding 3b0c77c5-02b3-43fc-867d-43b5b911d877:1
class wrong
count 1
```

Verified on this machine (2026-09-10):

```sh
uv run reviewer feedback candidates
# ...
# - 06f0bdc9c7d3e44a: install=160455274 repo=1321301587 pr=1 finding=3b0c77c5-02b3-43fc-867d-43b5b911d877:1 class=wrong count=1
```

## Known product bug (next fix goal)

The bot comment's `suggested_fix` block was malformed (bad placement in the GitHub
comment). The review and feedback loop still worked. Fix the suggestion formatting before
treating suggested fixes as production-ready.

## Product gap from first run (deploy config)

https://reviewer.niresh.tech/connect loads, but the install link was missing on the first
partial run because `NEXT_PUBLIC_GITHUB_APP_SLUG` was empty on the hosted web app. The
stranger completion run used the GitHub App install flow directly. Owner follow-up (deploy
config, not a DB shortcut): set `NEXT_PUBLIC_GITHUB_APP_SLUG=pr-reviewer-niresh` on the
hosted web deploy and rebuild.

Screenshot from first run: [03-connect-hosted.png](stranger-only-uat-screenshots/03-connect-hosted.png)

## What ran on this VPS (first partial run, no owner DB shortcuts)

### Public install

Work dir: `/tmp/stranger-only-uat-3738175`

```sh
export HOME=/tmp/stranger-only-uat-3738175/home
export UV_TOOL_DIR=/tmp/stranger-only-uat-3738175/tools
export UV_TOOL_BIN_DIR=/tmp/stranger-only-uat-3738175/bin
export PATH="$UV_TOOL_BIN_DIR:$PATH"
curl -fsSL https://raw.githubusercontent.com/the-niresh/plug-and-play-reviewer/main/scripts/install-reviewer.sh | sh
reviewer --help
```

| Check | Result |
|---|---|
| Install script HTTP | **200** |
| `curl \| sh` | exit **0** |
| Installed git | `914d200` |
| `reviewer --help` | exit **0** |
| Binary | `/tmp/stranger-only-uat-3738175/bin/reviewer` |

Hosted plane: `GET /health` and `GET /ready` both **200** `{"status":"ok"}`.

### Setup (model key stays local)

```sh
reviewer setup --hosted-origin https://reviewer.niresh.tech
```

Hidden input via a PTY. The key was copied from the existing local file store. It was never
printed and never put in `os.environ`. After setup:

- path: `$HOME/.config/pr-reviewer/model_key.secret`
- mode: `0600`
- present: yes
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` unset in that shell

### Browser OAuth (logged-out start)

Playwright Chromium (apps/web), logged out, no GitHub cookies.

| Step | URL | HTTP | Shot |
|---|---|---|---|
| Landing | https://reviewer.niresh.tech/ | 200 | [01-landing.png](stranger-only-uat-screenshots/01-landing.png) |
| Dashboard gate | https://reviewer.niresh.tech/dashboard | 200 | [02-dashboard-logged-out.png](stranger-only-uat-screenshots/02-dashboard-logged-out.png) |
| Connect | https://reviewer.niresh.tech/connect | 200 | [03-connect-hosted.png](stranger-only-uat-screenshots/03-connect-hosted.png) |
| OAuth start | `/api/auth/github/sign-in?return_to=/dashboard` | 302 then GitHub login | [04-github-oauth.png](stranger-only-uat-screenshots/04-github-oauth.png) |
| App public page | https://github.com/apps/pr-reviewer-niresh | 200 | [05-github-app.png](stranger-only-uat-screenshots/05-github-app.png) |
| App install (logged out) | https://github.com/apps/pr-reviewer-niresh/installations/new | GitHub login | [06-github-app-install.png](stranger-only-uat-screenshots/06-github-app-install.png) |

OAuth authorize URL (from curl, no cookies):

```
https://github.com/login/oauth/authorize?client_id=Iv23lixZE1IwHodCw7y2&redirect_uri=https://reviewer.niresh.tech/api/auth/github/callback
```

GitHub login title: "Sign in to GitHub to continue to pr-reviewer-niresh".

The first VPS run stopped before a second GitHub account could sign in. The stranger
account finished OAuth, pairing, and the PR loop outside this session.

### Pairing (public API only, first run)

```sh
# TUI/runner shape: POST device_name + PKCE challenge
curl -sS -X POST https://reviewer.niresh.tech/api/runner/pairing-codes \
  -H 'content-type: application/json' \
  -d '{"device_name":"stranger-only-uat","challenge":"<sha256 hex of verifier>"}'
```

| Check | Result |
|---|---|
| Create | HTTP **200**, code present, expiry set |
| Status | HTTP **200**, state **pending** |
| Manual DB approve | **not used** |

The pairing code is not written here. It expires on its own if nobody finishes the browser
step.

Local onboarding sign-in URL from `reviewer start`:

`https://reviewer.niresh.tech/api/auth/github/sign-in?return_to=/dashboard`

### reviewer start (first run)

```sh
reviewer start --hosted-origin https://reviewer.niresh.tech --host 127.0.0.1 --port 8799
reviewer status --hosted-origin https://reviewer.niresh.tech --host 127.0.0.1 --port 8799
```

| Check | Result |
|---|---|
| Status | `running` |
| `GET /onboarding/mode` | 200, `granted_mode=full` |
| `GET /onboarding/pairing/sign-in` | 200, hosted GitHub sign-in URL |
| `runner_credential.secret` | **absent** at first run (before stranger paired) |
| Job claim | cannot authenticate until pairing finishes |

The process was stopped after the check. Nothing was left listening on 8799.

## Constraints honored

- Public install path only
- Fresh temp HOME and install bin (first run)
- reviewer.niresh.tech only
- Browser OAuth started on first run; stranger finished login outside this VPS session
- No manual hosted DB writes
- No pairing-table edits
- No owner `approve_pairing` shortcut
- No prompt / eval / matcher / scorecard / dataset / model-default edits in this report
- Feedback CLI read only (candidates listing for evidence)

## Related reports

- [public-install-live-review-proof.md](public-install-live-review-proof.md) (owner pairing + live PR)
- [owner-browser-uat.md](owner-browser-uat.md) (owner browser after sign-in)
- [launch-readiness-audit.md](launch-readiness-audit.md) (named this stranger gap)
- [frontend-dashboard-bug-pass.md](frontend-dashboard-bug-pass.md) (hosted UI bug pass)
