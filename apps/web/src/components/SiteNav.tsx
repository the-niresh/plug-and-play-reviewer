"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { GithubMark } from "@/components/github-mark";
import { Logo } from "@/components/Logo";
import { PRODUCT_NAME } from "@/lib/site";

const GITHUB_REPO_URL = "https://github.com/the-niresh/plug-and-play-reviewer";

const LINKS = [
  { href: "/docs", label: "Docs" },
  { href: "/scorecard", label: "Scorecard" },
  { href: "/contact", label: "Talk to us" },
  { href: "/dashboard", label: "Dashboard" },
] as const;

function isNavCurrent(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteNav() {
  const pathname = usePathname();

  return (
    <header className="border-border bg-background/95 sticky top-0 z-40 border-b backdrop-blur-sm">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-2 px-4 py-2.5 sm:gap-4 sm:px-6 sm:py-3">
        <Link
          href="/"
          aria-current={pathname === "/" ? "page" : undefined}
          className="text-foreground focus-visible:ring-ring/50 aria-[current=page]:border-foreground inline-flex min-w-0 shrink items-center gap-2.5 text-sm font-semibold tracking-tight transition-colors focus-visible:ring-[3px] focus-visible:outline-none aria-[current=page]:border-b-2 aria-[current=page]:pb-0.5"
        >
          <Logo className="size-10 shrink-0" title={PRODUCT_NAME} variant="color" />
          <span className="hidden truncate sm:inline">{PRODUCT_NAME}</span>
          <span className="sr-only sm:hidden">{PRODUCT_NAME}</span>
        </Link>
        <nav
          aria-label="Site"
          className="flex min-w-0 shrink items-center gap-0.5 sm:gap-1"
        >
          {LINKS.map((item) => {
            const isCurrent = isNavCurrent(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isCurrent ? "page" : undefined}
                className="text-muted-foreground hover:text-foreground aria-[current=page]:text-foreground aria-[current=page]:border-foreground px-2 py-1.5 text-xs transition-colors aria-[current=page]:border-b-2 aria-[current=page]:font-semibold focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none sm:px-3 sm:text-sm"
              >
                {item.label}
              </Link>
            );
          })}
          <a
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground ml-0.5 inline-flex shrink-0 items-center gap-1 px-2 py-1.5 text-xs underline-offset-4 transition-colors hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none sm:ml-1 sm:gap-1.5 sm:px-3 sm:text-sm"
          >
            <GithubMark className="size-3.5 sm:size-4" />
            <span className="hidden md:inline">View on GitHub</span>
            <span className="sr-only md:hidden">View on GitHub</span>
          </a>
        </nav>
      </div>
    </header>
  );
}
