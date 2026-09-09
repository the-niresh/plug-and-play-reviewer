import { FindingCard } from "@/components/FindingCard";
import { Badge } from "@/components/ui/badge";
import type { ReviewFinding } from "@/lib/reviews";

export function ProductStage({ finding }: { finding: ReviewFinding }) {
  return (
    <aside
      aria-label="Example review from the real dashboard layout"
      className="landing-stage border-border bg-background/80 min-w-0 border"
    >
      <div className="border-border text-muted-foreground flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2 font-mono text-[11px] tracking-wide uppercase">
        <span>review_job  7f2c18</span>
        <span>head  a3f91c2</span>
      </div>
      <div className="border-border flex flex-wrap items-center gap-2 border-b px-4 py-2.5">
        <Badge variant="outline">claimed</Badge>
        <Badge variant="warning">allow_public_post false</Badge>
        <span className="text-muted-foreground text-xs">
          Example finding. It does not post until a human approves.
        </span>
      </div>
      <FindingCard finding={finding} />
      <dl className="border-border text-muted-foreground grid grid-cols-2 gap-px border-t font-mono text-[11px] sm:grid-cols-4">
        <div className="bg-card px-4 py-3">
          <dt>grounding dropped</dt>
          <dd className="text-foreground mt-1 text-sm">2</dd>
        </div>
        <div className="bg-card px-4 py-3">
          <dt>schema dropped</dt>
          <dd className="text-foreground mt-1 text-sm">0</dd>
        </div>
        <div className="bg-card px-4 py-3">
          <dt>retrieval</dt>
          <dd className="text-foreground mt-1 text-sm">on</dd>
        </div>
        <div className="bg-card px-4 py-3">
          <dt>suggestion</dt>
          <dd className="text-foreground mt-1 text-sm">ready</dd>
        </div>
      </dl>
    </aside>
  );
}
