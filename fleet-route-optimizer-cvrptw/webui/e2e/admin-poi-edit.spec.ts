import { expect, test } from "@playwright/test"

test.describe("Web2 admin POI edit", () => {
  test("edit category and tags persists after reload", async ({ page }) => {
    await page.goto("/admin/pois")
    await expect(page.getByTestId("admin-poi-row")).toHaveCount(22, { timeout: 15_000 })

    const targetRow = page.getByRole("row", { name: /Đại Nội Huế/ })
    await targetRow.getByTestId("admin-poi-edit-button").click()
    await expect(page.getByTestId("admin-poi-edit-panel")).toBeVisible()

    await page.locator('[data-testid="admin-poi-edit-panel"] select').selectOption("culture")
    await page.getByPlaceholder("lịch sử, unesco, văn hóa").fill("lịch sử, unesco")
    await page.getByRole("button", { name: "Lưu" }).click()
    await expect(page.getByText("Đã lưu Đại Nội Huế")).toBeVisible()

    await expect(targetRow.getByRole("cell", { name: "culture" })).toBeVisible()
    await expect(targetRow.getByRole("cell", { name: /unesco/ })).toBeVisible()

    await page.reload()
    await expect(page.getByTestId("admin-poi-row")).toHaveCount(22, { timeout: 15_000 })
    const reloadedRow = page.getByRole("row", { name: /Đại Nội Huế/ })
    await expect(reloadedRow.getByRole("cell", { name: "culture" })).toBeVisible()
    await expect(reloadedRow.getByRole("cell", { name: /unesco/ })).toBeVisible()
  })
})
