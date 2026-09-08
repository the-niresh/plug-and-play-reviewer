/** Build honest behavior panels for a review. Uses real field names from
 *  model_call_ledger_fields, ReviewOutcome, and OmissionReason. Never fabricates a number.
 *  OmissionReason values: token_budget, patch_omitted_by_github, patch_truncated_by_github,
 *  binary, generated, ignored_path, file_size_limit, clone_timeout. */

import type { ReviewBehavior, ReviewSummary } from "./reviews";

export const NO_DATA = "No data yet";

export type ReviewPanel = {
  label: string;
  value: string;
};

function sumReceiptTokens(review: ReviewSummary): number | null {
  let total = 0;
  let saw = false;
  for (const finding of review.findings) {
    const receipt = finding.receipt;
    if (!receipt) continue;
    if (receipt.input_tokens == null && receipt.output_tokens == null) continue;
    saw = true;
    total += (receipt.input_tokens ?? 0) + (receipt.output_tokens ?? 0);
  }
  return saw ? total : null;
}

function sumReceiptCost(review: ReviewSummary): string | null {
  let total = 0;
  let saw = false;
  for (const finding of review.findings) {
    const receipt = finding.receipt;
    if (!receipt?.cost_usd) continue;
    const parsed = Number.parseFloat(receipt.cost_usd);
    if (Number.isNaN(parsed)) continue;
    saw = true;
    total += parsed;
  }
  if (!saw) return null;
  const text = total.toFixed(4).replace(/\.?0+$/, "");
  return `$${text}`;
}

function formatRate(rate: number | null | undefined): string {
  if (rate == null) return NO_DATA;
  return `${Math.round(rate * 100)}%`;
}

function formatSuppressed(behavior: ReviewBehavior | null | undefined): string {
  const items = behavior?.suppressed_candidates;
  if (!items || items.length === 0) return NO_DATA;
  const parts = items.map((item) => {
    const reason = item.reflection_reason?.trim();
    return reason ? `${item.title} (${reason})` : item.title;
  });
  return `${items.length}: ${parts.join("; ")}`;
}

function formatCoverage(behavior: ReviewBehavior | null | undefined): string {
  if (behavior?.covers_all_changed_files == null) return NO_DATA;
  return behavior.covers_all_changed_files ? "All changed files covered" : "Incomplete coverage";
}

function formatOmitted(behavior: ReviewBehavior | null | undefined): string {
  const files = behavior?.omitted_files;
  if (!files || files.length === 0) return NO_DATA;
  const parts = files.map((file) => `${file.path} (${file.reason})`);
  return parts.join("; ");
}

function formatEvalScores(behavior: ReviewBehavior | null | undefined): string {
  const scores = behavior?.eval_scores;
  if (!scores || Object.keys(scores).length === 0) return NO_DATA;
  return Object.entries(scores)
    .map(([key, value]) => `${key}: ${value}`)
    .join("; ");
}

function formatMultiModel(behavior: ReviewBehavior | null | undefined): string {
  const models = behavior?.models_consulted;
  if (!models || models.length === 0) return NO_DATA;
  const names = models.map((entry) => `${entry.provider}/${entry.model}`).join(", ");
  if (behavior?.models_agreed == null) return names;
  return `${names} (${behavior.models_agreed ? "agreed" : "disagreed"})`;
}

function countSecurityFindings(review: ReviewSummary): string {
  const count = review.findings.filter((finding) => finding.concern === "security").length;
  return String(count);
}

function rejectionCount(
  behavior: ReviewBehavior | null | undefined,
  field: "schema_rejected_findings" | "grounding_rejected_findings" | "duplicate_rejected_findings",
): string {
  const value = behavior?.[field];
  if (value == null) return NO_DATA;
  return String(value);
}

/** One row per behavior dimension. Missing data is stated plainly, never guessed. */
export function buildReviewPanels(review: ReviewSummary): ReviewPanel[] {
  const behavior = review.behavior ?? null;
  const ledger = behavior?.ledger ?? null;

  const ledgerTokens =
    ledger != null ? ledger.input_tokens + ledger.output_tokens : null;
  const receiptTokens = sumReceiptTokens(review);
  const tokens =
    ledgerTokens != null
      ? String(ledgerTokens)
      : receiptTokens != null
        ? String(receiptTokens)
        : NO_DATA;

  const ledgerCost = ledger?.cost_usd ? `$${ledger.cost_usd}` : null;
  const receiptCost = sumReceiptCost(review);
  const cost = ledgerCost ?? receiptCost ?? NO_DATA;

  const latency =
    ledger?.latency_ms != null ? `${ledger.latency_ms} ms` : NO_DATA;

  const cacheHitRate = formatRate(ledger?.prompt_cache_hit_rate);

  const retrievalHitRate = formatRate(behavior?.retrieval_hit_rate ?? undefined);

  const budgetRemaining =
    behavior?.budget_remaining_usd != null
      ? `$${behavior.budget_remaining_usd}`
      : NO_DATA;

  return [
    { label: "Tokens", value: tokens },
    { label: "Cost", value: cost },
    { label: "Latency", value: latency },
    { label: "Cache hit rate", value: cacheHitRate },
    { label: "Retrieval hit rate", value: retrievalHitRate },
    {
      label: "Rejected for schema",
      value: rejectionCount(behavior, "schema_rejected_findings"),
    },
    {
      label: "Rejected for grounding",
      value: rejectionCount(behavior, "grounding_rejected_findings"),
    },
    {
      label: "Rejected for duplication",
      value: rejectionCount(behavior, "duplicate_rejected_findings"),
    },
    { label: "Suppressed by the judge", value: formatSuppressed(behavior) },
    { label: "Coverage", value: formatCoverage(behavior) },
    { label: "Omitted files", value: formatOmitted(behavior) },
    { label: "Budget remaining", value: budgetRemaining },
    { label: "Security findings", value: countSecurityFindings(review) },
    { label: "Eval scores", value: formatEvalScores(behavior) },
    { label: "Multi-model", value: formatMultiModel(behavior) },
  ];
}
