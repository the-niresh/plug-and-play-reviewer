import { expect, test, type Page } from "@playwright/test";
import fs from "fs";
import path from "path";

const OUT = path.join(
  __dirname,
  "../../../docs/reports/frontend-dashboard-bug-pass-screenshots",
);

const PUBLIC_ROUTES = [
  "/",
  "/docs",
  "/docs/agents",
  "/scorecard",
  "/connect",
  "/dashboard",
] as const;

async function collectConsoleErrors(page: Page): Promise<string[]> {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      errors.push(msg.text());
    }
  });
  page.on("pageerror", (error) => {
    errors.push(error.message);
  });
  return errors;
}

async function screenshot(page: Page, name: string) {
  fs.mkdirSync(OUT, { recursive: true });
  await page.screenshot({ path: path.join(OUT, name), fullPage: true });
}

async function auditRoute(page: Page, route: string, prefix: string) {
  const errors = await collectConsoleErrors(page);
  await page.goto(route);
  await page.waitForLoadState("networkidle");
  await screenshot(page, `${prefix}${route === "/" ? "landing" : route.replace(/\//g, "-").slice(1)}.png`);
  expect(errors, `console errors on ${route}`).toEqual([]);
  const overlapping = await page.evaluate(() => {
    const nodes = Array.from(document.querySelectorAll("body *")).filter((el) => {
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden") return false;
      if (style.position === "absolute" && style.width === "1px") return false;
      const rect = el.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return false;
      const text = (el as HTMLElement).innerText?.trim() ?? "";
      return text.length >= 2;
    });
    for (let i = 0; i < nodes.length; i += 1) {
      const elA = nodes[i];
      const a = elA.getBoundingClientRect();
      for (let j = i + 1; j < nodes.length; j += 1) {
        const elB = nodes[j];
        if (elA.contains(elB) || elB.contains(elA)) continue;
        const b = elB.getBoundingClientRect();
        const overlap =
          a.left < b.right &&
          a.right > b.left &&
          a.top < b.bottom &&
          a.bottom > b.top;
        if (!overlap) continue;
        const area =
          (Math.min(a.right, b.right) - Math.max(a.left, b.left)) *
          (Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
        if (area > 400) {
          return `${elA.tagName} overlaps ${elB.tagName}`;
        }
      }
    }
    return null;
  });
  expect(overlapping, `text overlap on ${route}`).toBeNull();
}

test.describe("frontend dashboard bug pass", () => {
  test("desktop 1440 public routes and dashboard sign-in gate", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    for (const route of PUBLIC_ROUTES) {
      await auditRoute(page, route, "after-desktop-");
    }
    await expect(page.getByRole("link", { name: /sign in with github/i })).toBeVisible();
  });

  test("mobile 390 landing scorecard connect dashboard", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    for (const route of ["/", "/scorecard", "/connect", "/dashboard"] as const) {
      await auditRoute(page, route, "after-mobile-");
    }
  });

  test("landing to dashboard navigation keeps webpack healthy", async ({ page }) => {
    const errors = await collectConsoleErrors(page);
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.goto("/docs");
    await page.waitForLoadState("networkidle");
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("heading", { name: /^dashboard$/i })).toBeVisible();
    expect(errors.filter((e) => /webpack|__webpack_require__/i.test(e))).toEqual([]);
  });

  test("keyboard tab reaches primary nav links on landing", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await page.keyboard.press("Tab");
    const focused = page.locator(":focus");
    await expect(focused).toBeVisible();
    const tag = await focused.evaluate((el) => el.tagName);
    expect(["A", "BUTTON", "INPUT"]).toContain(tag);
  });

  test("internal links respond 200", async ({ page, request }) => {
    const base = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";
    for (const route of PUBLIC_ROUTES) {
      const response = await request.get(`${base}${route}`);
      expect(response.status(), route).toBeLessThan(400);
    }
  });
});
