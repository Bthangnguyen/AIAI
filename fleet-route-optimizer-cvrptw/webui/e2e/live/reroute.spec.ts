import { expect, test } from "@playwright/test"
import { expectItineraryStructure, submitHomePrompt } from "./helpers-live"

test.describe("Live P8 re-route", () => {
  test("add place shows success or infeasible toast", async ({ page }) => {
    await submitHomePrompt(page, "Đi Huế 2 ngày ngân sách 1 triệu")
    await expectItineraryStructure(page)

    await page.getByRole("button", { name: "Add Place", exact: true }).click()
    await expect(page.getByText("Bạn muốn thêm địa điểm nào?")).toBeVisible()
    await page.getByPlaceholder(/Thêm một quán cafe/).fill("chùa")
    await page.getByRole("button", { name: /Add to day/i }).first().click()
    await expect(page.getByText("Bạn muốn thêm địa điểm nào?")).toBeHidden({ timeout: 30_000 })

    await expect(
      page.getByText(/đã thêm|thành công|ngày đã đầy|infeasible|không thể thêm/i).first(),
    ).toBeVisible({ timeout: 60_000 })
  })
})
