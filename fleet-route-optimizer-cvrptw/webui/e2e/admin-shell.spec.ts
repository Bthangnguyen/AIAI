import { expect, test } from "@playwright/test"

test.describe("Web2 admin shell", () => {
  test("admin layout loads with POI and QA nav", async ({ page }) => {
    await page.goto("/admin/pois")
    await expect(page.getByText("TripFlow QA")).toBeVisible()
    await expect(page.getByRole("link", { name: "POI" })).toBeVisible()
    await expect(page.getByRole("link", { name: "QA" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Danh sách POI" })).toBeVisible()
    await expect(page.getByPlaceholder("Tìm theo tên POI...")).toBeVisible()
  })

  test("admin link from home navigates to admin", async ({ page }) => {
    await page.goto("/")
    await page.getByRole("link", { name: "Admin" }).click()
    await expect(page).toHaveURL(/\/admin\/pois/)
  })
})
