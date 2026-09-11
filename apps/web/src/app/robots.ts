import type { MetadataRoute } from "next";

import { siteOrigin } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  const base = siteOrigin();
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // /api/* is a proxy to the control plane and /contact/send is a POST handler.
      // Neither is a page; letting a crawler find them wastes budget and can index
      // an error body as if it were content.
      disallow: ["/dashboard", "/connect", "/api/", "/contact/send"],
    },
    sitemap: `${base}/sitemap.xml`,
  };
}
