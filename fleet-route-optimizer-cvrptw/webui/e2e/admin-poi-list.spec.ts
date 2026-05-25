import { expect, test } from "@playwright/test"

test.describe("Web2 admin POI list", () => {
  test("loads POI table with at least 10 rows from mock gateway", async ({ page }) => {
    await page.goto("/admin/pois")
    await expect(page.getByRole("heading", { name: "Danh sách POI" })).toBeVisible()
    await expect(page.getByText(/22 POI trong cơ sở dữ liệu/)).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId("admin-poi-row")).toHaveCount(22)
    await expect(page.getByRole("columnheader", { name: "Embed" })).toBeVisible()
  })

  test("search filters table to matching POI", async ({ page }) => {
    await page.goto("/admin/pois")
    await expect(page.getByTestId("admin-poi-row")).toHaveCount(22, { timeout: 15_000 })
    await page.getByPlaceholder("Tìm theo tên POI...").fill("Đại Nội")
    await expect(page.getByTestId("admin-poi-row")).toHaveCount(1)
    await expect(page.getByRole("cell", { name: "Đại Nội Huế", exact: true })).toBeVisible()
  })

  test("clicking row highlights selection", async ({ page }) => {
    await page.goto("/admin/pois")
    await expect(page.getByTestId("admin-poi-row").first()).toBeVisible({ timeout: 15_000 })
    const row = page.getByRole("row", { name: /Chùa Thiên Mụ/ })
    await row.click()
    await expect(row).toHaveClass(/bg-yellow-50/)
  })
})
