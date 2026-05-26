import { expect, type Page } from "@playwright/test"

export async function submitHomePrompt(page: Page, prompt: string) {
  await page.goto("/")
  await page.getByPlaceholder(/Tôi muốn đi Huế/).fill(prompt)
  await page.getByRole("button", { name: "Build trip" }).click()
  await page.getByRole("button", { name: "Login và tiếp tục" }).click()
}

export async function waitForItinerary(page: Page) {
  await expect(page.getByText("Updated itinerary")).toBeVisible({ timeout: 180_000 })
}

export async function expectItineraryStructure(page: Page, minHeadings = 2) {
  await waitForItinerary(page)
  await expect(page.getByRole("button", { name: /Huế \d+ ngày/ })).toBeVisible()
  const count = await page.getByRole("heading").count()
  expect(count).toBeGreaterThanOrEqual(minHeadings)
}

export async function expectBudgetFollowUpOrItinerary(page: Page) {
  const budget = page.getByRole("paragraph").filter({ hasText: /ngân sách khoảng bao nhiêu/i })
  const itinerary = page.getByText("Updated itinerary")
  await expect(budget.or(itinerary)).toBeVisible({ timeout: 120_000 })
}
