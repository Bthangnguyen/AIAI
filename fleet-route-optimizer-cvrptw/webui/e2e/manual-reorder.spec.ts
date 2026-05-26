import { expect, test } from "@playwright/test"
import { submitHomePrompt, waitForItinerary } from "./helpers"

test.describe("Web2 manual POI reorder", () => {
  test("move POI down shows manual badge and apply route", async ({ page }) => {
    await submitHomePrompt(page, "Đi Huế 2 ngày ngân sách 1 triệu")
    await waitForItinerary(page)

    await page.getByRole("button", { name: "Timeline" }).click()
    const moveDown = page.getByRole("button", { name: "Di chuyển xuống" }).first()
    await moveDown.click()

    await expect(page.getByText("Thủ công").first()).toBeVisible()
    await expect(page.getByRole("button", { name: "Cập nhật lộ trình" })).toBeVisible()

    await page.getByRole("button", { name: "Cập nhật lộ trình" }).click()
    await expect(page.getByText(/Đã cập nhật lộ trình theo thứ tự thủ công/)).toBeVisible({
      timeout: 30_000,
    })
  })
})
