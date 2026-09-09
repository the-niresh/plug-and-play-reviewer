import { cookies } from "next/headers";
import type { ReactNode } from "react";

import { DashboardShell } from "@/components/DashboardShell";
import { fetchProfile } from "@/lib/profile";

export const metadata = {
  title: "Dashboard | PR Reviewer",
  description: "Signed-in review jobs, findings, and repository connections.",
};

export default async function DashboardLayout({ children }: { children: ReactNode }) {
  const cookieStore = await cookies();
  const result = await fetchProfile(cookieStore.toString());
  // Signed out or unreachable: the shell just shows no avatar/logout, and whichever page
  // is under it renders its own SignInPrompt -- this layout never blocks on that.
  const profile = result.kind === "ok" ? result.profile : null;

  return <DashboardShell profile={profile}>{children}</DashboardShell>;
}
