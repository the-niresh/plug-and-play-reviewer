import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import { Atkinson_Hyperlegible, IBM_Plex_Mono, Newsreader } from "next/font/google";

import "./globals.css";
import { ClientRuntime } from "@/components/ClientRuntime";
import { siteOrigin } from "@/lib/site";

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
  title: "PR Reviewer",
  description:
    "The PR reviewer that runs on your machine. Source, diffs, and model keys never leave it.",
  openGraph: {
    type: "website",
    siteName: "PR Reviewer",
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
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
