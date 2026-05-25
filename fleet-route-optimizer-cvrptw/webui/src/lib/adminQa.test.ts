import { describe, expect, it } from "vitest"
import { mapBackendQaSummary, qaCardTone } from "@/lib/adminQa"

describe("mapBackendQaSummary", () => {
  it("maps snake_case counts", () => {
    expect(
      mapBackendQaSummary({
        wrong_coords: 1,
        duplicates: 2,
        missing_hours: 0,
        missing_duration: 3,
        missing_embedding: 4,
      }),
    ).toEqual({
      wrong_coords: 1,
      duplicates: 2,
      missing_hours: 0,
      missing_duration: 3,
      missing_embedding: 4,
    })
  })
})

describe("qaCardTone", () => {
  it("returns ok for zero issues", () => {
    expect(qaCardTone(0)).toBe("ok")
  })

  it("returns warn for small non-zero counts", () => {
    expect(qaCardTone(2)).toBe("warn")
  })

  it("returns danger for large counts", () => {
    expect(qaCardTone(5)).toBe("danger")
  })
})
