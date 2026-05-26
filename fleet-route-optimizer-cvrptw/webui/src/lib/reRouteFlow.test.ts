import { describe, expect, it } from "vitest"
import { processReRouteResult } from "@/lib/reRouteFlow"
import type { ReRouteResult } from "@/lib/api"

const sampleDay = {
  day_index: 0,
  stops: [
    { poi_id: "hotel_day_0", arrival_time_min: 420 },
    { poi_id: "poi-1", poi_name: "Đại Nội", arrival_time_min: 540 },
  ],
}

describe("processReRouteResult", () => {
  it("returns timeline items on success (optimize day / add POI flow)", () => {
    const result = processReRouteResult(0, { status: "success", day: sampleDay })
    expect(result.ok).toBe(true)
    if (!result.ok) return
    expect(result.items).toHaveLength(1)
    expect(result.items[0].poiId).toBe("poi-1")
    expect(result.toastVariant).toBe("success")
  })

  it("returns warning variant for optimized_with_warning", () => {
    const result = processReRouteResult(0, {
      status: "optimized_with_warning",
      message: "Một phần",
      day: sampleDay,
    })
    expect(result.ok).toBe(true)
    if (!result.ok) return
    expect(result.toastVariant).toBe("warning")
  })

  it("returns failure for infeasible without calling API again", () => {
    const result = processReRouteResult(0, { status: "infeasible", message: "Ngày đầy" })
    expect(result.ok).toBe(false)
    if (result.ok) return
    expect(result.toastVariant).toBe("warning")
    expect(result.message).toContain("Ngày đầy")
  })

  it("returns error variant for solver error status", () => {
    const result = processReRouteResult(0, { status: "error", message: "Solver crash" })
    expect(result.ok).toBe(false)
    if (result.ok) return
    expect(result.toastVariant).toBe("error")
  })
})
