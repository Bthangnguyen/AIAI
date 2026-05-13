/**
 * Tests for MockTripService — validates SSE event order and shape.
 */
import { MockTripService, SSEEvent } from "../mockTripService"

describe("MockTripService", () => {
  jest.useFakeTimers()

  afterEach(() => {
    jest.clearAllTimers()
  })

  it("should emit events in correct order: status → l2_done → status → l3_done → status → l4_result", async () => {
    const events: string[] = []
    const controller = MockTripService.planTripStream("3 days in Huế", 16.46, 107.59)
    controller.subscribe((e: SSEEvent) => {
      events.push(e.event)
    })

    jest.advanceTimersByTime(200)
    expect(events).toEqual(["status"])

    jest.advanceTimersByTime(800)
    expect(events).toEqual(["status", "l2_done"])

    jest.advanceTimersByTime(500)
    expect(events).toEqual(["status", "l2_done", "status"])

    jest.advanceTimersByTime(1000)
    expect(events).toEqual(["status", "l2_done", "status", "l3_done"])

    jest.advanceTimersByTime(300)
    expect(events).toEqual(["status", "l2_done", "status", "l3_done", "status"])

    jest.advanceTimersByTime(1200)
    expect(events).toEqual(["status", "l2_done", "status", "l3_done", "status", "l4_result"])
  })

  it("l4_result should contain a valid TravelItinerary shape", () => {
    let itinerary: Record<string, unknown> | null = null
    const controller = MockTripService.planTripStream("3 days in Huế", 16.46, 107.59)
    controller.subscribe((e: SSEEvent) => {
      if (e.event === "l4_result") {
        itinerary = e.data
      }
    })

    jest.advanceTimersByTime(5000)

    expect(itinerary).not.toBeNull()
    expect(itinerary).toHaveProperty("status", "success")
    expect(itinerary).toHaveProperty("num_days")
    expect(itinerary).toHaveProperty("days")
    const itin = itinerary as unknown as { days: unknown[] }
    expect(Array.isArray(itin.days)).toBe(true)
    expect(itin.days.length).toBeGreaterThan(0)
  })

  it("l4_result days should each have stops with required fields", () => {
    const itinerary = MockTripService.getMockItinerary()
    expect(itinerary.num_days).toBe(3)
    expect(itinerary.days).toHaveLength(3)

    itinerary.days.forEach((day) => {
      expect(day).toHaveProperty("day_index")
      expect(day).toHaveProperty("date")
      expect(day).toHaveProperty("stops")
      expect(Array.isArray(day.stops)).toBe(true)

      day.stops.forEach((stop) => {
        expect(stop).toHaveProperty("poi_id")
        expect(stop).toHaveProperty("poi_name")
        expect(stop).toHaveProperty("location")
        expect(stop.location).toHaveProperty("latitude")
        expect(stop.location).toHaveProperty("longitude")
        expect(stop).toHaveProperty("arrival_time_min")
        expect(stop).toHaveProperty("departure_time_min")
      })
    })
  })

  it("should stop emitting events after cancel() is called", () => {
    const events: string[] = []
    const controller = MockTripService.planTripStream("test", 0, 0)
    controller.subscribe((e) => events.push(e.event))

    jest.advanceTimersByTime(200)
    expect(events).toHaveLength(1)

    controller.cancel()
    jest.advanceTimersByTime(5000)
    // No more events after cancel
    expect(events).toHaveLength(1)
  })

  it("getMockItinerary() should return synchronous result without stream", () => {
    const result = MockTripService.getMockItinerary()
    expect(result.status).toBe("success")
    expect(result.days[0].hotel_name).toBe("Hue Heritage Hotel")
  })
})
