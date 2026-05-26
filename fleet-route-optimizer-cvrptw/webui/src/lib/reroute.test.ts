import { describe, expect, it } from "vitest"
import { interpretReRoute } from "@/lib/reroute"

const sampleDay = {
  day_index: 0,
  stops: [
    { poi_id: "hotel_day_0", arrival_time_min: 0 },
    { poi_id: "poi-a", poi_name: "Đại Nội", arrival_time_min: 540 },
  ],
}

describe("interpretReRoute", () => {
  it("returns success when solver succeeds with stops", () => {
    const result = interpretReRoute({ status: "success", day: sampleDay })
    expect(result.outcome).toBe("success")
    expect(result.day).toBeDefined()
  })

  it("returns warning for optimized_with_warning (P5)", () => {
    const result = interpretReRoute({
      status: "optimized_with_warning",
      message: "Một số POI bị bỏ qua",
      day: sampleDay,
    })
    expect(result.outcome).toBe("warning")
    expect(result.message).toContain("Một số POI")
  })

  it("returns infeasible when day is missing", () => {
    const result = interpretReRoute({ status: "infeasible", message: "Hết thời gian" })
    expect(result.outcome).toBe("infeasible")
  })

  it("returns infeasible when success has no visitable stops", () => {
    const result = interpretReRoute({
      status: "success",
      day: { day_index: 0, stops: [{ poi_id: "hotel_day_0", arrival_time_min: 0 }] },
    })
    expect(result.outcome).toBe("infeasible")
  })

  it("returns error for unknown failure status", () => {
    const result = interpretReRoute({ status: "error", message: "Solver crash" })
    expect(result.outcome).toBe("error")
  })
})
