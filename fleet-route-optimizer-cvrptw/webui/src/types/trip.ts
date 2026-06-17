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

export interface TransportLeg {
  from_stop_id?: string
  from_name?: string
  to_stop_id?: string
  to_name?: string
  mode: string
  mode_label?: string
  distance_km?: number
  travel_time_min?: number
  transport_cost?: number
  cost_policy?: string
  cost_scope?: string
  icon?: string
  warning?: string | null
  is_from_lodging?: boolean
  is_return_to_lodging?: boolean
  distance_confidence?: string
}

export interface ItineraryItem {
  id: string
  poiId: string
  time: string
  note: string
  travel_time_from_prev_min?: number
  travel_time_to_next_min?: number
  transport_from_prev?: TransportLeg
  ticket_cost?: number
  expected_spend?: number
  vibe_note?: string
}

export interface ItineraryDay {
  dayNumber: number
  title: string
  items: ItineraryItem[]
  transportLegs?: TransportLeg[]
  overnightStay?: Record<string, any> | null
  startLodging?: Record<string, any> | null
  endLodging?: Record<string, any> | null
  dayTotalCost?: number
  dayTransportCost?: number
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
  costSummary?: Record<string, any>
  lodgingPlan?: Record<string, any>
  selectedPlanStyle?: PlanStyle
  manualDayNumbers?: number[]
  startDate?: string
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
