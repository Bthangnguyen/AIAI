import { expect, test } from "@playwright/test"
import { addPlaceFromModal, openAddPlaceModal, submitHomePrompt, waitForItinerary } from "./helpers"

test.describe("P5 reroute infeasible", () => {
  test("shows infeasible toast when day is full", async ({ page }) => {
    await submitHomePrompt(page, "Đi Huế 2 ngày ngân sách 1 triệu")
    await waitForItinerary(page)

    await openAddPlaceModal(page)
    await addPlaceFromModal(page, "lăng")
    await expect(page.getByText(/Mock: đã tối ưu lại/i)).toBeVisible({ timeout: 30_000 })

    await openAddPlaceModal(page)
    await addPlaceFromModal(page, "cafe")
    await expect(page.getByText(/Mock: đã tối ưu lại/i)).toBeVisible({ timeout: 30_000 })

    await openAddPlaceModal(page)
    await addPlaceFromModal(page, "chay")
    await expect(page.getByText(/ngày đã đầy/i)).toBeVisible({ timeout: 30_000 })
  })
})
