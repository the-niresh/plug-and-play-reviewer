# Options: raise 6-dev recall without making gpt-4.1 the default generator

Status: ⬜ not done, ✅ done or agreed, ❌ not doing, ❓ open, ⚠️ trap

Evidence (not a baseline): `docs/reports/dev-eval-3pass-gpt-4o-mini.txt`

## Status

- ✅ Keep `gpt-4o-mini` as the default generate model (`RoleModels.generate`)
- ❌ Do not switch default generation to `gpt-4.1`
- ⬜ Pick one recall option below
- ❌ Do not write `scorecard.json` from these numbers
- ❌ Do not use holdout for this decision
- ⚠️ Two one-pass mini runs already disagreed. Treat single-pass deltas as noise.

## What the 3-pass run showed

Measured on 6 `dev` cases, 3 passes, `gpt-4o-mini`, diff-only:

- exact total cost: $0.007733
- precision mean 0.417 (range 0.250-0.667)
- recall mean 0.278 (range 0.167-0.333)
- false findings per PR mean 0.500 (range 0.167-1.000)

Hit stability:

| case | hits / 3 | miss shape |
|---|---|---|
| flask-py-001 | 0/3 | no finding every pass |
| flask-py-006 | 0/3 | no finding twice; wrong concern once |
| flask-py-013 | 2/3 | flip |
| flask-py-020 | 0/3 | wrong concern twice; no finding once |
| zod-ts-005 | 0/3 | wrong concern every pass |
| zod-ts-010 | 3/3 | stable hit |

A one-pass `gpt-4.1` run (evidence only, $0.054604) hit flask-py-001, 006, 013, and 010. It still missed flask-py-020 and zod-ts-005 on concern.

Costs used below are per 6-case batch, from those runs. A live PR would be about one sixth of the batch, plus variance.

## Recommendation

Start with **option 2** if the goal is automated recall on silent PRs.

The 3-pass union cannot invent a hit for flask-py-001, 006, 020, or zod-ts-005. Only flask-py-013 is unstable. A second `gpt-4.1` call only when mini returns no findings is the cheap way to buy the flask-py-001 hit without changing the default generator.

Use **option 4** for flask-py-020 and zod-ts-005. Those are concern misses, not empty lists. More mini passes will not turn them into matcher hits.

Do **option 1** only if you want to stabilize flask-py-013. Do **option 3** only with a new failing prompt-contract test that does not name holdout words. A visible-hunk prompt bump already landed and flask-py-001 stayed 0/3.

## Option 1 - ⬜ multi-pass mini with merge and dedupe

Run `gpt-4o-mini` two or three times. Merge accepted findings. Dedupe by file path and line overlap (same rule as `match_findings` / `consensus.py`).

- **Expected cost:** about $0.0077 for 3 passes on 6 cases (measured). About 3x a one-pass mini batch ($0.0024-$0.0030). Default generate model stays mini.
- **Expected recall impact:** small. Union of these 3 passes still only hits flask-py-013 and zod-ts-010 (2/6). flask-py-001, 006, 020, and zod-ts-005 stay misses. Ceiling on this set is about 0.333 case recall.
- **False-finding risk:** high unless dedupe is strict. Pass 1 alone had false/PR 1.000. A naive union stacks extras.
- **Implementation size:** medium. `consensus.py` is multi-model and off. Same-model pass merge is new. Reuse the structural match helper, do not turn on `MULTI_MODEL_GENERATE_ENABLED`.
- **Test that would fail first:** three packed reviews of a flask-py-013 shaped hunk, two silent and one hit, merged result must keep the hit and drop duplicate titles on the same lines.
- **Metric that would prove it:** flask-py-013 hit rate 3/3 on a later 3-pass union, with false/PR no worse than the current mean 0.500.

## Option 2 - ⬜ stronger-model retry only when mini returns no findings

Keep mini as generate. If accepted findings are empty after grounding, call `gpt-4.1` once on the same packed diff. Do not retry when mini already emitted findings (so zod-ts-005 is unchanged).

