import { expect, test } from "@playwright/test"

test.describe("Mock gateway admin smoke", () => {
  test("admin POI list and QA summary endpoints respond", async ({ request }) => {
    const gatewayUrl = process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8001"

    const pois = await request.get(`${gatewayUrl}/v1/admin/pois?limit=5`)
    expect(pois.ok()).toBeTruthy()
    const poisBody = await pois.json()
    expect(poisBody.items.length).toBeGreaterThan(0)

    const summary = await request.get(`${gatewayUrl}/v1/admin/pois/qa-summary`)
    expect(summary.ok()).toBeTruthy()
    const summaryBody = await summary.json()
    expect(summaryBody.wrong_coords).toBeGreaterThanOrEqual(0)
    expect(summaryBody.missing_embedding).toBeGreaterThanOrEqual(0)
  })
})
