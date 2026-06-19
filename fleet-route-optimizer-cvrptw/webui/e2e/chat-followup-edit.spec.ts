import { expect, test, type Page } from "@playwright/test"
import { countTimelinePlaces, submitHomePrompt, waitForItinerary } from "./helpers"

async function sendChat(page: Page, message: string) {
  const input = page.locator("textarea").first()
  await expect(input).toBeVisible()
  await input.fill(message)
  await input.press("Enter")
}

test.describe("Web2 chat follow-up itinerary edits", () => {
  test("proposes and applies itinerary edits from chat follow-ups", async ({ page }) => {
    await submitHomePrompt(page, "build happy itinerary")
    await waitForItinerary(page)

    const beforeCount = await countTimelinePlaces(page)
    expect(beforeCount).toBeGreaterThanOrEqual(3)

    await page.getByRole("button", { name: /cafe/i }).click()
    await expect(page.getByText(/Type 'ap dung' to apply this edit/i)).toBeVisible({
      timeout: 30_000,
    })

    await sendChat(page, "ap dung")
    await expect(page.getByText(/Applied chat edit: add Cafe Muoi/i)).toBeVisible({
      timeout: 30_000,
    })
    await expect(page.getByRole("heading", { name: "Cafe Muoi" })).toBeVisible()

    const afterCafeCount = await countTimelinePlaces(page)
    expect(afterCafeCount).toBeGreaterThan(beforeCount)

    await sendChat(page, "giam chi phi")
    await expect(page.getByText(/lower paid attractions and reduce estimated cost/i)).toBeVisible({
      timeout: 30_000,
    })

    await sendChat(page, "ap dung")
    await expect(page.getByText(/Applied chat edit: lower paid attractions/i)).toBeVisible({
      timeout: 30_000,
    })
    await expect(page.getByText("Budget-friendly center")).toBeVisible()
  })
})
