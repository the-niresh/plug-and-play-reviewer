// One name, one origin, one place to change them.
//
// Before this, the name was hardcoded in 14 metadata blocks and the domain in 3 more,
// so a rename meant editing every route and silently missing one. Everything below flows
// from these two, which is why the rename that follows is a one-line change.
export const PRODUCT_NAME = "Plug and Play Reviewer";

/** The keyword phrase, in the words someone would actually search for.
 *
 *  It carries "PR reviewer" because that is the search term, and the brand name alone
 *  says nothing about what the product does. Title Case on purpose: a title is a name,
 *  and sentence case in a search result reads like a fragment. */
export const TAGLINE = "Private AI PR Reviewer for GitHub";

/** Where this website lives. */
const DEFAULT_SITE_ORIGIN = "https://plugandplayreviewer.online";

/** Where the hosted control plane answers webhooks and the runner points.
 *
 *  Deliberately a different host from the site, and deliberately a separate constant.
 *  Conflating the two is how docs end up telling people to point their runner at the
 *  marketing page. Still reviewer.niresh.tech: that host answers /health today. Flip it
 *  only once the replacement answers /health on its final hostname. */
const DEFAULT_CONTROL_PLANE_ORIGIN = "https://reviewer.niresh.tech";

export function siteOrigin(): string {
  return process.env.NEXT_PUBLIC_SITE_ORIGIN ?? DEFAULT_SITE_ORIGIN;
}

export function controlPlaneOrigin(): string {
  return process.env.NEXT_PUBLIC_CONTROL_PLANE_ORIGIN ?? DEFAULT_CONTROL_PLANE_ORIGIN;
}

function bareHost(origin: string): string {
  return origin.replace(/^https?:\/\//, "");
}

/** The bare host of this website, for display in body copy and the OG card. */
export function siteHost(): string {
  return bareHost(siteOrigin());
}

/** The bare host of the control plane, for setup commands and the privacy page. */
export function controlPlaneHost(): string {
  return bareHost(controlPlaneOrigin());
}

/** `Section | Product` for a subpage, `Product | Tagline` for the home page.
 *
 *  The home page gets the tagline because that title is the one a search result shows
 *  for the domain itself, and "Plug and Play Reviewer" on its own does not say it
 *  reviews pull requests. Subpages keep the brand at the end where a reader expects it.
 *  Section names are Title Case; every title here stays under 60 characters, which is
 *  roughly where Google truncates. */
export function pageTitle(section?: string): string {
  return section ? `${section} | ${PRODUCT_NAME}` : `${PRODUCT_NAME} | ${TAGLINE}`;
}
