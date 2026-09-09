# Holdout quality baseline (published)

**Status:** first honest published baseline  
**Date:** 2026-09-10  
**Model:** gpt-4o-mini (default generate model)  
**Sample:** 7 human-judged holdout cases from `datasets/public/eval_cases.jsonl`  
**Mode:** diff-only, retrieval off, `EMPTY_GENERATE_RETRY_ENABLED=false`  
**Repeats:** 1 pass per case (no multi-pass variance run)

This run is measure-only. No prompts, matcher, datasets, thresholds, or retry flags were
changed for this report.

## Cost

| Item | USD |
|---|---|
| Projected (estimate, 7 cases, 2 calls each) | 0.021060 |
| Measured (live run) | 0.004606 |
| Cap (stop threshold) | 0.25 |

Measured cost is below projection because actual token use was lower than the worst-case
estimate (`MAX_OUTPUT_TOKENS` on input heuristic).

## Aggregate metrics

| Metric | Value |
|---|---|
| precision_per_finding | 0.667 |
| precision_per_case | 0.571 |
| recall_per_finding | 0.571 |
| recall_per_case | 0.571 |
| false_findings_per_pr | 0.286 |
| needs_human_rate | 0.000 |
| reviewed_pr_count | 7 |
| total_latency_ms | 31037 |
| schema_rejected_findings | 0 |
| grounding_rejected_findings | 7 |
| duplicate_rejected_findings | 0 |

## Per-case results

| Case | Hit | cost_usd | accepted | matched | miss cause |
|---|---|---:|---:|---:|---|
| zod-ts-012 | no | 0.001576 | 2 | 0 | wrong lines (util.ts 577-629 vs label 286-292) |
| zod-ts-013 | no | 0.000616 | 0 | 0 | no finding (checks.ts label not surfaced) |
| zod-ts-014 | yes | 0.000391 | 1 | 1 | shallowClone util.ts |
| zod-ts-017 | yes | 0.000417 | 1 | 1 | abort/when schemas.ts |
| zod-ts-018 | yes | 0.000437 | 1 | 1 | discriminated union encode schemas.ts |
| zod-ts-020 | no | 0.000519 | 0 | 0 | no finding (security __proto__ label) |
| zod-ts-021 | yes | 0.000650 | 1 | 1 | domain regex regexes.ts |

**Hits:** 4 of 7 cases (zod-ts-014, zod-ts-017, zod-ts-018, zod-ts-021).

## Limitations

1. **Small sample.** Seven holdout cases, all from the Zod repository. Numbers are not
   representative of all languages or repos.
2. **Single pass.** One review per case. No repeat variance band (unlike the 3-pass dev
   sanity runs).
3. **Diff-only.** No retrieval, no specialist mode, no executable checks.
4. **Matcher strictness.** A finding counts only when concern, file_path, overlapping line
   range, and normalised category all match the human label.
5. **Not tuned from this run.** This report records current behaviour after recent fixes.
   It is not a tuning target.

## Published artifacts

- This report: `docs/reports/holdout-quality-baseline.md`
- Scorecard JSON for the web scorecard page: `docs/reports/scorecard.json`

These numbers replace prior refusal placeholders and cache-replay evidence. They are the
intended public baseline until a new measured run supersedes them.
