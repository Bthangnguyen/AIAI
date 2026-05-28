import type { ItineraryDay, ItineraryDraft, ItineraryItem, POI, TripIntent, ValidationNote } from "@/types/trip"
import type { OptimizationStats } from "@/types/stats"
import { GATEWAY_BASE_URL, gatewayFetch } from "@/lib/client"

export const POI_CACHE = new Map<string, POI>()

// Helper to save POI_CACHE to localStorage
export function saveCacheToStorage() {
  if (typeof window !== "undefined") {
    try {
      const entries = Array.from(POI_CACHE.entries())
      localStorage.setItem("tripflow_poi_cache", JSON.stringify(entries))
    } catch (e) {
      console.error("Failed to save POI_CACHE to localStorage", e)
    }
  }
}

// Helper to load POI_CACHE from localStorage
export function loadCacheFromStorage() {
  if (typeof window !== "undefined") {
    try {
      const stored = localStorage.getItem("tripflow_poi_cache")
      if (stored) {
        const entries = JSON.parse(stored) as [string, POI][]
        entries.forEach(([id, poi]) => {
          POI_CACHE.set(id, poi)
        })
      }
    } catch (e) {
      console.error("Failed to load POI_CACHE from localStorage", e)
    }
  }
}

// Load cache immediately when importing in browser
if (typeof window !== "undefined") {
  loadCacheFromStorage()
}

interface ChatContract {
  destination?: string | null
  budget_max?: number | null
  budget_is_unlimited?: boolean
  radius_km?: number
  num_days?: number
  tags?: string[]
  locked_pois?: string[]
  excluded_pois?: string[]
  hotel_lat?: number | null
  hotel_lon?: number | null
  hotel_name?: string | null
  hotel_confirmed?: boolean
  default_hotel_ok?: boolean
  time_window?: { start_min: number; end_min: number } | null
  time_slot?: string | null
  transport_modes?: string[]
  preferred_pace?: string | null
  walking_tolerance?: string | null
  food_preferences?: string[]
  avoid_tags?: string[]
  target_category_distribution?: Record<string, number>
  distribution_description?: string | null
  allow_cafe?: boolean
  allow_art?: boolean
  allow_shopping?: boolean
  distribution_locked?: boolean
}

interface ChatProcessResult {
  status: "ready" | "clarifying" | string
  reply: string
  updated_contract: ChatContract
  updated_itinerary?: any
  edit_intent?: any
  phase?: string
}

interface BackendPoiResponse {
  uuid: string
  name: string
  category: string
  category_group?: string | null
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
  llm_contract?: ChatContract
  pois?: BackendPoiResponse[]
  layer4_result?: Layer4Itinerary
}

interface Layer4Stop {
  poi_id: string
  poi_name?: string
  category?: string
  description?: string
  arrival_time_min: number
  departure_time_min?: number
  visit_duration_min?: number
  entrance_fee?: number
  location?: { latitude: number; longitude: number }
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
    category: poi.category_group ?? poi.category,
    description: poi.description ?? "",
    tags: poi.tags ?? [],
    estimatedDurationMinutes: poi.visit_duration_min ?? 60,
    estimatedCost: (poi.entrance_fee && poi.entrance_fee > 0) ? poi.entrance_fee : (poi.price || 0),
    rating: 4.5,
    lat: poi.latitude,
    lng: poi.longitude,
  }
  POI_CACHE.set(mapped.id, mapped)
  saveCacheToStorage()
  return mapped
}

export function cachePoisFromResponse(pois: BackendPoiResponse[] | undefined) {
  pois?.forEach((poi) => mapBackendPoi(poi))
  saveCacheToStorage()
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
    budgetIsUnlimited: contract?.budget_is_unlimited,
    interests: contract?.tags ?? interests ?? [],
    lockedPoiNames: contract?.locked_pois ?? [],
    excludedPoiNames: contract?.excluded_pois ?? [],
    preferredPace: contract?.preferred_pace ?? undefined,
    walkingTolerance: contract?.walking_tolerance ?? undefined,
    foodPreferences: contract?.food_preferences ?? [],
    avoidTags: contract?.avoid_tags ?? [],
    timeWindow: contract?.time_window ?? null,
    timeSlot: contract?.time_slot ?? undefined,
    transportModes: contract?.transport_modes ?? [],
    hotelName: contract?.hotel_name ?? undefined,
    hotelConfirmed: contract?.hotel_confirmed,
    defaultHotelOk: contract?.default_hotel_ok,
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
  llmContract?: ChatContract,
): ItineraryDraft {
  const now = new Date().toISOString()
  const days: ItineraryDay[] = l4.days.map((day) => {
    const items: ItineraryItem[] = day.stops
      .filter((stop) => !stop.poi_id.startsWith("hotel_day_") && stop.poi_id !== "__rest_break__")
      .map((stop, index) => {
        // Proactively seed/update POI_CACHE using stop's real coordinates from backend
        if (stop.poi_id && stop.location) {
          const cached = POI_CACHE.get(stop.poi_id)
          POI_CACHE.set(stop.poi_id, {
            id: stop.poi_id,
            name: stop.poi_name ?? cached?.name ?? "Unknown",
            category: stop.category ?? cached?.category ?? "general",
            description: stop.description ?? cached?.description ?? "",
            tags: cached?.tags ?? [],
            estimatedDurationMinutes: stop.visit_duration_min ?? cached?.estimatedDurationMinutes ?? 60,
            estimatedCost: (stop.entrance_fee && stop.entrance_fee > 0)
              ? stop.entrance_fee
              : ((stop as any).price && (stop as any).price > 0)
                ? (stop as any).price
                : cached?.estimatedCost ?? 0,
            rating: cached?.rating ?? 4.5,
            lat: stop.location.latitude,
            lng: stop.location.longitude,
          })
          saveCacheToStorage()
        }

        return {
          id: `${day.day_index}-${stop.poi_id}-${stop.arrival_time_min}-${index}`,
          poiId: stop.poi_id,
          time: minutesToTime(stop.arrival_time_min),
          note: stop.poi_name ?? "",
        }
      })

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
    llmContract,
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
  hasDraft?: boolean,
  currentItinerary?: any,
): Promise<ChatProcessResult> {
  const res = await gatewayFetch("/v1/trip/chat_process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      history,
      current_contract: currentContract,
      has_draft: !!hasDraft,
      current_itinerary: currentItinerary,
    }),
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
  currentContract?: any,
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
      contract: currentContract,
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

  return mapLayer4ResultToDraft(data.layer4_result, intent, dest, contract)
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
