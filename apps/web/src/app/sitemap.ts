import type { MetadataRoute } from "next";

import { siteOrigin } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = siteOrigin();
  // A single build-time date rather than a per-page one: these pages ship together,
  // and a fabricated per-page date is worse than an honest shared one.
  const lastModified = new Date();
  return [
    { url: `${base}/`, lastModified, changeFrequency: "weekly", priority: 1 },
    { url: `${base}/docs`, lastModified, changeFrequency: "monthly", priority: 0.8 },
    { url: `${base}/docs/agents`, lastModified, changeFrequency: "monthly", priority: 0.6 },
    { url: `${base}/scorecard`, lastModified, changeFrequency: "weekly", priority: 0.7 },
    { url: `${base}/contact`, lastModified, changeFrequency: "yearly", priority: 0.5 },
    { url: `${base}/privacy`, lastModified, changeFrequency: "yearly", priority: 0.3 },
    { url: `${base}/terms`, lastModified, changeFrequency: "yearly", priority: 0.3 },
  ];
}
