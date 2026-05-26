import type { OptimizationStats } from "./stats"
import type { PlanStyle } from "./plan"

export type TravelStyle = "relaxed" | "balanced" | "dense"
export type DraftStatus = "draft"
export type MissingIntentField = "destination" | "days" | "budget"
export type BuilderMode = "plan" | "build"
export type PreviewMode = "timeline" | "map" | "split" | "compare"
export type BuildStatus = "empty" | "building" | "resolving" | "live" | "error"

export interface ValidationNote {
  severity: "error" | "warning" | "info"
  message: string
  suggestedFix?: string
}

export interface POI {
  id: string
  name: string
  category: string
  description: string
  tags: string[]
  estimatedDurationMinutes: number
  estimatedCost: number
  rating: number
  area?: string
  lat: number
  lng: number
}

export interface TripIntent {
  destination?: string
  days?: number
  budget?: number
  interests: string[]
  lockedPoiNames: string[]
  travelStyle?: TravelStyle
  dietary?: string[]
  rawPrompt: string
}

export interface ItineraryItem {
  id: string
  poiId: string
  time: string
  note: string
}

export interface ItineraryDay {
  dayNumber: number
  title: string
  items: ItineraryItem[]
}

export interface ItineraryDraft {
  id: string
  destination: string
  days: ItineraryDay[]
  budget?: number
  tags: string[]
  createdAt: string
  updatedAt: string
  status: DraftStatus
  intent: TripIntent
  optimizationStats?: OptimizationStats
  validationNotes?: ValidationNote[]
  droppedPoiCount?: number
  budgetUsed?: number
  selectedPlanStyle?: PlanStyle
  manualDayNumbers?: number[]
}

export interface FollowUpQuestion {
  field: MissingIntentField
  question: string
}

export interface RemovedItemState {
  dayNumber: number
  item: ItineraryItem
  index: number
}
