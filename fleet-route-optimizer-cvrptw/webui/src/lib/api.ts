import type { ItineraryDay, ItineraryDraft, ItineraryItem, POI, TripIntent, ValidationNote } from "@/types/trip"
import type { OptimizationStats } from "@/types/stats"
import { GATEWAY_BASE_URL, gatewayFetch } from "@/lib/client"

export const POI_CACHE = new Map<string, POI>()

interface ChatContract {
  destination?: string | null
  budget_max?: number | null
  radius_km?: number
  num_days?: number
  tags?: string[]
  locked_pois?: string[]
}

interface ChatProcessResult {
  status: "ready" | "clarifying" | string
  reply: string
  updated_contract: ChatContract
}

interface BackendPoiResponse {
  uuid: string
  name: string
  category: string
  description?: string | null
  latitude: number
  longitude: number
  visit_duration_min?: number
  price?: number
  entrance_fee?: number
  tags?: string[] | null
  is_locked?: boolean
}

interface TripPlanResponse {
  status: string
  message?: string
  llm_contract?: ChatContract & { hotel_lat?: number; hotel_lon?: number; hotel_name?: string }
  pois?: BackendPoiResponse[]
  layer4_result?: Layer4Itinerary
}

interface Layer4Stop {
  poi_id: string
  poi_name?: string
  arrival_time_min: number
  departure_time_min?: number
  visit_duration_min?: number
  entrance_fee?: number
}

interface Layer4Day {
  day_index: number
  date?: string
  narrative_title?: string
  stops: Layer4Stop[]
}

interface Layer4Itinerary {
  status?: string
  message?: string
  num_days?: number
  days: Layer4Day[]
  total_pois_visited?: number
  total_pois_dropped?: number
  total_distance_km?: number
  total_entrance_fee?: number
  budget_total?: number
  budget_used?: number
  validation_notes?: string[]
}

export interface ReRouteResult {
  status: string
  day?: Layer4Day
  message?: string
}

