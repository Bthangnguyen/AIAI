import { HUE_POIS } from "@/data/huePois"
import { POI_CACHE } from "@/lib/api"
import type { ItineraryDraft, POI } from "@/types/trip"

export function getPoi(id: string): POI | undefined {
  return POI_CACHE.get(id) ?? HUE_POIS.find((poi) => poi.id === id)
}

export function searchPois(query: string): POI[] {
  const normalized = query.trim().toLowerCase()
  if (!normalized) return HUE_POIS.slice(0, 8)
  return HUE_POIS.filter((poi) => {
    const haystack = [poi.name, poi.category, poi.description, ...poi.tags].join(" ").toLowerCase()
    return haystack.includes(normalized)
  }).slice(0, 12)
}

export function draftTotals(draft: ItineraryDraft | null): { poiCount: number; estimatedCost: number } {
  if (!draft) return { poiCount: 0, estimatedCost: 0 }
  const poiCount = draft.days.reduce((sum, day) => sum + day.items.filter(item => !item.poiId.startsWith("__")).length, 0)
  const estimatedCost = draft.days.reduce((sum, day) => {
    return (
      sum +
      day.items.reduce((daySum, item) => {
        const poi = getPoi(item.poiId)
        return daySum + (poi?.estimatedCost ?? 0)
      }, 0)
    )
  }, 0)
  return { poiCount, estimatedCost }
}
