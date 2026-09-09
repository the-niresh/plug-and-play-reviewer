import type { MetadataRoute } from "next";

import { siteOrigin } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = siteOrigin();
  return [
    { url: `${base}/`, changeFrequency: "weekly", priority: 1 },
    { url: `${base}/docs`, changeFrequency: "monthly", priority: 0.8 },
    { url: `${base}/docs/agents`, changeFrequency: "monthly", priority: 0.6 },
    { url: `${base}/scorecard`, changeFrequency: "weekly", priority: 0.7 },
  ];
}
