import { test } from "@playwright/test"
import { expectItineraryStructure, submitHomePrompt } from "./helpers-live"

test.describe("Live P8 happy path", () => {
  test("builds itinerary from complete prompt via real Gateway", async ({ page }) => {
    await submitHomePrompt(page, "Đi Huế 2 ngày ngân sách 1 triệu, thích văn hóa")
    await expectItineraryStructure(page, 2)
  })
})
