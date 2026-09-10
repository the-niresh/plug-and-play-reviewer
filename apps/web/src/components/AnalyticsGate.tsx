"use client";

/** Mounts Vercel Analytics and Speed Insights only after the visitor accepts.
 *
 *  Both were previously mounted unconditionally in the root layout, which meant the
 *  site was collecting before it ever asked. Keeping the mount behind stored consent
 *  is the whole point: declining has to actually prevent the script, not just hide a
 *  banner over it. */

import { useEffect, useState } from "react";
import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";

import { CONSENT_KEY, readConsent } from "@/components/CookieNotice";

export function AnalyticsGate() {
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    const sync = () => setAllowed(readConsent() === "accepted");
    sync();
    // Same tab: CookieNotice fires this after writing. Other tabs: storage event.
    window.addEventListener(CONSENT_KEY, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(CONSENT_KEY, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  if (!allowed) {
    return null;
  }

  return (
    <>
      <Analytics />
      <SpeedInsights />
    </>
  );
}
