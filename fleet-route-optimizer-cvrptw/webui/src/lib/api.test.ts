import { describe, expect, it } from "vitest"
import { mapLayer4ResultToDraft } from "@/lib/api"
import type { TripIntent } from "@/types/trip"

const baseIntent: TripIntent = {
  destination: "Huế",
  days: 2,
  budget: 1_000_000,
  interests: ["văn hóa"],
  lockedPoiNames: [],
  rawPrompt: "Đi Huế 2 ngày 1 triệu",
}

describe("mapLayer4ResultToDraft", () => {
  it("maps validation_notes and dropped POI count (P4)", () => {
    const draft = mapLayer4ResultToDraft(
      {
        days: [
          {
            day_index: 0,
            narrative_title: "Ngày văn hóa",
            stops: [{ poi_id: "poi-1", poi_name: "Đại Nội", arrival_time_min: 480 }],
          },
        ],
        validation_notes: ["[warning] Ngân sách thấp — một số POI bị bỏ qua"],
        total_pois_dropped: 2,
        budget_used: 950_000,
        budget_total: 1_000_000,
      },
      baseIntent,
      "Huế",
    )

    expect(draft.validationNotes).toEqual([
      { severity: "warning", message: "Ngân sách thấp — một số POI bị bỏ qua" },
    ])
    expect(draft.droppedPoiCount).toBe(2)
    expect(draft.budgetUsed).toBe(950_000)
    expect(draft.days[0].items[0].time).toBe("08:00")
  })

  it("filters hotel and rest-break stops from timeline", () => {
    const draft = mapLayer4ResultToDraft(
      {
        days: [
          {
            day_index: 0,
            stops: [
              { poi_id: "hotel_day_0", arrival_time_min: 0 },
              { poi_id: "__rest_break__", arrival_time_min: 720 },
              { poi_id: "poi-2", arrival_time_min: 540 },
            ],
          },
        ],
      },
      baseIntent,
      "Huế",
    )

    expect(draft.days[0].items).toHaveLength(1)
    expect(draft.days[0].items[0].poiId).toBe("poi-2")
  })
})
