import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Atkinson_Hyperlegible, IBM_Plex_Mono, Newsreader } from "next/font/google";

import "./globals.css";
import { AnalyticsGate } from "@/components/AnalyticsGate";
import { ClientRuntime } from "@/components/ClientRuntime";
import { CookieNotice } from "@/components/CookieNotice";
import { PRODUCT_NAME, pageTitle, siteOrigin } from "@/lib/site";

const landingSans = Atkinson_Hyperlegible({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-landing-sans",
  display: "swap",
});

const landingDisplay = Newsreader({
  subsets: ["latin"],
  weight: ["500", "600"],
  variable: "--font-landing-display",
  display: "swap",
});

const landingMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-landing-mono",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(siteOrigin()),
  title: pageTitle(),
  description:
    "The PR reviewer that runs on your machine. Source, diffs, and model keys never leave it.",
  openGraph: {
    type: "website",
    siteName: PRODUCT_NAME,
  },
  twitter: {
    card: "summary_large_image",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      className={`${landingSans.variable} ${landingDisplay.variable} ${landingMono.variable}`}
    >
      <body>
        <ClientRuntime />
        {children}
        <CookieNotice />
        <AnalyticsGate />
      </body>
    </html>
  );
}
