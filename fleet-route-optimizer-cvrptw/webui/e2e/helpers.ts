import { expect, type Page } from "@playwright/test"

export async function submitHomePrompt(page: Page, prompt: string) {
  await page.goto("/")
  await page.getByPlaceholder(/Tôi muốn đi Huế/).fill(prompt)
  await page.getByRole("button", { name: "Build trip" }).click()
  await page.getByRole("button", { name: "Login và tiếp tục" }).click()
}

export async function waitForItinerary(page: Page) {
  await expect(page.getByText("Updated itinerary")).toBeVisible({ timeout: 60_000 })
}

export async function answerBudgetFollowUp(page: Page, budget = "1 triệu") {
  await expect(
    page.getByRole("paragraph").filter({ hasText: /ngân sách khoảng bao nhiêu/i }),
  ).toBeVisible({ timeout: 30_000 })
  await page.getByRole("button", { name: budget, exact: true }).click()
  await waitForItinerary(page)
}

export async function answerDaysFollowUp(page: Page, days = "2 ngày") {
  await expect(page.getByRole("paragraph").filter({ hasText: /mấy ngày/i })).toBeVisible({
    timeout: 30_000,
  })
  const chatInput = page.getByPlaceholder(/Bạn cũng có thể trả lời ở đây/)
  await chatInput.fill(days)
  await chatInput.press("Enter")
  await waitForItinerary(page)
}

export async function openAddPlaceModal(page: Page) {
  await page.getByRole("button", { name: "Add Place", exact: true }).click()
  await expect(page.getByText("Bạn muốn thêm địa điểm nào?")).toBeVisible()
}

export async function addPlaceFromModal(page: Page, searchQuery: string) {
  await page.getByPlaceholder(/Thêm một quán cafe/).fill(searchQuery)
  await page.getByRole("button", { name: /Add to day/i }).first().click()
  await expect(page.getByText("Bạn muốn thêm địa điểm nào?")).toBeHidden({ timeout: 30_000 })
}
