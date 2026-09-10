import type { ReactNode } from "react";
import { pageTitle } from "@/lib/site";

export const metadata = {
  title: pageTitle("Onboarding"),
  description:
    "Pair a local runner with GitHub. This page needs the daemon on your machine.",
};

export default function OnboardingLayout({ children }: { children: ReactNode }) {
  return children;
}
