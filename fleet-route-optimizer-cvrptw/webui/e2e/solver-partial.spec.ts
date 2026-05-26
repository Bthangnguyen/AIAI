import { expect, test } from "@playwright/test"
import { submitHomePrompt, waitForItinerary } from "./helpers"

test.describe("P4 solver partial / low budget", () => {
  test("shows constraint suggestions and warning toast", async ({ page }) => {
    await submitHomePrompt(page, "mock-partial Đi Huế 2 ngày 800k")
    await waitForItinerary(page)
    await expect(page.getByText("Gợi ý chỉnh lịch trình")).toBeVisible()
    await expect(page.getByText(/Ngân sách thấp/i)).toBeVisible()
    await expect(page.getByText(/cảnh báo/i)).toBeVisible()
    await expect(page.getByRole("button", { name: /Bớt \d+ điểm tham quan/i })).toBeVisible()
  })
})
