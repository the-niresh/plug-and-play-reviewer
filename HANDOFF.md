# Work for tomorrow

Written 2026-09-08 evening. Everything below is checked against the code, not remembered.

Repo: `/srv/claude/projects/plug-and-play-reviewer`
Branch: `main`, HEAD `89ed86d`, pushed, working tree clean.
Suite: 1413 passed, 0 failed. ruff clean. mypy 0 on 245 files.

Read `AGENTS.md` first. It has the rules every agent must follow. This file is only what to do next.

---

## Where things actually stand

Phase 35 is 40 of 40 steps built. Four acceptance items are still open, listed at the bottom of
`docs/phases/plans/phase-35-plan.md`.

Today the reviewer went from **never having worked** to **working and bad**. That is the honest
summary. The prompt asked the model for a schema it never described, so every finding it produced
was thrown away. Nine other bugs sat behind that one. All are fixed and pushed.

### The measured baseline

This is the first real number this project has ever produced. Seven holdout cases, one repeat,
`gpt-4o-mini`, real OpenAI calls.

```
                   precision  recall  false/PR  cost
diff_only            0.000    0.000    2.143    $0.0056
retrieval_backed     0.000    0.000    3.000    $0.0103
delta                +0.000   +0.000   +0.857
total run cost: $0.0755
```

Reproduce it with:

```bash
reviewer ablate --repeats 1
```

Read it as: the reviewer reports 2 to 3 findings per pull request and none of them are the real
bug. On `zod-ts-012` the real bug is `packages/zod/src/v4/core/util.ts:286` and it reported lines
634, 689 and 579. Right file, wrong lines. Retrieval currently makes it worse, not better.

Do not treat that as a verdict on retrieval. Seven cases, one repeat, one model, all TypeScript.
It is a starting number, and its only job is to let you tell whether a change helped.

---

## Task 1 - Find out WHY precision is zero. Do this first.

Nothing else matters until you know this. Do not tune the prompt before you have looked.

The eval reports totals and nothing else. You cannot improve what you cannot see.

**Build a per-case report.** For each of the 7 holdout cases, print:

- the case id and the labelled bug: file, line range, concern, category
- every finding the reviewer produced: file, line range, concern, title, confidence
- whether any finding overlaps the labelled lines at all
- the reflection score each finding was given, and which were dropped

Write it to a file, one section per case, plain text. Then read all seven yourself.

Then answer these, in writing, with evidence:

1. Is it finding the right FILE and the wrong LINES, or the wrong file entirely?
2. Are the labelled bugs even visible in what the model was shown? Check the packed diff for one
   case by hand. If the buggy lines were never in the prompt, precision cannot be above zero and
   the problem is packing, not the prompt.
3. Is the matcher too strict? `evals/match_findings.py` decides whether a finding counts as
   hitting the label. If it demands an exact line match, a finding one line off scores zero. Read
   how it matches before blaming the model.

Question 3 is the one I would check first. A finding at line 288 for a bug labelled at 286 may be
correct in substance and scored as a miss.

Files: `src/pr_reviewer/evals/`, a new reporting entry point, `tests/`.

Deliverable: the per-case report file, plus a written answer to the three questions above.

---

## Task 2 - Fix whatever task 1 found

Do not start this until task 1 is answered. The fix depends entirely on the answer.

If it is the matcher, fix the matcher and re-run the ablation. If it is packing, fix the packing.
If it is genuinely the prompt, then tune the prompt, but only against the SIX DEV cases, never the
seven holdout ones.

**The holdout rule.** `datasets/public/eval_cases.jsonl` has 6 dev cases and 7 holdout cases. Tune
against dev. Look at holdout once, at the end, and report that number. Once you read a holdout
case and change something because of it, that case is burned and must be moved to dev, and the
next report has to say so.

After any change, re-run `reviewer ablate --repeats 1` and compare against the baseline above.

---

## Task 3 - The four open acceptance items

From `docs/phases/plans/phase-35-plan.md`, still unticked:

1. **A stranger installs and gets a review on a real PR.** Never tested. Needs the control plane
   deployed, the GitHub App installed on a repo Niresh owns, and a pull request with a deliberate
   bug. This tests webhooks, job claiming, the human approval gate and posting, which the eval
   cannot reach. This is the biggest untested area in the product.

