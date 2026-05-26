import { describe, expect, it } from "vitest"
import { diversityTone, fatiguePercent, warningLabels, warningTooltip } from "@/lib/planMetricsDisplay"
import type { PlanMetrics } from "@/types/plan"

const baseMetrics: PlanMetrics = {
  totalCost: 500000,
  totalTravelMin: 120,
  poiCount: 8,
  totalDistanceKm: 30,
  fatigueScore: 0.72,
  diversityScore: 0.81,
  warnings: { meal: false, outdoor_heat: false, budget: false },
}

describe("planMetricsDisplay", () => {
  it("diversityTone thresholds", () => {
    expect(diversityTone(0.81)).toBe("good")
    expect(diversityTone(0.55)).toBe("mid")
    expect(diversityTone(0.42)).toBe("low")
  })

  it("fatiguePercent clamps 0-100", () => {
    expect(fatiguePercent(0.72)).toBe(72)
    expect(fatiguePercent(1.2)).toBe(100)
  })

  it("warningLabels from flags", () => {
    const metrics: PlanMetrics = {
      ...baseMetrics,
      warnings: { meal: true, outdoor_heat: true, budget: false },
    }
    expect(warningLabels(metrics)).toEqual(["Thiếu bữa trưa", "Nắng nóng ngoài trời"])
  })

  it("warningTooltip prefers validation messages", () => {
    const metrics: PlanMetrics = {
      ...baseMetrics,
      validationMessages: ["[warning] Ngày 1: thiếu quán ăn trưa"],
      warnings: { meal: true, outdoor_heat: false, budget: false },
    }
    expect(warningTooltip(metrics)).toBe("[warning] Ngày 1: thiếu quán ăn trưa")
  })
})
