import type { OptimizationStats } from "./stats"

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
export type PreviewMode = "timeline" | "map" | "split" | "compare"
export type BuildStatus = "empty" | "building" | "resolving" | "live"
export type ChatPhase = "collecting" | "confirming" | "ready" | "editing"
export type EditAction =
  | "add_place"
  | "remove_place"
  | "replace_place"
  | "change_budget"
  | "change_pace"
  | "change_time_window"
  | "add_preference"
  | "avoid_preference"
  | "rebuild_requested"
  | "answer_question"

export interface TimeWindowSpec {
  start_min: number
  end_min: number
}

export interface LLMDataContract {
  destination: string | null
  budget_max: number | null
  budget_is_unlimited: boolean
  radius_km: number
  num_days: number
  time_window?: TimeWindowSpec | null
  tags: string[]
  locked_pois: string[]
  excluded_pois: string[]
  weather_preference?: string | null
  hotel_lat?: number | null
  hotel_lon?: number | null
  hotel_name?: string | null
  hotel_confirmed: boolean
  default_hotel_ok: boolean
  transport_modes: string[]
  group_type?: string | null
  group_size?: number | null
  confirmed_fields: string[]
  last_question_field?: string | null
  confirmation_pending: boolean
  ready_to_plan: boolean
  estimated_pois?: number | null
  time_slot?: string | null
  trip_duration_hours?: number | null
  vibe?: string | null
  trip_type?: string | null
  preferred_pace?: string | null
  walking_tolerance?: string | null
  food_preferences: string[]
  avoid_tags: string[]
  target_category_distribution?: Record<string, number> | null
}

export interface EditIntent {
  action: EditAction
  target?: string | null
  constraints: Record<string, unknown>
  raw_message: string
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
