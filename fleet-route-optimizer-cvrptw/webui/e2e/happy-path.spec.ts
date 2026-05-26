import { expect, test } from "@playwright/test"
import { submitHomePrompt, waitForItinerary } from "./helpers"

test.describe("P3 happy path", () => {
  test("builds full itinerary from complete prompt", async ({ page }) => {
    await submitHomePrompt(page, "Đi Huế 2 ngày ngân sách 1 triệu")
    await waitForItinerary(page)
    await expect(page.getByRole("button", { name: "Huế 2 ngày" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Đại Nội Huế" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Chùa Thiên Mụ" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Quán chay Thanh Liễu" })).toBeVisible()
  })
})
