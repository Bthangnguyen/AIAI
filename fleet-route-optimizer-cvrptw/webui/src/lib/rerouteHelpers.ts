import type { ReRouteResult } from "@/lib/api"
import type { ItineraryItem } from "@/types/trip"

export function reRouteStopsToItems(dayIndex: number, day: NonNullable<ReRouteResult["day"]>): ItineraryItem[] {
  return day.stops
    .filter((stop) => !stop.poi_id.startsWith("hotel_day_"))
    .map((stop, index) => {
      const h = Math.floor(stop.arrival_time_min / 60)
      const m = stop.arrival_time_min % 60
      return {
        id: `${dayIndex}-${stop.poi_id}-${stop.arrival_time_min}-${index}`,
        poiId: stop.poi_id,
        time: `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`,
        note: stop.poi_name ?? "",
      }
    })
}
