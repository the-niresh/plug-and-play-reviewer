/** The product as one picture: a branch of commits, a bug hiding on one of them, and a
 *  lens that sweeps the history until it stops on the bug.
 *
 *  Pure CSS and SVG. No library, no JS, nothing to hydrate, so it costs the hero nothing.
 *  Under prefers-reduced-motion every animation is turned off and the lens is left parked
 *  on the bug, which is the frame that carries the meaning anyway. */

const GIT_ORANGE = "#F05032";

/** A commit node, drawn as a diamond the way the git mark draws a version. */
function Commit({ cy, r = 5.5 }: { cy: number; r?: number }) {
  return (
    <path
      d={`M40 ${cy - r}L${40 + r} ${cy}L40 ${cy + r}L${40 - r} ${cy}Z`}
      fill={GIT_ORANGE}
      stroke={GIT_ORANGE}
      strokeWidth={2}
    />
  );
}

export function BugHunt() {
  return (
    <div
      className="bug-hunt border-border bg-background/60 relative overflow-hidden border"
      role="img"
      aria-label="A magnifying glass moving down a branch of commits until it stops on a bug"
    >
      <p className="text-muted-foreground absolute top-3 left-4 font-mono text-[10px] tracking-widest uppercase">
        main
      </p>
      <svg viewBox="0 0 300 190" className="block h-auto w-full" aria-hidden="true">
        {/* the trunk and one merged branch */}
        <path d="M40 14V176" stroke={GIT_ORANGE} strokeWidth={2.5} fill="none" />
        <path
          d="M40 74c0-14 10-22 24-22h26"
          stroke={GIT_ORANGE}
          strokeWidth={2.5}
          fill="none"
          strokeLinecap="round"
        />
        <Commit cy={26} />
        <Commit cy={74} />
        <Commit cy={122} />
        <Commit cy={166} />

        {/* the bug, sitting on the commit the lens will stop at */}
        <g className="bug-hunt-bug" stroke="currentColor" strokeWidth={1.9} fill="none"
           strokeLinecap="round">
          <path d="M104 116l-7-4M104 122h-7M104 128l-7 4" />
          <path d="M124 116l7-4M124 122h7M124 128l7 4" />
          <path d="M110 108l-2-4M118 108l2-4" />
          <circle cx="114" cy="106" r="3" fill="currentColor" />
          <ellipse cx="114" cy="122" rx="6.5" ry="8" fill="#E5484D" stroke="currentColor" />
          <path d="M114 114v16" />
          <circle cx="111" cy="119" r="1.2" fill="#1F1F1F" stroke="none" />
          <circle cx="117" cy="119" r="1.2" fill="#1F1F1F" stroke="none" />
        </g>

        {/* the lens */}
        <g className="bug-hunt-lens" stroke="currentColor" fill="none" strokeLinecap="round">
          <circle cx="114" cy="122" r="21" strokeWidth={2.4} />
          <circle cx="114" cy="122" r="21" fill="currentColor" opacity="0.04" stroke="none" />
          <path d="M129 137l13 13" strokeWidth={3.4} />
        </g>
      </svg>
      <p className="text-muted-foreground bug-hunt-caption absolute right-4 bottom-3 font-mono text-[10px] tracking-widest uppercase">
        found  1 high
      </p>
    </div>
  );
}