- **Expected cost:** mini always (~$0.0024) plus `gpt-4.1` on empty cases. In the 3-pass log, empty cases averaged about 2.3 of 6 per pass. `gpt-4.1` was about $0.008-$0.009 per case. Extra about $0.018-$0.021 per 6-case pass. Total about $0.021-$0.024, still under half of a full `gpt-4.1` batch ($0.0546).
- **Expected recall impact:** the only clear gain is flask-py-001 (`gpt-4.1` hit; mini 0/3). flask-py-006 is empty 2/3 of the time and `gpt-4.1` hit it. flask-py-020 empty 1/3 of the time, and `gpt-4.1` still had the wrong concern. zod-ts-005 would not retry (mini always emitted).
- **False-finding risk:** medium, and limited to empty PRs. Full `gpt-4.1` had false/PR 0.500. Retry-only avoids extra findings on cases mini already answered.
- **Implementation size:** small. One branch in `review_pull_request` after `_candidates_from_parsed` is empty. Keep `RoleModels.generate` as mini. Do not change the default.
- **Test that would fail first:** fake mini returns `{"findings": []}`, fake `gpt-4.1` returns one grounded finding; the outcome must include that finding and record both costs. A second test: mini returns a finding, `gpt-4.1` must not be called.
- **Metric that would prove it:** flask-py-001 hit on a later mini-then-retry pass, plus a count that `gpt-4.1` was not called on zod-ts-010. Cost must stay well below a full `gpt-4.1` 6-case run.

## Option 3 - ⬜ prompt calibration for no-finding cases

Bump `diff_only_reviewer` again (insert-only content hash). Ask the model to report a visible inheritance or key-order bug. Do not name holdout words. Do not add hyphen or character-class markers.

- **Expected cost:** same as one mini pass (~$0.0024-$0.0030). No extra model call.
- **Expected recall impact:** weak on current evidence. A visible-hunk line already landed (`f4c6e3ada95c2b54`). flask-py-001 stayed 0/3 after that. flask-py-006 stayed 0/3. Another sentence may not move a model that is silent on the same hunk three times.
- **False-finding risk:** medium. Pass 1 already emitted extras when the model spoke. A more aggressive prompt can raise false/PR.
- **Implementation size:** small. Prompt version bump plus a contract test, same pattern as `tests/test_review_prompt_calibration.py`.
- **Test that would fail first:** prompt text must require a finding when a parent option is not copied onto a nested child (flask-py-001 shape). Must not mention holdout case ids.
- **Metric that would prove it:** flask-py-001 hit rate above 0/3 on a later 3-pass mini run, with false/PR mean no higher than 0.500.

## Option 4 - ⬜ human queue for low-confidence or wrong-concern security cases

Do not try to raise matcher recall. Route findings that look like session signing, or that sit on a security label but say correctness, to a person. `route_finding` already queues when `allow_public_post` is false. The model still cannot set `verified` or `allow_public_post`.

- **Expected cost:** one mini pass (~$0.0024) plus human time. No extra generate call if you only reroute existing findings.
- **Expected recall impact:** none on the matcher. flask-py-020 and zod-ts-005 stay automated misses. Posted recall can rise if a person corrects concern or keeps a useful finding the matcher would drop.
- **False-finding risk:** low for public posts. Humans drop junk. Queue volume may rise.
- **Implementation size:** small to medium. Gate already queues unverified findings. A new rule would need a system-owned signal (for example draft text that names a signing key, which `d8844d2` already promotes to security). Do not let the model set routing fields.
- **Test that would fail first:** a correctness draft that names a signing key becomes security (`d8844d2` already does this) and `route_finding` queues it as restricted. A plain null-check correctness finding is not treated as a security alert.
- **Metric that would prove it:** `needs_human_rate` or queue count on flask-py-020 shaped findings, with zero public posts that still have concern correctness and signing-key text. Do not use matcher recall as the proof.

## Open decisions

- ❓ Which option to implement first (recommend 2, then 4)
- ❓ How many mini passes for option 1 if chosen (2 vs 3)
- ❓ Empty-retry model for option 2 (`gpt-4.1` vs `gpt-4.1-mini`)
- ❓ Whether option 4 should queue all correctness findings that name a signing key, or only low confidence
- ⚠️ Do not treat option 1 as a recall fix for flask-py-001. Three silent passes already measured that.
- ⚠️ Do not add hyphen or character-class keyword guessing for zod-ts-005.
