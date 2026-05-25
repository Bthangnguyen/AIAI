import { describe, expect, it } from "vitest"
import { applyPlanVariant } from "@/lib/applyPlanVariant"
import type { ItineraryDraft } from "@/types/trip"
import type { PlanVariant } from "@/types/plan"

const draft: ItineraryDraft = {
  id: "draft-1",
  destination: "Huế",
  days: [{ dayNumber: 1, title: "Ngày 1", items: [{ id: "a", poiId: "old", time: "08:00", note: "Old" }] }],
  tags: [],
  createdAt: "2026-01-01T00:00:00.000Z",
  updatedAt: "2026-01-01T00:00:00.000Z",
  status: "draft",
  intent: { interests: [], lockedPoiNames: [], rawPrompt: "test" },
}

const variant: PlanVariant = {
  style: "chill",
  label: "Thoải mái",
  description: "Ít điểm",
  days: [
    {
      dayNumber: 1,
      title: "Chill day",
      items: [
        { id: "b", poiId: "dai-noi-hue", time: "09:00", note: "Đại Nội Huế" },
        { id: "c", poiId: "cafe-muoi", time: "11:00", note: "Cafe Muối" },
      ],
    },
  ],
  metrics: {
    totalCost: 200000,
    totalTravelMin: 60,
    poiCount: 2,
    totalDistanceKm: 10,
    fatigueScore: 0.3,
    diversityScore: 0.6,
    warnings: { meal: false, outdoor_heat: false, budget: false },
  },
}

describe("applyPlanVariant", () => {
  it("replaces days and sets selectedPlanStyle", () => {
    const next = applyPlanVariant(draft, variant)
    expect(next.days).toHaveLength(1)
    expect(next.days[0].items).toHaveLength(2)
    expect(next.days[0].items[0].poiId).toBe("dai-noi-hue")
    expect(next.selectedPlanStyle).toBe("chill")
    expect(next.id).toBe("draft-1")
  })
})
