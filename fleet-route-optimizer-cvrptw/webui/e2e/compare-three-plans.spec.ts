import { expect, test } from "@playwright/test"
import { openCompareTab, submitHomePrompt, waitForItinerary } from "./helpers"

test.describe("Web2 compare three plans", () => {
  test("shows Balanced, Budget, Chill columns after build", async ({ page }) => {
    await submitHomePrompt(page, "Đi Huế 2 ngày ngân sách 1 triệu")
    await waitForItinerary(page)
    await openCompareTab(page)

    await expect(page.getByRole("heading", { name: "Cân bằng" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Tiết kiệm" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Thoải mái" })).toBeVisible()
  })

  test("apply Chill keeps compare cache on revisit", async ({ page }) => {
    await submitHomePrompt(page, "Đi Huế 2 ngày ngân sách 1 triệu")
    await waitForItinerary(page)
    await openCompareTab(page)
    await expect(page.getByRole("heading", { name: "Thoải mái" })).toBeVisible()

    await page.getByRole("button", { name: "Áp dụng phương án này" }).nth(2).click()
    await expect(page.getByText(/Đã áp dụng lộ trình Thoải mái/)).toBeVisible()

    await openCompareTab(page)
    await expect(page.getByRole("heading", { name: "Cân bằng" })).toBeVisible()
    await expect(page.getByText("Đang dùng")).toBeVisible()
  })
})
