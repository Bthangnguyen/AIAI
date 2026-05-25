import { expect, test } from "@playwright/test"

test.describe("Web2 admin QA dashboard", () => {
  test("loads five QA summary cards", async ({ page }) => {
    await page.goto("/admin/qa")
    await expect(page.getByRole("heading", { name: "Kiểm tra chất lượng POI" })).toBeVisible()
    await expect(page.getByTestId("qa-card-wrong_coords")).toBeVisible()
    await expect(page.getByTestId("qa-card-duplicates")).toBeVisible()
    await expect(page.getByTestId("qa-card-missing_hours")).toBeVisible()
    await expect(page.getByTestId("qa-card-missing_duration")).toBeVisible()
    await expect(page.getByTestId("qa-card-missing_embedding")).toBeVisible()
  })

  test("filters wrong coords issue to affected POIs only", async ({ page }) => {
    await page.goto("/admin/qa")
    await page.getByTestId("qa-card-wrong_coords").click()
    await expect(page.getByText("POI lỗi — Tọa độ sai")).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId("admin-qa-row")).toHaveCount(2)
    await expect(page.getByRole("cell", { name: "POI tọa độ sai (QA)", exact: true })).toBeVisible()
    await expect(page.getByRole("cell", { name: "POI ngoài bbox (QA)", exact: true })).toBeVisible()
  })

  test("duplicate issue highlights grouped rows", async ({ page }) => {
    await page.goto("/admin/qa")
    await page.getByTestId("qa-card-duplicates").click()
    await expect(page.getByTestId("admin-qa-row")).toHaveCount(2, { timeout: 15_000 })
    await expect(page.getByRole("cell", { name: /cafe trung/i })).toHaveCount(2)
  })
})
