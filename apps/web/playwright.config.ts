import path from "path";
import { defineConfig, devices } from "@playwright/test";

const repoRoot = path.join(__dirname, "../..");
const localApi = process.env.NEXT_PUBLIC_LOCAL_API_ORIGIN ?? "http://127.0.0.1:8741";
const controlPlane = process.env.NEXT_PUBLIC_CONTROL_PLANE_ORIGIN ?? "http://127.0.0.1:8742";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  webServer: [
    {
      command: "bun run dev",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      // Without this the dev server inherited nothing, so next.config.ts saw no
      // NEXT_PUBLIC_CONTROL_PLANE_ORIGIN and src/lib/reviews.ts fell back to its
      // default. The app then talked to a real control plane while the config
      // carefully started stubs beside it that nothing ever called, and every
      // dashboard assertion timed out waiting for traffic that went elsewhere.
      // CONTROL_PLANE_INTERNAL_ORIGIN is set too because reviews.ts prefers it.
      env: {
        NEXT_PUBLIC_CONTROL_PLANE_ORIGIN: controlPlane,
        CONTROL_PLANE_INTERNAL_ORIGIN: controlPlane,
        NEXT_PUBLIC_LOCAL_API_ORIGIN: localApi,
      },
    },
    {
      command:
        "uv run reviewer start --host 127.0.0.1 --port 8741 --hosted-origin https://control.example.test",
      cwd: repoRoot,
      url: `${localApi}/onboarding/mode`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "python3 tests/control_plane_stub.py",
      url: `${controlPlane}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
