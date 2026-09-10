"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Logo } from "@/components/Logo";
import { PRODUCT_NAME } from "@/lib/site";

const LINKS = [
  { href: "/docs", label: "Docs" },
  { href: "/scorecard", label: "Scorecard" },
  { href: "/dashboard", label: "Dashboard" },
] as const;

function isNavCurrent(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteNav() {
  const pathname = usePathname();

  return (
    <header className="border-border/80 bg-background/85 sticky top-0 z-40 border-b backdrop-blur-sm">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-6 py-3">
        <Link
          href="/"
          aria-current={pathname === "/" ? "page" : undefined}
          className="text-foreground hover:text-primary focus-visible:ring-ring/50 aria-[current=page]:text-primary inline-flex items-center gap-2.5 text-sm font-semibold tracking-tight transition-colors focus-visible:ring-[3px] focus-visible:outline-none"
        >
          <Logo className="size-7 shrink-0" title={PRODUCT_NAME} />
          {/* The wordmark plus three links overflow a 390px viewport, so below sm the
              logo carries the brand on its own. Truncating instead just produced a
              clipped name and a page that still scrolled sideways. */}
          <span className="hidden sm:inline">{PRODUCT_NAME}</span>
          <span className="sr-only sm:hidden">{PRODUCT_NAME}</span>
        </Link>
        <nav aria-label="Site" className="flex shrink-0 items-center gap-1">
          {LINKS.map((item) => {
            const isCurrent = isNavCurrent(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isCurrent ? "page" : undefined}
                className="text-muted-foreground hover:text-foreground hover:bg-secondary aria-[current=page]:bg-secondary aria-[current=page]:text-foreground rounded-md px-3 py-1.5 text-sm transition-colors aria-[current=page]:font-semibold focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
