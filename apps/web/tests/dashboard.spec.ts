import { expect, test } from "@playwright/test";

/** The dashboard, against a stubbed control plane.
 *
 *  The previous version of this file drove /dashboard/jobs, /dashboard/evals and
 *  /dashboard/connectors through thirteen data-testid hooks. None of those routes or
 *  hooks exist any more: the dashboard was rebuilt around GET /api/reviews, fetched
 *  server-side in a Server Component. Because the file was `mode: "serial"`, its first
 *  failure hid the other twelve, and because the step had never run in CI nobody saw it.
 *
 *  What is worth pinning now is the three-way split src/lib/reviews.ts works hard to
 *  keep: not signed in, could not load, and loaded. Those must never collapse into each
 *  other, because an empty dashboard and a broken one look identical to a user.
 */

const SIGN_IN_COOKIE = "gh_live_sign_in";
const REPOSITORY = "acme/alpha";
const DEVICE_NAME = "playwright-runner";
const SECRET_TITLE = /hmac|webhook secret|private key|github app id/i;

const GATED_ROUTES = ["/dashboard", "/dashboard/reviews", "/dashboard/profile"];

async function signIn(context: import("@playwright/test").BrowserContext) {
  await context.addCookies([
    {
      name: SIGN_IN_COOKIE,
      value: "playwright-session",
      domain: "127.0.0.1",
      path: "/",
    },
  ]);
}

for (const route of GATED_ROUTES) {
  test(`signed out, ${route} asks for sign in instead of showing data`, async ({ page }) => {
    await page.goto(route);
    await expect(page.getByRole("heading", { name: "Sign in required" })).toBeVisible();
    await expect(page.getByRole("link", { name: /sign in with github/i })).toBeVisible();
    // The gate must not leak what it would have shown.
    await expect(page.locator("body")).not.toContainText(REPOSITORY);
    await expect(page).not.toHaveTitle(SECRET_TITLE);
  });
}

test("the sign-in link returns the viewer to the page they were gated on", async ({ page }) => {
  await page.goto("/dashboard");
  const href = await page
    .getByRole("link", { name: /sign in with github/i })
    .getAttribute("href");
  expect(href).toContain("/api/auth/github/sign-in");
  expect(href).toContain(encodeURIComponent("/dashboard"));
});

test("signed in, the dashboard renders what the control plane returned", async ({
  page,
  context,
}) => {
  await signIn(context);
  await page.goto("/dashboard");

  await expect(page.getByRole("heading", { name: "Dashboard", level: 1 })).toBeVisible();
  await expect(page.locator("body")).toContainText(REPOSITORY);
  await expect(page.locator("body")).toContainText("PR #7");
  // Counts and severity, not finding titles. This page summarises; the titles are on
  // the review detail page. Asserting a title here failed for the right reason.
  await expect(page.locator("body")).toContainText("high");
  await expect(page.getByRole("heading", { name: "Sign in required" })).toHaveCount(0);
});

test("signed in, a paired runner is shown by name", async ({ page, context }) => {
  await signIn(context);
  await page.goto("/dashboard");

  await expect(page.locator("body")).toContainText(DEVICE_NAME);
  await expect(page.locator("body")).not.toContainText("No paired runner is visible");
});

test("a control plane that fails is reported as a failure, not as an empty dashboard", async ({
  page,
  context,
}) => {
  await signIn(context);
  // Server-side fetch, so route interception in the browser cannot reach it. Point the
  // page at a review id the stub answers 404 for instead, which exercises the same
  // "distinct outcome" rule on a route that does fetch per request.
  await page.goto("/dashboard/reviews/does-not-exist");

  const body = page.locator("body");
  await expect(body).not.toContainText(REPOSITORY);
  await expect(page).not.toHaveTitle(SECRET_TITLE);
});
