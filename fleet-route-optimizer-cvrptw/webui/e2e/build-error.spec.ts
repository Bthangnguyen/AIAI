import { expect, test } from "@playwright/test"
import { submitHomePrompt } from "./helpers"

test.describe("P2+P3 build error", () => {
  test("shows BuildErrorPanel when mock SSE fails", async ({ page }) => {
    await submitHomePrompt(page, "mock-error Đi Huế 2 ngày")
    await expect(page.getByText("Không tạo được lịch trình")).toBeVisible({ timeout: 60_000 })
    await expect(page.locator(".border-red-200").getByText(/Mock: LLM timeout/i)).toBeVisible()
    await expect(page.getByRole("button", { name: "Thử lại" })).toBeVisible()
  })
})
