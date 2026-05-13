/**
 * Tầng 1: Unit Tests — presetHotels constants
 */
import { HUE_PRESET_HOTELS, DEFAULT_HOTEL } from "../../app/constants/presetHotels"

describe("presetHotels", () => {
  it("has at least 3 preset hotels", () => {
    expect(HUE_PRESET_HOTELS.length).toBeGreaterThanOrEqual(3)
  })

  it("each hotel has required fields", () => {
    HUE_PRESET_HOTELS.forEach((hotel) => {
      expect(hotel).toHaveProperty("id")
      expect(hotel).toHaveProperty("name")
      expect(hotel).toHaveProperty("lat")
      expect(hotel).toHaveProperty("lon")
      expect(hotel).toHaveProperty("emoji")
      expect(typeof hotel.lat).toBe("number")
      expect(typeof hotel.lon).toBe("number")
    })
  })

  it("all hotels have valid Huế coordinates (lat ~16.4, lon ~107.5-107.6)", () => {
    HUE_PRESET_HOTELS.forEach((hotel) => {
      expect(hotel.lat).toBeGreaterThan(16.3)
      expect(hotel.lat).toBeLessThan(16.6)
      expect(hotel.lon).toBeGreaterThan(107.4)
      expect(hotel.lon).toBeLessThan(107.7)
    })
  })

  it("all hotel IDs are unique", () => {
    const ids = HUE_PRESET_HOTELS.map((h) => h.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it("DEFAULT_HOTEL is the first preset", () => {
    expect(DEFAULT_HOTEL).toBe(HUE_PRESET_HOTELS[0])
  })
})
