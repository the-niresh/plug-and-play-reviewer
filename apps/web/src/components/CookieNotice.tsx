"use client";

/** Consent gate for analytics.
 *
 *  The only cookie this site sets on its own is the sign-in session cookie, which is
 *  strictly necessary and therefore not consentable: without it you cannot be signed in.
 *  Analytics is the part that needs a real choice, so this stores one and
 *  AnalyticsGate refuses to mount the script until the answer is "accepted".
 *  A banner that renders while the tracker already loaded is theatre, not consent. */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

export const CONSENT_KEY = "ppr-analytics-consent";
export type Consent = "accepted" | "declined";

/** Reads stored consent. Returns null when unset, unreadable, or storage is blocked. */
export function readConsent(): Consent | null {
  try {
    const value = window.localStorage.getItem(CONSENT_KEY);
    return value === "accepted" || value === "declined" ? value : null;
  } catch {
    // Private windows and blocked site data throw on access, not just return null.
    return null;
  }
}

function writeConsent(value: Consent): void {
  try {
    window.localStorage.setItem(CONSENT_KEY, value);
  } catch {
    // Nothing to do. The gate stays closed for this session, which is the safe direction.
  }
  window.dispatchEvent(new CustomEvent(CONSENT_KEY));
}

export function CookieNotice() {
  // Starts hidden so the server and first client paint agree. The effect decides.
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(readConsent() === null);
  }, []);

  const answer = useCallback((value: Consent) => {
    writeConsent(value);
    setVisible(false);
  }, []);

  if (!visible) {
    return null;
  }

  return (
    <div
      role="region"
      aria-label="Analytics consent"
      className="bg-card border-border fixed inset-x-0 bottom-0 z-50 border-t"
    >
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-muted-foreground max-w-prose text-sm leading-relaxed">
          We use one strictly necessary cookie to keep you signed in. Separately, we
          would like to count anonymous page views to see which docs people actually
          read. That part is your choice, and nothing loads until you pick.{" "}
          <Link
            href="/privacy"
            className="text-primary rounded-sm underline-offset-4 hover:underline focus-visible:ring-ring/50 focus-visible:ring-[3px] focus-visible:outline-none"
          >
            Read the privacy policy
          </Link>
          .
        </p>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={() => answer("declined")}
            className="border-border hover:bg-muted focus-visible:ring-ring/50 rounded-md border px-4 py-2 text-sm font-medium transition-colors focus-visible:ring-[3px] focus-visible:outline-none"
          >
            Decline
          </button>
          <button
            type="button"
            onClick={() => answer("accepted")}
            className="bg-primary text-primary-foreground hover:bg-primary/90 focus-visible:ring-ring/50 rounded-md px-4 py-2 text-sm font-medium transition-colors focus-visible:ring-[3px] focus-visible:outline-none"
          >
            Accept analytics
          </button>
        </div>
      </div>
    </div>
  );
}
