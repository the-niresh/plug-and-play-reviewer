import Link from "next/link";

const LINKS = [
  { href: "/docs", label: "Docs" },
  { href: "/dashboard", label: "Dashboard" },
] as const;

export function SiteNav() {
  return (
    <header className="border-b">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-6 py-3">
        <Link
          href="/"
          className="text-sm font-semibold tracking-tight focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
        >
          pr-reviewer
        </Link>
        <nav aria-label="Site" className="flex items-center gap-1">
          {LINKS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-muted-foreground hover:text-foreground rounded-md px-3 py-1.5 text-sm transition-colors focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
