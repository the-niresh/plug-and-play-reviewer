# CLAUDE.md - pr-reviewer

Index only. Source of truth for each area is the linked doc - read that instead of
re-exploring the tree. This file exists so a new session doesn't have to re-derive it.

**Stack:** Python 3.12, `uv` (never `pip`/`poetry` directly), Postgres (Neon hosted +
local), Textual (TUI), FastAPI-shaped control plane. Package manager commands below.

```bash
uv sync
docker compose up -d postgres
uv run ruff check .
uv run mypy src
flock -w 3600 /tmp/pr-reviewer-pytest.lock uv run pytest -q   # 747+ tests, always via flock - see protocols/waiting-on-work.md
```

## What this is

Two processes, one trust boundary (`docs/ARCHITECTURE.md` §1):
- **Hosted control plane** (`control_plane/`, `web/`) - owns GitHub App secrets, gets
  webhooks, stores job metadata in Neon. Never sees source, a diff, or a model key.
  It does store finding title and rationale on `review_findings`.
- **Local runner** (`runner/`) - owns model keys, fetches PR data with short-lived
  installation tokens, runs the review, posts only after a human approves.

Full map, file:line citations, settled vs. open decisions: `docs/ARCHITECTURE.md`.
Agent-facing CLI/MCP/A2A/ACP contract (exit codes, JSON shapes, error codes):
`docs/AGENT_CONTRACT.md`.

## The review pipeline (hot path, most sessions touch this)

1. Webhook in -> `github/lifecycle.py:handle_pull_request_event` -> enqueue/cancel/ignore.
2. `jobs/enqueue_review_job.py` inserts a Postgres row; `jobs/claim_review_job.py` claims
   with `FOR UPDATE SKIP LOCKED` (no Redis - see README "Why Redis is off").
3. Runner daemon (`runner/daemon.py:_run_claimed_job`) claims the job and calls the
   review protocol.
4. `reviewer/review_pull_request.py` - one model call against the packed diff, parses/
   validates findings (`contracts/finding_candidate.py`), drops ungrounded or duplicate
   ones.
5. `reviewer/reflect.py` - second model call scores each finding 0-1, drops anything at
   or below `REFLECTION_DROP_THRESHOLD`. Fails closed: raises `ModelSchemaMismatch` if
   the response doesn't score every input finding exactly once.
6. `notifications/gate.py:route_finding` - system-owned human gate. The model cannot set
   verification, public-safety, status, or posting fields. `allow_public_post` stays
   false until a human approves.
7. `github/post_review.py` posts, gated on the head SHA still matching (stale reviews
   don't post).

## Rules that actually bite

1. **The human gate is not negotiable.** No code path lets a model set `verified`,
   `allow_public_post`, or routing. If a change looks like it needs the model to touch
   those fields, the design is wrong - see `docs/ARCHITECTURE.md` §5.
2. **Hosted schema cannot hold source, diffs, or model keys.** `control_plane/boundary.py:assert_no_private_columns`
   enforces this against the live schema; `HOSTED_EXEMPTIONS` is empty. Finding title and
   rationale are allowlisted hosted text. Adding a hosted column that could carry
   source/diff/keys will fail `tests/test_hosted_boundary_enforcement.py`.
3. **Prompts are insert-only.** `PromptRegistry.register` raises on an existing
   name+version (`tests/test_prompt_registry.py`). Bump the version, don't edit content
   in place.
4. **Specialist mode and LangGraph are deliberately off**, not unfinished -
   `tests/test_specialists.py` and `tests/test_langgraph_engine.py` assert this. Don't
   "clean up" `workflow/langgraph_engine.py` as dead code without checking those tests
   first.
5. **No baseline claims without the holdout.** `run_diff_only_baseline` raises
   `BaselineBlocked` on the public dataset by design - precision/recall/cost numbers are
   not measured yet (README "What is not measured").

## Repo root scratch files

`CLAUDE-IN.md`, `CODEX-OUT.md`, `CURSOR-OUT.md`, `SONNET-OUT.md`, `BLOCKED.md` are
multi-agent handoff transcripts, not documentation - don't treat them as source of
truth, don't read them into context unless specifically continuing that handoff.
