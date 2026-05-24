import { ComponentProps } from "react"
import { BottomTabScreenProps } from "@react-navigation/bottom-tabs"
import {
  CompositeScreenProps,
  NavigationContainer,
  NavigatorScreenParams,
} from "@react-navigation/native"
import { NativeStackScreenProps } from "@react-navigation/native-stack"

// Demo Tab Navigator types
export type DemoTabParamList = {
  DemoCommunity: undefined
  DemoShowroom: { queryIndex?: string; itemIndex?: string }
  DemoDebug: undefined
  DemoPodcastList: undefined
}

/**
 * TravelItinerary shape received from SSE stream (Layer 4 output).
 * Matches fleet-route-optimizer-cvrptw TravelItinerary schema.
 */
export type TravelItineraryStop = {
  poi_id: string
  poi_name: string
  location: { latitude: number; longitude: number }
  arrival_time_min: number
  departure_time_min: number
  visit_duration_min: number
  travel_time_from_prev_min: number
  entrance_fee: number
}

export type TravelItineraryDay = {
  day_index: number
  date: string
  hotel_name: string
  hotel_location: { latitude: number; longitude: number }
  start_hotel_name?: string
  start_hotel_location?: { latitude: number; longitude: number }
  end_hotel_name?: string
  end_hotel_location?: { latitude: number; longitude: number }
  stops: TravelItineraryStop[]
  total_travel_min: number
  total_visit_min: number
  total_distance_km: number
  total_entrance_fee: number
  num_pois: number
}

export type TravelItinerary = {
  status: string
  num_days: number
  days: TravelItineraryDay[]
  total_pois_visited: number
  total_pois_dropped: number
  total_entrance_fee: number
  total_travel_min: number
  total_distance_km: number
  budget_total?: number
  budget_used: number
  dropped_pois?: any[]
  solver?: string
  message?: string
}

// ─── Re-route Types ───────────────────────────────────────────────────────────

/** Payload sent to Gateway POST /v1/trip/re_route */
export type ReRoutePayload = {
  current_lat: number
  current_lon: number
  current_time_min: number
  remaining_poi_ids: string[]
  excluded_poi_ids?: string[]
  day_index: number
  original_itinerary: TravelItinerary
}

/** Response from Gateway re-route endpoint */
export type ReRouteResponse = {
  status: string
  day?: TravelItineraryDay
  message?: string
}

// ─── Main Tab Navigator ───────────────────────────────────────────────────────
export type MainTabParamList = {
  Explore: undefined
  MyTrip: { itinerary?: TravelItinerary }
  History: undefined
  Profile: undefined
}

// App Stack Navigator types
export type AppStackParamList = {
  Welcome: undefined
  Login: undefined
  Register: undefined
  Demo: NavigatorScreenParams<DemoTabParamList>
  // 🔥 Travel App screens
  Onboarding: undefined
  MainTabs: NavigatorScreenParams<MainTabParamList>
  // Modal / push screens (accessible from anywhere)
  Loading: {
    prompt: string
    hotelName?: string
    hotelLat?: number
    hotelLon?: number
    numDays?: number
  }
  MapTimeline: {
    itinerary: TravelItinerary
  }
  POIDetail: {
    poiId: string
    poiName?: string
    photoUrl?: string
    rating?: number
    reviewCount?: number
    description?: string
    entranceFee?: number
    openTime?: string
    closeTime?: string
    lat?: number
    lon?: number
  }
  ItineraryForm: undefined
  TripSummary: { itinerary: TravelItinerary }
  Settings: undefined
  ShareTrip: { itinerary: TravelItinerary }
  // IGNITE_GENERATOR_ANCHOR_APP_STACK_PARAM_LIST
}

export type AppStackScreenProps<T extends keyof AppStackParamList> = NativeStackScreenProps<
  AppStackParamList,
  T
>

export type MainTabScreenProps<T extends keyof MainTabParamList> = CompositeScreenProps<
  BottomTabScreenProps<MainTabParamList, T>,
  AppStackScreenProps<keyof AppStackParamList>
>

export type DemoTabScreenProps<T extends keyof DemoTabParamList> = CompositeScreenProps<
  BottomTabScreenProps<DemoTabParamList, T>,
  AppStackScreenProps<keyof AppStackParamList>
>

export interface NavigationProps
  extends Partial<ComponentProps<typeof NavigationContainer<AppStackParamList>>> {}
