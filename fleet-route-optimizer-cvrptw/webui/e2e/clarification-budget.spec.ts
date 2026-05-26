import { expect, test } from "@playwright/test"
import { answerBudgetFollowUp, submitHomePrompt } from "./helpers"

test.describe("P1 clarification — missing budget", () => {
  test("shows budget follow-up after Huế 3 ngày prompt", async ({ page }) => {
    await submitHomePrompt(page, "Đi Huế 3 ngày")
    await expect(
      page.getByRole("paragraph").filter({ hasText: /ngân sách khoảng bao nhiêu/i }),
    ).toBeVisible({ timeout: 30_000 })
    await expect(page.getByRole("button", { name: "1 triệu", exact: true })).toBeVisible()
  })

  test("answers budget chip and builds itinerary", async ({ page }) => {
    await submitHomePrompt(page, "Đi Huế 3 ngày")
    await answerBudgetFollowUp(page, "1 triệu")
    await expect(page.getByRole("button", { name: /Huế \d+ ngày/ })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Đại Nội Huế" })).toBeVisible()
  })
})
