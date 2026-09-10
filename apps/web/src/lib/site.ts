// One name, one origin, one place to change them.
//
// Before this, the name was hardcoded in 14 metadata blocks and the domain in 3 more,
// so a rename meant editing every route and silently missing one. Everything below flows
// from these two, which is why the rename that follows is a one-line change.
export const PRODUCT_NAME = "Plug and Play Reviewer";

// Deliberately still reviewer.niresh.tech: that host is the live control plane and answers
// /health today (docs/DEMO.md). Flip this only once the new domain is bought and pointed,
// or the working deploy breaks.
const DEFAULT_ORIGIN = "https://reviewer.niresh.tech";

export function siteOrigin(): string {
  return process.env.NEXT_PUBLIC_SITE_ORIGIN ?? DEFAULT_ORIGIN;
}

/** The bare host, for display in body copy and the OG card. */
export function siteHost(): string {
  return siteOrigin().replace(/^https?:\/\//, "");
}

/** `Section | Product`, or just `Product` for the home page. */
export function pageTitle(section?: string): string {
  return section ? `${section} | ${PRODUCT_NAME}` : PRODUCT_NAME;
}
