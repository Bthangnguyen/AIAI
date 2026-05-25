import { defineConfig, devices } from "@playwright/test"

const gatewayUrl = process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8001"
const webPort = process.env.PLAYWRIGHT_WEB_PORT ?? "3000"
const baseURL = `http://localhost:${webPort}`

export default defineConfig({
  testDir: "./e2e",
  testIgnore: ["**/live/**"],
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: "list",
  timeout: 90_000,
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "npm run mock:gateway",
      url: `${gatewayUrl}/v1/trip/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: `npm run dev -- -p ${webPort}`,
      url: baseURL,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        ...process.env,
        NEXT_PUBLIC_GATEWAY_URL: gatewayUrl,
        PORT: webPort,
      },
    },
  ],
})
