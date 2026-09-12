import { expect, test } from "@playwright/test";

/** The local onboarding page.
 *
 *  Three tests here used to fill a model-key field on this page and assert a POST to
 *  /onboarding/model-key. That field was deliberately removed: the key belongs in the
 *  machine's keychain via the TUI, and the page now says so in as many words. Asserting
 *  the old behaviour meant the suite was guarding the return of a trust-boundary
 *  violation. The property those tests cared about -- a stored key is never echoed back
 *  -- is covered where the endpoint actually lives, in tests/runner/test_local_auth.py,
 *  which checks the key is absent from the body, the headers and the parsed JSON.
 */

const MODEL_KEY_CARD = /model key/i;

test("the page covers GitHub sign-in, the model key rule, and runtime mode", async ({
  page,
}) => {
  await page.goto("/onboarding");

  await expect(page.getByText("GitHub", { exact: true })).toBeVisible();
  await expect(page.getByText(MODEL_KEY_CARD).first()).toBeVisible();
  await expect(page.getByText(/runtime mode/i).first()).toBeVisible();
});

test("the model key card sends people to the TUI and offers no field of its own", async ({
  page,
}) => {
  await page.goto("/onboarding");

  await expect(page.getByText(/add your provider key in the tui, not here/i)).toBeVisible();
  await expect(page.getByText(/never sent to this site/i)).toBeVisible();

  // The point of the card. A key input here would put a model key on a web page, which
  // is the one thing the two-process split exists to prevent.
  await expect(page.getByLabel(/api key|model key/i)).toHaveCount(0);
  await expect(page.locator('input[type="password"]')).toHaveCount(0);
});

test("disabled features are the list GET /onboarding/mode returned", async ({ page }) => {
  const modeResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/onboarding/mode") && response.request().method() === "GET",
  );
  await page.goto("/onboarding");
  const body = (await (await modeResponse).json()) as { disabled_features: string[] };

  // The list element is always rendered, empty or not, so count the items in it rather
  // than the list itself. An empty list and a missing list are different things.
  const list = page.getByTestId("disabled-features");
  await expect(list.getByRole("listitem")).toHaveCount(body.disabled_features.length);
  if (body.disabled_features.length === 0) {
    return;
  }
  for (const feature of body.disabled_features) {
    await expect(list).toContainText(feature);
  }
});
