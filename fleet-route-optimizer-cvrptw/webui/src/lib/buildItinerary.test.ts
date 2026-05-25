/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { buildItineraryViaStream } from "@/lib/buildItinerary"
import { streamTripPlan } from "@/lib/streamApi"
import type { TripIntent } from "@/types/trip"

vi.mock("@/lib/streamApi", () => ({
  streamTripPlan: vi.fn(),
}))

const mockStreamTripPlan = vi.mocked(streamTripPlan)

const intent: TripIntent = {
  destination: "Huế",
  days: 2,
  budget: 1_000_000,
  interests: [],
  lockedPoiNames: [],
  rawPrompt: "Đi Huế 2 ngày",
}

const layer4Result = {
  days: [
    {
      day_index: 0,
      stops: [{ poi_id: "poi-1", poi_name: "Đại Nội", arrival_time_min: 480 }],
    },
  ],
  total_distance_km: 12.5,
}

describe("buildItineraryViaStream", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockStreamTripPlan.mockImplementation(({ onEvent }) => {
      onEvent({ stage: "intent_extraction_started" })
      onEvent({ stage: "poi_search_completed", pois_found: 5 })
      onEvent({ stage: "optimization_completed" })
      onEvent({ stage: "validation_completed", validation_notes: ["[warning] partial plan"] })
      onEvent({ stage: "narrative_completed", result: layer4Result })
      return Promise.resolve()
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it("resolves draft when SSE reaches narrative_completed (P3)", async () => {
    const promise = buildItineraryViaStream(intent.rawPrompt, intent)
    await vi.runAllTimersAsync()
    const draft = await promise

    expect(draft.destination).toBe("Huế")
    expect(draft.days[0].items[0].poiId).toBe("poi-1")
    expect(mockStreamTripPlan).toHaveBeenCalledOnce()
  })

  it("rejects when SSE emits error stage", async () => {
    mockStreamTripPlan.mockImplementation(({ onEvent }) => {
      onEvent({ stage: "error", message: "LLM timeout" })
      return Promise.resolve()
    })

    const promise = buildItineraryViaStream(intent.rawPrompt, intent)
    const assertion = expect(promise).rejects.toThrow("LLM timeout")
    await vi.runAllTimersAsync()
    await assertion
  })

  it("reports pipeline steps via callbacks", async () => {
    const steps: Array<{ index: number; detail: string }> = []
    const promise = buildItineraryViaStream(intent.rawPrompt, intent, {
      onStep: (index, detail) => steps.push({ index, detail }),
    })
    await vi.runAllTimersAsync()
    await promise

    expect(steps.some((s) => s.index === 0)).toBe(true)
    expect(steps.some((s) => s.index === 2)).toBe(true)
    expect(steps.some((s) => s.detail.includes("Tối ưu") || s.detail.includes("OR-Tools"))).toBe(true)
  })
})
