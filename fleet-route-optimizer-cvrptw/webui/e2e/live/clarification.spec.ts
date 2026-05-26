import { expect, test } from "@playwright/test"
import { expectBudgetFollowUpOrItinerary, submitHomePrompt } from "./helpers-live"

test.describe("Live P8 clarification", () => {
  test("Huế 3 ngày triggers budget follow-up or builds itinerary", async ({ page }) => {
    await submitHomePrompt(page, "Đi Huế 3 ngày")
    await expectBudgetFollowUpOrItinerary(page)
  })
})
