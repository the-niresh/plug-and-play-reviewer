/** Plug and Play Reviewer mark: a ladybug caught under a magnifying glass, sitting on a git
 *  branch whose commits are diamonds (versions).
 *
 *  Read as a visual pun, not a gag: memorable at poster size and still resolving at ~24px,
 *  which a joke usually does not.
 *
 *  Two variants, and the distinction matters:
 *  - "color" (default): git orange branch, red ladybug. For the landing page and marketing.
 *  - "mono": everything in currentColor. Required on the filled disc in LogoBadge, on the
 *    favicon, and anywhere the mark sits on an unknown background.
 *
 *  Outlines are always currentColor so the silhouette survives in both themes. Only fills
 *  carry brand colour, and the one fill that sits on the page background (the head) uses
 *  currentColor rather than black, because a black head on a dark background disappears. */

const GIT_ORANGE = "#F05032";
const LADYBUG_RED = "#E5484D";
const SPOT = "#1F1F1F";

type LogoProps = {
  className?: string;
  title?: string;
  variant?: "color" | "mono" | "nav";
};

/** A git commit node: a diamond, the way the git mark itself draws a version. */
function commitDiamond(cx: number, cy: number, r: number): string {
  return `M${cx} ${cy - r}L${cx + r} ${cy}L${cx} ${cy + r}L${cx - r} ${cy}Z`;
}

export function Logo({ className, title, variant = "color" }: LogoProps) {
  const mono = variant === "mono";
  const nav = variant === "nav";
  const git = mono ? "currentColor" : GIT_ORANGE;
  const shell = mono || nav ? "none" : LADYBUG_RED;
  const spot = mono || nav ? "currentColor" : SPOT;
  const detailStroke = nav ? "var(--foreground)" : undefined;

  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      stroke={detailStroke ?? "currentColor"}
      strokeWidth={2.2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
    >
      {title ? <title>{title}</title> : null}

      {/* git branch: trunk, two diamond commits, and a stub that stops clear of the lens.
          It must not touch the rim: overlapping strokes fuse into a blob under 24px. */}
      <path d="M4 44V10" stroke={git} />
      <path d="M4 26c0-3.5 2.5-5.5 5.5-5.5" stroke={git} />
      <path d={commitDiamond(4, 36, 3.2)} fill={git} stroke={git} />
      <path d={commitDiamond(4, 14, 3.2)} fill={git} stroke={git} />

      {/* magnifying glass */}
      <circle cx="24" cy="21" r="12.5" />
      <path d="M33.5 30.5L41 38" stroke={detailStroke ?? "currentColor"} strokeWidth={3.4} />

      {/* the ladybug, sized so no leg or antenna reaches the rim */}
      <path d="M19.9 19.5L17.2 18.2" />
      <path d="M19.6 23H16.8" />
      <path d="M20.1 26.4L17.5 28" />
      <path d="M28.1 19.5L30.8 18.2" />
      <path d="M28.4 23H31.2" />
      <path d="M27.9 26.4L30.5 28" />
      <path d="M23 14.8L21.8 12.8" />
      <path d="M25 14.8L26.2 12.8" />
      <circle
        cx="24"
        cy="16.4"
        r="2.1"
        fill={nav ? "var(--foreground)" : "currentColor"}
      />
      <ellipse
        cx="24"
        cy="23"
        rx="4.4"
        ry="5.2"
        fill={nav ? "none" : shell}
        stroke={nav ? "var(--foreground)" : undefined}
      />
      <path d="M24 18.4v9.6" />
      <circle cx="22.2" cy="21" r="0.85" fill={spot} stroke="none" />
      <circle cx="25.8" cy="21" r="0.85" fill={spot} stroke="none" />
      <circle cx="22.2" cy="25" r="0.85" fill={spot} stroke="none" />
      <circle cx="25.8" cy="25" r="0.85" fill={spot} stroke="none" />
    </svg>
  );
}

/** The mark on a filled disc, for the docs header and anywhere it must read as an icon.
 *  Forces the mono variant: brand colour on a foreground-filled disc muddies at icon size. */
export function LogoBadge({ className }: { className?: string }) {
  return (
    <span
      className={
        "bg-foreground text-background inline-flex items-center justify-center rounded-full " +
        (className ?? "size-10")
      }
    >
      <Logo variant="mono" className="size-2/3" />
    </span>
  );
}
