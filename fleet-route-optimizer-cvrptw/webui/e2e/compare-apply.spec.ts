import { expect, test } from "@playwright/test"
import { countTimelinePlaces, openCompareTab, submitHomePrompt, waitForItinerary } from "./helpers"

test.describe("Web2 compare apply variant", () => {
  test("apply Chill reduces timeline POI count and switches to split view", async ({ page }) => {
    await submitHomePrompt(page, "Đi Huế 2 ngày ngân sách 1 triệu")
    await waitForItinerary(page)

    const beforeCount = await countTimelinePlaces(page)
    expect(beforeCount).toBeGreaterThanOrEqual(3)

    await openCompareTab(page)
    await page.getByRole("button", { name: "Áp dụng phương án này" }).nth(2).click()
    await expect(page.getByText(/Đã áp dụng lộ trình Thoải mái/)).toBeVisible()

    const afterCount = await countTimelinePlaces(page)
    expect(afterCount).toBeLessThan(beforeCount)
    await expect(page.getByRole("heading", { name: "Chùa Thiên Mụ" })).toBeVisible()
  })
})
