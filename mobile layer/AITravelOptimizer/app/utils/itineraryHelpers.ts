/**
 * Itinerary helper utilities for re-route feature.
 *
 * Pure functions — no side effects, fully testable.
 */
import type {
  TravelItinerary,
  TravelItineraryDay,
  TravelItineraryStop,
} from "@/navigators/navigationTypes"

/**
 * Get IDs of POIs that haven't been visited yet in a given day.
 *
 * @param itinerary Full travel itinerary
 * @param dayIndex Day to check
 * @param visitedPOIIds POIs already visited (marked by user)
 * @returns Array of remaining POI IDs
 */
export function getRemainingPOIIds(
  itinerary: TravelItinerary,
  dayIndex: number,
  visitedPOIIds: string[] = [],
): string[] {
  const day = itinerary.days.find((d) => d.day_index === dayIndex)
  if (!day) return []

  const visited = new Set(visitedPOIIds)
  return day.stops
    .filter((stop) => !visited.has(stop.poi_id))
    .map((stop) => stop.poi_id)
}

/**
 * Merge a re-routed day into the existing itinerary.
 * Replaces the target day's stops, travel, distance etc.
 *
 * @param itinerary Original itinerary
 * @param reRoutedDay New day from solver
 * @returns New itinerary with merged day
 */
export function mergeReRoutedDay(
  itinerary: TravelItinerary,
  reRoutedDay: TravelItineraryDay,
): TravelItinerary {
  const newDays = itinerary.days.map((day) => {
    if (day.day_index === reRoutedDay.day_index) {
      return {
        ...reRoutedDay,
        // Preserve hotel info from original if re-route doesn't provide it
        hotel_name: reRoutedDay.hotel_name || day.hotel_name,
        hotel_location: reRoutedDay.hotel_location || day.hotel_location,
        date: reRoutedDay.date || day.date,
      }
    }
    return day
  })

  // Recalculate totals
  const totalPois = newDays.reduce((sum, d) => sum + d.num_pois, 0)
  const totalTravel = newDays.reduce((sum, d) => sum + d.total_travel_min, 0)
  const totalDist = newDays.reduce((sum, d) => sum + d.total_distance_km, 0)
  const totalFee = newDays.reduce((sum, d) => sum + d.total_entrance_fee, 0)

  return {
    ...itinerary,
    days: newDays,
    total_pois_visited: totalPois,
    total_travel_min: totalTravel,
    total_distance_km: Math.round(totalDist * 100) / 100,
    total_entrance_fee: totalFee,
    budget_used: totalFee,
  }
}

/**
 * Convert minutes-from-midnight to HH:MM string.
 */
export function minutesToHHMM(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`
}

/**
 * Get current time as minutes from midnight.
 */
export function getCurrentTimeMin(): number {
  const now = new Date()
  return now.getHours() * 60 + now.getMinutes()
}
