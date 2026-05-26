import { expect, test } from "@playwright/test"
import { answerDaysFollowUp, submitHomePrompt } from "./helpers"

test.describe("P1 clarification — missing days", () => {
  test("asks for trip length when budget given without days", async ({ page }) => {
    await submitHomePrompt(page, "Đi Huế 1 triệu")
    await expect(page.getByRole("paragraph").filter({ hasText: /mấy ngày/i })).toBeVisible({
      timeout: 30_000,
    })
  })

  test("answers days and builds itinerary", async ({ page }) => {
    await submitHomePrompt(page, "Đi Huế 1 triệu")
    await answerDaysFollowUp(page, "2 ngày")
    await expect(page.getByText("Updated itinerary")).toBeVisible()
    await expect(page.getByRole("heading", { name: "Chùa Thiên Mụ" })).toBeVisible()
  })
})
