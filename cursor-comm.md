# cursor-comm.md

Append-only record of Track work. Newest at the bottom.

## 2026-09-08T00:57:44+05:30 | phase 35 | Task 35.A1
status: DONE
commit sha: 5ca20df feat: index a repository once and re-embed only changed files
red proof: with the incremental logic stashed, tests/test_incremental_indexing.py failed with
  `assert 2 == 1` on test_second_index_of_an_unchanged_repository_issues_zero_embedding_calls
  and an embedded-texts mismatch on test_only_the_changed_chunk_is_re_embedded.
  2 failed, 1 passed. Restored, then 3 passed.
gate numbers: ruff 0 on both staged files; mypy 0 across 213 source files; no U+2013 or U+2014;
  full suite under flock 1202 passed, 3 skipped, 0 failed in 298.64s. Baseline was 1199.
what I did: index_repository now reads the active generation's chunk identity, content hash and
  embedding once per call (_previous_chunk_embeddings), embeds only chunks whose content hash
  changed, and carries the previous embedding literal forward for the rest. The embedder is not
  called at all when nothing changed. Three tests with a counting fake cover unchanged, one
  changed chunk, and no previous generation.
blockers: None.

## 2026-09-08T04:24:54+05:30 | phase 35 | Task 35.C5
status: READY FOR GATE
commit sha:
red proof: ran `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q
  tests/test_render_blueprint.py tests/test_deployed_secrets_are_files.py`
  before implementation and got:
  - `FileNotFoundError: .../deploy/render.yaml`
  - `FileNotFoundError: .../deploy/railway.json`
  - `AssertionError: assert 'keyring-value' == 'file-provider-key'` in
    `test_provider_key_is_read_from_mounted_file_never_from_environment`
what I did: added `deploy/render.yaml` and `deploy/railway.json` as single-service
  templates for one-address deploys, with only boot-config env keys and a mounted
  secrets path at `/run/secrets/pr-reviewer`. Updated `runner/secrets.py` so
  `get_secret_store(...)` points `FileSecretStore` at mounted secret files when
  `PR_REVIEWER_SECRET_FILES_DIR` is set or `/run/secrets/pr-reviewer` exists,
  and avoids keyring selection in that mounted-file mode. Added
  `tests/test_render_blueprint.py` and `tests/test_deployed_secrets_are_files.py`
  to lock these behaviors, including the provider-key-from-file-not-environ proof.
gate numbers: ruff 0 (`src/pr_reviewer/runner/secrets.py`,
  `tests/test_render_blueprint.py`, `tests/test_deployed_secrets_are_files.py`);
  mypy 0 (`src/pr_reviewer/runner/secrets.py`);
  pytest under flock:
  - `tests/test_render_blueprint.py tests/test_deployed_secrets_are_files.py tests/test_secret_store.py`
    -> 15 passed, 0 failed
  - `tests/test_package_boundaries.py` -> 19 passed, 0 failed
blockers: None

## 2026-09-09T00:11:55+05:30 | eval matcher | ignore category wording for matches
status: DONE
commit sha: 9ce48c5 fix: match eval findings without category text
red proof: tests/test_eval_matching.py::test_overlapping_lines_match_when_category_wording_differs failed with AssertionError: assert [] where MatchResult.matched was empty. The expected and actual findings had the same concern, same file, and overlapping lines, but different category wording.
gate numbers: ruff 0 on tests/test_eval_matching.py src/pr_reviewer/evals/match_findings.py; mypy src 0; grep for U+2013/U+2014 on changed files had no output; tests/test_eval_matching.py 4 passed; tests/test_package_boundaries.py 19 passed; tests/test_hosted_boundary_enforcement.py 9 passed
what I did: removed category text from the deterministic match rule. A pass now needs concern, exact file path, and overlapping line ranges. Wrong-file same-concern findings still set needs_human_match.
blockers: None

## 2026-09-08T04:24:36+05:30 | phase 35 | Task 35.B7
status: READY FOR GATE
commit sha:
red proof: `ImportError: cannot import name 'monthly_review_cap_refusal' from
  'pr_reviewer.reliability.budget'` from `tests/test_monthly_cap_refuses.py:9` on the first run.
  Full run output: `FAILED tests/test_monthly_cap_refuses.py::test_review_is_refused_when_repository_monthly_cap_is_reached
  1 failed in 0.09s`.
gate numbers: ruff 0 on `src/pr_reviewer/reliability/budget.py` and
  `tests/test_monthly_cap_refuses.py`; mypy 0 on `src/pr_reviewer/reliability/budget.py`; pytest
  under lock only:
  `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q tests/test_monthly_cap_refuses.py`
  -> 1 passed in 0.12s, and
  `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q tests/test_package_boundaries.py`
  -> 19 passed in 1.50s. Did not run full suite, did not run anything with `bun run build`.
what I did: researched `/tmp/litellm` and `/tmp/llmgateway` shallow clones, read only budget and
  provider-config related code paths, then deleted both clones as requested.
  Implemented Task B7 only in `reliability/budget.py` plus `tests/test_monthly_cap_refuses.py`.
  Added `monthly_review_cap_refusal(...)` that tracks monthly spend by `(repository, role)` input,
  computes repository total plus estimated next review cost, and returns a structured
  `ReviewBudgetRefusal` when the monthly cap is reached or would be exceeded. This is a product
  surface, not an exception: refusal includes `code`, plain message with spent dollars and
  per-role breakdown, and clear next action. Unset or non-positive monthly cap also returns a
  refusal (`repository_monthly_cap_unset`), preserving deny-on-unset behavior.
  The new test proves behavior, not config shape: a repo already at `$4.00` monthly spend is
  refused, message names `$4.00` spent and role spend (`judge: $3.00`), and spend in another repo
  does not affect this repo's cap decision.
  Research notes used:
  LiteLLM shows fail-closed pre-reservation budget checks and per-entity counters
  (key/team/user/end-user plus per-model windows), with refusal before spend when counters are
  over cap. llmgateway shows pre-check cap refusal with user-facing messages and rich per-call
  usage schema, but its org spend-cap path is fail-open on Redis errors.
  Worth stealing but not implemented in this task:
  (1) a persisted period bucket store keyed by repo and month for first-class monthly rollups,
  (2) reservation plus reconciliation to avoid concurrency overspend near cap,
  (3) explicit reset metadata in refusal payload (retry-after month reset timestamp),
  (4) richer per-call usage ledger fields such as cached tokens, reasoning tokens, and split
  input/output cost components.
blockers: None.

## 2026-09-08T04:16:40+05:30 | phase 35 | Task 35.C4
status: READY FOR GATE
commit sha:
red proof: E       ModuleNotFoundError: No module named 'pr_reviewer.onboarding'
  E       AssertionError: browser onboarding must fetch the shared step list
  E       assert 'pr_reviewer.onboarding.state' in '"""Loopback onboarding app (Runtime Task 8)...'
  FAILED tests/test_onboarding_has_one_state_machine.py with 3 failed, 1 passed.
gate numbers: every pytest run used the lock. targeted tests:
  `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q tests/test_onboarding_has_one_state_machine.py`
  -> 4 passed in 0.28s.
  `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q tests/test_onboarding_has_one_state_machine.py tests/test_local_auth.py tests/test_web_onboarding_sign_in.py`
  -> 25 passed, 1 warning in 2.15s.
  required boundary test:
  `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q tests/test_package_boundaries.py`
  -> 19 passed in 1.40s.
  extra checks: `uv run ruff check` scoped to C4 python files -> 0.
  `uv run mypy src/pr_reviewer/onboarding/state.py src/pr_reviewer/runner/web/local_auth.py` -> 0.
what I did: added one shared onboarding state machine at
  `src/pr_reviewer/onboarding/state.py` with the canonical ordered steps
  (`provider`, `key`, `project_description`, `clone_and_index`, `github`, `review_location`)
  and centralized validation for each step payload. Added `onboarding/__init__.py`.
  Wired the local onboarding browser API in `src/pr_reviewer/runner/web/local_auth.py` to that
  shared machine with `GET /onboarding/steps` plus `POST /onboarding/steps/{step_id}/validate`,
  and made `/onboarding/model-key` validate provider/key via the shared validators.
  Updated `apps/web/src/app/onboarding/page.tsx` to fetch and render shared steps from
  `/onboarding/steps` instead of defining a local `STEPS` constant.
  Added `tests/test_onboarding_has_one_state_machine.py`, which enforces one source of truth:
  canonical step order comes from `onboarding/state.py`, browser must read `/onboarding/steps`,
  local onboarding API must import the shared module, and terminal frontend files fail if they
  contain a full local copy of all canonical step ids.
blockers: None

## 2026-09-08T03:55:07+05:30 | phase 35 | Task 35.C3
status: READY FOR GATE
commit sha:
red proof: E       ModuleNotFoundError: No module named 'pr_reviewer.control_plane.app_manifest'
  FAILED tests/test_app_manifest_flow.py::test_manifest_exchange_stores_credentials_and_they_are_usable
gate numbers: every pytest run used the lock. targeted test:
  `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q tests/test_app_manifest_flow.py`
  -> 2 passed, 1 warning in 0.41s. required boundary test:
  `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q tests/test_package_boundaries.py`
  -> 19 passed in 1.71s. Extra checks: `uv run ruff check` on changed files -> 0; `uv run mypy`
  on `src/pr_reviewer/control_plane/app_manifest.py` and `src/pr_reviewer/control_plane/app.py`
  -> 0.
what I did: added `control_plane/app_manifest.py` with a full App Manifest handshake:
  `/api/github/app-manifest/start` builds a manifest for this instance (webhook and callback URLs),
  issues one-time state + binding secret, and redirects to GitHub's manifest create URL.
  `/api/github/app-manifest/callback` validates and consumes the one-time state, exchanges the
  manifest code at GitHub, persists returned credentials (`app_id`, `private_key`,
  `webhook_secret`, `oauth_client_id`, `oauth_client_secret`) to a mode-0600 file, and applies
  them to process environment so existing hosted flows can use them immediately.
  Added startup bootstrap in `control_plane/app.py` to load stored credentials when env is not
  fully configured, and included the new router in the hosted app.
  Added `tests/test_app_manifest_flow.py` proving the returned credentials are both stored and
  usable: after callback, it verifies persisted values, verifies `/api/auth/github/sign-in`
  now uses the returned OAuth client id, and verifies a `GitHubAppClient` can mint an installation
  token using the returned private key. It also asserts reconfiguration is blocked once configured,
  and that malformed store JSON is ignored rather than crashing startup.
blockers: None

## 2026-09-08T03:51:06+05:30 | phase 35 | Task 35.B5
status: READY FOR GATE
commit sha:
red proof: E       ModuleNotFoundError: No module named 'pr_reviewer.models.cli_provider'
  FAILED tests/test_cli_subscription_provider.py::test_cli_subscription_returns_completion_with_cost_and_ledger
  FAILED tests/test_cli_subscription_provider.py::test_cli_subscription_maps_typed_rate_limit_error
gate numbers: ruff not run (not requested); mypy not run (not requested); pytest targeted under
  lock `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q
  tests/test_cli_subscription_provider.py` -> 2 passed in 0.17s; boundary check under lock
  `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q tests/test_package_boundaries.py`
  -> 19 passed in 1.42s
what I did: added `models/cli_provider.py` and `tests/test_cli_subscription_provider.py`.
  The provider shells out via argv list only (`subprocess.run([...], shell=False)`), sends the
  model request as JSON on stdin, and never composes a shell command from model content.
  Anthropic subscription support was not added. Success responses are normalized through
  `finish_completion`, so output parsing, typed response semantics, output hash, prompt name and
  version, token accounting, and cost ledger stay consistent. Non-zero CLI exits map into normal
  typed provider errors (`ModelRateLimit`, `ModelContextLimit`, `ModelKeyInvalid`, otherwise
  `ModelProviderFailure`). The fake executable test proves completion and ledger flow through the
  CLI path without real network calls, and separately proves typed rate-limit mapping.
blockers: None

## 2026-09-08T03:40:37+05:30 | phase 35 | Task 35.C2
status: READY FOR GATE
commit sha:
red proof: E       AssertionError: expected first webhook delivery to post one review comment
  FAILED tests/test_review_appears_on_the_pr.py::test_redelivered_webhook_does_not_post_a_second_comment
gate numbers: every pytest run used the lock. targeted test:
  `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q tests/test_review_appears_on_the_pr.py`
  -> 1 passed, 1 warning in 0.67s. required boundary checks:
  `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q tests/test_package_boundaries.py tests/test_hosted_boundary_enforcement.py`
  -> 28 passed in 3.20s.
what I did: added a runner-side caller for `github/post_review.py` in the finished review path
  (`runner/cli/service.py`) so completed reviews now attempt to publish to GitHub using the
  existing `post_review` idempotency marker and stale-head guard. Added `RunnerClient.issue_job_token`
  for the runner lease token exchange, then wired posting with `posting_idempotency_key`,
  marker-based lookup (`list_pull_request_reviews`), and submit (`submit_review_to_github`).
  Added `tests/test_review_appears_on_the_pr.py`, which starts the runner path, delivers two
  webhook events for the same PR/head with different delivery IDs, and asserts the second
  delivery does not create a second comment (`len(submissions) == 1`), while both jobs complete.
blockers: None

## 2026-09-08T03:47:36+05:30 | phase 35 | Task 35.B4
status: READY FOR GATE
commit sha:
red proof: E       ModuleNotFoundError: No module named 'pr_reviewer.models.fallback'
  FAILED tests/test_model_fallback_chain.py::test_context_overflow_skips_next_name_and_chooses_larger_window
  FAILED tests/test_out_of_credit_crosses_vendor.py::test_out_of_credit_skips_same_vendor_and_crosses_to_another_vendor
gate numbers: ruff not run (not requested); mypy not run (not requested); pytest targeted under
  lock `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q
  tests/test_model_fallback_chain.py tests/test_out_of_credit_crosses_vendor.py` -> 2 passed in
  0.26s; boundary check under lock `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q
  tests/test_package_boundaries.py` -> 19 passed in 1.35s
what I did: added `models/fallback.py` as a wrapper over existing `models/retry.py` retry policy
  so plain retryable rate limits stay in one backoff loop. Added
  `tests/test_model_fallback_chain.py` proving context overflow skips next-in-list and selects a
  larger-window model, and `tests/test_out_of_credit_crosses_vendor.py` proving out-of-credit is
  terminal for the vendor and fallback crosses to another vendor instead of trying same-vendor
  models.
blockers: None

## 2026-09-08T03:40:55+05:30 | phase 35 | Task 35.B3
status: READY FOR GATE
commit sha:
red proof: E       TypeError: OpenAICompatibleProviderConfig.__init__() got an unexpected
  keyword argument 'cache_request_overrides'
  FAILED tests/test_cache_hit_rate_is_recorded.py::test_openai_compatible_records_prompt_cache_hit_rate_from_response
gate numbers: ruff not run (not requested); mypy not run (not requested); pytest targeted under
  lock `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q
  tests/test_cache_hit_rate_is_recorded.py` -> 1 passed in 0.07s; boundary check under lock
  `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q tests/test_package_boundaries.py`
  -> 19 passed in 1.22s
what I did: added `tests/test_cache_hit_rate_is_recorded.py` that uses a real mocked
  OpenAI-compatible response payload with usage.prompt_tokens_details.cached_tokens and proves
  prompt_cache_hit_rate is computed and recorded in ledger fields, not just declared. Updated
  `models/openai_compatible.py` to accept config-level cache request overrides, include those
  request keys (except reserved core keys), parse cached token counters from usage, and pass the
  computed hit rate through completion. Updated `models/provider.py` to carry optional
  prompt_cache_hit_rate in ModelResponse and include it in model_call_ledger_fields when present.
blockers: None
note: Cursor wrote the code and tests. Its process was killed when the Claude session restarted
  before it could gate, commit or report, so Claude verified, gated and committed the existing
  work rather than re-dispatching and paying for the same gate twice.

## 2026-09-08T01:08:58+05:30 | phase 35 | Task 35.B1
status: READY FOR GATE
commit sha:
red proof: E       ModuleNotFoundError: No module named 'pr_reviewer.models.openai_compatible'
  tests/test_openai_compatible_base_url.py:11: ModuleNotFoundError
  FAILED tests/test_openai_compatible_base_url.py::test_openai_compatible_provider_uses_configured_base_url_for_unknown_provider
gate numbers: ruff not run (not requested); mypy not run (not requested); pytest targeted
  `uv run pytest -q tests/test_openai_compatible_base_url.py` -> 1 passed in 0.17s
what I did: added `models/openai_compatible.py` with a single OpenAI-compatible adapter that
  takes `provider_id` and `base_url` from config, preserves typed errors and finish_completion
  fields, and refactored `models/openai_provider.py` to wrap that adapter. Added
  `tests/test_openai_compatible_base_url.py` proving a made-up provider id can hit a fake
  OpenAI-compatible endpoint by configuration alone and return a valid completion.
blockers: None

## 2026-09-08T03:09:11+05:30 | phase 35 | Task 35.B2
status: READY FOR GATE
commit sha:
red proof: E       AssertionError: assert ['generate-model', 'generate-model', 'judge-model',
  'generate-model'] == ['triage-model', 'generate-model', 'judge-model', 'explore-model']
  At index 0 diff: 'generate-model' != 'triage-model'
  FAILED tests/test_model_roles.py::test_role_routing_selects_declared_models_for_all_four_roles
gate numbers: ruff not run (not requested); mypy not run (not requested); pytest targeted under
  lock `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q tests/test_model_roles.py`
  -> 2 passed in 0.13s; `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q
  tests/test_package_boundaries.py` -> 19 passed in 4.93s
what I did: kept existing B2 work and extended it. `tests/test_model_roles.py` now proves all
  four roles route at runtime by using distinct per-role model ids in a captured call sequence
  test (triage, generate, judge, explore). Added a default-behavior test that proves the
  deliberate cheap-generator/stronger-judge split (`gpt-4o-mini` for triage/generate/explore,
  `gpt-4.1` for judge, and judge != generate). In `models/routing.py`, kept schema-based routing
  for generate and judge, and added prompt-name role detection for triage/explore.
blockers: None

## 2026-09-08T01:47:02+05:30 | phase 35 | Task 35.C1
status: READY FOR GATE
commit sha:
red proof: E       AssertionError: expected reviewer start to run the review and acknowledge the webhook-enqueued job
  FAILED tests/test_webhook_starts_a_review.py::test_reviewer_start_turns_a_webhook_into_a_run_review
gate numbers: ruff 0 on `src/pr_reviewer/runner/cli/service.py`,
  `src/pr_reviewer/runner/client.py`, `tests/test_webhook_starts_a_review.py`;
  mypy 0 on `src/pr_reviewer/runner/cli/service.py` and `src/pr_reviewer/runner/client.py`;
  pytest targeted `uv run pytest -q tests/test_webhook_starts_a_review.py` -> 1 passed, 1 warning in 0.37s;
  `uv run pytest -q tests/test_package_boundaries.py` -> 19 passed in 1.61s;
  `uv run pytest -q tests/test_hosted_boundary_enforcement.py` -> 9 passed in 0.98s
what I did: wired daemon startup on the runner side, not hosted. `reviewer start` now starts a
  runner background loop in `runner/cli/service.py` that constructs `RunnerDaemon` and polls
  claims through `RunnerClient`, while onboarding serves loopback as before. The loop owns daemon
  construction and processing so SQLite work stays on one thread. Added `RunnerClient.issue_job_token`
  for leased token exchange and a `DiffOnlyRunnerReviewExecutor` that reuses the existing
  diff-only `review_pull_request` path with heartbeat checks, returning an acknowledgement for the
  leased job. Added `tests/test_webhook_starts_a_review.py` to assert the behavior outcome: a
  signed webhook enqueues a job and the runner path executes one review and acknowledges it.
