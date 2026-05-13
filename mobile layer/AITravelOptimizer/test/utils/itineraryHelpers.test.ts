/**
 * Tests for itineraryHelpers — pure function tests.
 */
import {
  getRemainingPOIIds,
  mergeReRoutedDay,
  minutesToHHMM,
  getCurrentTimeMin,
} from "../../app/utils/itineraryHelpers"
import type {
  TravelItinerary,
  TravelItineraryDay,
} from "../../app/navigators/navigationTypes"

const mockDay: TravelItineraryDay = {
  day_index: 0,
  date: "2026-06-01",
  hotel_name: "Test Hotel",
  hotel_location: { latitude: 16.46, longitude: 107.59 },
  stops: [
    {
      poi_id: "poi-a",
      poi_name: "POI A",
      location: { latitude: 16.47, longitude: 107.58 },
      arrival_time_min: 480,
      departure_time_min: 540,
      visit_duration_min: 60,
      travel_time_from_prev_min: 15,
      entrance_fee: 100000,
    },
    {
      poi_id: "poi-b",
      poi_name: "POI B",
      location: { latitude: 16.48, longitude: 107.59 },
      arrival_time_min: 570,
      departure_time_min: 630,
      visit_duration_min: 60,
      travel_time_from_prev_min: 10,
      entrance_fee: 50000,
    },
    {
      poi_id: "poi-c",
      poi_name: "POI C",
      location: { latitude: 16.49, longitude: 107.60 },
      arrival_time_min: 660,
      departure_time_min: 720,
      visit_duration_min: 60,
      travel_time_from_prev_min: 10,
      entrance_fee: 0,
    },
  ],
  total_travel_min: 35,
  total_visit_min: 180,
  total_distance_km: 8.5,
  total_entrance_fee: 150000,
  num_pois: 3,
}

const mockItinerary: TravelItinerary = {
  status: "success",
  num_days: 2,
  days: [
    mockDay,
    {
      ...mockDay,
      day_index: 1,
      date: "2026-06-02",
      stops: [mockDay.stops[0]],
      num_pois: 1,
      total_entrance_fee: 100000,
      total_travel_min: 15,
      total_distance_km: 3.0,
    },
  ],
  total_pois_visited: 4,
  total_pois_dropped: 0,
  total_entrance_fee: 250000,
  total_travel_min: 50,
  total_distance_km: 11.5,
  budget_used: 250000,
}

describe("getRemainingPOIIds", () => {
  it("returns all POI IDs when none visited", () => {
    const result = getRemainingPOIIds(mockItinerary, 0)
    expect(result).toEqual(["poi-a", "poi-b", "poi-c"])
  })

  it("excludes visited POIs", () => {
    const result = getRemainingPOIIds(mockItinerary, 0, ["poi-a"])
    expect(result).toEqual(["poi-b", "poi-c"])
  })

  it("returns empty when all visited", () => {
    const result = getRemainingPOIIds(mockItinerary, 0, ["poi-a", "poi-b", "poi-c"])
    expect(result).toEqual([])
  })

  it("returns empty for non-existent day", () => {
    const result = getRemainingPOIIds(mockItinerary, 99)
    expect(result).toEqual([])
  })

  it("works with day_index 1", () => {
    const result = getRemainingPOIIds(mockItinerary, 1)
    expect(result).toEqual(["poi-a"])
  })
})

describe("mergeReRoutedDay", () => {
  const reRoutedDay: TravelItineraryDay = {
    day_index: 0,
    date: "2026-06-01",
    hotel_name: "Test Hotel",
    hotel_location: { latitude: 16.46, longitude: 107.59 },
    stops: [mockDay.stops[1]], // Only POI B remains
    total_travel_min: 20,
    total_visit_min: 60,
    total_distance_km: 4.0,
    total_entrance_fee: 50000,
    num_pois: 1,
  }

  it("replaces the target day stops", () => {
    const result = mergeReRoutedDay(mockItinerary, reRoutedDay)
    expect(result.days[0].stops).toHaveLength(1)
    expect(result.days[0].stops[0].poi_id).toBe("poi-b")
  })

  it("preserves other days untouched", () => {
    const result = mergeReRoutedDay(mockItinerary, reRoutedDay)
    expect(result.days[1].stops).toHaveLength(1)
    expect(result.days[1].num_pois).toBe(1)
  })

  it("recalculates itinerary totals", () => {
    const result = mergeReRoutedDay(mockItinerary, reRoutedDay)
    expect(result.total_pois_visited).toBe(2) // 1 (day0) + 1 (day1)
    expect(result.total_travel_min).toBe(35) // 20 + 15
    expect(result.total_entrance_fee).toBe(150000) // 50000 + 100000
  })

  it("preserves hotel info from original when re-route omits it", () => {
    const dayWithoutHotel: TravelItineraryDay = {
      ...reRoutedDay,
      hotel_name: "",
      hotel_location: { latitude: 0, longitude: 0 },
    }
    const result = mergeReRoutedDay(mockItinerary, dayWithoutHotel)
    // Should keep original hotel info since re-route returned empty
    expect(result.days[0].hotel_name).toBeTruthy()
  })
})

describe("minutesToHHMM", () => {
  it("converts 480 to 08:00", () => {
    expect(minutesToHHMM(480)).toBe("08:00")
  })

  it("converts 810 to 13:30", () => {
    expect(minutesToHHMM(810)).toBe("13:30")
  })

  it("converts 0 to 00:00", () => {
    expect(minutesToHHMM(0)).toBe("00:00")
  })

  it("converts 1439 to 23:59", () => {
    expect(minutesToHHMM(1439)).toBe("23:59")
  })
})

describe("getCurrentTimeMin", () => {
  it("returns a number between 0 and 1440", () => {
    const result = getCurrentTimeMin()
    expect(result).toBeGreaterThanOrEqual(0)
    expect(result).toBeLessThan(1440)
  })
})
