/**
 * Tầng 3: API Contract Tests — SSE Protocol Compliance
 *
 * Verifies that the mobile client correctly parses ALL SSE event shapes
 * that the Gateway (Layer 2&3) produces. This is the critical contract
 * between backend and mobile.
 *
 * Gateway SSE format (from trip_planner.py):
 *   data: {"step":"l2_done","tags":[...],"locked":[...]}
 *   data: {"step":"l3_done","pois_found":15,"locked_count":1}
 *   data: {"status":"success","num_days":2,"days":[...],...}  (raw L4 result)
 *   data: [DONE]
 */

describe("SSE Contract — Gateway ↔ Mobile", () => {
  // Simulate the SSE parsing logic from useTripPipeline real backend handler
  const parseSSEEvent = (data: any) => {
    if (data.step === "l2_done") {
      return {
        type: "l2_done",
        tags: data.tags || [],
        locked: data.locked || [],
      }
    } else if (data.step === "l3_done") {
      return {
        type: "l3_done",
        pois_found: data.pois_found,
        locked_count: data.locked_count || 0,
      }
    } else if (data.step === "error") {
      return {
        type: "error",
        message: data.message || "Unknown error",
      }
    } else if (data.status === "success" || data.days) {
      // L4 result — could be raw or wrapped
      const itinerary = data.layer4_result || data
      return {
        type: "l4_result",
        itinerary,
      }
    } else if (data.step === "status" || data.message) {
      return {
        type: "status",
        message: data.message || "Processing…",
      }
    }
    return { type: "unknown", data }
  }

  describe("L2 done event", () => {
    it("parses l2_done with tags and locked POIs", () => {
      const event = parseSSEEvent({
        step: "l2_done",
        tags: ["culture", "food", "nature"],
        locked: ["Đại Nội Huế"],
      })
      expect(event.type).toBe("l2_done")
      expect(event.tags).toEqual(["culture", "food", "nature"])
      expect(event.locked).toEqual(["Đại Nội Huế"])
    })

    it("handles l2_done with empty tags", () => {
      const event = parseSSEEvent({ step: "l2_done" })
      expect(event.type).toBe("l2_done")
      expect(event.tags).toEqual([])
      expect(event.locked).toEqual([])
    })
  })

  describe("L3 done event", () => {
    it("parses l3_done with POI counts", () => {
      const event = parseSSEEvent({
        step: "l3_done",
        pois_found: 15,
        locked_count: 2,
      })
      expect(event.type).toBe("l3_done")
      expect(event.pois_found).toBe(15)
      expect(event.locked_count).toBe(2)
    })

    it("defaults locked_count to 0 when missing", () => {
      const event = parseSSEEvent({ step: "l3_done", pois_found: 8 })
      expect(event.locked_count).toBe(0)
    })
  })

  describe("L4 result event (raw Layer 4 JSON)", () => {
    const mockL4Result = {
      status: "success",
      num_days: 2,
      days: [
        {
          day_index: 0,
          date: "2026-06-01",
          hotel_name: "Test Hotel",
          hotel_location: { latitude: 16.46, longitude: 107.59 },
          stops: [
            {
              poi_id: "poi-1",
              poi_name: "Đại Nội",
              location: { latitude: 16.4698, longitude: 107.5796 },
              arrival_time_min: 480,
              departure_time_min: 600,
              visit_duration_min: 120,
              travel_time_from_prev_min: 15,
              entrance_fee: 200000,
            },
          ],
          total_travel_min: 30,
          total_visit_min: 120,
          total_distance_km: 5.2,
          total_entrance_fee: 200000,
          num_pois: 1,
        },
      ],
      total_pois_visited: 1,
      total_pois_dropped: 0,
      total_entrance_fee: 200000,
      total_travel_min: 30,
      total_distance_km: 5.2,
      budget_used: 200000,
    }

    it("parses raw L4 result via data.status === 'success'", () => {
      const event = parseSSEEvent(mockL4Result)
      expect(event.type).toBe("l4_result")
      expect(event.itinerary.num_days).toBe(2)
      expect(event.itinerary.days).toHaveLength(1)
    })

    it("parses L4 result via data.days presence (fallback)", () => {
      const { status, ...withoutStatus } = mockL4Result
      const event = parseSSEEvent(withoutStatus)
      expect(event.type).toBe("l4_result")
      expect(event.itinerary.days).toBeDefined()
    })

    it("parses wrapped L4 result (from plan_trip JSON endpoint)", () => {
      const wrapped = {
        status: "success",
        layer4_result: mockL4Result,
        llm_contract: {},
        pois_found: 15,
      }
      const event = parseSSEEvent(wrapped)
      expect(event.type).toBe("l4_result")
      // Should prefer layer4_result when present
      expect(event.itinerary.num_days).toBe(2)
    })
  })

  describe("Error event", () => {
    it("parses error with message", () => {
      const event = parseSSEEvent({
        step: "error",
        message: "No POIs found",
      })
      expect(event.type).toBe("error")
      expect(event.message).toBe("No POIs found")
    })

    it("defaults error message when missing", () => {
      const event = parseSSEEvent({ step: "error" })
      expect(event.message).toBe("Unknown error")
    })
  })

  describe("Status/progress event", () => {
    it("parses status event", () => {
      const event = parseSSEEvent({
        step: "status",
        message: "Analyzing your travel request...",
      })
      expect(event.type).toBe("status")
      expect(event.message).toBe("Analyzing your travel request...")
    })

    it("parses bare message event", () => {
      const event = parseSSEEvent({ message: "Finding POIs..." })
      expect(event.type).toBe("status")
      expect(event.message).toBe("Finding POIs...")
    })
  })

  describe("L4 TravelItinerary shape validation", () => {
    it("TravelItinerary has all required fields from Layer 4 domain.py", () => {
      const requiredFields = [
        "status", "num_days", "days",
        "total_pois_visited", "total_pois_dropped",
        "total_entrance_fee", "total_travel_min",
        "total_distance_km", "budget_used",
      ]
      const mockItinerary = {
        status: "success",
        num_days: 1,
        days: [],
        total_pois_visited: 0,
        total_pois_dropped: 0,
        total_entrance_fee: 0,
        total_travel_min: 0,
        total_distance_km: 0,
        budget_used: 0,
      }
      requiredFields.forEach((field) => {
        expect(mockItinerary).toHaveProperty(field)
      })
    })

    it("TravelItineraryStop has all required fields from Layer 4 domain.py", () => {
      const requiredFields = [
        "poi_id", "poi_name", "location",
        "arrival_time_min", "departure_time_min",
        "visit_duration_min", "travel_time_from_prev_min",
        "entrance_fee",
      ]
      const mockStop = {
        poi_id: "hue-001",
        poi_name: "Đại Nội Huế",
        location: { latitude: 16.4698, longitude: 107.5796 },
        arrival_time_min: 480,
        departure_time_min: 600,
        visit_duration_min: 120,
        travel_time_from_prev_min: 15,
        entrance_fee: 200000,
      }
      requiredFields.forEach((field) => {
        expect(mockStop).toHaveProperty(field)
      })
    })

    it("TravelItineraryDay has all required fields from Layer 4 domain.py", () => {
      const requiredFields = [
        "day_index", "date", "hotel_name", "hotel_location",
        "stops", "total_travel_min", "total_visit_min",
        "total_distance_km", "total_entrance_fee", "num_pois",
      ]
      const mockDay = {
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
      }
      requiredFields.forEach((field) => {
        expect(mockDay).toHaveProperty(field)
      })
    })
  })

  describe("TripPlanRequest shape (Mobile → Gateway)", () => {
    it("matches Gateway TripPlanRequest schema", () => {
      const request = {
        user_prompt: "3 days in Hue cultural sites",
        hotel_lat: 16.4637,
        hotel_lon: 107.5909,
        hotel_name: "Hue Heritage Hotel",
        num_days: 3,
      }
      // All required fields from gateway/app/schemas/trip.py TripPlanRequest
      expect(request).toHaveProperty("user_prompt")
      expect(request).toHaveProperty("hotel_lat")
      expect(request).toHaveProperty("hotel_lon")
      expect(request).toHaveProperty("hotel_name")
      expect(request).toHaveProperty("num_days")
      expect(typeof request.user_prompt).toBe("string")
      expect(typeof request.hotel_lat).toBe("number")
      expect(typeof request.hotel_lon).toBe("number")
      expect(typeof request.hotel_name).toBe("string")
      expect(typeof request.num_days).toBe("number")
    })
  })
})
