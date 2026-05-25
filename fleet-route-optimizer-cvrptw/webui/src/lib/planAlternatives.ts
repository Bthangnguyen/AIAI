import { GATEWAY_BASE_URL, gatewayFetch } from "@/lib/client"
import type { ItineraryDay, ItineraryDraft, ItineraryItem } from "@/types/trip"
import type { PlanAlternativesResult, PlanMetrics, PlanStyle, PlanVariant } from "@/types/plan"
import { PLAN_STYLE_ORDER } from "@/types/plan"

interface BackendPlanMetrics {
  total_cost: number
  total_travel_min: number
  poi_count: number
  total_distance_km: number
  fatigue_score: number
  diversity_score: number
  warnings: { meal: boolean; outdoor_heat: boolean; budget: boolean }
  validation_messages?: string[]
}

interface BackendPlanDay {
  day_index: number
  narrative_title?: string
  stops: Array<{
    poi_id: string
    poi_name?: string
    arrival_time_min: number
  }>
}

interface BackendPlan {
  style: string
  label: string
  description: string
  days: BackendPlanDay[]
  metrics?: BackendPlanMetrics
  total_pois?: number
  overlap_warning?: string | null
}

interface BackendAlternativesResponse {
  status: string
  plans: BackendPlan[]
}

function minutesToTime(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`
}

function mapMetrics(raw?: BackendPlanMetrics): PlanMetrics {
  return {
    totalCost: raw?.total_cost ?? 0,
    totalTravelMin: raw?.total_travel_min ?? 0,
    poiCount: raw?.poi_count ?? 0,
    totalDistanceKm: raw?.total_distance_km ?? 0,
    fatigueScore: raw?.fatigue_score ?? 0,
    diversityScore: raw?.diversity_score ?? 0,
    warnings: {
      meal: raw?.warnings?.meal ?? false,
      outdoor_heat: raw?.warnings?.outdoor_heat ?? false,
      budget: raw?.warnings?.budget ?? false,
    },
    validationMessages: raw?.validation_messages,
  }
}

export function mapBackendPlanToVariant(plan: BackendPlan): PlanVariant {
  const days: ItineraryDay[] = (plan.days ?? []).map((day) => ({
    dayNumber: day.day_index + 1,
    title: day.narrative_title ?? `Ngày ${day.day_index + 1}`,
    items: (day.stops ?? [])
      .filter((s) => s.poi_id && !s.poi_id.startsWith("hotel_"))
      .map(
        (stop, idx): ItineraryItem => ({
          id: `${plan.style}-d${day.day_index}-i${idx}`,
          poiId: stop.poi_id,
          time: minutesToTime(stop.arrival_time_min),
          note: stop.poi_name ?? "",
        }),
      ),
  }))

  const style = (PLAN_STYLE_ORDER.includes(plan.style as PlanStyle) ? plan.style : "balanced") as PlanStyle
  const metrics = mapMetrics(plan.metrics)
  if (!plan.metrics && plan.total_pois != null) {
    metrics.poiCount = plan.total_pois
  }

  return {
    style,
    label: plan.label,
    description: plan.description,
    days,
    metrics,
    overlapWarning: plan.overlap_warning,
  }
}

export function mapAlternativesResponse(data: BackendAlternativesResponse): PlanVariant[] {
  const byStyle = new Map(data.plans.map((p) => [p.style, mapBackendPlanToVariant(p)]))
  return PLAN_STYLE_ORDER.map((style) => byStyle.get(style)).filter((p): p is PlanVariant => Boolean(p))
}

export async function fetchPlanAlternatives(draft: ItineraryDraft): Promise<PlanAlternativesResult> {
  const intent = draft.intent
  const body = {
    user_prompt: intent.rawPrompt,
    num_days: draft.days.length || intent.days || 2,
    budget: draft.budget ?? intent.budget,
    destination: draft.destination || intent.destination || "Huế",
    preferences: intent.interests ?? [],
  }

  const res = await gatewayFetch("/v1/trip/plan_alternatives", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`plan_alternatives failed (${res.status}): ${text}`)
  }

  const data: BackendAlternativesResponse = await res.json()

  return {
    status: data.status,
    plans: mapAlternativesResponse(data),
  }
}
