export const PRODUCT_NAME = "PR Reviewer";

export function siteOrigin(): string {
  return process.env.NEXT_PUBLIC_SITE_ORIGIN ?? "https://reviewer.niresh.tech";
}
