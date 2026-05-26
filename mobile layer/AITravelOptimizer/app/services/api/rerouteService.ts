import { ReRoutePayload, TravelItinerary } from "@/navigators/navigationTypes"
import { getRemainingPOIIds, getCurrentTimeMin } from "@/utils/itineraryHelpers"

/** Helper to calculate Haversine distance in km */
function getDistanceFromLatLonInKm(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6371 // Radius of the earth in km
  const dLat = (lat2 - lat1) * (Math.PI / 180)
  const dLon = (lon2 - lon1) * (Math.PI / 180)
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180)) * Math.sin(dLon / 2) * Math.sin(dLon / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

export const RerouteService = {
  /**
   * Check if user is off-route based on distance and time.
   * Returns true if user is > 2km away OR > 30 mins late.
   */
  checkOffRouteTolerance(
    currentLat: number,
    currentLon: number,
    nextPoiLat: number,
    nextPoiLon: number,
    currentTimeMin: number,
    expectedTimeMin: number
  ): boolean {
    const distanceKm = getDistanceFromLatLonInKm(currentLat, currentLon, nextPoiLat, nextPoiLon)
    const timeDiffMin = currentTimeMin - expectedTimeMin

    return distanceKm > 2.0 || timeDiffMin > 30
  },

  /**
   * Mock NLP extraction of user state from chat.
   * In a real app, this would call a Layer 2 LLM endpoint.
   */
  async extractUserState(chatText: string): Promise<ReRoutePayload['user_state']> {
    // Simulate network delay
    await new Promise((res) => setTimeout(res, 1000))
    
    const text = chatText.toLowerCase()
    const state: ReRoutePayload['user_state'] = { text: chatText }

    if (text.includes("mưa")) {
      state.weather = "rain"
      state.wants_indoor = true
    }
    if (text.includes("mệt")) {
      state.tired = true
      state.wants_shorter_plan = true
    }
    if (text.includes("đói") || text.includes("ăn")) {
      state.hungry = true
    }
    
    return state
  },

  /**
   * Helper to build the reroute payload.
   */
  buildReroutePayload(
    currentLat: number,
    currentLon: number,
    itinerary: TravelItinerary,
    currentDayIndex: number,
    visitedPOIIds: string[],
    userState?: ReRoutePayload['user_state']
  ): ReRoutePayload {
    const remainingIds = getRemainingPOIIds(itinerary, currentDayIndex, visitedPOIIds)
    
    const remainingBudget = itinerary.budget_total ? itinerary.budget_total - itinerary.budget_used : 300000;
    
    return {
      current_location: {
        lat: currentLat,
        lon: currentLon
      },
      current_time_min: getCurrentTimeMin(),
      remaining_poi_ids: remainingIds,
      locked_remaining_poi_ids: [], // To be implemented when UI allows locking
      constraints: {
        budget_remaining: remainingBudget,
        end_time_min: 1080 // 18:00
      },
      day_index: currentDayIndex,
      original_itinerary: itinerary,
      user_state: userState
    }
  }
}
