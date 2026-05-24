import EventSource from "react-native-sse"

import type { ReRoutePayload, ReRouteResponse } from "@/navigators/navigationTypes"
import { FeatureFlags } from "@/config/features"

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || "http://10.0.2.2:8001"

export const TripService = {
  /**
   * Pre-flight health check — verify gateway is reachable before starting pipeline.
   */
  async checkHealth(): Promise<{ ready: boolean; message: string }> {
    try {
      const res = await fetch(`${API_BASE_URL}/v1/trip/health`, {
        method: "GET",
        headers: { Accept: "application/json", "ngrok-skip-browser-warning": "1" },
      })
      if (!res.ok) return { ready: false, message: `Server error: ${res.status}` }
      const data = await res.json()
      return { ready: data.status === "ready", message: data.status }
    } catch (e: any) {
      return { ready: false, message: e?.message || "Server unreachable" }
    }
  },

  planTripStream(
    prompt: string,
    hotelLat: number | undefined,
    hotelLon: number | undefined,
    hotelName: string | undefined,
    numDays: number | undefined,
    onMessage: (data: any) => void,
    onError: (error: any) => void,
    onDone: () => void,
  ) {
    const url = `${API_BASE_URL}/v1/trip/plan_trip_stream`
    const eventSource = new EventSource(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "ngrok-skip-browser-warning": "1" },
      body: JSON.stringify({
        user_prompt: prompt,
        hotel_lat: hotelLat,
        hotel_lon: hotelLon,
        hotel_name: hotelName,
        num_days: numDays,
      }),
    })

    eventSource.addEventListener("message", (event: any) => {
      if (event.data === "[DONE]") {
        eventSource.close()
        onDone()
        return
      }
      try {
        const parsedData = JSON.parse(event.data)
        onMessage(parsedData)
      } catch (e) {
        console.error("Error parsing SSE data", e)
      }
    })

    eventSource.addEventListener("error", (error: any) => {
      console.error("SSE Error:", error)
      onError(error)
      eventSource.close()
    })

    return eventSource
  },

  /**
   * Re-route remaining POIs from current location (JIT).
   * Sends current GPS + remaining POI IDs + original itinerary to Gateway,
   * which forwards to Layer 4 OR-Tools solver.
   */
  async reRoute(payload: ReRoutePayload): Promise<ReRouteResponse> {
    if (FeatureFlags.USE_MOCK_BACKEND) {
      console.log("MOCK REROUTE", payload.user_state);
      // Simulate network delay
      await new Promise(res => setTimeout(res, 1500));
      
      const day = payload.original_itinerary.days.find(d => d.day_index === payload.day_index);
      if (!day) return { status: "error", message: "Day not found" };

      // Create a deeply cloned mock day to simulate AI changes
      const modifiedDay = JSON.parse(JSON.stringify(day));
      const userText = payload.user_state?.text?.toLowerCase() || "";
      const currentMin = payload.current_time_min || 600; // default 10:00 AM

      const userState = payload.user_state || {};

      if (userText.match(/lỗi|quá tải|infeasible/)) {
        return { status: "error", message: "Infeasible: Lịch hiện tại quá dày." };
      }

      if (userState.tired || userText.match(/mệt|đau chân|nghỉ ngơi/)) {
        // Scenario A: Tired -> Insert Cafe
        const cafeStop = {
          poi_id: "mock_cafe_1",
          poi_name: "The Note Coffee (Nghỉ ngơi)",
          location: { latitude: 21.0315, longitude: 105.8525 },
          arrival_time_min: currentMin + 15,
          departure_time_min: currentMin + 60,
          visit_duration_min: 45,
          travel_time_from_prev_min: 15,
          entrance_fee: 50000,
        };
        modifiedDay.stops.splice(0, 0, cafeStop);
        modifiedDay.total_visit_min += 45;
        modifiedDay.total_entrance_fee += 50000;
      } 
      else if (userState.hungry || userText.match(/đói|khát|ăn|uống/)) {
        // Scenario B: Hungry -> Insert Restaurant
        const restStop = {
          poi_id: "mock_rest_1",
          poi_name: "Phở 10 Lý Quốc Sư",
          location: { latitude: 21.0305, longitude: 105.8495 },
          arrival_time_min: currentMin + 10,
          departure_time_min: currentMin + 55,
          visit_duration_min: 45,
          travel_time_from_prev_min: 10,
          entrance_fee: 80000,
        };
        modifiedDay.stops.splice(0, 0, restStop);
        modifiedDay.total_visit_min += 45;
        modifiedDay.total_entrance_fee += 80000;
      }
      else if (userState.weather || userText.match(/mưa|nóng|thời tiết/)) {
        // Scenario C: Weather -> Swap next outdoor with indoor
        if (modifiedDay.stops.length > 0) {
          const indoorStop = {
            poi_id: "mock_indoor_1",
            poi_name: "Bảo tàng Mỹ thuật VN (Tránh thời tiết)",
            location: { latitude: 21.0275, longitude: 105.8355 },
            arrival_time_min: modifiedDay.stops[0].arrival_time_min,
            departure_time_min: modifiedDay.stops[0].arrival_time_min + 90,
            visit_duration_min: 90,
            travel_time_from_prev_min: modifiedDay.stops[0].travel_time_from_prev_min,
            entrance_fee: 40000,
          };
          modifiedDay.total_entrance_fee -= modifiedDay.stops[0].entrance_fee;
          modifiedDay.total_entrance_fee += indoorStop.entrance_fee;
          modifiedDay.total_visit_min = modifiedDay.total_visit_min - modifiedDay.stops[0].visit_duration_min + indoorStop.visit_duration_min;
          modifiedDay.stops[0] = indoorStop;
        }
      }
      else if (userState.wants_cafe || userText.match(/cafe|cà phê|trà/)) {
        // Scenario Cafe -> Insert Cafe
        const cafeStop = {
          poi_id: "mock_cafe_2",
          poi_name: "Giảng Café (Cà phê trứng)",
          location: { latitude: 21.032, longitude: 105.853 },
          arrival_time_min: currentMin + 15,
          departure_time_min: currentMin + 60,
          visit_duration_min: 45,
          travel_time_from_prev_min: 15,
          entrance_fee: 40000,
        };
        modifiedDay.stops.splice(0, 0, cafeStop);
        modifiedDay.total_visit_min += 45;
        modifiedDay.total_entrance_fee += 40000;
      }
      else if (userText.match(/mua|siêu thị|thuốc|đột xuất/)) {
        // Scenario D: Quick stop -> Insert Pharmacy/Mart
        const martStop = {
          poi_id: "mock_mart_1",
          poi_name: "Circle K / Pharmacity (Tạt ngang)",
          location: { latitude: payload.current_location?.lat || 21.0, longitude: payload.current_location?.lon || 105.8 },
          arrival_time_min: currentMin + 5,
          departure_time_min: currentMin + 20,
          visit_duration_min: 15,
          travel_time_from_prev_min: 5,
          entrance_fee: 0,
        };
        modifiedDay.stops.splice(0, 0, martStop);
        modifiedDay.total_visit_min += 15;
      }
      else if (userState.extend_time) {
        // Scenario E: Extend time -> Add 60 mins to the day
        if (modifiedDay.stops.length > 0) {
          modifiedDay.stops[modifiedDay.stops.length - 1].visit_duration_min += 30;
          modifiedDay.total_visit_min += 30;
        }
      }
      else if (userState.prioritize_free) {
        // Scenario F: Prioritize free -> remove the most expensive stop
        let maxFeeIdx = -1;
        let maxFee = 0;
        for (let i = 0; i < modifiedDay.stops.length; i++) {
          if (modifiedDay.stops[i].entrance_fee > maxFee) {
            maxFee = modifiedDay.stops[i].entrance_fee;
            maxFeeIdx = i;
          }
        }
        if (maxFeeIdx !== -1) {
          modifiedDay.total_entrance_fee -= maxFee;
          modifiedDay.total_visit_min -= modifiedDay.stops[maxFeeIdx].visit_duration_min;
          modifiedDay.stops.splice(maxFeeIdx, 1);
        }
      }
      else {
        // Generic fallback: Drop the last stop to save time
        if (modifiedDay.stops.length > 0) {
          modifiedDay.stops.pop();
          modifiedDay.total_distance_km = Math.max(0, modifiedDay.total_distance_km - 2.5);
          modifiedDay.total_visit_min = Math.max(0, modifiedDay.total_visit_min - 60);
        }
      }

      // Re-adjust subsequent arrival times based on insertions/swaps
      if (modifiedDay.stops.length > 1) {
        for (let i = 1; i < modifiedDay.stops.length; i++) {
          modifiedDay.stops[i].arrival_time_min = modifiedDay.stops[i - 1].departure_time_min + modifiedDay.stops[i].travel_time_from_prev_min;
          modifiedDay.stops[i].departure_time_min = modifiedDay.stops[i].arrival_time_min + modifiedDay.stops[i].visit_duration_min;
        }
      }

      return { status: "success", day: modifiedDay };
    }

    try {
      const res = await fetch(`${API_BASE_URL}/v1/trip/re_route`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "ngrok-skip-browser-warning": "1",
        },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        return {
          status: "error",
          message: `Server error: ${res.status}`,
        }
      }

      const data: ReRouteResponse = await res.json()
      return data
    } catch (e: any) {
      return {
        status: "error",
        message: e?.message || "Re-route request failed",
      }
    }
  },
}