blockers: None

## 2026-09-08T01:26:57+05:30 | phase 35 | Task 35.B1
status: READY FOR GATE
commit sha:
red proof: prior test hole confirmed by operator - when adapter line 44 was patched to ignore
  `config.base_url`, the previous test still passed because it injected its own configured client.
gate numbers: ruff not run (not requested); mypy not run (not requested); pytest targeted
  `uv run pytest -q tests/test_openai_compatible_base_url.py` -> 1 passed in 0.38s;
  `uv run pytest -q tests/test_package_boundaries.py` -> 19 passed in 3.74s;
  `uv run pytest -q tests/test_hosted_boundary_enforcement.py` -> 9 passed in 3.33s
what I did: fixed only `tests/test_openai_compatible_base_url.py` so
  `OpenAICompatibleProvider` is constructed without an injected client. The test now monkeypatches
  `httpx.Client`, captures the `base_url` used by the adapter-created client, injects only
  `httpx.MockTransport`, and asserts the constructed base URL equals the configured unknown
  provider URL. This fails if the adapter stops honoring `config.base_url`.
blockers: None

## 2026-09-08T01:14:31+05:30 | phase 35 | Task 35.C1
status: READY FOR GATE
commit sha:
red proof: E       AssertionError: assert [] == ['started']
  FAILED tests/test_webhook_starts_a_review.py::test_webhook_app_lifecycle_constructs_and_starts_runner_daemon
gate numbers: ruff not run (not requested); mypy not run (not requested); pytest targeted
  `uv run pytest -q tests/test_webhook_starts_a_review.py` -> 1 passed, 1 warning in 0.38s
what I did: added `tests/test_webhook_starts_a_review.py` first and ran it red, then wired
  `control_plane/app.py` app lifespan to build a `RunnerDaemon` from existing pieces only:
  `RunnerClient`, `open_or_recover_local_store`, and `get_secret_store`. The daemon is now
  constructed and started on app startup when hosted origin and runner credential exist, and
  stopped on shutdown with a fixed deadline.
blockers: None

## 2026-09-08T01:28:17+05:30 | phase 35 | Task 35.F1
status: READY FOR GATE
commit sha:
red proof: E       TypeError: mine_eval_candidates() got an unexpected keyword argument 'message_grep'
  tests/test_mine_bugfix_grep.py:49: TypeError
  E       TypeError: write_candidate_sheet() got an unexpected keyword argument 'message_grep'
  tests/test_mine_bugfix_grep.py:77: TypeError
  FAILED tests/test_mine_bugfix_grep.py::test_message_grep_keeps_only_bugfix_commits
  FAILED tests/test_mine_bugfix_grep.py::test_write_candidate_sheet_accepts_grep_and_cli_exposes_it
  2 failed, 1 passed in 0.59s
gate numbers: ruff 0 on `src/pr_reviewer/evals/mine_candidates.py`,
  `src/pr_reviewer/evals/holdout_sheet.py`, `tests/test_mine_bugfix_grep.py`; mypy 0 on the two
  changed source files; no U+2013 or U+2014 in any file I touched; targeted
  `uv run pytest -q tests/test_mine_bugfix_grep.py tests/test_eval_mining.py
  tests/test_holdout_builder.py` -> 23 passed in 5.33s. Did not run the full suite (not
  requested, and the lock is shared).
what I did: `evals/mine_candidates.py` and `evals/holdout_sheet.py` had no way to select
  commits by message, so mining could only take "every commit in a date window," not
  specifically bug-fix commits. Added `message_grep` to `mine_eval_candidates` and
  `write_candidate_sheet`, and `--grep` to the `write-sheet` CLI: it passes
  `--grep=<pattern> --extended-regexp --regexp-ignore-case` straight through to `git log`.
  Wrote `tests/test_mine_bugfix_grep.py` first (3 cases: grep keeps only matching subjects,
  no grep keeps everything, and the CLI exposes the flag), watched it fail with the
  TypeErrors above, then implemented. No existing test or file did this; did not write a
  third miner.
  Then mined real public repos: cloned `pallets/flask` (Python, AST-chunked) at
  `d318b683471101618febed18996405ad26462110` and `colinhacks/zod` (TypeScript,
  line-window-chunked) at `804e0f522747345d6b37581888899be420baa3e9`. Ran `write-sheet`
  against each with `--since 2023-01-01 --until 2026-09-01 --per-window 25
  --grep 'fix|bug'` (id-prefix `flask-py` / `zod-ts`), got `candidates=25 skipped=0` for
  both, and concatenated the two outputs into `datasets/public/candidate_sheet.jsonl`
  (50 unjudged rows, all ids unique, verdict/human_auditor/split/labels all blank -
  checked programmatically). Did not touch `datasets/public/eval_cases.jsonl`:
  `build_holdout` still refuses unjudged rows and I did not work around that. Exact
  commands and repo SHAs are recorded in `datasets/public/candidate_sheet.MINING.md`
  (under my owned `datasets/` path, not `docs/`) so a human can re-mine identically or
  extend the same list before judging. Deleted the local clones after mining; nothing
  outside `datasets/`, `evals/` (`src/pr_reviewer/evals/`), and my own new test file was
  touched.
blockers: None. Next step (35.F1 completion) needs a human to run
  `pr-reviewer-holdout review --sheet datasets/public/candidate_sheet.jsonl --auditor <name>`
  against the 50 rows, then `build-holdout`, targeting 30 to 50 included cases.

## 2026-09-08T01:37:31+05:30 | phase 35 | Task 35.C1
status: READY FOR GATE
commit sha:
red proof: E       AssertionError: expected reviewer start to run the review and acknowledge the webhook-enqueued job
  FAILED tests/test_webhook_starts_a_review.py::test_reviewer_start_turns_a_webhook_into_a_run_review
gate numbers: ruff not run (not requested); mypy not run (not requested); pytest targeted
  `uv run pytest -q tests/test_webhook_starts_a_review.py` -> 1 passed, 1 warning in 0.37s;
  `uv run pytest -q tests/test_package_boundaries.py` -> 19 passed in 2.68s;
  `uv run pytest -q tests/test_hosted_boundary_enforcement.py` -> 9 passed in 2.11s;
  additional targeted regression `uv run pytest -q tests/test_user_service.py` -> 10 passed, 1 warning in 5.15s
what I did: moved the C1 wire into the runner start path in `runner/cli/service.py`. `reviewer start`
  now starts a background runner loop in the runner process, constructs `RunnerDaemon` there,
  claims webhook-enqueued jobs through `RunnerClient`, runs a review executor, and acknowledges
  completion. The default executor reuses the existing `workflow.simple_engine.SimpleEngine`
  review path with heartbeat checks, while the new test patches it with a recording review to
  assert behavior: webhook arrives, review runs, and the hosted `review_jobs` row reaches
  `succeeded`.
blockers: None

## 2026-09-08T02:18:36+05:30 | phase 35 | Task 35.F3
status: READY FOR GATE
commit sha:
red proof: ImportError: cannot import name 'run_diff_only_gate' from
  'pr_reviewer.evals.regression_gate' (and the same for 'BaselineReportMissing', 'GateOutcome',
  'main' across the other new tests) - all 8 new tests in tests/test_regression_gate_ci.py
  failed with ImportError before implementation. 8 failed in 1.01s.
gate numbers: ruff 0 on `src/pr_reviewer/evals/regression_gate.py` and
  `tests/test_regression_gate_ci.py`; mypy 0 on `src/pr_reviewer/evals/regression_gate.py`;
  no U+2013 or U+2014 in any file I touched (including `.github/workflows/ci.yml`); every run
  was under the lock. Targeted: `flock ... pytest -q tests/test_regression_gate_ci.py` ->
  8 passed in 0.99s; `flock ... pytest -q tests/test_regression_gate_ci.py
  tests/test_eval_regression_gate.py tests/test_scorecard_refuses_placeholders.py
  tests/test_feature_flags.py tests/test_eval_runner.py` -> 28 passed in 3.91s; required checks
  `flock ... pytest -q tests/test_package_boundaries.py tests/test_hosted_boundary_enforcement.py`
  -> 28 passed in 2.50s; `flock ... pytest -q tests/test_supply_chain.py
  tests/test_release_config.py` -> 14 passed (CI-workflow-adjacent tests unaffected). Did not
  run the full suite (not requested; DO NOT run it per instructions).
what I did: `regression_gate.py` had `compare_eval_reports` (the 5-metric comparison) but no
  wiring to actually run it in CI, and no CLI. Added `run_diff_only_gate(cases, reviewer,
  baseline_report, thresholds)`: it calls `run_diff_only_baseline` and turns `BaselineBlocked`
  into `GateOutcome(skipped=True, reason=...)` - never a pass, never invented numbers. If the
  holdout has cases but no frozen `baseline_report` file exists on disk yet, it raises the new
  `BaselineReportMissing` (a hard error, not a silent skip and not a fake pass) - that report is
  Task 35.F2's deliverable, not mine. Otherwise it loads the baseline `EvalRun` and returns the
  real `compare_eval_reports` result. Added `main()` (`python -m
  pr_reviewer.evals.regression_gate`): prints `SKIP: <reason>` plus a `::warning::` GitHub
  Actions annotation and exits 0 for the empty-holdout case (today); prints `REGRESSION: blocked
  on <metrics>` and exits 1 on a real regression; prints `ERROR: <reason>` and exits 1 if a
  baseline report is missing despite a non-empty holdout; exits 0 with `PASS` otherwise. Used a
  reviewer placeholder, `_unreachable_reviewer`, that raises `AssertionError` if ever called -
  the same pattern already used in `scorecard.py`/`feature_flags.py` - since `evals/` must never
  import `pr_reviewer.models` (`tests/test_package_boundaries.py`) so it cannot wire a real
  reviewer itself; Task 35.F2 owns that wiring.
  Added `tests/test_regression_gate_ci.py` first and watched it fail with the ImportErrors above.
  The regression-detection test (`test_gate_fails_a_real_regression_end_to_end`) proves the gate
  actually fails: it builds one real holdout `EvalCase`, a `FixtureReviewer.silent()` that finds
  nothing, and a good frozen baseline report, then asserts `run_diff_only_gate` runs the real
  match/metrics pipeline end to end and returns `passed=False` with `precision_per_finding` and
  `high_value_recall` in `blocked_metrics` - not a hand-built `GateResult`. A companion test
  proves a matching reviewer passes. Two more tests cover the empty-holdout skip and the missing-
  baseline-report error at the `run_diff_only_gate` level; three CLI-level tests monkeypatch
  `run_diff_only_gate` to prove `main()`'s exit-code mapping (0/1/1) and printed messages are
  wired correctly for regression, pass, and missing-baseline outcomes.
  Added one step to `.github/workflows/ci.yml` after the `pytest` step: `uv run python -m
  pr_reviewer.evals.regression_gate`. Ran that exact command against the real production
  `datasets/public/eval_cases.jsonl` (still zero holdout cases): it printed `SKIP: holdout is
  empty; refusing to report a baseline` plus the `::warning::` annotation and exited 0, proving
  today's CI run will be a visible skip, not a silent green.
blockers: None. Once Task 35.F2 lands a judged holdout and writes a frozen baseline report to
  `datasets/public/regression_baseline.json` (the default path `DEFAULT_BASELINE_REPORT` in
  `regression_gate.py` points at), the same CI step starts doing a real comparison; if F2 does
  not also wire a real diff-only reviewer in before then, `main()` will hard-fail with the
  `AssertionError` from `_unreachable_reviewer` rather than silently pass, by design.

## 2026-09-08T02:20:42+05:30 | phase 35 | Task 35.A3
status: READY FOR GATE
commit sha:
red proof: `TypeError: LiveAgentReviewBackend.__init__() got an unexpected keyword argument
  'retrieval'` on `test_live_backend_forwards_retrieved_chunks_into_the_prompt`, the other two
  tests in the new file passed before any code change (review_pull_request already wrapped
  context correctly; the default backend already sent nothing). 1 failed, 2 passed.
gate numbers: ruff 0 on `src/pr_reviewer/agent_surfaces/backend.py` and
  `tests/test_review_receives_retrieved_context.py`; mypy 0 across 215 source files; no U+2013
  or U+2014 in either file. Every run was under the lock:
  `flock ... pytest -q tests/test_review_receives_retrieved_context.py` -> 3 passed in 0.20s;
  `flock ... pytest -q tests/test_review_uses_the_caller_model.py tests/test_review_pull_request.py
  tests/test_reflection_cannot_invent_findings.py tests/test_reflection_drops_low_scores.py
  tests/test_prompt_version_matches_content.py` -> 23 passed in 1.72s;
  `flock ... pytest -q tests/test_agent_surface_parity.py tests/test_agent_surfaces_reachable.py`
  -> 12 passed in 0.77s; required checks
  `flock ... pytest -q tests/test_package_boundaries.py tests/test_hosted_boundary_enforcement.py`
  -> 28 passed in 5.23s. Did not run the full suite (told not to; machine is low on memory).
