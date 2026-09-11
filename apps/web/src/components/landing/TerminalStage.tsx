/** The terminal half of the product, rendered rather than screenshotted.
 *
 *  The runner is the part people actually sit in front of, and a landing page that only
 *  shows the hosted dashboard hides it. This is the reviews section of `reviewer`, with
 *  example numbers: a PNG of the same thing would go stale the first time the screen
 *  changes, blur on a retina display, and ignore the reader's theme. */

const SEVERITIES = [
  { label: "Critical", count: 1, tone: "text-destructive" },
  { label: "High", count: 3, tone: "text-destructive" },
  { label: "Medium", count: 4, tone: "text-warning" },
  { label: "Low", count: 2, tone: "text-muted-foreground" },
  { label: "Info", count: 0, tone: "text-muted-foreground" },
] as const;

const ROWS = [
  { repo: "YeahScene-AI", pr: "#11", findings: "4 findings", current: true },
  { repo: "Niresh-portfolio", pr: "#7", findings: "2 findings", current: false },
  { repo: "plug-and-play-reviewer", pr: "#42", findings: "4 findings", current: false },
] as const;

const SECTIONS = ["repositories", "agent-prompts", "profile", "reviews"] as const;

export function TerminalStage() {
  return (
    <aside
      aria-label="The reviewer terminal, showing its reviews section"
      className="landing-stage border-border bg-background/80 min-w-0 overflow-hidden border"
    >
      <div className="border-border text-muted-foreground flex items-center gap-2 border-b px-4 py-2 font-mono text-[11px] tracking-wide uppercase">
        <span className="text-foreground">reviewer</span>
        <span aria-hidden="true">&middot;</span>
        <span>local runner</span>
        <span className="ml-auto">example</span>
      </div>

      <div className="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)] font-mono text-xs">
        <nav
          aria-label="Terminal sections"
          className="border-border text-muted-foreground flex flex-col gap-1 border-r px-3 py-4"
        >
          {SECTIONS.map((section) => {
            const isCurrent = section === "reviews";
            return (
              <span
                key={section}
                // The focused row is filled, not merely coloured. A list you drive with
                // arrow keys has to say where you are without relying on hue.
                aria-current={isCurrent ? "true" : undefined}
                className={
                  isCurrent
                    ? "bg-foreground text-background -mx-1 rounded-sm px-1 font-semibold"
                    : ""
                }
              >
                &gt; {section}
              </span>
            );
          })}
        </nav>

        <div className="flex min-w-0 flex-col gap-4 px-4 py-4">
          <div>
            <p className="text-warning font-semibold">Reviews</p>
            <dl className="text-muted-foreground mt-2 flex flex-wrap gap-x-5 gap-y-1">
              <div className="flex gap-2">
                <dt>Reviews:</dt>
                <dd className="text-foreground">10</dd>
              </div>
              <div className="flex gap-2">
                <dt>Findings:</dt>
                <dd className="text-foreground">10</dd>
              </div>
            </dl>
            <dl className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
              {SEVERITIES.map((severity) => (
                <div key={severity.label} className="flex gap-1.5">
                  <dt className="text-muted-foreground">{severity.label}:</dt>
                  <dd className={severity.tone}>{severity.count}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="min-w-0">
            <p className="text-warning font-semibold">Reviews table</p>
            <ul className="mt-2 flex flex-col gap-1">
              {ROWS.map((row) => (
                <li
                  key={`${row.repo}${row.pr}`}
                  aria-current={row.current ? "true" : undefined}
                  // A grid, not flex-wrap: at the hero's column width a wrapping row put
                  // the timestamp on its own line and the list stopped reading as a table.
                  className={
                    "grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-3 " +
                    (row.current
                      ? "bg-foreground text-background -mx-1 rounded-sm px-1 font-semibold"
                      : "text-muted-foreground")
                  }
                >
                  <span className="truncate">
                    {row.repo} {row.pr}
                  </span>
                  <span className="whitespace-nowrap">{row.findings}</span>
                </li>
              ))}
            </ul>
            <p className="text-muted-foreground mt-3">Press enter on a review row to open it.</p>
          </div>
        </div>
      </div>

      <div className="border-border text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 border-t px-4 py-2 font-mono text-[11px]">
        <span>
          <b className="text-foreground">tab</b> next pane
        </span>
        <span>
          <b className="text-foreground">&darr;&uarr;</b> move
        </span>
        <span>
          <b className="text-foreground">&crarr;</b> open
        </span>
        <span>
          <b className="text-foreground">esc</b> back
        </span>
      </div>
    </aside>
  );
}
