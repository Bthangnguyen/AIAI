import { TripService } from "./tripService"

// Save original fetch
const originalFetch = global.fetch

describe("TripService.reRoute", () => {
  afterEach(() => {
    jest.clearAllMocks()
    global.fetch = originalFetch
  })

  it("calls reRoute API successfully with typed payload", async () => {
    const mockResponse = {
      status: "success",
      day: {
        day_index: 0,
        date: "2026-06-01",
        hotel_name: "Test",
        hotel_location: { latitude: 16.46, longitude: 107.59 },
        stops: [],
        total_travel_min: 0,
        total_visit_min: 0,
        total_distance_km: 0,
        total_entrance_fee: 0,
        num_pois: 0,
      },
    }

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    }) as any

    const result = await TripService.reRoute({
      current_lat: 16.46,
      current_lon: 107.59,
      current_time_min: 840,
      remaining_poi_ids: ["poi-a", "poi-b"],
      day_index: 0,
      original_itinerary: {
        status: "success",
        num_days: 1,
        days: [],
        total_pois_visited: 0,
        total_pois_dropped: 0,
        total_entrance_fee: 0,
        total_travel_min: 0,
        total_distance_km: 0,
        budget_used: 0,
      },
    })

    expect(result.status).toBe("success")
    expect(result.day).toBeDefined()
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/v1/trip/re_route"),
      expect.objectContaining({ method: "POST" }),
    )
  })

  it("returns error on network failure", async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error("Network error")) as any

    const result = await TripService.reRoute({
      current_lat: 0,
      current_lon: 0,
      current_time_min: 0,
      remaining_poi_ids: [],
      day_index: 0,
      original_itinerary: {
        status: "success",
        num_days: 1,
        days: [],
        total_pois_visited: 0,
        total_pois_dropped: 0,
        total_entrance_fee: 0,
        total_travel_min: 0,
        total_distance_km: 0,
        budget_used: 0,
      },
    })

    expect(result.status).toBe("error")
    expect(result.message).toBe("Network error")
  })
})

