import type { ItineraryDay } from "@/types/trip"

export type PlanStyle = "balanced" | "budget" | "chill"

export interface PlanWarningFlags {
  meal: boolean
  outdoor_heat: boolean
  budget: boolean
}

export interface PlanMetrics {
  totalCost: number
  totalTravelMin: number
  poiCount: number
  totalDistanceKm: number
  fatigueScore: number
  diversityScore: number
  warnings: PlanWarningFlags
  validationMessages?: string[]
}

export interface PlanVariant {
  style: PlanStyle
  label: string
  description: string
  days: ItineraryDay[]
  metrics: PlanMetrics
  overlapWarning?: string | null
}

export interface PlanAlternativesResult {
  status: string
  plans: PlanVariant[]
}

export const PLAN_STYLE_ORDER: PlanStyle[] = ["balanced", "budget", "chill"]

export const PLAN_STYLE_LABELS: Record<PlanStyle, string> = {
  balanced: "Cân bằng",
  budget: "Tiết kiệm",
  chill: "Thoải mái",
}
