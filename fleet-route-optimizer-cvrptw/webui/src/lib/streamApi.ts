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
  step?: string
  status?: string
  contract?: Record<string, unknown>
  tags?: string[]
  locked?: string[]
  pois_found?: number
  locked_count?: number
  validation_notes?: string[]
  result?: Record<string, unknown>
  message?: string
  error_code?: string
  days?: unknown[]
  num_days?: number
  [key: string]: unknown
}

export interface StreamTripPlanOptions {
  userPrompt: string
  hotelLat?: number
  hotelLon?: number
  hotelName?: string
  numDays?: number
  budget?: number
  destination?: string
  interests?: string[]
  contract?: Record<string, unknown>
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
      headers: { 
        "Content-Type": "application/json", 
        Accept: "text/event-stream",
        Authorization: "Bearer mock-session-token-xyz-987",
      },
      body: JSON.stringify({
        user_prompt: userPrompt,
        hotel_lat: hotelLat,
        hotel_lon: hotelLon,
        hotel_name: hotelName,
        num_days: numDays,
        budget: options.budget,
        destination: options.destination ?? "Huế",
        preferences: options.interests,
        contract: options.contract,
      }),
      signal,
    })

    if (!res.ok || !res.body) {
      let detail = ""
      try { detail = await res.text() } catch { /* ignore */ }
      throw new Error(`Không tạo được lịch trình\n\nSSE failed (${res.status}): ${detail}`)
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
