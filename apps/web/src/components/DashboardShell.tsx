"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import type { ReactNode } from "react";

import { SiteNav } from "@/components/SiteNav";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// Approvals, Evals and Connectors used to live here too, each reading a session from the
// local runner's own loopback API. They moved to the runner's own web surface (task
// 33.C5): a hosted https origin can never reach a loopback address on the viewer's
// machine, which is why those pages hung on "Loading" forever. Everything under
// /dashboard needs none of that -- it reads the viewer's GitHub sign-in cookie and calls
// the hosted control plane -- so this shell is a plain nav with nothing of its own to fetch.
const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard/reviews", label: "Reviews" },
  { href: "/dashboard/profile", label: "Profile" },
  { href: "/dashboard/settings", label: "Settings" },
] as const;

type Profile = { login: string | null; github_user_id: number } | null;

function initialsFor(login: string | null): string {
  return login ? login.slice(0, 2).toUpperCase() : "?";
}

/** GitHub serves any account's picture from its numeric id, so there is nothing to store
 *  and nothing to keep in sync when someone changes their photo. This is the one
 *  third-party request on the dashboard, and it is the viewer's own avatar on a page they
 *  reached by signing in with GitHub; it carries no identifier GitHub does not already
 *  have. It never appears on the marketing pages, which stay request-free. */
function avatarUrlFor(githubUserId: number): string {
  return `https://avatars.githubusercontent.com/u/${githubUserId}?v=4&s=96`;
}

function UserMenu({ profile }: { profile: Profile }) {
  const router = useRouter();
  const [isSigningOut, setIsSigningOut] = useState(false);

  if (!profile) return null;

  async function handleSignOut() {
    setIsSigningOut(true);
    try {
      await fetch("/api/auth/github/sign-out", { method: "POST", credentials: "same-origin" });
    } finally {
      // A full navigation, not router.refresh(): every /dashboard page is a Server
      // Component that already reads the sign-in cookie once at request time, so this is
      // what makes them re-render as signed out instead of serving a stale, cached "ok".
      router.push("/");
      router.refresh();
    }
  }

  const label = profile.login ?? "your account";

  return (
    <div className="ml-auto flex items-center">
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label={`Account menu for ${label}`}
          className="focus-visible:ring-ring/50 rounded-full focus-visible:ring-[3px] focus-visible:outline-none"
        >
          <Avatar size="default">
            {/* Empty alt: the trigger's aria-label already names this control, and a
                second name here would be read out twice. */}
            <AvatarImage src={avatarUrlFor(profile.github_user_id)} alt="" />
            <AvatarFallback>{initialsFor(profile.login)}</AvatarFallback>
          </Avatar>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel className="truncate">{label}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            disabled={isSigningOut}
            onSelect={(event) => {
              // Radix closes the menu on select and would unmount this handler's owner
              // mid-request; the sign-out finishes on its own and navigates.
              event.preventDefault();
              void handleSignOut();
            }}
          >
            {isSigningOut ? "Signing out..." : "Log out"}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

export function DashboardShell({
  children,
  profile,
}: {
  children: ReactNode;
  profile: Profile;
}) {
  const pathname = usePathname();

  return (
    <>
      <SiteNav />
      <header className="border-b">
        <div className="mx-auto flex w-full max-w-4xl flex-wrap items-center gap-x-6 gap-y-2 px-6 py-3">
          <nav aria-label="Dashboard" className="flex items-center gap-1">
            {NAV.map((item) => {
              // "/dashboard" itself must not stay lit for every nested route under it, so
              // it gets an exact match while the rest also match their own subpaths (a
              // single review page under /dashboard/reviews/[id] still shows "Reviews" as
              // current).
              const isCurrent =
                item.href === "/dashboard"
                  ? pathname === item.href
                  : pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={isCurrent ? "page" : undefined}
                  className="text-muted-foreground hover:text-foreground aria-[current=page]:text-foreground px-3 py-1.5 text-sm font-medium underline-offset-4 transition-colors aria-[current=page]:font-semibold aria-[current=page]:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <UserMenu profile={profile} />
        </div>
      </header>
      {children}
    </>
  );
}
