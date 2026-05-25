import { defineConfig, devices } from "@playwright/test"

const gatewayUrl = process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8001"
const webPort = process.env.PLAYWRIGHT_WEB_PORT ?? "3000"
const baseURL = `http://localhost:${webPort}`

export default defineConfig({
  testDir: "./e2e/live",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: "list",
  timeout: 180_000,
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
  webServer: {
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
})
