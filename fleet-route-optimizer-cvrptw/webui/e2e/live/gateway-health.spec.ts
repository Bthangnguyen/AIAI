import { expect, test } from "@playwright/test"

test.describe("Live gateway health", () => {
  test("real Gateway health is ready", async ({ request }) => {
    const response = await request.get("http://localhost:8001/v1/trip/health")
    expect(response.ok()).toBeTruthy()
    const body = await response.json()
    expect(body.status).toBe("ready")
  })
})
