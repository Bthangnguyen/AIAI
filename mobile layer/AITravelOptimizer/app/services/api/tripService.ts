import EventSource from "react-native-sse"

import type { ReRoutePayload, ReRouteResponse } from "@/navigators/navigationTypes"

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8001"

export const TripService = {
  /**
   * Pre-flight health check — verify gateway is reachable before starting pipeline.
   */
  async checkHealth(): Promise<{ ready: boolean; message: string }> {
    try {
      const res = await fetch(`${API_BASE_URL}/v1/trip/health`, {
        method: "GET",
        headers: { Accept: "application/json" },
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
    hotelLat: number,
    hotelLon: number,
    hotelName: string,
    numDays: number,
    onMessage: (data: any) => void,
    onError: (error: any) => void,
    onDone: () => void,
  ) {
    const url = `${API_BASE_URL}/v1/trip/plan_trip_stream`
    const eventSource = new EventSource(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
    try {
      const res = await fetch(`${API_BASE_URL}/v1/trip/re_route`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
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