function minutesToTime(minutes: number): string {
  const h = Math.floor(minutes / 60) % 24
  const m = minutes % 60
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`
}

function mapBackendPoi(poi: BackendPoiResponse): POI {
  const mapped: POI = {
    id: String(poi.uuid),
    name: poi.name,
    category: poi.category,
    description: poi.description ?? "",
    tags: poi.tags ?? [],
    estimatedDurationMinutes: poi.visit_duration_min ?? 60,
    estimatedCost: poi.entrance_fee ?? poi.price ?? 0,
    rating: 4.5,
    lat: poi.latitude,
    lng: poi.longitude,
  }
  POI_CACHE.set(mapped.id, mapped)
  return mapped
}

function cachePoisFromResponse(pois: BackendPoiResponse[] | undefined) {
  pois?.forEach((poi) => mapBackendPoi(poi))
}

function buildIntent(
  rawPrompt: string,
  contract: ChatContract | undefined,
  days?: number,
  budget?: number,
  destination?: string,
  interests?: string[],
): TripIntent {
  return {
    destination: contract?.destination ?? destination,
    days: contract?.num_days ?? days ?? 1,
    budget: contract?.budget_max ?? budget,
    interests: contract?.tags ?? interests ?? [],
    lockedPoiNames: contract?.locked_pois ?? [],
    rawPrompt,
  }
}

function parseValidationNotes(notes: string[] | undefined): ValidationNote[] {
  if (!notes?.length) return []
  return notes.map((raw) => {
    const match = raw.match(/^\[(error|warning|info)\]\s*(.+)$/i)
    if (!match) return { severity: "info" as const, message: raw }
    return { severity: match[1].toLowerCase() as ValidationNote["severity"], message: match[2].trim() }
  })
}

export function mapLayer4ResultToDraft(
  l4: Layer4Itinerary,
  intent: TripIntent,
  destination: string,
): ItineraryDraft {
  const now = new Date().toISOString()
  const days: ItineraryDay[] = l4.days.map((day) => {
    const items: ItineraryItem[] = day.stops
      .filter((stop) => !stop.poi_id.startsWith("hotel_day_") && stop.poi_id !== "__rest_break__")
      .map((stop, index) => ({
        id: `${day.day_index}-${stop.poi_id}-${stop.arrival_time_min}-${index}`,
        poiId: stop.poi_id,
        time: minutesToTime(stop.arrival_time_min),
        note: stop.poi_name ?? "",
      }))

    return {
      dayNumber: day.day_index + 1,
      title: day.narrative_title ?? `Ngày ${day.day_index + 1}`,
      items,
    }
  })

  const optimizationStats: OptimizationStats = {
    totalDistanceKm: l4.total_distance_km ?? 0,
    customersServed: l4.total_pois_visited ?? days.reduce((s, d) => s + d.items.length, 0),
    totalPoisAvailable: l4.total_pois_visited ?? 0,
    totalLoadUsed: 0,
    totalLoadCapacity: 0,
    saturationPercent: 0,
    vehiclesUsed: l4.num_days ?? days.length,
    totalVehicles: l4.num_days ?? days.length,
    budgetUsed: l4.budget_used ?? l4.total_entrance_fee ?? 0,
    budgetMax: l4.budget_total ?? intent.budget ?? 0,
    avgTravelTimePerVehicleMin: 0,
    avgTotalTimePerVehicleMin: 0,
    solverTimeSeconds: 0,
  }

  return {
    id: `draft-${Date.now()}`,
    destination,
    days,
    budget: intent.budget,
    tags: intent.interests,
    createdAt: now,
    updatedAt: now,
    status: "draft",
    intent,
    optimizationStats,
    validationNotes: parseValidationNotes(l4.validation_notes),
    droppedPoiCount: l4.total_pois_dropped ?? 0,
    budgetUsed: l4.budget_used ?? l4.total_entrance_fee ?? 0,
  }
}

export async function chatProcess(
  message: string,
  history: { role: string; content: string }[],
  currentContract: ChatContract,
): Promise<ChatProcessResult> {
  const res = await gatewayFetch("/v1/trip/chat_process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, current_contract: currentContract }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`chat_process failed (${res.status}): ${text}`)
  }
  return res.json()
}

export async function generateRealItinerary(
  rawPrompt: string,
  days?: number,
  budget?: number,
  destination?: string,
  interests?: string[],
): Promise<ItineraryDraft> {
  const res = await gatewayFetch("/v1/trip/plan_trip", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_prompt: rawPrompt,
      num_days: days,
      budget,
      destination: destination ?? "Huế",
      preferences: interests,
    }),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`plan_trip failed (${res.status}): ${text}`)
  }

  const data: TripPlanResponse = await res.json()
  cachePoisFromResponse(data.pois)

  if (data.status === "error" || !data.layer4_result) {
    throw new Error(data.message ?? "Không thể tạo lịch trình")
  }

  const contract = data.llm_contract
  const intent = buildIntent(rawPrompt, contract, days, budget, destination, interests)
  const dest = contract?.destination ?? destination ?? "Huế"

  return mapLayer4ResultToDraft(data.layer4_result, intent, dest)
}

export async function searchPoisBackend(query: string): Promise<POI[]> {
  const params = new URLSearchParams({ query, limit: "8" })
  const res = await gatewayFetch(`/v1/trip/search_pois?${params.toString()}`)
  if (!res.ok) return []
  const data: BackendPoiResponse[] = await res.json()
  return data.map(mapBackendPoi)
}

export async function reRouteDay(
  currentLat: number,
  currentLon: number,
  remainingPoiIds: string[],
  originalItinerary: object,
  dayIndex: number,
  excludedPoiIds: string[] = [],
  currentTimeMin = 480,
): Promise<ReRouteResult> {
  const res = await gatewayFetch("/v1/trip/re_route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      current_lat: currentLat,
      current_lon: currentLon,
      current_time_min: currentTimeMin,
      remaining_poi_ids: remainingPoiIds,
      excluded_poi_ids: excludedPoiIds.length ? excludedPoiIds : undefined,
      day_index: dayIndex,
      original_itinerary: originalItinerary,
    }),
  })

  if (!res.ok) {
    const text = await res.text()
    return { status: "error", message: `re_route failed (${res.status}): ${text}` }
  }

  return res.json()
}

export async function checkGatewayHealth(): Promise<boolean> {
  try {
    const res = await gatewayFetch("/v1/trip/health")
    if (!res.ok) return false
    const data = await res.json()
    return data.status === "ready"
  } catch {
    return false
  }
}

export { GATEWAY_BASE_URL }
