import EventSource from "react-native-sse"
import type { ReRoutePayload, ReRouteResponse } from "@/navigators/navigationTypes"
import type { ChatMessage, ChatProcessResponse, LLMDataContract } from "../../types/api"
import { FeatureFlags } from "@/config/features"

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || "http://127.0.0.1:8001"

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
    contractOrOnMessage: LLMDataContract | ((data: any) => void) | undefined,
    onMessageOrOnError?: ((data: any) => void) | ((error: any) => void),
    onErrorOrOnDone?: ((error: any) => void) | (() => void),
    onDoneMaybe?: () => void,
  ) {
    const contract = typeof contractOrOnMessage === "function" ? undefined : contractOrOnMessage
    const onMessage = (typeof contractOrOnMessage === "function" ? contractOrOnMessage : onMessageOrOnError) as
      | ((data: any) => void)
      | undefined
    const onError = (typeof contractOrOnMessage === "function" ? onMessageOrOnError : onErrorOrOnDone) as
      | ((error: any) => void)
      | undefined
    const onDone = (typeof contractOrOnMessage === "function" ? onErrorOrOnDone : onDoneMaybe) as
      | (() => void)
      | undefined

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
        contract,
      }),
    })

    eventSource.addEventListener("message", (event: any) => {
      if (event.data === "[DONE]") {
        eventSource.close()
        onDone?.()
        return
      }
      try {
        const parsedData = JSON.parse(event.data)
        onMessage?.(parsedData)
      } catch (e) {
        console.error("Error parsing SSE data", e)
      }
    })

    eventSource.addEventListener("error", (error: any) => {
      console.error("SSE Error:", error)
      onError?.(error)
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
      console.log("[MOCK] Intercepting reroute request via FeatureFlags");
      await new Promise(res => setTimeout(res, 1200));
      
      const day = payload.original_itinerary?.days?.find((d: any) => d.day_index === payload.day_index);
      if (!day) return { status: "error", message: "Day index not found in mock state" };

      const modifiedDay = JSON.parse(JSON.stringify(day));
      const userText = payload.user_state?.text?.toLowerCase() || "";
      const currentMin = payload.current_time_min || 600;
      const userState = payload.user_state || {};

      if (userText.includes("lỗi") || userText.includes("quá tải") || userText.includes("infeasible")) {
        return { status: "error", message: "Infeasible: Lịch di chuyển quá dày đặc hoặc tắc nghẽn." };
      }

      if (userState.tired || userText.match(/mệt|đau chân|nghỉ ngơi/)) {
        const cafeStop = {
          poi_id: "mock_cafe_1",
          poi_name: "The Note Coffee (Nghỉ chân)",
          location: { latitude: 16.4625, longitude: 107.5925 },
          arrival_time_min: currentMin + 15,
          departure_time_min: currentMin + 60,
          visit_duration_min: 45,
          travel_time_from_prev_min: 15,
          entrance_fee: 45000,
        };
        modifiedDay.stops.splice(0, 0, cafeStop);
        modifiedDay.total_visit_min += 45;
        modifiedDay.total_entrance_fee += 45000;
      } 
      else if (userState.hungry || userText.match(/đói|khát|ăn|uống/)) {
        const restStop = {
          poi_id: "mock_rest_1",
          poi_name: "Phở 10 Lý Quốc Sư (Chi nhánh Huế)",
          location: { latitude: 16.4615, longitude: 107.5915 },
          arrival_time_min: currentMin + 10,
          departure_time_min: currentMin + 55,
          visit_duration_min: 45,
          travel_time_from_prev_min: 10,
          entrance_fee: 75000,
        };
        modifiedDay.stops.splice(0, 0, restStop);
        modifiedDay.total_visit_min += 45;
        modifiedDay.total_entrance_fee += 75000;
      }
      else if (userState.weather || userText.match(/mưa|nóng|thời tiết/)) {
        if (modifiedDay.stops.length > 0) {
          const indoorStop = {
            poi_id: "mock_indoor_1",
            poi_name: "Cung Diên Thọ (Tránh nắng/mưa)",
            location: { latitude: 16.4695, longitude: 107.5785 },
            arrival_time_min: modifiedDay.stops[0].arrival_time_min,
            departure_time_min: modifiedDay.stops[0].arrival_time_min + 90,
            visit_duration_min: 90,
            travel_time_from_prev_min: modifiedDay.stops[0].travel_time_from_prev_min,
            entrance_fee: 150000,
          };
          modifiedDay.total_entrance_fee = modifiedDay.total_entrance_fee - modifiedDay.stops[0].entrance_fee + indoorStop.entrance_fee;
          modifiedDay.total_visit_min = modifiedDay.total_visit_min - modifiedDay.stops[0].visit_duration_min + indoorStop.visit_duration_min;
          modifiedDay.stops[0] = indoorStop;
        }
      }
      else if (userState.wants_cafe || userText.match(/cafe|cà phê|trà/)) {
        const cafeStop = {
          poi_id: "mock_cafe_2",
          poi_name: "Giảng Café (Cà phê trứng muối Huế)",
          location: { latitude: 16.465, longitude: 107.595 },
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
      else if (userState.extend_time) {
        if (modifiedDay.stops.length > 0) {
          modifiedDay.stops[modifiedDay.stops.length - 1].visit_duration_min += 30;
          modifiedDay.total_visit_min += 30;
        }
      }
      else if (userState.prioritize_free) {
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
        if (modifiedDay.stops.length > 0) {
          const oldStop = modifiedDay.stops[0];
          const alternativeStop = {
            poi_id: "mock_alt_1",
            poi_name: "Hồ Tịnh Tâm (Điểm dừng thư thả)",
            location: { latitude: 16.476, longitude: 107.579 },
            arrival_time_min: oldStop.arrival_time_min,
            departure_time_min: oldStop.arrival_time_min + 60,
            visit_duration_min: 60,
            travel_time_from_prev_min: oldStop.travel_time_from_prev_min,
            entrance_fee: 0,
          };
          modifiedDay.total_entrance_fee -= oldStop.entrance_fee;
          modifiedDay.total_visit_min = modifiedDay.total_visit_min - oldStop.visit_duration_min + alternativeStop.visit_duration_min;
          modifiedDay.stops[0] = alternativeStop;
        }
      }

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

  async processChat(
    message: string,
    history: ChatMessage[],
    currentContract: any
  ): Promise<ChatProcessResponse> {
    try {
      const res = await fetch(`${API_BASE_URL}/v1/trip/chat_process`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "ngrok-skip-browser-warning": "1",
        },
        body: JSON.stringify({
          message,
          history,
          current_contract: currentContract,
        }),
      })

      if (!res.ok) {
        throw new Error(`Server returned code ${res.status}`)
      }

      const data = await res.json()
      return data
    } catch (e: any) {
      console.error("Conversational chat_process error:", e)
      return {
        status: "clarifying",
        reply: "Dạ kết nối mạng đang gián đoạn một chút. Bạn có thể cho tôi biết rõ hơn số ngày đi và ngân sách mong muốn tại Huế không?",
        updated_contract: currentContract,
      }
    }
  },
}
