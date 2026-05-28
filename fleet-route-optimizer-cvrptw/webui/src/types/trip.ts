import type { OptimizationStats } from "./stats"
import type { PlanStyle } from "./plan"

export interface TimeWindowSpec {
  start_min: number
  end_min: number
}

export type LLMDataContract = Record<string, any>

export type TravelStyle = "relaxed" | "balanced" | "dense"
export type DraftStatus = "draft"
export type MissingIntentField =
  | "destination"
  | "days"
  | "num_days"
  | "budget"
  | "interests"
  | "pace"
  | "walking"
  | "food"
  | "must_visit"
  | "avoid"
  | "time_window"
  | "transport"
  | "group"
  | "hotel"
export type BuilderMode = "plan" | "build"
export type PreviewMode = "timeline" | "map" | "split"
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
  budgetIsUnlimited?: boolean
  interests: string[]
  lockedPoiNames: string[]
  excludedPoiNames?: string[]
  travelStyle?: TravelStyle
  dietary?: string[]
  preferredPace?: string
  walkingTolerance?: string
  foodPreferences?: string[]
  avoidTags?: string[]
  timeWindow?: TimeWindowSpec | null
  timeSlot?: string
  transportModes?: string[]
  groupType?: string
  groupSize?: number
  hotelName?: string
  hotelConfirmed?: boolean
  defaultHotelOk?: boolean
  confirmedFields?: string[]
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
  llmContract?: LLMDataContract
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