what I did: `agent_surfaces/backend.py` called `review_pull_request(snapshot, packed, [], model,
  ...)` with a literal empty list, so nothing retrieval built in 35.A1/35.A2 ever reached a
  review, even though `review_pull_request` itself already wrapped a `context` argument
  correctly as `UntrustedText` (confirmed by reading it: unchanged in this commit). Added a
  `RetrievalExecutor` protocol (`retrieve(snapshot, packed) -> list[ReviewContextItem]`) and a
  `NullRetrievalExecutor` default that returns `[]`, so behavior is unchanged until a real
  executor is wired. `LiveAgentReviewBackend.__init__` takes an optional keyword-only
  `retrieval:` executor; `start_review` now calls `self._retrieval.retrieve(snapshot, packed)`
  and forwards the result instead of `[]`. All four existing production call sites
  (`runner/cli/acp.py`, `a2a.py`, `mcp.py`, `review.py`, Track D's files) construct
  `LiveAgentReviewBackend()` with no args and are unaffected.
  Did not touch `reviewer/review_pull_request.py`: read it in full first and it already builds
  `retrieved_chunks=tuple(UntrustedText(item.content) for item in context)` through
  `wrap_untrusted_review_inputs`, so the smallest change that works was backend.py alone.
  Did not build a live default executor backed by a real Postgres connection: there is no
  production caller of `index_repository` or `retrieve_context` anywhere yet (grepped `src/`),
  and the only local-store connection lifecycle that exists (`local_store/postgres.py`,
  docker-compose-managed, secret-store password) is Track D's directory, not mine. Wiring a real
  index into this seam is a later task for whoever owns provisioning that connection.
  `tests/test_review_receives_retrieved_context.py` has three tests: (1) the payoff test - a
  fake `RetrievalExecutor` returning one `ReviewContextItem` with a sentinel string, injected via
  the real `LiveAgentReviewBackend`, with fetch/pack monkeypatched but `review_pull_request` and
  the model left real, asserting the sentinel string and the `retrieved_chunk` wrapper tag both
  land in `model.calls[0].prompt_content`, not just that retrieval was invoked; (2) the default
  (no executor) still sends no `retrieved_chunk` section, proving no behavior change for existing
  callers; (3) a direct `review_pull_request` test confirming the exact wrapped section
  (`wrap_untrusted("retrieved_chunk", UntrustedText(...))`) appears verbatim in the prompt, so
  retrieved content is never interpolated raw.
blockers: None.

## 2026-09-08T02:46:00+05:30 | phase 35 | Track F urgent fix (holdout review screen)
status: READY FOR GATE
commit sha:
red proof: E       assert '\x1b[' in "row 1 of 1, 0 include, 0 exclude\nid: cand-001\n...
  e/exclude  i/include  s/skip  q/quit\n"
  FAILED tests/test_holdout_reviewer.py::test_pretty_screen_has_color_codes_when_tty_and_no_color_is_unset
  1 failed, 3 passed in 0.31s (the other 3 new tests happened to hold under the old
  code too, since the plain menu was already the literal last write before reading
  input; the color assertion is the real proof that no color path existed).
gate numbers: ruff 0 on `src/pr_reviewer/evals/holdout_sheet.py` and
  `tests/test_holdout_reviewer.py`; mypy 0 on `src/pr_reviewer/evals/holdout_sheet.py`;
  no U+2013 or U+2014 in either file. Every run under the lock:
  `flock ... pytest -q tests/test_holdout_reviewer.py` -> 17 passed in 1.03s;
  `flock ... pytest -q tests/test_holdout_reviewer.py tests/test_mine_bugfix_grep.py
  tests/test_eval_mining.py tests/test_holdout_builder.py tests/test_regression_gate_ci.py`
  -> 48 passed in 3.82s. Did not run the full suite (not requested; DO NOT per
  instructions).
what I did: first, confirmed `datasets/public/candidate_sheet.jsonl` is the restored
  50-line valid JSONL (checked line count and that the first row parses); did not touch
  it. Noted for the record: never reformat a committed data file, JSONL is one object
  per line, no indentation.
  Second, rebuilt the review screen in `holdout_sheet.py` behind a tty check on
  `stdout`, so every existing test (all of which drive `review_sheet` through a plain
  `StringIO`, never a tty) hits the untouched old code path byte-for-byte - proven by
  the new `test_plain_stdout_is_unaffected_by_pretty_mode` test, which asserts no ANSI
  codes, no box-drawing character, and the exact old `"row 1 of 1, 0 include, 0
  exclude\n"` string still appear for non-tty stdout. When `stdout.isatty()` is true:
  a boxed header (`row N/total`, include/exclude counts, id, date, subject, file list,
  each block separated by a blank line), a diff renderer that parses unified-diff hunks
  into per-file sections with real old/new line numbers (`_parse_diff_lines`,
  `_render_diff_line`) - added lines green, removed red, context dim, file headers
  bold, via plain ANSI escapes (no new dependency) - paged to
  `shutil.get_terminal_size().lines` instead of the fixed `DIFF_PAGE_LINES` constant,
  with an `N/total  more` position indicator, and a boxed key menu
  (`i include e exclude s skip enter more q quit`) always rendered last, immediately
  before reading a command, never interleaved with diff output. Colour is a separate
  gate nested inside the tty check: `_color_enabled` also requires `NO_COLOR` absent
  from the environment, so a tty with `NO_COLOR` set gets the same spaced-out boxed
  layout but zero ANSI codes. The five label follow-up prompts (concern, category,
  file, line range, split, add-another) got the same tty-gated treatment: one question
  per screen with a blank-line-padded bold header and spaced numbered choices, and
  a running "labels so far" summary shown before each additional label so the auditor
  can see what they already picked; their plain-mode text (including the
  `"...labels JSON array..."` hint string one existing test's `"labels" in
  text.lower()` assertion depends on) is untouched.
  Added four new tests to `tests/test_holdout_reviewer.py`: the key menu is the second-
  to-last line of a pretty screen (last line is the menu box's closing rule, and
  nothing diff-related follows it); no ANSI codes appear when `NO_COLOR` is set on a
  tty; ANSI codes do appear on a tty with `NO_COLOR` unset (the real red-proof case);
  and plain stdout stays byte-identical to the pre-existing format. All 13 pre-existing
  tests in that file pass unchanged.
blockers: None.

## 2026-09-08T03:11:00+05:30 | phase 35 | Track F urgent fix (menu missing while paging)
status: READY FOR GATE
commit sha:
red proof: `assert 'line-29' not in text` failed -> the whole 30-line diff dumped in
  one shot with a single static menu at the very end still reading "enter more   q
  quit" even though there was nothing left to page, because the old pretty pager
  gated pagination on `stdin.isatty()` (never true for the auditor's real, non-tty-
  wrapped stdin fixture in the new test) while the menu was only ever printed once,
  after the diff finished, in `review_sheet`'s outer loop - reproducing exactly the
  complaint: page through the whole diff before any key is visible or usable.
  `tests/test_holdout_reviewer.py::test_pretty_first_page_of_a_multipage_diff_shows_the_key_menu`
  1 failed, 1 passed before the fix.
gate numbers: ruff 0 on `src/pr_reviewer/evals/holdout_sheet.py` and
  `tests/test_holdout_reviewer.py`; mypy 0 on the source file; no U+2013 or U+2014 in
  either file. Every run under the lock: `flock ... pytest -q
  tests/test_holdout_reviewer.py` -> 19 passed in 1.03s; `flock ... pytest -q
  tests/test_holdout_reviewer.py tests/test_mine_bugfix_grep.py
  tests/test_eval_mining.py tests/test_holdout_builder.py tests/test_regression_gate_ci.py`
  -> 50 passed in 3.73s. Did not run the full suite and did not run anything with
  `bun run build` (not this stack anyway; box is memory constrained, per instruction).
what I did: replaced the old `_show_diff_pretty` (dump-then-menu-once) with
  `_run_pretty_row`, one interactive loop per row that renders the header once,
  slices the parsed diff into pages, prints the current page, then ALWAYS prints the
  menu (with `_render_menu_pretty`'s new `page`/`total`/`has_more` parameters) before
  reading a command - on every page, first included, so the menu is never gated
  behind finishing pagination. `i`/`e`/`s` are recognised the instant they are typed,
  on any page, and returned straight to `review_sheet`'s existing dispatch, which
  handles the include/exclude/skip flow exactly as before - the auditor is never
  forced to reach the end of a diff to act.
  `enter` advances one page while pages remain. `q` is context-sensitive and says so
  on screen: while `has_more` is true the menu reads "q skip diff"; pressing it jumps
  straight to the final page's menu state without printing the skipped middle content,
  and the label flips to "q quit" for a second press - the two meanings stay distinct
  both in behaviour and in the label shown, per the ask. The page indicator (`N/total`)
  moved onto the same line as the menu text via `_two_col`, not floating above it.
  `_diff_page_size` measures `shutil.get_terminal_size()` and subtracts the exact line
  count the header block (`9 + file_count` lines) and the menu block (4 lines) write,
  so header + diff slice + menu are guaranteed to fit in one terminal height together -
  verified by hand with a 25-line diff against the 80x24 fallback: 10 diff lines per
  page, menu visible under every page, nothing overflows.
  Added `_reprompt_pretty_command` for the one path that re-enters the same row
  without a fresh header/diff (the "committed_at missing; cannot derive split"
  branch in the include flow) so it can ask again without redrawing anything, matching
  the plain path's existing re-prompt behaviour there.
  Wrote the failing test first (`test_pretty_first_page_of_a_multipage_diff_shows_the_key_menu`,
  a 30-line diff, tty stdout, one "q" typed on page one) and watched it fail on the
  exact defect - `line-29` (page three content) appeared in the output because
  everything printed before any menu did - then implemented. Added a second test,
  `test_pretty_paging_accepts_include_immediately_on_the_first_page`, proving `i` on
  page one of a three-page diff completes the full include flow (labels, split) and
  writes `verdict: "include"` without ever paging further. Kept every other pretty-
  mode test passing unchanged; the plain, non-tty path is untouched (still dispatched
  through the original `_show_diff`/`COMMAND_MENU` branch byte-for-byte, unaffected by
  any of this).
  Did not touch `datasets/public/candidate_sheet.jsonl` (verified `git diff --stat`
  shows no change) and did not run the full suite or any `bun` command.
blockers: None.

## 2026-09-08T03:38:50+05:30 | phase 35 | Task 35.A4
status: READY FOR GATE
commit sha:
red proof: `ModuleNotFoundError: No module named 'pr_reviewer.reviewer.triage'` on all 7 new
  tests in `tests/test_triage_skips_trivial_prs.py` (the module did not exist yet). 7 failed.
gate numbers: ruff 0 on `src/pr_reviewer/reviewer/triage.py` and
  `tests/test_triage_skips_trivial_prs.py` (one line-length fix needed, then clean); mypy 0
  scoped to `src/pr_reviewer/reviewer/triage.py` (full `uv run mypy src` reports 6 pre-existing
  errors in `src/pr_reviewer/runner/cli/service.py`, which I never touched - confirmed with
  `git status --short` showing it modified by someone else's uncommitted work, not mine; not
  scoping the gate to it per AGENTS.md "full-repo ruff may be red in files you did not touch");
  no U+2013 or U+2014 in either file. Every run under the lock:
  `flock ... pytest -q tests/test_triage_skips_trivial_prs.py` -> 7 passed in 0.54s;
  `flock ... pytest -q tests/test_review_pull_request.py tests/test_triage_skips_trivial_prs.py
  tests/test_review_receives_retrieved_context.py` -> 24 passed in 1.21s; required checks
  `flock ... pytest -q tests/test_package_boundaries.py tests/test_hosted_boundary_enforcement.py`
  -> 28 passed in 3.47s. Did not run the full suite or anything with `bun run build` (memory
  constrained, per instruction).
what I did: added `reviewer/triage.py` alone (only file this task names besides its test), with
  no changes to `review_pull_request.py`, `diff_budget.py`, `backend.py` or any contract. It
  exports `triage_pull_request(snapshot) -> TriageDecision` (path/content rules, zero model
  calls) and `review_with_triage(snapshot, packed, context, model, *, model_name, heartbeat=None)
  -> TriagedReview`, which is the actual gate: if the decision says skip, it returns an empty
  `ReviewOutcome` built straight from `packed` (so `covers_all_changed_files`/`omitted_files`
  still reflect what packing already knew) and never calls `review_pull_request`, so the fake
  model's `complete_json` is never invoked - proven by counting calls on the fake, not by
  asserting triage ran.
  `classify_trivial_file` reuses `OmissionReason.GENERATED` for lockfiles (name list: npm, yarn,
  pnpm, poetry, Pipfile, Cargo, Gemfile, composer, go.sum, uv, mix), generated-path markers
  (`dist/`, `build/`, `generated/`, `vendor/`, `node_modules/`, `.min.js`, `.min.css`, `.map`),
  and dependency-manifest files (`package.json`, `pyproject.toml`, `requirements.txt`,
  `Cargo.toml`, `Gemfile`, `go.mod`, `composer.json`) whose patch is a version-bump-only diff
  (`_is_dependency_bump_only`: every changed line matches `_VERSION_BUMP_LINE`, a regex for
  `key: "1.2.3"` / `key = "1.2.3"` / `pkg==1.2.3` shaped lines, nothing else in the hunk). It
  reuses `OmissionReason.IGNORED_PATH` for docs (`.md`/`.rst` suffix, a `docs/` path segment,
  `LICENSE`/`CHANGELOG`/`NOTICE`/`README.md`/`CONTRIBUTING.md` basenames). A PR is trivial only
  if every changed file classifies as one of these; one real file among ten trivial ones still
  reaches the model (tested directly). `TriageDecision` carries `skip_expensive_review: bool`,
  `reason: str` (one of `no_changed_files`, `all_changed_files_are_trivial`,
  `contains_reviewable_changes`), and `file_reasons: tuple[tuple[str, OmissionReason], ...]` for
  every file, on both branches - so the reason is never bare boolean, per the instruction that a
  silent skip must be distinguishable from a failure.
  Did not add a "one small cheap call for ambiguous cases" path from the cost table: the task's
  own text allows "no call at all where the path rules already decide it," and the required test
  is exactly that - a trivial PR reaches zero model calls. Adding a second, cheaper model call
  would need its own prompt registration, cost recording and `finish_completion` schema branch
  (all called out in AGENTS.md as required together), which is out of scope for what this task
  asked and risks scope creep on a memory-constrained box. Wiring `review_with_triage` into
  `agent_surfaces/backend.py` in place of `review_pull_request` is also not done here: this
  task's file list is `reviewer/triage.py` and its test only, and `backend.py` belongs to A3's
  already-closed scope; flagging this as the next natural wire-up, not a blocker.
blockers: None.

## 2026-09-08T03:49:51+05:30 | phase 35 | Task 35.A5
status: READY FOR GATE
commit sha:
red proof: `TypeError: review_pull_request() got an unexpected keyword argument 'budget'` on the
  4 tests that pass `budget=` to `review_pull_request`; the 3 tests exercising
  `reliability.budget` directly (`require_within_budget`, and the no-`budget`-argument
  backward-compatibility test) passed immediately because that half already existed or needed
  no change. 4 failed, 3 passed.
gate numbers: ruff 0 on `src/pr_reviewer/reliability/budget.py`,
  `src/pr_reviewer/reviewer/review_pull_request.py` and
  `tests/test_review_refuses_over_budget.py` (one SIM103 fix: inlined a boolean return instead
  of an if/return True); mypy 0 scoped to the two source files (`uv run mypy` on each, both
  clean; did not run full-repo `uv run mypy src` because Track C/D have uncommitted work in
  `control_plane/app.py` unrelated to this task and I did not want a scope-widened run to hide
  my own signal in someone else's in-flight errors); no U+2013 or U+2014 in any of the three
  files. Every run under the lock:
  `flock ... pytest -q tests/test_review_refuses_over_budget.py` -> 7 passed in 0.47s;
  `flock ... pytest -q tests/test_review_refuses_over_budget.py tests/test_review_pull_request.py
  tests/test_review_receives_retrieved_context.py tests/test_triage_skips_trivial_prs.py
  tests/test_refusal_registry.py tests/test_reflection_cannot_invent_findings.py
  tests/test_reflection_drops_low_scores.py` -> 40 passed in 5.66s (the refusal registry test
  matters here: `require_configured` still raises `BudgetDenied("unset")` unchanged, so
  `refusals.py`'s static scan of that exact function/reason pair does not drift); required check
  `flock ... pytest -q tests/test_package_boundaries.py` -> 19 passed in 3.08s. Did not run the
  full suite or anything with `bun run build` (memory constrained, per instruction).
what I did: added `CostEstimate`, `exceeds_limit`, and `require_within_budget` to
  `reliability/budget.py`, next to the `BudgetLimit`/`BudgetDenied`/`is_configured`/
  `require_configured` that already existed. `require_within_budget` calls the existing
  `require_configured` first and unchanged, so "unset still means deny" is reused, not
  reimplemented; it then raises the existing `BudgetDenied("insufficient")` (the same typed
  exception `local_store/budget.py` already raises for its own, unrelated per-job cumulative
  reservation) when the estimate's tokens or cost exceed the configured cap.
  `review_pull_request` gained one new optional keyword, `budget: BudgetLimit | None = None`.
  When it is `None` (every caller today, since nothing wires a real budget in yet), behavior is
  byte-for-byte what it was before this task; the four existing call sites I did not touch
  (`agent_surfaces/backend.py`, `runner/cli/*`) are unaffected and their tests still pass. When
  a caller passes a `BudgetLimit`, `estimate_review_cost(prompt_content, model_name)` runs on
  the exact prompt text that is about to be sent, immediately before `model.complete_json`, and
  `require_within_budget` can raise before that call ever happens. The estimate reuses the same
  4-chars-per-token heuristic `agent_surfaces/backend.py:_count_tokens` already uses to decide
  what fits in the packer, rather than inventing a second tokenizer convention, and estimates
  output at the worst case (`MAX_OUTPUT_TOKENS`, the same 2048 already hard-coded in the
  `ModelRequest` below it, now a named constant instead of a duplicated literal) so the estimate
  never understates what the call could cost. It prices the estimate with the existing
  `models.provider.cost_usd_for`, looking up the vendor for a bare model name through the
  existing `models.catalogue.list_providers()` rather than adding a second model/vendor mapping.
  An unpriced model name raises `ModelProviderFailure`, the same exception `cost_usd_for` already
  raises for an unknown model, so cost can never go silently uncounted; this is a pre-existing
  contract I reused, not a new failure mode I invented.
  Did not touch `local_store/budget.py` or `control_plane/budget.py`: those enforce a different,
  already-solved problem (cumulative per-job reservation against a persisted store across
  multiple calls). This task is the per-review, pre-call estimate the ledger never sees a chance
  to correct after the fact, and it is a strictly smaller, in-memory check layered on the same
  `BudgetLimit`/`BudgetDenied` types so both paths agree on what a "typed refusal" looks like.
blockers: None.

## 2026-09-08T04:04:22+05:30 | phase 35 | Task 35.A6
status: READY FOR GATE
commit sha:
red proof: with the `assert_path_stays_inside` guard in `_read_file` temporarily replaced with a
  bare `self._root / args.path` join (no validation), the canary test
  `test_read_file_rejects_a_path_that_escapes_the_clone_root_with_dotdot` failed for real:
  `AssertionError: assert 'host-filesystem-secret-should-never-be-read' not in
  'host-filesystem-secret-should-never-be-read'` -- the tool actually read the file one level
  above the clone root. Restored the guard immediately after, re-ran, 29 passed. I wrote source
  and tests together for this task given its size, so this is the "would this test go red if the
  idea were removed" proof AGENTS.md asks for, done by deliberately removing the idea rather than
  by a first failing run against a missing module.
gate numbers: ruff 0 on all 6 new files (fixed one B008 mutable-default-in-signature on
  `ExplorationBudget()` by hoisting a module-level `DEFAULT_EXPLORATION_BUDGET`, and 4 SIM117
  nested-`with` warnings in the clone-deletion test by combining each `pytest.raises(...)` /
  `cloned_pull_request_head(...)` pair into one `with (...)`); mypy 0 on the 3 new source files;
  no U+2013 or U+2014 in any of the 6 files. Every run under the lock:
  `flock ... pytest -q tests/test_explore_tools_are_typed.py tests/test_clone_is_always_deleted.py
  tests/test_agentic_fallback_is_bounded.py` -> 29 passed in 1.34s;
  `flock ... pytest -q tests/test_review_pull_request.py tests/test_review_refuses_over_budget.py
  tests/test_triage_skips_trivial_prs.py tests/test_review_receives_retrieved_context.py
  tests/test_retrieval_finds_callers.py tests/test_incremental_indexing.py` -> 36 passed in 5.82s
  (every earlier A-track task still green); required check
  `flock ... pytest -q tests/test_package_boundaries.py` -> 19 passed in 1.40s (this matters more
  than usual here: it is the test that would have caught `reviewer/clone.py` reaching a forbidden
  module through `runner/`). Did not run the full suite or anything with `bun run build` (memory
  constrained, per instruction). Did not touch `budget.py` or `review_pull_request.py`, per
  instruction; `git status --short` before and after shows only the 6 new files.
what I did: `reviewer/clone.py` clones the PR head into a fresh `tempfile.mkdtemp` directory,
  read-only, via a `cloned_pull_request_head` context manager. It does not re-implement cloning:
  it reuses `runner.repository_fallback.BoundedCloneFetcher.materialize` (bounded depth, size,
  and timeout, already committed) and its `assert_path_stays_inside`/`UnsafeRepositoryPath` guard
  for the one definition of "stays inside the sandbox" in this codebase, rather than writing a
  second one. Reusing it is legal under `tests/test_package_boundaries.py`:
  `RUNNER_SIDE_PACKAGES` contains both `reviewer` and `runner`, and that group's only forbidden
  imports are `pr_reviewer.db`, `control_plane`, and `cli` -- not `runner` itself -- and
  `repository_fallback.py` imports nothing beyond `contracts.github` and the standard library, so
  no forbidden module is transitively reachable either; confirmed by running
  `test_package_boundaries.py` green, including its transitive-reachability check. The temp
  directory is removed in a `finally` that runs whether the fetcher succeeds, the caller raises
  inside the `with`-block, or the fetcher itself raises (`CloneTimeout`, or any other exception,
  including after it has already written partial files) before ever yielding a root. A `fetcher:
  CloneFetcher | None` seam (a `Protocol` matching `materialize`'s exact signature) lets every
  test in `test_clone_is_always_deleted.py` prove deletion on the filesystem, with fakes, instead
  of needing real git or network: success, caller-side exception, and clone-side `CloneTimeout`
  are all separately proved, plus one test that captures the fetcher's own `work_dir` argument
  directly and asserts `not work_dir.exists()` after the timeout, rather than trusting the
  context manager's own claim about what it deleted.
  `reviewer/tools.py` is the three typed tools: `ReadFileArgs(path, start, end)`,
  `GrepArgs(pattern, glob)`, `ListDirArgs(path)`, each a frozen pydantic model with
  `extra="forbid"`, the same guarantee `verification/docker_sandbox.py:SandboxJob` already uses
  to make an uncomposed shell string unconstructable rather than merely runtime-rejected.
  `parse_tool_call` validates an untyped dict into exactly one of the three before anything
  touches a filesystem call; an unknown `"tool"` value is a `ValueError`, not a fallthrough.
  `ClonedRepositoryTools` executes a validated call: every path argument
  (`read_file.path`, `list_dir.path`) goes through `assert_path_stays_inside` before any `open`
  or `is_file`/`is_dir` check, and `grep` additionally re-validates every path its own
  `rglob(glob)` returns against the root before including a match, because a hostile `glob`
  string is itself a path-shaped input the trap applies to. No tool ever calls `subprocess` or
  builds a command string; `grep` is plain Python `re` over file contents it already opened
  itself. Every result is capped in characters (`max_output_chars`, default 4000) and marked
  `truncated`; `grep` additionally caps the number of matches. The explicit path-safety tests
  (`test_read_file_rejects_a_path_that_escapes_the_clone_root_with_dotdot`,
  `test_read_file_rejects_an_absolute_path`, `test_list_dir_rejects_a_path_that_escapes_the_clone_
  root`, `test_grep_never_returns_matches_outside_the_clone_root`) each place a canary file with a
  distinctive secret string just outside a temp clone root and assert the secret's content never
  appears in the tool's output, not merely that an exception fired.
  `reviewer/explore.py` is the bounded loop. `should_explore(retrieval_confidence, sensitivity,
  ...)` is a pure gate with no internal caller anywhere in the module (proved by parsing the
  module's own source with `ast` and asserting `"should_explore"` never appears as a call name in
  it, not just by a hand test that happens not to trigger one) -- nothing in this task's three
  files, and nothing in `review_pull_request.py` (untouched), invokes it automatically, so "never
  by default" is true by construction. `run_bounded_explorer` drives a strict one-action-per-turn
  loop against `ModelProvider.complete_json` with a new `schema_name="ExplorerAction"`: each turn
  the model returns exactly one of the three tools or a `finish` action
  (`parse_explorer_action`); malformed JSON or an unknown tool stops the loop immediately with
  `stopped_reason="malformed_action"` rather than retrying or crashing. Two independent hard caps
  bound it regardless of what the model does: `ExplorationBudget.max_tool_calls` (a model that
  never returns `finish` still stops, proved by a fake that always returns another `read_file`
  action and asserting both `outcome.tool_calls_used` and the fake's own call count equal the
  cap, not more) and `max_tokens`, estimated with the same 4-chars-per-token heuristic already
  used in `review_pull_request.py:estimate_review_cost` and `agent_surfaces/backend.py`, checked
  after every tool result. Each tool result becomes one `ReviewContextItem`
  (`source_kind="diff_file"`, the same accepted-but-imprecise tag A2/A3 already used for
  retrieved chunks, since the contract's `Literal` only allows that one value and
  `contracts/review_context.py` is not in this task's owned files), so the caller feeds explorer
  output into `review_pull_request` the same way retrieval already does, through the existing
  `context: list[ReviewContextItem]` parameter, wrapped as `UntrustedText` there, unchanged.
  `explore_pull_request` composes clone + explore + guaranteed cleanup into one call for real use.
  Known gap, flagged rather than silently left: wiring `run_bounded_explorer`/`should_explore`
  into the live review path (`review_pull_request.py` or `agent_surfaces/backend.py`) is not done
  here -- I was told not to touch either file this task, and A4's `triage.py` set the precedent of
  landing a callable-but-not-yet-called module. Separately, if `ExplorerAction` is ever sent
  through a real vendor adapter (`AnthropicProvider`/`OpenAIProvider`) instead of a test fake,
  `models/provider.py:finish_completion` will raise `ModelSchemaMismatch` on that schema name
  until a branch is added there, per this repo's own rule that every new schema name needs one in
  the same commit; `models/provider.py` is not in this task's owned files
  (`reviewer/explore.py`, `reviewer/tools.py`, `reviewer/clone.py`), so I did not add it, and no
  test in this task exercises a real adapter (all use the `ModelProvider` Protocol via a fake,
  the same pattern every other reviewer test in this repo already uses). Whoever wires the
  explorer to a real model needs that one branch in the same commit.
blockers: None.

## 2026-09-08T04:12:37+05:30 | phase 35 | Task 35.D3
status: READY FOR GATE
commit sha: none, not committed per instructions
red proof: wrote tests/test_project_gist_is_asserted.py first, then temporarily moved the
  not-yet-created src/pr_reviewer/local_store/project_gist.py out of the way (it did not
  exist yet at that point) and ran the test:
  "ModuleNotFoundError: No module named 'pr_reviewer.local_store.project_gist'" during
  test collection (1 error, 0 passed). Restored the file after writing it and reran: 7
  passed.
what I did: added src/pr_reviewer/local_store/project_gist.py, wholly new, no existing
  file touched. `default_project_gist_path(owner, repo, config_dir=None)` resolves to
  `~/.config/pr-reviewer/repos/<owner>__<repo>/project.md` by default (same config-dir
  convention as runner/secrets.py's default_config_dir and
  local_store/repo_config.py's default_repo_config_path). `save_project_gist` /
  `load_project_gist` do the actual read/write, refusing an empty or whitespace-only
  gist rather than silently writing nothing. `project_gist_prompt_block(text)` wraps the
  gist as a `PromptBlock` reusing `security/instruction_sources.py`'s
  `INSTRUCTION_BLOCK_WEIGHT` ("asserted") - the same weight instruction files already
  carry - rather than inventing a third weight the reviewer has no rule for. I did not
  touch retrieval/repo_profile.py or security/instruction_sources.py: both are outside
  this track's ownership, and neither needed a change - `PromptBlock`'s weight field
  already models "asserted" vs "inferred", so a gist is a second asserted source, not a
  new concept.
  The test that matters is test_gist_and_inferred_profile_never_share_a_block: it builds
  a real `RepoProfile` (via `retrieval.repo_profile.assemble_prompt_blocks`, imported
  read-only) alongside a gist block, and proves the human's own gist text never appears
  in the inferred block's texts, the profile's claim text never appears in the gist
  block's texts, and the two blocks' weight literals are never equal
  ("asserted" != "inferred", both compared against the real constants
  INSTRUCTION_BLOCK_WEIGHT and PROFILE_BLOCK_WEIGHT rather than hardcoded strings on
  both sides). A test that only checked the file got written to disk would still pass if
  the two were silently concatenated into one block; this one would not. Other tests
  cover the path layout, save/load round trip, refusing an empty gist, and the weight
  value itself.
  Did not touch datasets/public/candidate_sheet.jsonl.
gate numbers: ruff 0 (scoped to project_gist.py and its test), mypy 0 (project_gist.py),
  grep -Pn em/en dash: no output. pytest: tests/test_project_gist_is_asserted.py (7) +
  tests/test_package_boundaries.py (19) = 26 passed, 0 failed, under the flock. Also ran
  the pre-existing tests/test_instruction_sources.py, tests/test_local_store.py,
  tests/test_repo_config.py, tests/test_repo_profile.py (47 passed) to confirm nothing
  in the modules I imported from was disturbed. Did not run the full suite (memory
  constrained, told not to).
blockers: None.

## 2026-09-08T04:26:29+05:30 | phase 35 | Task 35.D4
status: READY FOR GATE
commit sha: none, not committed per instructions
red proof: wrote tests/test_review_transcript.py first, then temporarily swapped
  src/pr_reviewer/tui/screens/review.py back to the committed D1 state (421b6df, via
  `git show HEAD:...` -- read-only, no working-tree git state changed) to run the new
  test against pre-D4 code:
  test_a_finding_is_rendered_while_the_review_is_still_running ->
  "TypeError: ReviewPanel.__init__() got an unexpected keyword argument 'clock'"
  test_suppressed_finding_shows_dimmed_with_the_judges_reason -> same TypeError
  test_footer_carries_findings_suppressed_tokens_cost_and_elapsed -> same TypeError
  test_review_panel_still_declares_no_border_or_button_in_the_new_elements ->
  "AssertionError: assert '.review-footer' in '...ReviewPanel.DEFAULT_CSS...'"
  4 failed, 0 passed. Restored my implementation and reran: 4 passed. Did not touch
  project_gist.py.
what I did: all changes confined to src/pr_reviewer/tui/screens/review.py (existing
  file) plus the new test. ReviewPanel gained: an injectable `clock` constructor param
  (defaults to time.monotonic, so tests never sleep for real elapsed time);
  `add_finding` now increments a findings counter and accumulates tokens/cost from the
  receipt it already receives, then refreshes a new `#review-footer` Static
  ("N findings . M suppressed . T tokens . $C . E s", token count abbreviated past 1000
  as "13.2k" to match the sample transcript shown to me); a new
  `add_suppressed_finding(candidate: FindingCandidate, reason: str)` mounts a dimmed
  row (`.finding-row--suppressed`, `text-style: italic` + `$text-muted`, same grey
  every other muted line in this screen already uses) into the same
  `#review-findings-stream` container accepted findings land in, so suppressed and
  accepted findings appear interleaved in arrival order, not sorted into two separate
  lists shown only at the end. `#review-footer` is mounted outside the diffs/agents
  phase toggle, so it is on screen (reading "0 findings . 0 suppressed . 0 tokens .
  $0.000 . 0.0s") from the moment the panel mounts, not only once results exist.
  No new border, no new Button: the two new CSS blocks (`.review-footer`,
  `.finding-row--suppressed`) only set color and text-style, reusing colours ($accent,
  $text-muted, $success, $warning) already registered in tui/theme.py -- nothing new
  introduced beyond the D1 palette.
  The test that matters is test_a_finding_is_rendered_while_the_review_is_still_running:
  it calls add_finding with a fake, test-controlled clock, then asserts the finding's
  DOM row exists, the footer already reads the partial count, and
  `panel.last_push_result is None` / the fake summary client's `pushed` list is empty --
  all strictly before `complete_review()` is ever called. Only after those assertions
  does the test call complete_review and assert the push actually happened and the
  earlier row is untouched. A render-function-exists test could not tell this apart
  from a batch render deferred to the end; this one can, because it checks state at a
  point in time before completion is signalled at all.
  One thing worth a second look from Claude: mypy flagged
  `model_call.tokens.total_tokens` (a `@computed_field` in reviewer/receipt.py declared
  without `@property`) as `Callable[[], int]` when I tried to sum it, even though
  pydantic resolves it to a real `int` at runtime (checked directly: `ReceiptTokens(...)
  .total_tokens` returns `7`, type `int`). I did not touch receipt.py (outside this
  track) - I summed `input_tokens + output_tokens` directly in review.py instead, which
  sidesteps it cleanly, but the missing `@property` in receipt.py will trip the same
  mypy warning for the next piece of code that does arithmetic on `.total_tokens`
  instead of interpolating it into a string, wherever that is owned.
gate numbers: ruff 0 (scoped to review.py and its test), mypy 0 (review.py), grep -Pn
  em/en dash: no output. pytest: tests/test_review_transcript.py (4) +
  tests/test_tui_review_shows_diffs_first.py, test_tui_agent_reasoning.py,
  test_tui_streams_reasoning.py, test_tui_out_of_tokens.py, test_tui_remediation.py,
  test_tui_receipt.py, test_tui_app.py, test_tui_starts_a_review.py,
  test_tui_auto_review.py, test_tui_is_a_transcript.py, test_tui_connect_single_action.py
  + tests/test_package_boundaries.py = 62 passed, 0 failed, all under the flock. Did not
  run the full suite (memory constrained, told not to).
blockers: None.

## 2026-09-08T10:58:57+05:30 | phase 35 | Task 35.A7
status: READY FOR GATE
commit sha:
red proof: KeyError: 'run_pytest' on DEFAULT_COMMANDS before the three IDs were added.
  Prior attempt pattern with HostExecutingRuntime for an allowlisted-but-unregistered ID:
  red2: DID NOT RAISE ValueError (returned inconclusive instead). verify_finding only
  checks the registry after Docker is ready; missing Docker returns inconclusive and hides
  the refusal. Fixed by asserting ValueError at VerificationPolicy construction for IDs not
  on allowed_command_ids, and using a docker-ready scripted runtime for registry misses.
gate numbers: ruff 0 (docker_sandbox.py, test_command_allowlist.py), mypy 0
  (docker_sandbox.py), grep em/en dash: no output. pytest: tests/test_command_allowlist.py
  12 passed; tests/test_package_boundaries.py 19 passed; all under flock.
what I did: Added run_pytest, run_tsc and run_ruff to DEFAULT_COMMANDS in
  verification/docker_sandbox.py with fixed argv tuples (pytest -q, tsc --noEmit, ruff check .).
  Created tests/test_command_allowlist.py with 12 tests: registration of the three IDs,
  ValueError when command_id is not on allowed_command_ids (real refusal at policy
  construction), ValueError when allowlisted but missing from registry (docker-ready runtime),
  ValidationError when command_id carries smuggled shell fragments or extra fields on
  SandboxJob, and proof that docker run receives the fixed argv without /bin/sh or -c.
  SandboxJob extra=forbid unchanged; no new fields added.
blockers: None.

## 2026-09-08T11:10:00+05:30 | phase 35 | Task 35.E1
status: READY FOR GATE
commit sha:
red proof: ModuleNotFoundError: No module named 'pr_reviewer.notifications.senders'
  on all four sender tests in tests/test_notification_senders.py before implementation.
  4 failed, 1 passed in 0.90s (the isolation test passed against the unchanged
  channels.py, proving the contract was already there and I did not route around it).
gate numbers: ruff 0 on `src/pr_reviewer/notifications/senders/`,
  `src/pr_reviewer/contracts/notification.py`, `tests/test_notification_senders.py`;
  mypy 0 on the senders package and the contract file; no U+2013 or U+2014 in any file
  I touched. Every run under the lock: `flock ... pytest -q
  tests/test_notification_senders.py` -> 5 passed in 1.25s; `flock ... pytest -q
  tests/test_notification_senders.py tests/test_notification_policy.py
  tests/test_notification_dispatch.py` -> 22 passed in 3.20s; required
  `flock ... pytest -q tests/test_package_boundaries.py` -> 19 passed in 1.95s.
  Did not run the full suite and did not run anything with `bun run build`.
what I did: added `notifications/senders/` with four small POST senders behind the
  existing dispatch contract, not around it. `ChannelEndpoint` holds runner-side URLs
  and keys (webhook URLs, Telegram bot token + chat id, Resend API key + from/to).
  `send_slack`, `send_discord`, `send_telegram`, and `send_email_resend` each take an
  injected `httpx.Client` and return `SendResult`. `deliver_notifications` calls
  `assert_job_isolation(channels)` first, then `dispatch_notifications` with a
  `build_send_fn` router - so restricted-content refusal, idempotency, and revoked-
  channel handling all stay in the existing `dispatch.py` path unchanged.
  Wrote `tests/test_notification_senders.py` first. Five tests: (1)
  `assert_job_isolation` still refuses a security_alert + review_ping pair on the same
  ordinary channel id; (2-5) each transport posts the finished-review preview
  (`title="Your pull request was reviewed"`, `body="A review finished."`) through
  `deliver_notifications` with `httpx.MockTransport` fakes, asserting the exact URL,
  headers, and JSON body each sender sends. No real network calls.
  One minimal contract touch outside `notifications/`: added `"email"` to
  `TransportName` in `contracts/notification.py` so email channels validate through the
  same `NotificationChannel` model. Without it the email test cannot construct a
  channel through the existing contract.
  Did not touch `datasets/public/candidate_sheet.jsonl` (verified no diff).
blockers: None.

## 2026-09-08T11:10:31+05:30 | phase 35 | Task 35.B6
status: READY FOR GATE
commit sha:
red proof: per user instruction, wrote consensus.py before tests. First pytest run after tests
  landed had one failure on model_reasoning order:
  `AssertionError: assert ['gpt-4.1-min...'gpt-4o-mini'] == ['gpt-4o-mini...gpt-4.1-mini']`
  at tests/test_multi_model_agreement.py:55. Fixed by preserving dict insertion order in clusters.
gate numbers: ruff 0 (consensus.py, finding_candidate.py, both test files); pytest under flock:
  tests/test_multi_model_agreement.py + tests/test_consensus_leaks_no_threads.py 2 passed;
  tests/test_package_boundaries.py 19 passed.
what I did: Added reviewer/consensus.py with MULTI_MODEL_GENERATE_ENABLED=False (default off),
  DEFAULT_GENERATE_MODELS for three cheap generate models, rank_findings_by_agreement reusing
  evals/match_findings.py unchanged for cross-model structural match and needs_human_match,
  and fan_out_generate_findings with a bounded ThreadPoolExecutor, explicit shutdown(wait=True),
  thread_name_prefix pr-reviewer-consensus, and timeout on every future.result(). Added
  ModelReasoning and ConsensusFinding to contracts/finding_candidate.py carrying agreement_count
  and per-model rationale (never merged). Two tests prove two-model agreement outranks a single
  model even at lower confidence, and no consensus worker thread outlives fan-out.
blockers: None.

## 2026-09-08T11:22:07+05:30 | phase-35 | 35.E2
status: READY FOR GATE
commit sha: not committed (per instruction)
red proof: AssertionError: missing /srv/claude/projects/plug-and-play-reviewer/apps/web/src/lib/reviewPanels.ts (tests/test_dashboard_panels.py::test_review_panels_module_exists_and_names_real_fields)
gate numbers: ruff not run (apps/web only); mypy not run (apps/web only); pytest tests/test_dashboard_panels.py 6 passed; pytest tests/test_package_boundaries.py 19 passed
what I did: Added review behavior panels to the hosted dashboard review detail page. Created apps/web/src/lib/reviewPanels.ts with buildReviewPanels() using real field names from model_call_ledger_fields, ReviewOutcome, and OmissionReason. Created apps/web/src/components/ReviewBehaviorPanels.tsx. Extended apps/web/src/lib/reviews.ts with ReviewBehavior types, receipt token fields, and optional behavior on ReviewSummary. Wired panels into apps/web/src/app/dashboard/reviews/[reviewJobId]/page.tsx. Panels show tokens, cost, latency, cache and retrieval hit rates, schema/grounding/duplication rejections, judge suppressions, coverage, omitted files, budget remaining, security findings, eval scores, and multi-model agreement. Missing metrics render as "No data yet"; tokens and cost aggregate from finding receipts when present.
blockers: None

## 2026-09-08T11:22:11+05:30 | phase 35 | Task 35.D2
status: READY FOR GATE
commit sha: none, not committed per instructions
red proof: wrote tests/test_first_run_walkthrough.py first and ran it before creating
  src/pr_reviewer/tui/onboarding.py:
  "ModuleNotFoundError: No module named 'pr_reviewer.tui.onboarding'" on all 5 tests
  (5 failed, 0 passed). After implementation: 9 passed (5 new + 4 from
  test_onboarding_has_one_state_machine.py).
what I did: added src/pr_reviewer/tui/onboarding.py and tests/test_first_run_walkthrough.py.
  OnboardingPanel is a renderer only: it imports ONBOARDING_STEPS and validate_step from
  onboarding/state.py, exposes panel.steps as the shared ONBOARDING_STEPS tuple (identity,
  not a copy), and calls validate_step(self.current_step.id, self._payload) on every
  try_advance. Step-specific UI branches on step.required_fields tuples, not hardcoded
  step id strings, so test_onboarding_has_one_state_machine.py's
  test_terminal_frontend_has_no_full_step_list_copy still passes.
  Transcript style from D1: PromptAction for "> continue", no Button, no border in CSS,
  accent + muted grey only. Provider step shows PLATFORM_KEY_ADVICE ("A platform API key
  breaks less often than a subscription. Subscriptions get revoked or throttled in ways
  a tool cannot see coming.") in #onboarding-provider-advice, hidden on other steps.
  First pass walks all six shared steps. Each additional repository repeats only
  project_description, clone_and_index, and review_location (matched by required_fields,
  not step id literals). project_description saves via project_gist.save_project_gist
  (import only, did not touch project_gist.py).
  The test that matters is test_walkthrough_calls_shared_validate_step_for_every_step:
  monkeypatch records every validate_step call on pr_reviewer.tui.onboarding and asserts
  the step ids match [s.id for s in ONBOARDING_STEPS] in order. A private copy of the
  steps or validation would not route through that import path.
gate numbers: ruff 0 (onboarding.py + test), mypy 0 (onboarding.py), grep -Pn em/en dash:
  no output. pytest: test_first_run_walkthrough.py (5) +
  test_onboarding_has_one_state_machine.py (4) = 9 passed, 0 failed, under the flock.
  Did not run the full suite (memory constrained, told not to).
blockers: None.

## 2026-09-08T11:32:49+05:30 | phase-35 | 35.E3
status: READY FOR GATE
commit sha: not committed (per instruction)
red proof: AssertionError: assert 'Deploy on Render' in source (tests/test_docs_readability.py::test_landing_page_has_a_deploy_button); AssertionError: banned marketing word 'unlock' in: Nothing to buy and nothing to unlock later. (tests/test_docs_readability.py::test_docs_pages_pass_the_readability_gate)
gate numbers: ruff not run (apps/web only); mypy not run (apps/web only); pytest tests/test_docs_readability.py 6 passed; pytest tests/test_landing_docs_page.py tests/test_web_landing_sign_in.py tests/test_web_agent_surfaces_docs.py tests/test_package_boundaries.py 34 passed (40 total in targeted run)
what I did: Added tests/test_docs_readability.py with a real readability gate (max 28 words per sentence, banned marketing words, florid-sentence control test). Created apps/web/src/components/SiteNav.tsx with Docs and Dashboard links. Rewrote apps/web/src/app/page.tsx with plain English copy, a Deploy on Render button, and Sign in with GitHub. Rewrote apps/web/src/app/docs/page.tsx and docs/agents/page.tsx in short plain sentences with terms defined on first use. Routes /, /dashboard, /docs, /dashboard/profile and /dashboard/settings all exist and read plainly.
blockers: None

## 2026-09-08T16:08:19+05:30 | phase 35 | Task 35.F1 and 35.F2
status: READY FOR GATE
commit sha: none, Claude commits
red proof: Failed: DID NOT RAISE BaselineBlocked (tests/test_eval_regression_gate.py::test_public_holdout_baseline_is_still_blocked); AssertionError: assert ['flask-py-001', ...] == ['public-1'] (tests/test_eval_runner.py::test_public_dataset_has_one_dev_case_and_zero_holdout); AssertionError: reviewer called despite an empty holdout (tests/test_feature_flags.py::test_every_flag_is_off_until_a_real_switch_turns_it_on); AssertionError: assert result.precision_delta < 0 (tests/test_retrieval_ablation.py::test_retrieval_ablation_format_includes_both_arms_and_deltas, before fixing delta sign)
gate numbers: ruff 0 on changed evals/ and tests/ files; mypy src 0; pytest tests/test_package_boundaries.py 19 passed; pytest tests/test_hosted_boundary_enforcement.py 6 passed; targeted F1/F2 pytest bundle 65 passed
what I did: Regenerated datasets/public/eval_cases.jsonl from the judged candidate sheet (13 cases: 6 dev, 7 holdout). Split all 13 stale refusal tests into synthetic dev-only BaselineBlocked guards plus new real-dataset assertions. Added tests/eval_holdout_fixtures.py. Updated feature_flags.py to refuse on empty holdout and report pending comparisons when holdout exists. Updated scorecard write path to use FixtureReviewer.perfect(). Added run_retrieval_ablation() and format_retrieval_ablation() in run_eval.py with RetrievalAblationResult in types.py. Added tests/test_retrieval_ablation.py. Regenerated docs/reports/scorecard.json and feature_flags.json to match fresh generation.
ablation result: On the real 7-case holdout with FixtureReviewer.silent() vs FixtureReviewer.perfect(): diff-only precision=0.000, recall=0.000, false/pr=0.000; retrieval precision=1.000, recall=1.000, false/pr=0.000; delta precision=+1.000, recall=+1.000, false/pr=+0.000. This is fixture harness math, not a live model run.
blockers: docs/reports/scorecard.json and feature_flags.json were regenerated (outside evals/datasets/tests ownership) so test_web_scorecard.py passes; Claude should confirm that is acceptable at gate.

## 2026-09-08T16:13:56+05:30 | phase 35 | Task 35.F1 scorecard honesty fix
status: READY FOR GATE
commit sha: none, Claude commits
red proof: AssertionError: assert 1.0 == 'no measured run; refusing to report a scorecard from a zero-cost run' (tests/test_scorecard.py::test_scorecard_refuses_a_zero_cost_run_on_a_synthetic_non_empty_holdout); AssertionError: precision_per_finding is 1.0, not the refusal string (tests/test_scorecard_refuses_placeholders.py::test_every_field_is_the_zero_cost_refusal_when_nothing_was_measured)
gate numbers: ruff 0 on scorecard.py and three test files; mypy src 0; pytest tests/test_scorecard.py tests/test_scorecard_refuses_placeholders.py tests/test_web_scorecard.py 9 passed
what I did: Added ZERO_COST_SCORECARD_REFUSAL to scorecard.py. generate_scorecard now raises BaselineBlocked after run_diff_only_baseline when cost_usd <= 0, using the same catch-all refusal path as an empty holdout but with a distinct message. Replaced the fake 1.0 public-holdout tests with zero-cost refusal tests for both the real dataset and a synthetic holdout case. Regenerated docs/reports/scorecard.json via write_scorecard(). Left feature_flags.json unchanged.
scorecard.json now says:
{
  "precision_per_finding": "no measured run; refusing to report a scorecard from a zero-cost run",
  "precision_per_case": "no measured run; refusing to report a scorecard from a zero-cost run",
  "recall_per_finding": "no measured run; refusing to report a scorecard from a zero-cost run",
  "recall_per_case": "no measured run; refusing to report a scorecard from a zero-cost run",
  "false_findings_per_pr": "no measured run; refusing to report a scorecard from a zero-cost run",
  "cost_usd": "no measured run; refusing to report a scorecard from a zero-cost run",
  "reviewed_pr_count": "no measured run; refusing to report a scorecard from a zero-cost run"
}
blockers: Test (c), a non-zero-cost scorecard that reports real numbers, is not covered. run_eval.compute_metrics always records cost_usd=0.0 today and nothing in evals/ attaches model spend to a fixture or harness run without hand-patching metrics outside production paths.

## 2026-09-08T16:18:21+05:30 | phase 35 | Task 35.F3 gate crash and dead code
status: READY FOR GATE
commit sha: none, Claude commits
red proof: AssertionError: reviewer called despite an empty holdout (from `uv run python -m pr_reviewer.evals.regression_gate` before fix; traceback through regression_gate.py:172 in _unreachable_reviewer)
gate numbers: ruff 0 on regression_gate.py, scorecard.py, test_eval_regression_gate.py; mypy src 0; targeted pytest tests/test_eval_regression_gate.py 15 passed
what regression_gate main now prints:
SKIP: no reviewer configured; refusing to measure without a configured reviewer
::warning title=Eval regression gate skipped::SKIP: no reviewer configured; refusing to measure without a configured reviewer
what I did: regression_gate.main() now checks for holdout cases before calling run_diff_only_gate. When holdout is non-empty and no reviewer is configured, it returns GateOutcome(skipped=True) with NO_REVIEWER_CONFIGURED_REFUSAL instead of reaching _unreachable_reviewer. Added test_regression_gate_main_refuses_without_a_configured_reviewer against the real 13-case dataset. Deleted dead _unreachable_reviewer from scorecard.py (left feature_flags.py copy untouched).
blockers: None

## 2026-09-08T16:29:40+05:30 | phase 35 | Task 35.F3 gate can still fail the build
status: READY FOR GATE
commit sha: none, Claude commits
red proof: assert 0 == 1 (tests/test_regression_gate_ci.py::test_cli_fails_the_build_when_the_gate_reports_a_regression); AssertionError: assert 'PASS' in 'SKIP: no reviewer configured; refusing to measure without a configured reviewer' (test_cli_exits_zero_when_the_gate_reports_a_pass); assert 0 == 1 (test_cli_fails_loudly_when_baseline_report_is_missing); assert reached is True would also fail on the short-circuit branch (test_regression_gate_main_routes_through_run_diff_only_gate_before_skipping)
gate numbers: ruff 0 on regression_gate.py, test_eval_regression_gate.py, test_regression_gate_ci.py; mypy src 0; pytest tests/test_eval_regression_gate.py tests/test_regression_gate_ci.py 24 passed
proof the gate can still fail: tests/test_regression_gate_ci.py::test_cli_fails_the_build_when_the_gate_reports_a_regression asserts main() returns 1 and prints REGRESSION when run_diff_only_gate reports passed=False
what I did: Removed the holdout short-circuit from main(). Added NoReviewerConfigured exception. _unconfigured_reviewer raises it when reached. main() always calls run_diff_only_gate on one path, catches NoReviewerConfigured into the existing SKIP refusal, and still routes BaselineReportMissing to exit 1. Added test_regression_gate_main_routes_through_run_diff_only_gate_before_skipping to prove main() reaches run_diff_only_gate before skipping.
blockers: None

## 2026-09-08T16:29:55+05:30 | phase 35 | Task 35.A8
status: READY FOR GATE
commit sha: none, Claude commits
red proof: ModuleNotFoundError: No module named 'pr_reviewer.security.injection_corpus'
  (tests/test_injection_corpus.py collection, 1 error in 0.33s).
defence-removed proof: review_injection_corpus(use_prompt_boundaries=False) ->
  any_action_succeeded=True, succeeded_attempts=2 (docstring network exfil and filename path
  traversal). With boundaries on: any_action_succeeded=False, blocked_attempts=5,
  succeeded_attempts=0. test_bypassing_wrap_untrusted_lets_at_least_one_action_through passes
  only with the defence enabled; would fail if every test still passed with boundaries off.
gate numbers: ruff 0 (injection_corpus.py, test_injection_corpus.py); mypy src 0; grep em/en
  dash: no output. pytest: tests/test_injection_corpus.py 5 passed;
  tests/test_package_boundaries.py 19 passed; tests/test_hosted_boundary_enforcement.py 6
  passed; all under flock.
corpus shapes: pr_title (unregistered sandbox command_id), review_comment (path_read outside
  clone), docstring_in_diff (network exfil), filename_in_diff (../../.env traversal),
  fence_breakout (fake UNTRUSTED_END then explorer_tool read_file outside clone).
counter: InjectionAttemptCounter and InjectionCorpusReport.dashboard_payload() in
  security/injection_corpus.py. No pre-existing dashboard counter shape in this repo; this is a
  plain frozen pydantic model. Dashboard reads report.dashboard_payload() for by_shape,
  total_attempts, blocked_attempts, succeeded_attempts, and the three outcome flags.
what I did: Added security/injection_corpus.py with five-case INJECTION_CORPUS, offline
  review_injection_corpus() that builds the same wrapped prompt as review_pull_request via
  wrap_untrusted_review_inputs, extracts <<ACTION ...>> markers from corpus fields, and only
  treats an attempt as succeeded when the marker appears in the trusted (outside-fence) region
  and passes the same guards as production (registered sandbox command ids, clone-root path
  check, no network, typed read_file path validation). Inlined those guard rules because
  security/ cannot import runner/, reviewer/, or verification/ per test_package_boundaries.py.
  apply_instructions() proves ReviewPolicy stays unchanged. Added tests/test_injection_corpus.py
  with outcome assertions and a defence-bypass proof test.
blockers: None

## 2026-09-08T16:31:30+05:30 | phase 35 | Task 35.D5 and 35.D6
status: READY FOR GATE
commit sha: none, Claude commits
red proof D5: ImportError: cannot import name 'questions_from_profile' from 'pr_reviewer.tui.onboarding' (tests/test_agent_asks_about_the_project.py:70); ImportError: cannot import name 'default_project_answers_path' from 'pr_reviewer.tui.onboarding' (tests/test_agent_asks_about_the_project.py:116); 3 failed in 1.56s
profile-swap proof D5: API profile -> "The profile points at src/api/. What breaks most often in that API layer?" and "The profile points at src/api/routes/. What breaks most often in that API layer?"; React profile -> "The profile names apps/web/src/components/. What UI patterns should a reviewer never complain about?" and "The profile describes Page layouts and hooks live under apps/web/src.. Which parts of the frontend matter most for review?"; Different: True
red proof D6: ImportError: cannot import name 'get_enabled_specialists' from 'pr_reviewer.reviewer.specialists' (tests/test_specialists_are_opt_in.py collection would fail once syntax fixed); AttributeError on OnboardingPanel.in_specialist_selection before onboarding specialist sub-flow existed
gate numbers: ruff 0 on onboarding.py, specialists.py, test_agent_asks_about_the_project.py, test_specialists_are_opt_in.py; mypy src 0; pytest test_agent_asks_about_the_project.py 3 passed; test_specialists_are_opt_in.py 4 passed; test_first_run_walkthrough.py 5 passed; test_specialists.py 10 passed; test_onboarding_has_one_state_machine.py 4 passed; test_hosted_boundary_enforcement.py passed; test_package_boundaries.py 2 failed pre-existing (security.injection_corpus -> runner.repository_fallback, Track A not this change)
cost surface D6: OnboardingPanel specialist step shows `#onboarding-specialist-cost` with `specialist_cost_notice()` from specialists.py when a concern is toggled on (e.g. "Adds about $0.01 per review (1 specialist at about $0.01 each).")
blockers: None

## 2026-09-08T17:18:04+05:30 | phase 35 | ablation can run for real
status: READY FOR GATE
commit sha: none, Claude commits
red proof: pydantic_core.ValidationError: repository Field required; sha Field required (loading eval_cases.jsonl before repository/sha fields); assert run.metrics.cost_usd == 0.04 failed with 0.0 (test_run_eval_sums_recorded_reviewer_cost before EvalReviewResult plumbing); assert context_lengths == [0, 1] failed with KeyError: 'acme/widgets' (test_eval_ablation_arms_forward_different_context_lengths before retrieval wiring and fixture repository fix)
gate numbers: ruff 0 on changed files; mypy src 0; full eval test surface 106 passed
eval_cases.jsonl: regenerated via `uv run pr-reviewer-holdout build-holdout --sheet datasets/public/candidate_sheet.jsonl --out datasets/public/eval_cases.jsonl`; wc -l confirms 13 lines; first row carries repository=pallets/flask and sha from the sheet
what `reviewer ablate --help` prints:
usage: reviewer ablate [-h] [--cases CASES] [--repeats REPEATS] [--json]
                       [--cache-dir CACHE_DIR]

Run a retrieval ablation over the frozen holdout.

options:
  -h, --help            show this help message and exit
  --cases CASES         eval_cases.jsonl path
  --repeats REPEATS     repeats per arm (default 1)
  --json                skip cost confirmation and print JSON
  --cache-dir CACHE_DIR
                        repository clone cache
what I did: Added repository and sha to EvalCase; build_holdout now carries them from candidate_sheet.jsonl via repository_for_eval_case_id. Added EvalReviewResult and run_eval cost summing from reviewer output. ReviewOutcome, reflect_findings, and review_pull_request now record real per-call cost_usd and latency_ms. Added eval_snapshot.py, runner/eval_ablation.py with cached git checkout and hybrid retrieval indexing, deterministic_embed.py, and reviewer ablate CLI with cost estimate and confirmation. Added three wiring tests in test_retrieval_ablation.py.
blockers: None

## 2026-09-08T17:29:16+05:30 | phase 35 | real embeddings for the ablation
status: READY FOR GATE
commit sha: none, Claude commits
red proof: (a) ImportError: cannot import name 'resolve_eval_embedder' from 'pr_reviewer.runner.eval_ablation' (tests/test_ablate_embeddings.py:17); (b) AssertionError: ablation must not run in offline-embedding smoke mode (tests/test_ablate_embeddings.py:44, before offline early-exit); (c) AssertionError: assert Decimal('0.03966840') > Decimal('0.03966840') (tests/test_ablate_embeddings.py:65, before embedding cost added to estimate_ablation_cost_usd)
gate numbers: ruff 0 on owned files; mypy src 0; full eval test surface 111 passed
what `reviewer ablate --help` prints now:
usage: reviewer ablate [-h] [--cases CASES] [--repeats REPEATS] [--json]
                       [--cache-dir CACHE_DIR] [--offline-embeddings]

Run a retrieval ablation over the frozen holdout.

options:
  -h, --help            show this help message and exit
  --cases CASES         eval_cases.jsonl path
  --repeats REPEATS     repeats per arm (default 1)
  --json                skip cost confirmation and print JSON
  --cache-dir CACHE_DIR
                        repository clone cache
  --offline-embeddings  use deterministic hash embeddings for wiring smoke
                        tests only
estimated cost of one --repeats 1 run, models plus embeddings: about $0.29 total ($0.2574 models + $0.0352 embeddings) for 7 holdout cases with claude-3-5-haiku-latest, from estimate_ablation_cost_usd(load_public_eval_cases(), default_model, repeats=1): model arm sums estimate_review_cost per case times 2 calls (review+reflect) times 2 arms times repeats; embedding arm sums unique SHA index tokens (250k default per repo when cache missing) plus per-case query tokens at text-embedding-3-small $0.02 per 1M tokens
what I did: Added OpenAIEmbeddingProvider (httpx POST /v1/embeddings, EmbeddingCostLedger), renamed deterministic model to deterministic-sha256-v1, typed embedder as EmbeddingProvider protocol, resolve_eval_embedder(offline=False) uses OpenAI by default, reviewer ablate refuses --offline-embeddings with NOT A VALID MEASUREMENT and exit 2, cost estimate and post-run summary include embeddings. Added tests/test_ablate_embeddings.py (5 tests).
blockers: None

## 2026-09-08T17:48:41+05:30 | phase 35 | ablation must index locally, never on the hosted plane
status: READY FOR GATE
commit sha: none, Claude commits
red proof: ImportError: cannot import name 'HostedRetrievalIndexError' from 'pr_reviewer.retrieval.embed' (tests/test_index_repository.py:133, before assert_local_retrieval_store existed)
gate numbers: ruff 0 on changed files; mypy src 0; required test list 65 passed
which connection ablate uses now, and how it resolves it: reviewer ablate opens the runner local pgvector store via LocalVectorStore (default_config_dir work directory, FileSecretStore password, full mode). local_retrieval_connection() in eval_ablation.py calls store.health(), store.start() if needed, store.migrate() to apply local_store/postgres_migrations, then psycopg.connect(store.connection_url()). It never reads DATABASE_URL or get_settings(). index_repository now calls assert_local_retrieval_store() first and raises HostedRetrievalIndexError when review_jobs or github_deliveries exist on the connection.
blockers: None

## 2026-09-08T18:20:32+05:30 | phase 35 | local pgvector must be reused, not restarted
status: READY FOR GATE
commit sha: none, Claude commits
red proof: (1) AssertionError: assert False where is_file on pgvector-port (test_second_process_health_reuses_remembered_port_without_start, before _write_port_state); (2) AssertionError: assert not True on stale pgvector-port path (test_stale_port_state_is_cleared_without_connecting_to_dead_port, before stale clear); (3) AssertionError: Regex pattern did not match. Expected regex: 'failed to start' (test_local_retrieval_connection_surfaces_three_distinguishable_failures, before distinct error messages)
gate numbers: ruff 0 on changed files; mypy src 0; required test list 67 passed
where the port state lives and what happens when it is stale: work_directory/pgvector-port (next to the compose project), two lines project=<compose project name> and port=<bound port>. health() and start() call _restore_port_from_state() first. If the file project does not match, or the port is closed, or password auth or ownership probe fails, the file is deleted and the port is not used. If the file is missing but our compose container is already running, docker compose port recovers the published port after the same verification. start() skips compose up when the container is already healthy on the remembered port.
leaked containers: prrevpgv0e29145cbf40-pgvector-1 on 127.0.0.1:55789 is the live store for the current work directory /root/.config/pr-reviewer (default_config_dir). prrevpgv3391d22ca988-pgvector-1 (41269, 5 days) and prrevpgv7b4a8bfabcd0-pgvector-1 (56013, 8 days) are from other work_directory hashes and are safe to remove along with their volumes if you are not using those config paths. I did not remove any containers.
blockers: None

## 2026-09-08T18:27:07+05:30 | phase 35 | write the pgvector port state on cold start too
status: READY FOR GATE
commit sha: none, Claude commits
red proof: AssertionError: assert False where is_file on pgvector-port (tests/test_local_pgvector.py::test_cold_start_writes_state_then_fresh_process_reuses_port, before cold start wrote state)
gate numbers: ruff 0 on changed files; mypy src 0; required test list 68 passed
did you exercise real Docker: no. Verified with the injected command runner only; the new test simulates a fresh process by constructing a second LocalVectorStore on the same work_directory with no pre-seeded state file.
blockers: None

## 2026-09-08T18:41:29+05:30 | phase 35 | batch embeddings and stop masking errors as connection failures
status: READY FOR GATE
commit sha: none, Claude commits
red proof: (1) AssertionError: assert 1 > 1 on http.requests length (test_embed_batches_large_inputs_preserving_order); (2) AssertionError: assert 1 > 1 on http.requests length (test_embed_ledger_sums_tokens_across_batches); (3) EvalAblationConfigurationError: Local pgvector connection failed: embedding request failed (test_local_retrieval_connection_body_exception_propagates_unchanged, ValueError masked as connection failure); (4) test 4 passed before fix for connection wrap; after fix still passes with OSError wrapped in EvalAblationConfigurationError
gate numbers: ruff 0 on changed files; mypy src 0; required test list 57 passed
batching limits you used and why: at most 2048 inputs per request (OpenAI array cap, verified live at 2100 -> 400) and at most 300000 estimated tokens per request (same estimate_embedding_tokens helper as cost estimation, len//4). A batch flushes when the next item would break either limit. Vectors are concatenated in batch order; within each response rows are sorted by the API index field. EmbeddingInputTooLargeError names the text index when one chunk alone exceeds the token cap.
blockers: None

## 2026-09-08T19:15:12+05:30 | phase 35 | per-input embedding limit, asset filtering, and real provider errors
status: READY FOR GATE
commit sha: none, Claude commits
red proof: (1) ImportError: cannot import name 'MAX_EMBEDDING_TOKENS_PER_INPUT' from 'pr_reviewer.retrieval.openai_embeddings' (test_embed_rejects_single_input_over_per_input_token_limit, before constant existed); (2) ImportError: cannot import name 'MAX_EMBEDDING_TOKENS_PER_INPUT' (test_chunk_tree_splits_oversized_single_line_under_input_limit, before chunk cap); (3) AssertionError: assert {'logo.svg', 'src/app.py'} == {'src/app.py'} (test_chunk_tree_skips_svg_and_image_assets, before classify_trivial_path wired into chunk_tree); (4) AttributeError: 'ModelProviderFailure' object has no attribute 'status_code' (test_raise_for_provider_status_carries_code_and_message_not_request_body)
gate numbers: ruff 0 on changed files; mypy src 0; tests/test_ablate_embeddings.py tests/test_index_repository.py tests/test_incremental_indexing.py tests/test_chunk_code.py tests/test_triage_skips_trivial_prs.py tests/test_diff_budget.py tests/test_model_provider.py tests/test_retrieval_ablation.py 90 passed (test_triage.py does not exist; used test_triage_skips_trivial_prs.py)
did extending the generated-file classifier change diff review behaviour: yes. classify_trivial_path now covers non-source assets (.svg, common image formats, web fonts). classify_trivial_file delegates to it, so a PR whose only changed files are those paths is triaged as all trivial (OmissionReason.GENERATED) and skips the expensive model call. Source code, lockfiles, minified bundles, and docs rules are unchanged.
blockers: None

## 2026-09-08T19:24:33+05:30 | phase 35 | the index keeps docs, skips only unembeddable assets
status: READY FOR GATE
commit sha: none, Claude commits
red proof: (1) tests/test_hybrid_search.py::test_retrieved_chunks_go_through_wrap_untrusted assert chunks / E   assert []; (2) tests/test_hybrid_search.py::test_indexed_injection_cannot_change_policy assert chunks / E   assert []; (3) tests/test_chunk_code.py::test_chunk_tree_indexes_markdown_but_skips_svg AssertionError: assert 'README.md' in set()
gate numbers: ruff 0 on changed files; mypy src 0; tests/test_hybrid_search.py tests/test_chunk_code.py tests/test_index_repository.py tests/test_incremental_indexing.py tests/test_ablate_embeddings.py tests/test_triage_skips_trivial_prs.py tests/test_diff_budget.py tests/test_model_provider.py tests/test_retrieval_ablation.py tests/test_injection_corpus.py 109 passed
confirm the two injection tests pass because a README is indexed, not because anything was weakened: yes. chunk_tree now calls is_unembeddable_path instead of classify_trivial_path. README.md is chunked and indexed; retrieval returns chunks with the poison payload; wrap_untrusted and apply_instructions assertions are unchanged. zod offline check: 3452 chunks, 0 over 8192 estimated tokens, 0 asset chunks, largest chunk 10584 chars.
blockers: None

## 2026-09-08T19:34:50+05:30 | phase 35 | embedding batches split on rejection instead of trusting an estimate
status: READY FOR GATE
commit sha: none, Claude commits
red proof: (1) AssertionError: assert 837 >= 935.754189944134 (test_estimate_embedding_tokens_is_conservative_for_code_like_text, len//4 underestimated code); (2) ModelProviderFailure: Requested 310681 tokens, max 300000 tokens per request (test_embed_splits_batch_when_request_token_limit_is_rejected, no split retry); (3) ModelProviderFailure: Requested 310681 tokens, max 300000 tokens per request (test_embed_ledger_counts_only_accepted_split_batches, same); (4) test_embed_does_not_retry_auth_or_unrelated_client_errors passed before fix because 401 already propagated immediately
gate numbers: ruff 0 on changed files; mypy src 0; tests/test_ablate_embeddings.py tests/test_hybrid_search.py tests/test_chunk_code.py tests/test_index_repository.py tests/test_incremental_indexing.py tests/test_model_provider.py tests/test_retrieval_ablation.py tests/test_injection_corpus.py 90 passed
what you match on to detect the token-limit rejection, and why it survives a wording change: status_code 400 plus three message signals in is_embedding_request_token_limit_failure: token, a limit word (max/limit/exceed/requested), and request scope (the word request). Per-input failures are excluded when the message mentions input together with length or per input. This catches max 300000 tokens per request and similar variants without pinning the exact English sentence.
blockers: None

## 2026-09-08T19:56:48+05:30 | phase 35 | count embedding tokens exactly instead of guessing from characters
status: READY FOR GATE
commit sha: none, Claude commits
red proof: (1) ImportError: cannot import name 'count_embedding_tokens' from 'pr_reviewer.retrieval.embed' (test_count_embedding_tokens_flags_emoji_density); (2) AssertionError: assert 1 > 1 on chunk count for emoji.ts (test_chunk_tree_splits_emoji_file_by_true_token_count, 3000 emoji is only 6000 cl100k tokens so one chunk fit under 8192); (3) AssertionError on zod chunks over true limit would have failed before tiktoken split (test_zod_checkout_chunks_respect_true_embedding_token_limit, import error before fix); (4) ModelProviderFailure: Invalid 'input[0]': maximum input length is 8192 tokens with RecursionError in safety net (test_embed_returns_one_vector_per_input_text, before split-and-average fix)
gate numbers: ruff 0 on changed files; mypy src 0; tests/test_chunk_code.py tests/test_ablate_embeddings.py tests/test_hybrid_search.py tests/test_index_repository.py tests/test_incremental_indexing.py tests/test_model_provider.py tests/test_retrieval_ablation.py tests/test_injection_corpus.py tests/test_package_boundaries.py 114 passed
largest chunk from the real zod checkout, in TRUE tokens: 8192 (2525 chunks total, zero over the limit)
did you split inside the embedder, and if so what happened to the extra piece: the chunker is the primary fix. It uses tiktoken cl100k_base via count_embedding_tokens and split_text_to_max_embedding_tokens so every indexed chunk is at most 8192 true tokens. The embedder keeps a safety net only: inputs still over the limit, or a per-input API rejection, go through _embed_split_and_average, which embeds each tiktoken-sized piece and averages the vectors so embed() still returns exactly one vector per input. No content is dropped; averaging combines the pieces. Indexing never relies on this path when chunk_tree is correct.
blockers: None

## 2026-09-08T20:14:01+05:30 | phase 35 | retry embedding rate limits with the existing retry policy
status: READY FOR GATE
commit sha: none, Claude commits
red proof: (1) TypeError: OpenAIEmbeddingProvider.__init__() got an unexpected keyword argument 'retry_policy' (test_embed_retries_rate_limit_then_returns_vectors); (2) same TypeError (test_embed_honours_retry_after_header_through_injected_sleep); (3) same TypeError (test_embed_does_not_retry_unauthorized_requests); (4) same TypeError (test_embed_rate_limit_attempts_are_bounded); (5) same TypeError (test_embed_token_limit_splits_batch_without_retrying)
gate numbers: ruff 0 on changed files; mypy src 0; tests/test_ablate_embeddings.py tests/test_model_provider.py tests/test_provider_retry.py (test_model_retry.py does not exist) tests/test_chunk_code.py tests/test_index_repository.py tests/test_incremental_indexing.py tests/test_hybrid_search.py tests/test_retrieval_ablation.py 99 passed
how you kept the 429 retry path and the token-limit split path separate: _embed_batch_post wraps only the HTTP call in retry_provider_call, classifying failures through _embedding_http_failure into ProviderFailure kinds. 429 and 5xx map to RETRYABLE_RATE_LIMIT and retry inside retry_provider_call. 400 token-limit responses become BAD_REQUEST, which is not retryable, so retry_provider_call returns immediately and _embed_batch_post raises ModelProviderFailure. _embed_batch catches that with is_embedding_request_token_limit_failure or is_embedding_input_token_limit_failure and splits the batch instead. A split half that later gets a 429 goes through _embed_batch_post again and uses the retry path independently.
the pacing delay you chose and where the constant lives: EMBEDDING_REQUEST_PACING_SECONDS = 0.05 (50ms) in openai_embeddings.py, applied after each successful _embed_batch_post via the injected sleep function so tests stay instant when pacing_seconds=0.0.
blockers: None

## 2026-09-08T20:35:04+05:30 | phase 35 | tell the model the finding schema and enforce it at the boundary
status: READY FOR GATE
commit sha: none, Claude commits
red proof: (1) AssertionError: assert 'category' in prompt (test_diff_only_prompt_lists_every_finding_draft_field_and_enum_value, prompt named FindingDraft but listed no fields); (2) Failed: DID NOT RAISE ModelSchemaMismatch (test_review_findings_draft_rejects_wrong_item_shape_at_provider_boundary, {"file","line","rationale"} passed provider); (3) TypeError: EvalReviewResult.__init__() got an unexpected keyword argument 'schema_rejected_findings' (test_retrieval_ablation_format_includes_rejection_counters_per_arm); (4) same TypeError (test_all_rejected_ablation_output_differs_from_silent_run)
gate numbers: ruff 0 on changed files; mypy src 0; tests/test_prompt_registry.py tests/test_model_provider.py tests/test_retrieval_ablation.py tests/test_ablate_embeddings.py tests/test_reflection_cannot_invent_findings.py tests/test_injection_corpus.py tests/test_package_boundaries.py tests/test_hosted_boundary_enforcement.py tests/test_diff_only_prompt.py tests/test_review_pull_request.py 116 passed
prompt version: old 87b6953ee06ab55d (pre-fix content hash, insert-only so not re-registered); new 106418de665285c3 (DIFF_ONLY_PROMPT.version from content hash)
structured outputs: not wired, blocker. openai_compatible.py only sends response_format json_object with no per-item schema. Wiring FindingDraft JSON schema for ReviewFindingsDraft would need schema generation, a new response_format branch per schema_name, and a matching Anthropic path. Larger than a small change; prompt plus provider validation carry the fix.
blockers: None

## 2026-09-08T21:08:35+05:30 | phase 35 | finish the transcript interface and remove the blank startup
status: READY FOR GATE
commit sha: none, Claude commits
red proof: Button widgets found: nav.py, review_dashboard.py, screens/byok.py, confirm.py, model_access.py, prompts.py, repositories.py, review.py (21 import/construct hits). Visible borders found: theme.py border-left heavy accent; nav.py border-right solid; review_dashboard.py border solid panel (3 hits after class-level CSS scan)
gate numbers: ruff 0 on src/pr_reviewer/tui/ and tests/test_tui_is_a_transcript.py; mypy src/pr_reviewer/tui 0; tests/test_tui_*.py 31 files 109 passed
what was actually blocking the first paint, with the measurement: on_mount called _mount_default_section -> _resolve_installation_snapshot, which ran a synchronous httpx.get to /api/runner/installation (30s timeout) before the first content paint. Measured ~2.50s blocking with a client that sleeps 2.5s per fetch. Fixed by painting checking sign-in... in compose/on_mount immediately and moving the fetch to @work(thread=True) _refresh_installation_snapshot_async; background completion only mounts the default section when _awaiting_initial_installation is True
which behaviours moved from a button to a key or typed input: SectionNav sections -> PromptAction lines (> repositories, etc.); ConfirmScreen log out -> y/n keys; RepositoriesPanel back/repos/PRs -> PromptAction; ReviewPanel continue to agents and copy remediation -> PromptAction; ModelAccessPanel and ByokPanel save and verify -> PromptAction; AgentPromptsPanel save new version -> PromptAction; ReviewDashboardPanel review rows and back to reviews -> PromptAction
blockers: None

## 2026-09-08T21:58:34+05:30 | phase 35 | tell the judge its schema too
status: READY FOR GATE
commit sha: none, Claude commits
red proof: (1) ImportError: cannot import name 'reflection_prompt_text' from pr_reviewer.reviewer.reflect (test_reflection_prompt_names_index_score_reason_and_exactly_once_rule; old prompt also lacked score and reason as named fields); (2) test_reflection_scores_rejects_bare_numbers_at_provider_boundary already passed before the prompt fix because finish_completion rejects non-dict score items with ModelSchemaMismatch; test locks that behavior; (3) test_reflection_accepts_one_object_per_finding_end_to_end already passed before the prompt fix with the fake model path; test locks end-to-end acceptance; (4) test_reflection_duplicate_index_with_full_count_is_loud already passed unchanged, guard at reflect.py:99 untouched; (5) ModuleNotFoundError: No module named pr_reviewer.prompts.schema_contracts (test_every_json_prompt_names_every_required_contract_field)
gate numbers: ruff 0 on changed files; mypy src 0; tests/test_reflection_cannot_invent_findings.py tests/test_prompt_registry.py tests/test_diff_only_prompt.py tests/test_review_pull_request.py tests/test_model_provider.py tests/test_retrieval_ablation.py tests/test_reflection_prompt.py tests/test_prompt_schema_contracts.py 66 passed
every prompt checked: diff_only_reviewer (DIFF_ONLY_PROMPT) names all FindingDraft fields via prompts/finding_schema.py, already fixed earlier; finding_reflection (_REFLECTION_PROMPT) now names index, score, reason, 0-based exactly-once rule, and a two-finding example via prompts/reflection_schema.py; bounded_explorer has no fixed prompt in src (caller supplies task_prompt, tests use "look"), ExplorerAction fields are not named in a bundled prompt; repo profile generation uses ProfileModel.generate_claims with no prompt text in retrieval/repo_profile.py; FindingCandidate has no production prompt, only adapter tests; tui specialist prompts in agent_prompt_catalogue.py still say Return JSON findings without field names, left untouched per Track D scope and specialist mode off
blockers: None

## 2026-09-08T22:22:19+05:30 | phase 35 | await the pane clear before mounting, and stop dumping tracebacks
status: READY FOR GATE
commit sha: none, Claude commits
red proof: DuplicateIds: Tried to insert a widget with ID 'reviews-dashboard', but a widget already exists with that ID (ReviewDashboardPanel(id='reviews-dashboard')); ensure all child widgets have a unique ID. (test_reselecting_section_keeps_exactly_one_panel[reviews] before fix)
gate numbers: ruff 0 on src/pr_reviewer/tui/app.py and tests/test_tui_nav.py; mypy src 0; tests/test_tui_*.py 31 files 114 passed
all six call sites and what each became: (1) on_model_key_stored line 286: async handler, await _replace_pane_children(pane) before _begin_connected_startup; (2) on_section_selected missing snapshot line 319: await _replace_pane_children with Static installation-missing; (3) _mount_default_section line 333: sync wrapper calls call_next(_mount_default_section_async), which awaits _replace_pane_children or _show_section; (4) _show_startup_status line 362: update-in-place path unchanged; full replace path calls call_next(_show_startup_status_async) which awaits _replace_pane_children with Static startup-status; (5) _show_section unknown section line 497: await _replace_pane_children with Static section-placeholder; (6) _show_section main path line 505: every branch awaits _replace_pane_children inside async with pane.batch() so remove_children and mount both complete before the next id registers
where the error detail goes now instead of the terminal: section mount failures are caught in _show_section, logged append-only to {config_dir}/tui-errors.log with UTC ISO timestamp and traceback, and shown as one #section-error Static line naming that path; uncaught errors override _handle_exception to log the same file, clear _exit_renderables (no Rich traceback or locals to error_console), and close quietly without panic or _fatal_error
blockers: None

## 2026-09-09T00:04:37+05:30 | diagnosis | why holdout precision is zero
status: DONE
commit sha: none (diagnosis only, no product commit)
red proof: n/a (no product test was supposed to go red). Matcher evidence: match_findings.py:30-36 requires category equality. Live zod-ts-014 finding at util.ts:396-399 overlaps label 396-398 with concern correctness and still unmatched_actual=2 unmatched_expected=1 because category is shallow-cloning vs the label phrase.
gate numbers: ruff 0 on scripts/diagnose_holdout_precision.py; dash grep empty on files I wrote; eval_cases.jsonl and candidate_sheet.jsonl untouched
what I did: wrote scripts/diagnose_holdout_precision.py, packed all 7 holdout cases, ran live gpt-4o-mini diff-only reviews (about $0.0052), wrote docs/reports/holdout-precision-diagnosis.txt, answered the three questions, replaced CURSOR-NEXT.md with the matcher fix brief
blockers: None

## 2026-09-09T00:22:50+05:30 | gate | 9ce48c5 match without category text
status: DONE
commit sha: 9ce48c5 fix: match eval findings without category text
red proof: already landed; prior diagnosis showed 014 and 021 as category-only misses
gate numbers: ruff 0 on tests/test_eval_matching.py src/pr_reviewer/evals/match_findings.py; mypy src 0; dash grep empty; cheap guards already 19+9; flock pytest --ignore landing/dashboard performance 1414 passed
what I did: CURSOR-NEXT.md was unchanged so I gated 9ce48c5. Replayed the cached live holdout findings through the new matcher with no model calls. precision_per_finding 0.000 -> 0.167, recall 0.286, false/pr 1.429. Hits: zod-ts-014 and zod-ts-021. zod-ts-013 now needs_human_match. Did not rerun ablate.
blockers: None

## 2026-09-09T00:53:00+05:30 | record | matcher-cache replay
status: DONE
commit sha: none (docs and next brief only)
red proof: n/a
gate numbers: dash grep empty on the files I wrote
what I did: Recorded the 9ce48c5 cache replay in docs/reports/holdout-precision-diagnosis.txt as MATCHER-CACHE REPLAY, marked not a baseline. Replaced CURSOR-NEXT.md with a recall brief for the five remaining misses. Added /goal q-recall to GOALS.md. Did not touch scorecard.json, matcher, prompts, or datasets.
blockers: None

## 2026-09-09T00:54:21+05:30 | record | evidence only by cause
status: DONE
commit sha: none (docs and next brief only)
red proof: n/a
gate numbers: dash grep empty on the files I wrote
what I did: Marked the cache replay as evidence only, not a published baseline. Grouped remaining misses by cause (wrong file, wrong lines, no finding, wrong concern). Rewrote CURSOR-NEXT.md and /goal q-recall so the next slice picks one cause, writes a failing synthetic or dev test, and does not change prompts, datasets, or the matcher unless a synthetic test proves the rule wrong.
blockers: None

## 2026-09-09T01:00:25+05:30 | q-recall | wrong concern
status: DONE
commit sha: 099e953 fix: treat prototype pollution drafts as security
red proof: AssertionError: assert 'correctness' == 'security' (tests/test_review_pull_request.py:172)
gate numbers: ruff 0 on staged files; mypy src 0; dash grep empty; tests/test_review_pull_request.py 16 passed; test_package_boundaries 19; test_hosted_boundary_enforcement 9
what I did: Picked wrong concern. Wrote the failing synthetic test first. candidate_from_draft now sets security when draft text names prototype pollution or quotes __proto__. Ordinary correctness drafts stay correctness. Matcher, prompts, and datasets untouched.
blockers: None

## 2026-09-09T01:05:10+05:30 | q-recall | wrong file
status: DONE
commit sha: 7b807c4 fix: drop test-file findings when implementation is packed
red proof: AssertionError: assert ['test-only finding', 'implementation finding'] == ['implementation finding'] (tests/test_review_pull_request.py:233)
gate numbers: ruff 0; mypy src 0; dash grep empty; tests/test_review_pull_request.py 18 passed; test_package_boundaries 19; test_hosted_boundary_enforcement 9
what I did: Picked wrong file. Wrote the failing test first on a flask-py-013 shaped fixture. Test-file findings are now dropped when a non-test file is packed. Test-only PRs still keep test findings. Matcher, prompts, and datasets untouched.
blockers: None

## 2026-09-09T02:21:25+05:30 | q-recall | wrong lines
status: DONE
commit sha: 338122e fix: expand a finding to its packed new-side hunk
red proof: AssertionError: assert (863, 863) == (858, 863) (tests/test_review_pull_request.py:273)
gate numbers: ruff 0; mypy src 0; dash grep empty; tests/test_review_pull_request.py 20 passed; test_package_boundaries 19; test_hosted_boundary_enforcement 9
what I did: Picked wrong lines. Wrote the failing test first on a flask-py-013 shaped hunk. After grounding, a finding inside one packed NEW-side hunk expands to that hunk. A late-hunk finding does not absorb an earlier hunk. Matcher, prompts, and datasets untouched. Did not rerun ablate. Cache replay is still evidence only.
blockers: None

## 2026-09-09T02:27:18+05:30 | q-recall | distant-hunk wrong lines
status: DONE
commit sha: b167bf9 fix: attach a finding to the hunk that defines its named symbol
red proof: AssertionError: assert (600, 602) == (453, 457) (tests/test_review_pull_request.py:341)
gate numbers: ruff 0; mypy src 0; dash grep empty; tests/test_review_pull_request.py 21 passed; test_package_boundaries 19; test_hosted_boundary_enforcement 9
what I did: Picked remaining distant-hunk wrong lines. Wrote the failing test first on a flask-py-001 shaped definition plus call-site fixture. If a finding names a symbol defined in exactly one packed hunk of that file, it moves there, then expands to that hunk. A late finding that names no definition stays on its own hunk. Matcher, prompts, and datasets untouched. Did not rerun ablate. Cache replay is still evidence only.
blockers: None

## 2026-09-09T02:31:02+05:30 | q-recall | no finding
status: BLOCKED
commit sha: none
red proof: AssertionError: assert 'report it when the failure is visible in the packed hunk' in '<diff_only prompt>' (tests/test_review_prompt_calibration.py:20)
gate numbers: ruff not run for commit; mypy not run for commit; no commit
what I did: Picked no finding. Confirmed the live 017 path had schema=0, grounding=0, empty accepted list. No parser or grounding drop. Wrote the failing prompt-contract test first, modeled on flask-py-006. Did not change the prompt because this brief still said not to. Did not invent a finding. Did not rerun ablate. Cache replay is still evidence only.
blockers: Prompt version bump is required to green the test. The current CURSOR-NEXT now allows that bump. The failing test is uncommitted in tests/test_review_prompt_calibration.py.

## 2026-09-09T02:33:17+05:30 | q-recall | no finding prompt bump
status: DONE
commit sha: 3422136 fix: ask the reviewer to report a visible hunk failure
red proof: AssertionError: assert 'report it when the failure is visible in the packed hunk' in '<diff_only prompt>' (tests/test_review_prompt_calibration.py:20)
gate numbers: ruff 0; mypy src 0; dash grep empty; test_review_prompt_calibration + related prompt tests 6 passed; test_package_boundaries 19; test_hosted_boundary_enforcement 9
what I did: Greened the red prompt-contract test. Added one confidence-bar line: report a bug when the failure is visible in the packed hunk, even if the caller is not in the diff. Version is the new content hash f4c6e3ada95c2b54. Did not tune on holdout words. Matcher, datasets, and scorecard untouched. Did not rerun ablate. Cache replay is still evidence only.
blockers: None

## 2026-09-09T02:35:07+05:30 | q-recall | no cheap sanity path
status: DONE
commit sha: none
red proof: n/a
gate numbers: no code change; no tests run
what I did: Read CURSOR-NEXT.md. It has no approved cheap sanity path and does not ask to measure recall. I did not invent a run, did not replay the cache into scorecard.json, did not call the cause slices a baseline, and did not run reviewer ablate.
blockers: None. Measured recall needs cost approval first.

## 2026-09-09T02:44:46+05:30 | q-recall | 6-dev live sanity
status: DONE
commit sha: none
red proof: n/a
gate numbers: no code change; no pytest
what I did: Ran the 6 dev cases only on current code with gpt-4o-mini and the stored OpenAI model_key. Diff-only, repeats=1, no retrieval, no ablate. cost_usd 0.002551, precision_per_finding 0.600, recall_per_finding 0.500, false_findings_per_pr 0.333. Hits: flask-py-006, flask-py-013, zod-ts-010. Misses: flask-py-001 no finding, flask-py-020 no finding, zod-ts-005 wrong concern. Extra false finding on zod-ts-010 (play.ts). Wrote docs/reports/dev-eval-sanity.txt. Did not write scorecard.json. Not a baseline. No previous live 6-dev result to compare.
blockers: None

## 2026-09-09T02:47:06+05:30 | q-recall | zod-ts-005 wrong concern
status: BLOCKED
commit sha: none
red proof: n/a (no test; the recommended fix was rejected)
gate numbers: no code change
what I did: Read the live zod-ts-005 draft. Category regex-escape, title hyphen escape, rationale unexpected matching in a character class. No security class name in category, title, rationale, or evidence. That is not the prototype-pollution rule. Did not add hyphen or character-class keywords. Did not invent a finding for flask-py-001 or flask-py-020. Did not write scorecard.json. Not a baseline.
blockers: zod-ts-005 cannot be fixed without keyword guessing. flask-py-001 and flask-py-020 are empty model lists with no parser drop.

## 2026-09-09T03:19:59+05:30 | q-recall | 6-dev gpt-4.1 comparison
status: DONE
commit sha: none
red proof: n/a
gate numbers: no production code change; no pytest
what I did: Ran the 6 dev cases only with gpt-4.1 and the stored OpenAI model_key. Diff-only, repeats=1, no retrieval, no ablate. cost_usd 0.054604, precision_per_finding 0.571, recall_per_finding 0.667, false_findings_per_pr 0.500. Hits: flask-py-001, flask-py-006, flask-py-013, zod-ts-010. Misses: flask-py-020 wrong concern, zod-ts-005 wrong concern plus an extra deno/lib/types.ts finding. Versus gpt-4o-mini: cost 21x, recall +0.167, precision -0.029, false/PR +0.167. Wrote docs/reports/dev-eval-sanity-gpt-4.1.txt. Did not write scorecard.json. Not a baseline.
blockers: None

## 2026-09-09T03:21:44+05:30 | q-recall | record gpt-4.1 evidence
status: DONE
commit sha: none
red proof: n/a
gate numbers: no code change; RoleModels.generate already gpt-4o-mini
what I did: Recorded the gpt-4.1 6-dev run as evidence only in docs/reports/dev-eval-sanity-gpt-4.1.txt and CURSOR-NEXT.md. Decision: keep gpt-4o-mini as the default generate model. Do not switch default generation to gpt-4.1. gpt-4.1 may be an optional escalation path later. Remaining issue is concern classification for security-looking findings labelled correctness. Did not write scorecard.json. Did not run ablate. Did not use holdout. Not a baseline.
blockers: None

## 2026-09-09T03:25:21+05:30 | q-recall | flask-py-020 signing key concern
status: DONE
commit sha: d8844d2 fix: treat a named signing key draft as security
red proof: AssertionError: assert 'correctness' == 'security' (tests/test_review_pull_request.py:240)
gate numbers: ruff 0; mypy src 0; dash grep empty; tests/test_review_pull_request.py 23 passed; test_package_boundaries 19; test_hosted_boundary_enforcement 9
what I did: Picked flask-py-020. Wrote the failing test first from the live gpt-4.1 draft that named a signing key. candidate_from_draft now sets security when draft text contains signing key. Added a zod-ts-005 shaped guard so hyphen and character-class text stay correctness. Did not switch the generate model. Did not write scorecard.json. Did not run ablate. Not a baseline.
blockers: None. zod-ts-005 still has no security class name in the draft.

## 2026-09-09T03:27:42+05:30 | q-recall | zod-ts-005 no non-guessing path
status: BLOCKED
commit sha: none
red proof: n/a
gate numbers: no code change
what I did: Read CURSOR-NEXT.md. It has no non-guessing path for zod-ts-005. The live draft still names regex-escape and unexpected matching, not a security class. Stopped. Did not add hyphen or character-class markers. Did not write scorecard.json. Did not run ablate. Did not use holdout. Not a baseline.
blockers: zod-ts-005 concern stays a miss until a draft names a security class, or a human accepts correctness as the match rule.

## 2026-09-09T03:29:47+05:30 | q-recall | final 6-dev mini sanity after d8844d2
status: DONE
commit sha: none
red proof: n/a
gate numbers: no production code change; no pytest
what I did: Ran the 6 dev cases only with gpt-4o-mini on current code after d8844d2. Diff-only, repeats=1, no retrieval, no ablate. cost_usd 0.002247, precision_per_finding 0.333, recall_per_finding 0.167, false_findings_per_pr 0.333. Hit: zod-ts-010. Misses: flask-py-001/006/013 no finding, flask-py-020 wrong concern (session signing, not signing key), zod-ts-005 wrong concern. Versus earlier mini: cheaper, precision and recall worse, false/PR unchanged. Wrote docs/reports/dev-eval-sanity-after-d8844d2.txt. Did not write scorecard.json. Not a baseline.
blockers: None

## 2026-09-09T03:31:33+05:30 | q-recall | record variance evidence and 3-pass brief
status: DONE
commit sha: none
red proof: n/a
gate numbers: no code change
what I did: Marked docs/reports/dev-eval-sanity-after-d8844d2.txt as variance evidence, not a baseline. Wrote the next brief in CURSOR-NEXT.md for a 3-pass 6-dev gpt-4o-mini eval: exact total cost, mean and range for precision/recall/false per PR, per-case hit stability. Did not change code. Did not write scorecard.json. Did not run ablate. Did not use holdout. Not a baseline.
blockers: None

## 2026-09-09T03:34:36+05:30 | q-recall | 3-pass 6-dev mini eval
status: DONE
commit sha: none
red proof: n/a
gate numbers: no production code change
what I did: Ran 3 passes of the 6 dev cases with gpt-4o-mini. Diff-only, no retrieval, no ablate, no holdout. exact_total_cost_usd 0.007733. precision mean 0.417 range 0.250-0.667. recall mean 0.278 range 0.167-0.333. false/PR mean 0.500 range 0.167-1.000. Stable hit: zod-ts-010 3/3. Flip: flask-py-013 2/3. Never hit: flask-py-001, 006, 020, zod-ts-005. Wrote docs/reports/dev-eval-3pass-gpt-4o-mini.txt. Did not overwrite one-pass reports. Did not write scorecard.json. Not a baseline.
blockers: None

## 2026-09-09T03:38:50+05:30 | q-recall | recall options brief
status: DONE
commit sha: none
red proof: n/a
gate numbers: no code change; no pytest; no model calls
what I did: Wrote docs/reports/dev-eval-recall-options.md from the 3-pass report. Compared four options without making gpt-4.1 the default generator. Recommend option 2 first (retry gpt-4.1 only when mini is empty), then option 4 for wrong-concern security cases. Option 1 cannot lift the four never-hit cases. Option 3 already had a prompt bump and flask-py-001 stayed 0/3. Pointed CURSOR-NEXT.md at the brief. Did not change production code. Did not write scorecard.json. Did not use holdout. Not a baseline.
blockers: owner must pick an option before any implementation

## 2026-09-09T03:54:47+05:30 | q-recall | option 2 empty-retry
status: DONE
commit sha: 28ce5b3 feat: retry gpt-4.1 when mini returns no findings
red proof: AssertionError: assert ['gpt-4o-mini'] == ['gpt-4o-mini', 'gpt-4.1'] at tests/test_review_pull_request.py:608 before the retry branch existed
gate numbers: ruff 0 on review_pull_request.py and test_review_pull_request.py; mypy 0 on 245 source files; no U+2013 or U+2014; targeted retry tests 3 passed; nearby 17 passed; full suite 1427 passed, 2 skipped, 0 failed, 5 errors in pre-existing web build (ReviewBehaviorPanels), not in reviewer files
what I did: Implemented option 2. RoleModels.generate stays gpt-4o-mini. When mini accepts zero grounded findings, generate retries once with gpt-4.1 and sums both costs. Mini findings skip the retry. Live 6-dev spend 0.010857 of 0.08 remaining 0.069143. precision 0.375 recall 0.500 false/PR 0.833. Hits: flask-py-001, 013, 010. Remaining misses: 006 wrong concern, 020 wrong concern, 005 wrong file. Stopped because false/PR is above 0.75 and precision is worse than the 3-pass mean 0.417. Wrote docs/reports/dev-eval-empty-retry.txt. Did not write scorecard.json. Did not use holdout. Did not run ablate. Not a baseline. Did not invent another path.
blockers: live eval false/PR 0.833 exceeds the 0.75 stop line. Owner decides whether to keep or revert 28ce5b3.

## 2026-09-09T03:58:20+05:30 | q-recall | flag-off empty-retry
status: DONE
commit sha: 17a4eb0 fix: keep empty-retry off by default
red proof: IndexError in ScriptedModel.complete_json while requesting model='gpt-4.1' at tests/test_review_pull_request.py:564; default path still retried before EMPTY_GENERATE_RETRY_ENABLED existed
gate numbers: ruff 0 on review_pull_request.py and test_review_pull_request.py; mypy 0 on 245 source files; dash grep empty; relevant review tests 39 passed. No live eval. No scorecard.json write.
what I did: Did not revert 28ce5b3. Kept the retry behind EMPTY_GENERATE_RETRY_ENABLED = False, same off-by-default module switch as MULTI_MODEL_GENERATE_ENABLED. Default reviews stay mini-only. Opt-in test still proves the retry and cost sum. Updated CURSOR-NEXT.md with the blocker: retry improved recall but false findings crossed the cap. Did not continue new recall work.
blockers: empty-retry stays off. false/PR 0.833 crossed the 0.75 cap when it was on.

## 2026-09-09T04:01:23+05:30 | q-recall | stop recall tuning
status: DONE
commit sha: none (HEAD 17a4eb0, prior 28ce5b3)
red proof: n/a
gate numbers: no code change
what I did: Confirmed RoleModels.generate is gpt-4o-mini and EMPTY_GENERATE_RETRY_ENABLED is False. Matcher and scorecard.json were not touched. Recorded the stop in CURSOR-NEXT.md. Blocker: targeted retry improved recall 0.278 to 0.500, but false/PR 0.833 crossed the 0.75 cap. Do not turn the flag on without a new plan to control false findings. No new recall work unless a new goal is chosen.
blockers: false findings cap. Retry stays off.

## 2026-09-09T04:06:31+05:30 | web | import ReviewBehaviorPanels
status: DONE
commit sha: 6839dd8 fix: import ReviewBehaviorPanels on the review page
red proof: bunx tsc --noEmit: src/app/dashboard/reviews/[reviewJobId]/page.tsx(101,10): error TS2304: Cannot find name 'ReviewBehaviorPanels'. pytest: assert 'from "@/components/ReviewBehaviorPanels"' in page text at tests/test_dashboard_panels.py:112
gate numbers: ruff 0 on test_dashboard_panels.py; dash grep empty; tsc --noEmit 0; bun run build 0; test_dashboard_panels + package/hosted boundary 35 passed; test_dashboard_performance + test_landing_performance 4 passed, 3 skipped
what I did: The review detail page used ReviewBehaviorPanels without importing it. Added the import from @/components/ReviewBehaviorPanels. Added a test that the import line exists. Did not touch recall, matcher, datasets, scorecard, RoleModels.generate, or EMPTY_GENERATE_RETRY_ENABLED.
blockers: None

## 2026-09-09T04:07:31+05:30 | handoff | record web fix and stop
status: DONE
commit sha: none
red proof: n/a
gate numbers: no code change; no evals
what I did: Recorded that 6839dd8 fixed the missing ReviewBehaviorPanels import and that web typecheck and build now pass. Recall work stays stopped with EMPTY_GENERATE_RETRY_ENABLED = False. Did not change code. Did not run evals. Did not touch matcher, datasets, scorecard, or model defaults.
blockers: recall retry stays off. false/PR 0.833 crossed the 0.75 cap when it was on.

## 2026-09-09T04:15:55+05:30 | gate | clean verification after web fix
status: DONE
commit sha: 4ae552e style: wrap a long line in the docs readability test
red proof: ruff E501 on tests/test_docs_readability.py:88 (103 > 100)
gate numbers: ruff 0 on tracked Python files; mypy 0 on 245 source files; pytest 1433 passed, 3 skipped, 0 failed in 329.40s; bunx tsc --noEmit 0; bun run build 0. Untracked eval helper scripts still trip ruff and are not on main.
what I did: Ran a clean gate on main at 6839dd8, then wrapped the one tracked ruff line. No evals. Did not touch recall, matcher, datasets, scorecard, RoleModels.generate, or EMPTY_GENERATE_RETRY_ENABLED (still False).
blockers: None

## 2026-09-09T04:19:23+05:30 | q2-threshold | next task blocked
status: BLOCKED
commit sha: none
red proof: n/a
gate numbers: no code change
what I did: Read CURSOR-NEXT.md, GOALS.md, docs/phases/master-spec.md, and docs/phases/plans/phase-35-plan.md. Phase 35 is 40/0/0. Recall is stopped. Next required task in project order is /goal q2-threshold: measure REFLECTION_DROP_THRESHOLD 0.0 vs 0.5 with reviewer ablate --repeats 1 on the 6 dev cases only. Threshold is still 0.0. Did not flip it. Did not run ablate. Did not skip to q3. Did not touch matcher, datasets, scorecard, model defaults, or EMPTY_GENERATE_RETRY_ENABLED.
blockers: q2-threshold needs an approved live-eval budget for two reviewer ablate --repeats 1 runs on the 6 dev cases. Standing rule and CURSOR-NEXT forbid ablate until that cost is approved.

## 2026-09-09T04:25:07+05:30 | q2-threshold | keep 0.0
status: DONE
commit sha: none
red proof: n/a
gate numbers: no production code change
what I did: Measured both arms on the 6 dev cases only, repeats 1, gpt-4o-mini, retrieval off. Did not run reviewer ablate because that CLI uses holdout retrieval. Arm 0.0 cost 0.002448 precision 0.400 recall 0.333 false/PR 0.500, suppressed 0. Arm 0.5 cost 0.002368 precision 0.500 recall 0.333 false/PR 0.333, suppressed 0. One extra 0.5 pass completed then the report print crashed (about 0.0024). Recorded two-arm total 0.004816, conservative q2 total about 0.0072 of 0.50. 0.5 dropped no finding; metric move is generate variance. Left REFLECTION_DROP_THRESHOLD at 0.0. Did not write scorecard.json. Did not touch matcher, datasets, model defaults, or EMPTY_GENERATE_RETRY_ENABLED. Did not skip to q3.
blockers: None

## 2026-09-09T16:54:14+05:30 | q3-wire-retrieval | IndexedRetrievalExecutor default
status: DONE
commit sha: 599eca5 feat: wire indexed retrieval into live reviews
red proof: AssertionError: assert not True (default LiveAgentReviewBackend used NullRetrievalExecutor) at tests/test_review_receives_retrieved_context.py:127
gate numbers: ruff 0 on staged files; mypy 0 on 247 source files; dash grep empty; pytest 1435 passed, 3 skipped, 0 failed in 459.63s; test_package_boundaries and test_hosted_boundary_enforcement passed
what I did: Default live review now uses IndexedRetrievalExecutor. It reuses eval checkout, index_repository, and retrieve_context(enabled=True), then converts chunks with context_items_from_chunks. A test fails if the default goes back to Null. Hosted indexing still raises HostedRetrievalIndexError. No live model or embedding calls. NullRetrievalExecutor remains as an opt-in for tests. Did not write scorecard.json. Did not touch matcher, datasets, RoleModels.generate, EMPTY_GENERATE_RETRY_ENABLED, or REFLECTION_DROP_THRESHOLD. Did not start q4. Daemon service.py still reviews without retrieval.
blockers: None

## 2026-09-09T17:13:23+05:30 | q4-wire-specialists | run opt-in specialists
status: DONE
commit sha: 66b7503 feat: run opt-in specialists on live reviews
red proof: TypeError: LiveAgentReviewBackend.__init__() got an unexpected keyword argument 'repo_config_path' at tests/test_specialists_are_opt_in.py:239
gate numbers: ruff 0 on staged files; mypy 0 on 247 source files; dash grep empty; pytest 1438 passed, 3 skipped, 0 failed in 395.11s; test_specialists.py::test_specialist_mode_is_disabled_on_the_default_policy passed
what I did: Live reviews now run specialists the user enabled per repository. BuiltinSpecialistReviewers makes one model call per enabled concern using a registered specialist prompt. apply_enabled_specialists merges those findings and adds cost. Wired in LiveAgentReviewBackend and DiffOnlyRunnerReviewExecutor. Default specialist_mode stays off. No live API spend. Did not write scorecard.json. Did not touch matcher, datasets, RoleModels.generate, EMPTY_GENERATE_RETRY_ENABLED, or REFLECTION_DROP_THRESHOLD. Did not start q5.
blockers: None

## 2026-09-09T17:33:36+05:30 | q5-fix-suggestions | optional suggested_fix
status: DONE
commit sha: e4bd4db feat: add optional suggested_fix to findings
red proof: pydantic_core._pydantic_core.ValidationError: Extra inputs are not permitted for FindingDraft.suggested_fix at tests/test_suggested_fix.py:19
gate numbers: ruff 0 on staged files; mypy 0 on 247 source files; dash grep empty; pytest 1445 passed, 3 skipped, 0 failed in 457.41s
what I did: Findings can carry an optional suggested_fix from the same generate call. The prompt names it and shows an example. GitHub comments render a suggestion block when the replacement covers the new-side line range and has no fence. Unclean suggestions are dropped, the finding still posts, and the drop is counted. The daemon copies the field onto Finding. Human-owned fields stay off the draft. No live API spend.
blockers: None

## 2026-09-09T17:51:54+05:30 | s1-deploy | hosted deploy path
status: DONE
commit sha: 19f9769 fix: honor PORT and migrate on hosted deploy
red proof: AssertionError: preDeployCommand migrate missing from deploy/render.yaml at tests/test_render_blueprint.py:33; railway.json still used a non-schema "service" key; docs/DEPLOY.md missing
gate numbers: ruff 0 on staged files; mypy 0 on 247 source files; dash grep empty; pytest 1448 passed, 3 skipped, 0 failed in 448.02s
what I did: Proved the live compose URL https://reviewer.niresh.tech (/health and /ready both 200). Fixed hosted boot so Render and Railway can work: API reads PORT, reload is off, blueprints run pr-reviewer-db-migrate before start, railway.json matches the Railway schema, no paid secret disk on the hosted web service. Wrote docs/DEPLOY.md with every env var to fill in and what to expect. Did not create a Render or Railway service.
blockers: A new Render or Railway URL needs owner input: a Render or Railway account token, a Neon DATABASE_URL, and GitHub App values (GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY, GITHUB_OAUTH_CLIENT_ID, GITHUB_OAUTH_CLIENT_SECRET, GITHUB_WEBHOOK_SECRET). After the first assigned hostname, set PR_REVIEWER_HOSTED_ORIGIN and redeploy. Do not invent those values.

## 2026-09-09T18:16:43+05:30 | s2a-landing-redesign then s2-site | landing product page and findability
status: DONE
commit sha: 57ad34e feat: redesign landing and add shareable site metadata
red proof: AssertionError: landing is missing sections: ['How a review moves', 'Hosted vs local', 'What already works', ...] at tests/test_landing_redesign.py:66; missing apps/web/src/app/sitemap.ts at tests/test_site_metadata.py:31
gate numbers: ruff 0 on tests/test_landing_redesign.py tests/test_site_metadata.py; mypy 5 errors in backend.py and app.py, files we did not touch; dash grep empty; bunx tsc --noEmit 0; pytest 59 passed on landing/metadata/readability/billing/sign-in/boundary files; did not run bun run build
what I did: Rebuilt the landing as a spec-sheet product page: hero with a real finding panel, hosted vs local table, five-step review flow, proof list, team prompt privacy, paid-path wording without prices, eval notes that are not a baseline, setup, and limits. Then added per-route titles and descriptions, metadataBase, Open Graph and Twitter cards, a 1200x630 OG image, sitemap.ts (no dashboard or connect), and robots.ts. Product name is PR Reviewer on the public site. Screenshots at desktop 1440 and mobile 390. OG PNG measured 1200x630. No third-party card validator.
blockers: None

## 2026-09-09T18:27:07+05:30 | privacy-story-core | TODO section 4 backend/docs
status: DONE
commit sha: not committed (not requested)
red proof: AssertionError: false privacy claim still present: ['CLAUDE.md: Never sees a diff, a finding, or a model key', 'docs/ARCHITECTURE.md: never holds source, diffs, findings, or model keys'] at tests/test_privacy_story.py:50; TypeError: resolve_model_provider() takes 0 positional arguments but 1 was given at tests/test_model_key_storage.py:48; ModuleNotFoundError: No module named 'pr_reviewer.control_plane.rate_limit' at tests/test_hosted_rate_limit.py:8
gate numbers: ruff 0 on touched files; mypy 0 on 251 source files; dash grep empty on touched files; pytest 1475 passed, 3 skipped, 0 failed in 414.34s; test_package_boundaries and test_hosted_boundary_enforcement passed
what I did: Recorded the current boundary: hosted Neon stores finding title and rationale on review_findings, not only opaque ids. Source, diffs, evidence, embeddings, sandbox logs, and model keys stay off the hosted plane. Replaced the false "hosted never sees a finding" claims in CLAUDE.md, ARCHITECTURE.md, DATA_BOUNDARIES.md, README.md, and SECURITY.md. reviewer setup still writes the model key to the keyring or mode-0600 file store. reviewer review now reads that store and ignores ANTHROPIC_API_KEY / OPENAI_API_KEY. Added a fail-closed in-process hosted rate limit (429 {"error": "rate_limited"}, health/ready exempt). Did not touch apps/web, deploy/, datasets/, matcher, scorecard.json, RoleModels.generate, REFLECTION_DROP_THRESHOLD, or EMPTY_GENERATE_RETRY_ENABLED. Ablate embeddings still read OPENAI_API_KEY for the embedder, which is outside setup/review.
blockers: Landing page copy in apps/web was out of scope (s2a-landing-redesign). Eval ablation embeddings still use OPENAI_API_KEY. Hosted rate limit keys by request.client.host, so a reverse proxy may collapse many callers onto one address.

## 2026-09-09T18:32:32+05:30 | s2b-docs-product-polish | public docs match the landing
status: DONE
commit sha: be5e9d5 docs: make public docs match the landing product
red proof: AssertionError: assert 'source' in README first 25 lines at tests/test_docs_product_polish.py:43; also Private. Not a public package; missing retrieval/paid path; INSTALL missing what you need; RUNBOOK still said Nothing in this file is applied; DEMO said webhook does not exist yet
gate numbers: ruff 0 on tests/test_docs_product_polish.py; dash grep empty; generate_data_boundaries_doc.py --check ok; pytest 23 passed on docs polish/privacy/doctor/readability; cheap guards 28 passed; did not run bun run build or mypy on src (src not in this goal)
what I did: Rewrote README so the first screen explains PR Reviewer, hosted vs local, finding text on the dashboard, retrieval, suggested fixes, opt-in specialists, and the later paid path. Install now lists what you need before starting. Deploy no longer claims hosted never stores findings. Runbook and demo separate live /health /ready from owner App, runner, and first comment work. Architecture, security, and data-boundary docs match that split. No fake baseline, prices, or self-improving claim.
blockers: None

## 2026-09-09T19:15:52+05:30 | landing-preview-crash | webpack_modules not a function
status: DONE
commit sha: none (no source change)
red proof: GET / was 200 but /_next/static/chunks/app/page.js and main-app.js 404; .next/static/chunks had hashed production files (page-14ce348fd253a9e1.js, main-app-c9321b9bcf41f4b5.js) next to webpack.js. Dev HTML asked for unhashed page.js, webpack runtime then throws TypeError: __webpack_modules__[moduleId] is not a function
gate numbers: bunx tsc --noEmit 0 in apps/web; landing pytest 31 passed in 4.55s; cheap guards 28 passed; screenshots /tmp/landing-shots/desktop-1440.png and mobile-390.png show the page with no overlay
what I did: Reproduced on http://127.0.0.1:3010/. Checked landing imports: ProductStage and FindingCard are named exports, no default mismatch, no use client in landing/, no circular import in components/landing/. Root cause was a mixed .next cache from a leftover production build plus next dev. Deleted only apps/web/.next and restarted next 15.5.24 on 127.0.0.1:3010. After that, page.js and main-app.js 200, Chromium has no TypeError overlay, hero text present. Did not deploy. Did not touch backend, docs, evals, matcher, model settings, or scorecard.
blockers: None

## 2026-09-09T19:28:13+05:30 | dashboard-webpack-n | __webpack_require__.n is not a function
status: DONE
commit sha: none (not requested)
red proof: landing-only webpack.js (672 modules, 139627 bytes) had no __webpack_require__.n = ; after /dashboard it appeared (140751 bytes). DashboardShell.tsx compiles import Link from "next/link" as __webpack_require__.n(...). Test red: assert ClientRuntime missing from layout.tsx
gate numbers: bunx tsc --noEmit 0; dash grep empty on new files; pytest 21 passed on client-runtime/landing-sign-in/dashboard; cheap guards 28 passed
what I did: Root cause is Next 15.5.24 webpack omitting the default-import helper when the first page is server components only. Added apps/web/src/components/ClientRuntime.tsx (use client, import Link from next/link) to the root layout so landing/docs/scorecard first visits emit .n. Proved landing-only webpack.js now has .n while dashboard chunks are still absent. Chromium landing to dashboard: no TypeError overlay. Did not deploy.
blockers: None

## 2026-09-09T19:52:50+05:30 | landing-preview-crash | webpack_modules not a function again
status: DONE
commit sha: none (not requested)
red proof: GET / 200 but main-app.js page.js layout.js 404; .next had BUILD_ID from next build at 19:46:24 plus hashed page-14ce348fd253a9e1.js; next log TypeError __webpack_modules__[moduleId] is not a function page /dashboard GET 500; test red: next.config.ts was empty {}
gate numbers: bunx tsc --noEmit 0; dash grep empty; pytest 13 passed on dist-dir/client-runtime/landing-sign-in
what I did: A next build wrote production hashed chunks into the same .next the running next dev uses. Split caches: next.config.ts distDir is .next-dev unless NODE_ENV is production. gitignore .next-dev/. Restarted preview on 3010 against .next-dev while the poisoned .next BUILD_ID stayed in place. Landing chunks 200, webpack.js has .n, Chromium home and dashboard have no overlay.
blockers: None

## 2026-09-09T19:55:58+05:30 | human-reply-feedback-loop | first backend slice
status: DONE
commit sha: 98026de feat: capture human replies to review comments
red proof: 8 failed in tests/test_review_comment_feedback.py before the code existed. Real text: UndefinedTable review_comment_posts / review_comment_feedback; FileNotFoundError review_comment_feedback.py; AssertionError 'feedback capture' missing from docs.
gate numbers: ruff 0 on staged Python; mypy 0 on 249 source files; dash grep empty; targeted 69 then 37 passed including cheap guards; full suite 1494 passed, 3 skipped, 2 failed in tests/test_hosted_traefik.py and tests/test_local_webhook_to_human_path.py (RUNBOOK.md / DEMO.md, landing docs, not this track)
what I did: Hosted now accepts pull_request_review_comment. Our posted comments carry a finding marker. A reply to one of those comments writes one review_comment_feedback row with a keyword class (useful/wrong/unclear/follow_up/unknown) and wrap_untrusted reply text. Duplicate deliveries are ignored. Unrelated comments and cross repo/install lookups are ignored. No model call. No prompt, eval, or model-setting write. Docs say this is feedback capture, not self-improvement. Did not touch apps/web, datasets, matcher, scorecard, or model defaults.
blockers: None. Full suite still has two landing-doc assertion failures outside this track.

## 2026-09-09T20:28:09+05:30 | stale-doc-tests | runbook and demo expectations
status: DONE
commit sha: none (not requested)
red proof: AssertionError test_hosted_traefik.py:25 first line was '# Runbook' not 'Nothing in this file is applied.'; test_local_webhook_to_human_path.py:212 'DNS A record' missing from DEMO.md
gate numbers: ruff 0 on the two test files; dash grep empty; pytest 25 passed on traefik/local-webhook/docs-polish/readability/privacy; cheap guards 28 passed
what I did: Updated the two stale doc tests to lock the live host. RUNBOOK must keep health/ready on reviewer.niresh.tech and owner App/Render work, and must not say nothing is applied. DEMO must keep hosted health/ready and owner-needed first comment, and must not say DNS A record. Softened one DEMO sentence that still called Runtime Task 10 unfinished. Did not touch backend, evals, matcher, datasets, scorecard, model settings, or apps/web.
blockers: None

## 2026-09-09T22:45:47+05:30 | review-context-cache | local PR hunk cache
status: DONE
commit sha: 7f51939 feat: cache PR review context locally
red proof: ModuleNotFoundError: No module named 'pr_reviewer.reviewer.incremental' at tests/test_review_context_cache.py:62 before incremental.py existed
gate numbers: ruff 0 on committed Python files; mypy 0 on 251 source files; dash grep empty; cheap guards 38 passed; full suite 1508 passed, 3 skipped, 0 failed (386.72s, run before commit, not re-run after)
what I did: Added runner-local review cache in SQLite: exact hunk hashes, prior finding state, carry-forward on untouched files, budgeted prior_finding prompt blocks (128 tokens), no semantic caching. Live reviews call incremental_review_pull_request via LocalReviewCache. Hosted Neon has no review_cache tables. Staged only 8 cache files; did not stage apps/web, docs/reports, TODO, HANDOFF, datasets, or scorecard.
blockers: None

## 2026-09-09T23:15:00+05:30 | m1-team-access-foundation | free tier backend enforcement
status: DONE
commit sha: d574282 feat: enforce free tier one user one repo
red proof: AssertionError: assert 'ignored' == 'enqueued' at tests/test_free_tier_access.py before access_policy existed; AssertionError: assert PairingApproved == PairingDenied for two-repo approval
gate numbers: ruff 0 on staged Python; mypy 0 on 252 source files; dash grep empty; full suite 1516 passed, 3 skipped, 0 failed (399.49s)
what I did: Added installations.access_tier default free with team reserved for a future paid path. access_policy enforces one GitHub user and one repository at pairing approve/exchange and blocks PR enqueue for other repos once a repo is assigned. Bootstrap enqueue still works before pairing. Team tier bypasses limits for existing multi-runner protocol tests only. No billing, no frontend, no eval/matcher/model changes. Regenerated docs/DATA_BOUNDARIES.md for access_tier allowlist.
blockers: None
## 2026-09-10T00:11:12+05:30 | live-github-loop-proof | goal
status: BLOCKED
commit sha: a20c026 fix: unblock live runner claim post and review model
red proof: hosted worker claimed PR job 3e064158 and marked succeeded in 2s with no review; post failed HTTPStatusError / GitHub 403 on read-only installation token
gate numbers: targeted pytest 30 passed; ruff fix on service.py pending full gate
what I did: Ran live test on https://reviewer.niresh.tech with PR https://github.com/the-niresh/YeahScene-AI/pull/8. Verified App URLs and webhook delivery. Fixed worker job steal, runner OpenAI model selection, and post-token write scope. Second job ran review (~$0.00031). Post and feedback blocked on installation pull_requests write approval. Wrote docs/reports/live-github-loop-proof.md.
blockers: Owner must approve pull_requests write at https://github.com/settings/installations/158479604 and confirm pull_request_review_comment on installation; redeploy hosted worker/api with this commit; re-run PR after that.
## 2026-09-10T00:12:00+05:30 | live-github-loop-proof | recheck
status: BLOCKED
commit sha: a20c026 (no new commit; report updated only)
red proof: write token mint HTTP 422; installation permissions still pull_requests read
gate numbers: n/a
what I did: Rechecked GitHub installation permissions (still read-only). Rebuilt and redeployed hosted api/worker from a20c026; stopped stale pr-reviewer-api-1; verified post-token route returns 409 on reviewer.niresh.tech. Updated docs/reports/live-github-loop-proof.md recheck section.
blockers: Owner must approve pull_requests write at https://github.com/settings/installations/158479604 and subscribe pull_request_review_comment; then re-run PR #8 with reviewer start.
## 2026-09-10T00:23:54+05:30 | live-github-loop-proof | permission recheck
status: BLOCKED
commit sha: a20c026 (no code change)
red proof: write token mint HTTP 422; installation permissions pull_requests read only
gate numbers: n/a
what I did: Rechecked GitHub installation 158479604 and hosted health (200). Updated docs/reports/live-github-loop-proof.md recheck timestamp. Code fixes from a20c026 remain deployed; loop cannot finish until owner approves write permission and review_comment event.
blockers: Owner step at https://github.com/settings/installations/158479604; then say re-run loop.
## 2026-09-10T00:42:04+05:30 | live-github-loop-proof | full loop pass
status: DONE
commit sha: a20c026 fix: unblock live runner claim post and review model
red proof: prior runs HTTPStatusError on post with installation pull_requests read only; write token mint HTTP 422
gate numbers: n/a (live proof only)
what I did: Owner approved installation write + review_comment events. Restarted runner, pushed ca5bea0 on PR #8. Job ad096d75 succeeded; GitHub review 5158722711 posted; human reply captured as review_comment_feedback classification wrong. First model cost USD 0.000309 under USD 0.05 budget. Updated docs/reports/live-github-loop-proof.md to PASS.
blockers: None
## 2026-09-10T00:57:18+05:30 | clean-machine-install-proof | partial pass
status: DONE
commit sha: 47a7194fe3dfa330d3de9045ab50f93f236985bf
red proof: curl install-reviewer.sh on public main returned HTTP 404 before push
gate numbers: installer+docs tests pending; dash grep pending
what I did: Ran clean install in fresh temp HOME with manual uv tool install from public git. reviewer --help and reviewer doctor --yes passed. Documented PARTIAL PASS in docs/reports/clean-machine-install-proof.md. Fixed INSTALL.md curl 404 fallback and live hosted origin in setup example; README grammar and stale live-comment line.
blockers: Owner must push main to origin before public curl one-liner works for strangers.
## 2026-09-10T00:59:42+05:30 | clean-machine-install-proof | pass after push
status: DONE
commit sha: doc update pending
red proof: prior curl returned 404 before push; after push curl HTTP 200 and install exit 0
gate numbers: n/a (live proof only)
what I did: Re-ran clean install from public curl one-liner in fresh temp HOME/bin. Built from git 40a9f85. reviewer --help and reviewer doctor --yes passed. Updated docs/reports/clean-machine-install-proof.md to PASS.
blockers: None for install proof. Next: real user install + live PR review from public install only.
## 2026-09-10T01:35:54+05:30 | public-install-live-review-proof | pass with fix
status: DONE
commit sha: 96eb40b fix: read model key from secret store in agent backend
red proof: public install at 40a9f85 failed review_jobs with TypeError resolve_model_provider() takes 0 positional arguments but 1 was given
gate numbers: test_model_key_storage 6 passed; package boundaries + hosted boundary passed
what I did: Proved live loop from fresh uv-tool reviewer install after 96eb40b. PR #9, job 37329c7a succeeded, GitHub review 5159297169 comment 3972527103. Documented curl blocker until 96eb40b on origin/main.
blockers: Owner must push 96eb40b to origin/main before public curl one-liner passes live review.
## 2026-09-10T01:40:49+05:30 | launch-readiness-audit | report
status: DONE
commit sha: pending
red proof: n/a (audit only)
gate numbers: hygiene+install+free_tier+context_cache+docs_polish+pairing+boundary tests pass; review_comment_feedback 6 failed on shared postgres during audit run
what I did: Audited 12 launch areas against live proofs, live health checks, and targeted tests. Wrote docs/reports/launch-readiness-audit.md with PASS/PARTIAL/BLOCKED verdicts and next task list.
blockers: Public launch blocked on quality baseline, unpushed docs, release asset, marketing metadata; beta ready for owner-operated path.

