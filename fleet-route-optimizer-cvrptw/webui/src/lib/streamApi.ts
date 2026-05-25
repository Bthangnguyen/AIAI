import { GATEWAY_BASE_URL } from "@/lib/client"

export type StreamStep =
  | "intent_extraction_started"
  | "intent_extraction_completed"
  | "poi_search_started"
  | "poi_search_completed"
  | "optimization_started"
  | "optimization_completed"
  | "validation_completed"
  | "narrative_completed"
  | "error"
  | "done"

export interface StreamEvent {
  stage: StreamStep | string
  contract?: Record<string, unknown>
  pois_found?: number
  locked_count?: number
  validation_notes?: string[]
  result?: Record<string, unknown>
  message?: string
}

export interface StreamTripPlanOptions {
  userPrompt: string
  hotelLat?: number
  hotelLon?: number
  hotelName?: string
  numDays?: number
  onEvent: (event: StreamEvent) => void
  onError: (error: Error) => void
  onDone: () => void
  signal?: AbortSignal
}

export async function streamTripPlan(options: StreamTripPlanOptions): Promise<void> {
  const { userPrompt, hotelLat, hotelLon, hotelName, numDays, onEvent, onError, onDone, signal } = options

  try {
    const res = await fetch(`${GATEWAY_BASE_URL}/v1/trip/plan_trip_stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({
        user_prompt: userPrompt,
        hotel_lat: hotelLat,
        hotel_lon: hotelLon,
        hotel_name: hotelName,
        num_days: numDays,
      }),
      signal,
    })

    if (!res.ok || !res.body) {
      throw new Error(`SSE failed (${res.status})`)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split("\n\n")
      buffer = parts.pop() ?? ""

      for (const part of parts) {
        const line = part
          .split("\n")
          .find((l) => l.startsWith("data:"))
          ?.slice(5)
          .trim()
        if (!line) continue
        if (line === "[DONE]") {
          onDone()
          return
        }
        try {
          onEvent(JSON.parse(line) as StreamEvent)
        } catch {
          // ignore malformed chunks
        }
      }
    }

    onDone()
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)))
  }
}
