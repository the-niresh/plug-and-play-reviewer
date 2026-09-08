import { buildReviewPanels } from "@/lib/reviewPanels";
import type { ReviewSummary } from "@/lib/reviews";

/** Panel labels rendered: Tokens, Cost, Latency, Cache hit rate, Retrieval hit rate,
 *  Rejected for schema, Rejected for grounding, Rejected for duplication,
 *  Suppressed by the judge, Coverage, Omitted files, Budget remaining,
 *  Security findings, Eval scores, Multi-model */

export function ReviewBehaviorPanels({ review }: { review: ReviewSummary }) {
  const panels = buildReviewPanels(review);

  return (
    <section className="mt-8" data-testid="review-behavior-panels">
      <h2 className="mb-4 text-xs font-medium tracking-[0.14em] uppercase">
        How the machine behaved
      </h2>
      <dl className="overflow-hidden rounded-lg border">
        {panels.map((panel) => (
          <div
            key={panel.label}
            className="bg-card flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-b px-4 py-3 last:border-b-0"
          >
            <dt className="text-sm">{panel.label}</dt>
            <dd
              className={
                panel.value === "No data yet"
                  ? "text-muted-foreground max-w-prose text-right text-sm italic"
                  : "max-w-prose text-right font-mono text-sm tabular-nums"
              }
            >
              {panel.value}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
