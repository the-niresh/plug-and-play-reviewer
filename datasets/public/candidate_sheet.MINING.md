# How `candidate_sheet.jsonl` was built

Unjudged. A human must run `pr-reviewer-holdout review` against this file before
`build-holdout` will touch it. Mining picks candidates, never labels.

Both repos are public, cloned fresh from GitHub. `--grep` targets commits whose
subject looks like a bug fix, since a later commit fixing a bug an earlier one
introduced is a defensible label without a human inventing one. The commit
message is evidence, not proof: the human judging the sheet still decides
include or exclude per row.

One Python repo (Flask, AST-based chunking) and one TypeScript repo (Zod,
line-window chunking), so a judged holdout can tell whether the chunking
strategy affects reviewer quality.

Repos cloned at:

- `https://github.com/pallets/flask.git` at `d318b683471101618febed18996405ad26462110`
- `https://github.com/colinhacks/zod.git` at `804e0f522747345d6b37581888899be420baa3e9`

Commands run (2026-09-08), from the repo root:

```bash
git clone https://github.com/pallets/flask.git /tmp/pr-reviewer-mining/flask
git clone https://github.com/colinhacks/zod.git /tmp/pr-reviewer-mining/zod

uv run python -m pr_reviewer.evals.holdout_sheet write-sheet \
  --repo /tmp/pr-reviewer-mining/flask \
  --out /tmp/pr-reviewer-mining/flask_sheet.jsonl \
  --id-prefix flask-py \
  --since 2023-01-01 \
  --until 2026-09-01 \
  --per-window 25 \
  --grep 'fix|bug'
# candidates=25 skipped=0

uv run python -m pr_reviewer.evals.holdout_sheet write-sheet \
  --repo /tmp/pr-reviewer-mining/zod \
  --out /tmp/pr-reviewer-mining/zod_sheet.jsonl \
  --id-prefix zod-ts \
  --since 2023-01-01 \
  --until 2026-09-01 \
  --per-window 25 \
  --grep 'fix|bug'
# candidates=25 skipped=0

cat /tmp/pr-reviewer-mining/flask_sheet.jsonl /tmp/pr-reviewer-mining/zod_sheet.jsonl \
  > datasets/public/candidate_sheet.jsonl
```

`--per-window` samples evenly across the date window instead of taking only the
newest commits, so the sheet is not biased toward the last few weeks. `--grep`
is a new flag on `write-sheet` (this track added it): it passes
`--grep=<pattern> --extended-regexp --regexp-ignore-case` straight through to
`git log`, so re-running the two commands above against the same repo state
reproduces the same 50 rows byte for byte (git history for these public repos
does not get rewritten).

Result: 50 unjudged rows in `datasets/public/candidate_sheet.jsonl`
(`flask-py-001..025`, `zod-ts-001..025`), verdict/human_auditor/split/labels
all blank. Next step is a human running:

```bash
uv run python -m pr_reviewer.evals.holdout_sheet review \
  --sheet datasets/public/candidate_sheet.jsonl \
  --auditor <name>
```

then `build-holdout` once enough rows are judged, targeting 30 to 50 included
cases per the phase plan (Task 35.F1). The public `eval_cases.jsonl` file is
untouched by this task on purpose: `build_holdout` refuses unjudged rows and
this track does not work around that.
