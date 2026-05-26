import { expect, test } from "@playwright/test"
import { openCompareTab, submitHomePrompt, waitForItinerary } from "./helpers"

test.describe("Web2 compare metrics", () => {
  test("shows cost, travel, POI, distance, fatigue and diversity on each column", async ({ page }) => {
    await submitHomePrompt(page, "Đi Huế 2 ngày ngân sách 1 triệu")
    await waitForItinerary(page)
    await openCompareTab(page)

    for (const label of ["Tổng chi phí", "Thời gian di chuyển", "Tổng số POI", "Quãng đường"]) {
      await expect(page.getByText(label).first()).toBeVisible()
    }

    await expect(page.getByText("Fatigue").first()).toBeVisible()
    await expect(page.getByText("Diversity").first()).toBeVisible()

    await expect(page.getByText("650.000").first()).toBeVisible()
    await expect(page.getByText("420.000").first()).toBeVisible()
    await expect(page.getByText("380.000").first()).toBeVisible()

    await expect(page.getByText("72%").first()).toBeVisible()
    await expect(page.getByText("81%").first()).toBeVisible()

    await expect(page.getByText("Thiếu bữa trưa").first()).toBeVisible()
    await expect(page.getByText("Nắng nóng").first()).toBeVisible()
    await expect(page.getByText("Ngân sách").first()).toBeVisible()
  })
})
