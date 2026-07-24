import { defineConfig, devices } from "@playwright/test";

/**
 * Config e2e do Catálogo Público (feature 185) — sem login (visitante anônimo), mesma premissa
 * de `apps/internal/playwright.config.ts`: o backend Flask deve já estar rodando contra
 * `manto_local` (ver `scripts/db/run-local.ps1`).
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://localhost:5175",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5175",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
