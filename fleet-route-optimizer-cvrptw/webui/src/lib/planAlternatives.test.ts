import { describe, expect, it } from "vitest"
import { fetchPlanAlternatives, mapAlternativesResponse, mapBackendPlanToVariant } from "@/lib/planAlternatives"

describe("planAlternatives mapper", () => {
  it("maps backend plan with metrics to PlanVariant", () => {
    const variant = mapBackendPlanToVariant({
      style: "chill",
      label: "Thoải mái",
      description: "Ít điểm, nhiều thời gian thư giãn",
      days: [
        {
          day_index: 0,
          narrative_title: "Ngày nhẹ nhàng",
          stops: [
            { poi_id: "hotel_day_0", arrival_time_min: 420 },
            { poi_id: "dai-noi-hue", poi_name: "Đại Nội Huế", arrival_time_min: 480 },
          ],
        },
      ],
      metrics: {
        total_cost: 200000,
        total_travel_min: 90,
        poi_count: 1,
        total_distance_km: 12.5,
        fatigue_score: 0.35,
        diversity_score: 0.62,
        warnings: { meal: true, outdoor_heat: false, budget: false },
        validation_messages: ["[warning] Thiếu bữa trưa"],
      },
    })

    expect(variant.style).toBe("chill")
    expect(variant.days[0].items).toHaveLength(1)
    expect(variant.days[0].items[0].poiId).toBe("dai-noi-hue")
    expect(variant.metrics.poiCount).toBe(1)
    expect(variant.metrics.warnings.meal).toBe(true)
  })

  it("orders plans balanced → budget → chill", () => {
    const ordered = mapAlternativesResponse({
      status: "success",
      plans: [
        { style: "chill", label: "Thoải mái", description: "", days: [], metrics: { total_cost: 0, total_travel_min: 0, poi_count: 5, total_distance_km: 0, fatigue_score: 0.3, diversity_score: 0.5, warnings: { meal: false, outdoor_heat: false, budget: false } } },
        { style: "balanced", label: "Cân bằng", description: "", days: [], metrics: { total_cost: 0, total_travel_min: 0, poi_count: 12, total_distance_km: 0, fatigue_score: 0.7, diversity_score: 0.8, warnings: { meal: false, outdoor_heat: false, budget: false } } },
        { style: "budget", label: "Tiết kiệm", description: "", days: [], metrics: { total_cost: 0, total_travel_min: 0, poi_count: 10, total_distance_km: 0, fatigue_score: 0.6, diversity_score: 0.7, warnings: { meal: false, outdoor_heat: false, budget: false } } },
      ],
    })

    expect(ordered.map((p) => p.style)).toEqual(["balanced", "budget", "chill"])
    expect(ordered[2].metrics.poiCount).toBeLessThanOrEqual(ordered[0].metrics.poiCount)
  })
})

describe("fetchPlanAlternatives failure handling", () => {
  it("mapAlternativesResponse returns empty when no plans", () => {
    expect(mapAlternativesResponse({ status: "success", plans: [] })).toEqual([])
  })

  it("fetchPlanAlternatives throws on non-ok response", async () => {
    const originalFetch = global.fetch
    global.fetch = async () =>
      ({
        ok: false,
        status: 503,
        text: async () => "service unavailable",
      }) as Response

    try {
      await expect(
        fetchPlanAlternatives({
          id: "d1",
          destination: "Huế",
          days: [{ dayNumber: 1, title: "D1", items: [] }],
          tags: [],
          createdAt: "",
          updatedAt: "",
          status: "draft",
          intent: { interests: [], lockedPoiNames: [], rawPrompt: "test" },
        }),
      ).rejects.toThrow(/plan_alternatives failed \(503\)/)
    } finally {
      global.fetch = originalFetch
    }
  })
})
