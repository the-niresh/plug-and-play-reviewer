import { expect, test, type Page } from "@playwright/test";
import fs from "fs";
import path from "path";

const OUT = path.join(
  __dirname,
  "../../../docs/reports/frontend-launch-qa-screenshots",
);

async function shot(page: Page, name: string) {
  fs.mkdirSync(OUT, { recursive: true });
  await page.screenshot({ path: path.join(OUT, name), fullPage: true });
}

test.describe("launch QA screenshots", () => {
  test("desktop public routes", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    for (const route of ["/", "/docs", "/docs/agents", "/scorecard", "/connect"]) {
      await page.goto(route);
      await page.waitForLoadState("networkidle");
      const slug = route === "/" ? "landing" : route.replace(/\//g, "-").slice(1);
      await shot(page, `desktop-${slug}.png`);
    }
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");
    await shot(page, "desktop-dashboard.png");
  });

  test("mobile landing overlap check", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await shot(page, "mobile-landing.png");
    await page.goto("/scorecard");
    await page.waitForLoadState("networkidle");
    await shot(page, "mobile-scorecard.png");
  });

  test("metadata routes respond", async ({ request }) => {
    for (const route of ["/sitemap.xml", "/robots.txt", "/opengraph-image"]) {
      const response = await request.get(route);
      expect(response.status(), route).toBe(200);
    }
  });
});