2. **A measured review costs under five cents, from the ledger, not estimated.** The ablation now
   records real cost. Diff-only came in at $0.0056 for 7 reviews, well under a cent each, and
   retrieval at $0.0103. Cost is not the problem. This may already be satisfied; check the ledger
   and tick it or say why not.

3. **No border and no button anywhere in the review path.** Done as of `89ed86d`. `grep -rn
   "Button(" src/pr_reviewer/tui/` returns 0 and there are no visible border declarations. Verify
   and tick it.

4. **The docs read plainly to someone who has never seen the project.** Nobody has read them.
   This one is Niresh's judgement, not an agent's.

---

## Task 4 - Things nobody has ever looked at

None of these have been opened by a person. Each is a likely source of the same class of bug that
took all of today: code that passes tests and has never run.

- the web app. The `pr-reviewer-ui-1` container is days old and serves a stale build. Rebuild with
  `docker compose up -d --build ui`, or `cd apps/web && bun run dev`, then actually look at the
  landing, docs, settings, dashboard and scorecard pages.
- the onboarding flow end to end
- the Slack, Discord, Telegram and email notification paths
- `reviewer doctor`, `reviewer start`, `reviewer trace`

Open them. Write down what looks wrong. Fix the worst.

---

## Rules every agent must follow

From `AGENTS.md`, the ones that bite:

- **Every pytest run goes through the lock**, targeted runs included:
  `flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q <file>`
  Several agents share one Postgres. A run without the lock produces `ForeignKeyViolation` or
  `DeadlockDetected` in tests unrelated to your change.
- **Never run** `bun run build`, `tests/test_landing_performance.py` or
  `tests/test_dashboard_performance.py`. This box runs out of memory.
- **Write the failing test first.** Run it, watch it fail, keep the real failure text.
- **Commits are one line, one `-m`, no body, no trailers, no AI attribution.**
- **Never stage** `docs/phases/` or `datasets/private/`.
- **No em dash, no en dash.** Check with `grep -Pn '[\x{2013}\x{2014}]' <file>`.
- `control_plane/` must never import `runner/`. Run `tests/test_package_boundaries.py` and
  `tests/test_hosted_boundary_enforcement.py` before reporting ready.
- Source code, diffs, findings and model keys never reach the hosted plane.

The gate before any commit:

```bash
uv run ruff check <staged files>
uv run mypy src
grep -Pn '[\x{2013}\x{2014}]' <staged files>
flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q \
  --ignore=tests/test_landing_performance.py --ignore=tests/test_dashboard_performance.py
```

Must be at or above 1413 passed, 0 failed.

---

## Traps that cost real time today

Every one of these was a green test suite hiding a broken feature. Expect more of them.

1. **A stub is not a test of the thing.** Every eval test used `FixtureReviewer`, which returns
   the right answer by construction. A stub never disagrees with your schema, so the reviewer's
   central defect survived 1400 passing tests. If a test never makes a real call or a real
   equivalent, it proves the plumbing, not the product.

2. **A guard that holds by accident is not a guard.** The ablation pointed at the hosted database
   and would have uploaded source code to it. The only thing that stopped it was a table dropped
   two months earlier for unrelated reasons.

3. **A proxy condition outlives the thing it stood for.** "Is the holdout empty" was a stand-in
   for "have we measured anything". The moment the holdout filled, three separate places started
   lying: the public scorecard claimed 100 percent precision from a stub, and the CI gate became
   structurally incapable of failing a build.

4. **An error handler that lies costs more than the error.** Four failures tonight arrived as a
   bare exception with no status code and no message, each needing a hand-rolled reproduction
   against the live API. Carry the real status and message. Never relabel one failure as another.

5. **A heuristic right on average is catastrophic on the tail.** Four chars per token is fine for
   prose and wrong by 5x for a file full of emoji. The tail is where production lives.

6. **Test the second time, not just the first.** The TUI crashed on pressing the same menu item
   twice, because `remove_children()` is async and was never awaited. No test navigated to a
   section twice.

7. **Write the test so it cannot pass vacuously.** Two injection-defence tests survived only
   because someone wrote `assert chunks` before the security assertions. Without that line they
   would have passed with the defence switched off.

---

## Suggested order

1. Task 1, the per-case report. Half a day. Nothing else is worth doing first.
2. Task 2, the fix it points to. Re-run the ablation and compare.
3. Task 3 item 1, the real pull request test. This is the biggest unknown left.
4. Task 4, open the surfaces nobody has looked at.
