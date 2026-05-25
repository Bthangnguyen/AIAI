import { describe, expect, it } from "vitest"
import { mapBackendAdminPoi, parseTagsInput } from "@/lib/adminPois"
import { formatLatLng, formatMinutesFromMidnight } from "@/lib/adminFormat"

describe("parseTagsInput", () => {
  it("splits comma-separated tags and trims whitespace", () => {
    expect(parseTagsInput("lịch sử,  văn hóa,unesco")).toEqual(["lịch sử", "văn hóa", "unesco"])
  })

  it("removes empty segments and deduplicates case-insensitively", () => {
    expect(parseTagsInput("cafe, Cafe, ,CAFE")).toEqual(["cafe"])
  })

  it("returns empty array for blank input", () => {
    expect(parseTagsInput("   ")).toEqual([])
  })
})

describe("mapBackendAdminPoi", () => {
  it("maps snake_case backend fields to AdminPoiRow", () => {
    const row = mapBackendAdminPoi({
      uuid: "dai-noi-hue",
      name: "Đại Nội Huế",
      category: "Di tích",
      tags: ["lịch sử"],
      latitude: 16.4678,
      longitude: 107.5784,
      visit_duration_min: 120,
      open_time: 480,
      close_time: 1260,
      has_embedding: true,
    })

    expect(row).toEqual({
      uuid: "dai-noi-hue",
      name: "Đại Nội Huế",
      category: "Di tích",
      tags: ["lịch sử"],
      latitude: 16.4678,
      longitude: 107.5784,
      visitDurationMin: 120,
      openTime: 480,
      closeTime: 1260,
      hasEmbedding: true,
    })
  })
})

describe("adminFormat", () => {
  it("formats minutes from midnight", () => {
    expect(formatMinutesFromMidnight(480)).toBe("08:00")
    expect(formatMinutesFromMidnight(1260)).toBe("21:00")
  })

  it("formats lat/lng", () => {
    expect(formatLatLng(16.4678, 107.5784)).toBe("16.4678, 107.5784")
  })
})
