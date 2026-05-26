import { describe, expect, it } from "vitest"
import { reRouteStopsToItems } from "@/lib/rerouteHelpers"

describe("reRouteStopsToItems", () => {
  it("skips hotel stops and formats arrival time", () => {
    const items = reRouteStopsToItems(0, {
      day_index: 0,
      stops: [
        { poi_id: "hotel_day_0", arrival_time_min: 0 },
        { poi_id: "poi-1", poi_name: "Lăng Khải Định", arrival_time_min: 570 },
      ],
    })

    expect(items).toHaveLength(1)
    expect(items[0].poiId).toBe("poi-1")
    expect(items[0].time).toBe("09:30")
    expect(items[0].note).toBe("Lăng Khải Định")
  })
})
