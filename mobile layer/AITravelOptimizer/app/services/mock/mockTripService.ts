/**
 * MockTripService — simulates the full L2→L3→L4 SSE pipeline.
 *
 * When USE_MOCK_BACKEND = true, this replaces real API calls.
 * Emits the same SSE event shapes as the real gateway for drop-in compatibility.
 */
import { TravelItinerary } from "@/navigators/navigationTypes"

export type SSEEventType = "l2_done" | "l3_done" | "l4_result" | "error" | "status"

export interface SSEEvent {
  event: SSEEventType
  data: Record<string, unknown>
  timestamp: number
}

export type SSEListener = (event: SSEEvent) => void

export interface MockStreamController {
  /** Subscribe to SSE events */
  subscribe: (listener: SSEListener) => void
  /** Cancel the stream (cleanup) */
  cancel: () => void
}

// ─── Mock 3-day Huế Itinerary ────────────────────────────────────────────────
const HUE_MOCK_ITINERARY: TravelItinerary = {
  status: "success",
  num_days: 3,
  total_pois_visited: 9,
  total_pois_dropped: 2,
  total_entrance_fee: 800000,
  total_travel_min: 180,
  total_distance_km: 42.5,
  budget_used: 800000,
  days: [
    {
      day_index: 1,
      date: "2026-06-14",
      hotel_name: "Hue Heritage Hotel",
      hotel_location: { latitude: 16.4637, longitude: 107.5909 },
      total_travel_min: 60,
      total_visit_min: 330,
      total_distance_km: 14,
      total_entrance_fee: 350000,
      num_pois: 3,
      stops: [
        {
          poi_id: "hue-001",
          poi_name: "Đại Nội Huế",
          location: { latitude: 16.4698, longitude: 107.5796 },
          arrival_time_min: 480, // 08:00
          departure_time_min: 600, // 10:00
          visit_duration_min: 120,
          travel_time_from_prev_min: 15,
          entrance_fee: 200000,
        },
        {
          poi_id: "hue-009",
          poi_name: "Vườn Cơ Hạ",
          location: { latitude: 16.4712, longitude: 107.576 },
          arrival_time_min: 615, // 10:15
          departure_time_min: 660, // 11:00
          visit_duration_min: 45,
          travel_time_from_prev_min: 10,
          entrance_fee: 50000,
        },
        {
          poi_id: "hue-007",
          poi_name: "Bún Bò Huế Mợ Tôn",
          location: { latitude: 16.465, longitude: 107.595 },
          arrival_time_min: 690, // 11:30
          departure_time_min: 735, // 12:15
          visit_duration_min: 45,
          travel_time_from_prev_min: 10,
          entrance_fee: 0,
        },
      ],
    },
    {
      day_index: 2,
      date: "2026-06-15",
      hotel_name: "Hue Heritage Hotel",
      hotel_location: { latitude: 16.4637, longitude: 107.5909 },
      total_travel_min: 75,
      total_visit_min: 315,
      total_distance_km: 18.5,
      total_entrance_fee: 300000,
      num_pois: 3,
      stops: [
        {
          poi_id: "hue-008",
          poi_name: "Lăng Minh Mạng",
          location: { latitude: 16.4378, longitude: 107.547 },
          arrival_time_min: 480, // 08:00
          departure_time_min: 570, // 09:30
          visit_duration_min: 90,
          travel_time_from_prev_min: 25,
          entrance_fee: 150000,
        },
        {
          poi_id: "hue-003",
          poi_name: "Lăng Tự Đức",
          location: { latitude: 16.4578, longitude: 107.5528 },
          arrival_time_min: 600, // 10:00
          departure_time_min: 690, // 11:30
          visit_duration_min: 90,
          travel_time_from_prev_min: 20,
          entrance_fee: 150000,
        },
        {
          poi_id: "hue-013",
          poi_name: "Làng Hương Thủy Xuân",
          location: { latitude: 16.4456, longitude: 107.5634 },
          arrival_time_min: 720, // 12:00
          departure_time_min: 780, // 13:00
          visit_duration_min: 60,
          travel_time_from_prev_min: 10,
          entrance_fee: 0,
        },
      ],
    },
    {
      day_index: 3,
      date: "2026-06-16",
      hotel_name: "Hue Heritage Hotel",
      hotel_location: { latitude: 16.4637, longitude: 107.5909 },
      total_travel_min: 45,
      total_visit_min: 225,
      total_distance_km: 10,
      total_entrance_fee: 150000,
      num_pois: 3,
      stops: [
        {
          poi_id: "hue-002",
          poi_name: "Chùa Thiên Mụ",
          location: { latitude: 16.453, longitude: 107.5487 },
          arrival_time_min: 480, // 08:00
          departure_time_min: 540, // 09:00
          visit_duration_min: 60,
          travel_time_from_prev_min: 15,
          entrance_fee: 0,
        },
        {
          poi_id: "hue-004",
          poi_name: "Lăng Khải Định",
          location: { latitude: 16.4039, longitude: 107.5875 },
          arrival_time_min: 570, // 09:30
          departure_time_min: 645, // 10:45
          visit_duration_min: 75,
          travel_time_from_prev_min: 20,
          entrance_fee: 150000,
        },
        {
          poi_id: "hue-005",
          poi_name: "Cầu Trường Tiền",
          location: { latitude: 16.4627, longitude: 107.5996 },
          arrival_time_min: 1080, // 18:00 (evening)
          departure_time_min: 1110, // 18:30
          visit_duration_min: 30,
          travel_time_from_prev_min: 10,
          entrance_fee: 0,
        },
      ],
    },
  ],
}

