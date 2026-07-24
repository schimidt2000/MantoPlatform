import { defineConfig, devices } from "@playwright/test";

/**
 * Config e2e do app interno (feature 180). Sobe só o Vite dev server — o backend Flask deve
 * já estar rodando contra `manto_local` (ver `scripts/db/run-local.ps1`), mesma premissa de
 * toda verificação funcional do projeto.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "list",
  globalSetup: "./e2e/global-setup.ts",
  use: {
    baseURL: "http://localhost:5173",
    storageState: "e2e/.auth/state.json",
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
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
