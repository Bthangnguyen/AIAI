import { expect, type Page } from "@playwright/test"

export async function submitHomePrompt(page: Page, prompt: string) {
  await page.goto("/")
  const input = page.getByPlaceholder(/Tôi muốn đi Huế/)
  await input.fill(prompt)
  const buildBtn = page.getByRole("button", { name: "Build trip" })
  await expect(buildBtn).toBeEnabled({ timeout: 15_000 })
  await buildBtn.click()
  await page.getByRole("button", { name: "Login và tiếp tục" }).click()
}

export async function waitForItinerary(page: Page) {
  await expect(page.getByText("Updated itinerary")).toBeVisible({ timeout: 60_000 })
}

export async function openCompareTab(page: Page) {
  await page.getByRole("button", { name: "⚡ Compare" }).click()
  await expect(page.getByRole("heading", { name: "So sánh 3 phương án lộ trình" })).toBeVisible({
    timeout: 30_000,
  })
}

export async function countTimelinePlaces(page: Page) {
  return page.locator("article h4").count()
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