// ─── MockTripService ──────────────────────────────────────────────────────────

export const MockTripService = {
  /**
   * Simulate the full SSE pipeline: L2 → L3 → L4.
   * Emits events with realistic delays matching real backend performance.
   *
   * @param _prompt    User's travel prompt (unused in mock)
   * @param _hotelLat  Hotel latitude (unused in mock)
   * @param _hotelLon  Hotel longitude (unused in mock)
   * @returns MockStreamController — subscribe to events, cancel when done
   */
  planTripStream: (
    _prompt: string,
    _hotelLat?: number,
    _hotelLon?: number,
    _hotelName?: string,
    _numDays?: number,
  ): MockStreamController => {
    const listeners: SSEListener[] = []
    let cancelled = false
    const timeouts: ReturnType<typeof setTimeout>[] = []

    const emit = (event: SSEEvent) => {
      if (!cancelled) {
        listeners.forEach((l) => l(event))
      }
    }

    // Schedule SSE events
    const t1 = setTimeout(() => {
      emit({
        event: "status",
        data: { message: "Analyzing your travel request..." },
        timestamp: Date.now(),
      })
    }, 200)

    const t2 = setTimeout(() => {
      emit({
        event: "l2_done",
        data: {
          intent: {
            destination: "Huế, Vietnam",
            num_days: _numDays ?? 3,
            interests: ["culture", "food", "nature"],
            budget_vnd: 2000000,
          },
        },
        timestamp: Date.now(),
      })
    }, 1000)

    const t3 = setTimeout(() => {
      emit({
        event: "status",
        data: { message: "Finding the best attractions for you..." },
        timestamp: Date.now(),
      })
    }, 1500)

    const t4 = setTimeout(() => {
      emit({
        event: "l3_done",
        data: {
          pois_found: 15,
          pois_selected: 11,
          search_radius_km: 50,
        },
        timestamp: Date.now(),
      })
    }, 2500)

    const t5 = setTimeout(() => {
      emit({
        event: "status",
        data: { message: "Optimizing your route..." },
        timestamp: Date.now(),
      })
    }, 2800)

    const t6 = setTimeout(() => {
      emit({
        event: "l4_result",
        data: HUE_MOCK_ITINERARY as unknown as Record<string, unknown>,
        timestamp: Date.now(),
      })
    }, 4000)

    timeouts.push(t1, t2, t3, t4, t5, t6)

    return {
      subscribe: (listener: SSEListener) => {
        listeners.push(listener)
      },
      cancel: () => {
        cancelled = true
        timeouts.forEach(clearTimeout)
      },
    }
  },

  /** Return the pre-built mock itinerary synchronously (for testing) */
  getMockItinerary: (): TravelItinerary => HUE_MOCK_ITINERARY,
}
