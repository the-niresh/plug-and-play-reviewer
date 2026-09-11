import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Atkinson_Hyperlegible, IBM_Plex_Mono, Newsreader } from "next/font/google";

import "./globals.css";
import { AnalyticsGate } from "@/components/AnalyticsGate";
import { ClientRuntime } from "@/components/ClientRuntime";
import { CookieNotice } from "@/components/CookieNotice";
import { PRODUCT_NAME, SUPPORT_EMAIL, TAGLINE, pageTitle, siteOrigin } from "@/lib/site";

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

/** Who publishes this and what the site is. Every value is a literal in this file, so
 *  nothing a visitor supplied reaches the JSON. */
const SITE_JSON_LD = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": `${siteOrigin()}/#website`,
      url: siteOrigin(),
      name: PRODUCT_NAME,
      description: TAGLINE,
      inLanguage: "en",
      publisher: { "@id": `${siteOrigin()}/#org` },
    },
    {
      "@type": "Organization",
      "@id": `${siteOrigin()}/#org`,
      name: PRODUCT_NAME,
      url: siteOrigin(),
      email: SUPPORT_EMAIL,
      sameAs: ["https://github.com/the-niresh/plug-and-play-reviewer"],
    },
  ],
};

export const metadata: Metadata = {
  metadataBase: new URL(siteOrigin()),
  title: pageTitle(),
  description:
    "The PR reviewer that runs on your machine. Source, diffs, and model keys never leave it.",
  applicationName: PRODUCT_NAME,
  // robots.txt cannot say how large a preview may be, and a small preview is what a
  // result looks like when it loses to a competitor. These are per-page meta tags.
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
  openGraph: {
    type: "website",
    siteName: PRODUCT_NAME,
    locale: "en_US",
  },
  // Google Search Console needs a property before it will crawl a new domain on request,
  // and the meta tag is the verification method that survives a redeploy. Set the token
  // in Vercel; without it this renders nothing, which is the correct default.
  verification: process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION
    ? { google: process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION }
    : undefined,
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
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(SITE_JSON_LD) }}
        />
        <ClientRuntime />
        {children}
        <CookieNotice />
        <AnalyticsGate />
      </body>
    </html>
  );
}
