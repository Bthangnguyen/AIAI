import type { ItineraryDay, ItineraryDraft } from "@/types/trip"
import { getPoi } from "@/lib/mockItineraryFallback"
import { POI_CACHE } from "@/lib/api"

export type MoveDirection = "up" | "down"

function minutesToTime(minutes: number): string {
  const h = Math.floor(minutes / 60) % 24
  const m = minutes % 60
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`
}

export function recalculateDayTimes(day: ItineraryDay): ItineraryDay {
  let currentMin = 480 // 08:00 default
  if (day.items.length > 0) {
    const firstTime = day.items[0].time
    const match = firstTime?.match(/^(\d{1,2}):(\d{2})/)
    if (match) {
      currentMin = parseInt(match[1]) * 60 + parseInt(match[2])
    }
  }

  const items = day.items.map((item, index) => {
    // Robust fallback: getPoi (POI_CACHE → HUE_POIS) → direct POI_CACHE
    const poi = getPoi(item.poiId) ?? POI_CACHE.get(item.poiId)
    const duration = poi?.estimatedDurationMinutes ?? 60
    const arrivalTime = minutesToTime(currentMin)
    
    // Thời gian di chuyển ước tính mặc định giữa các điểm
    const travelTime = 15
    const nextMin = currentMin + duration

    const note = [
      poi?.name ?? item.note?.split(" · ")[0] ?? "",
      `${duration} phút`,
      index < day.items.length - 1 ? `di chuyển tiếp ${travelTime} phút` : null,
    ].filter(Boolean).join(" · ")

    const updatedItem = {
      ...item,
      time: arrivalTime,
      note,
    }

    currentMin = nextMin + travelTime
    return updatedItem
  })

  return { ...day, items }
}

export function canMoveDayItem(day: ItineraryDay, itemId: string, direction: MoveDirection): boolean {
  const index = day.items.findIndex((item) => item.id === itemId)
  if (index < 0) return false
  if (direction === "up") return index > 0
  return index < day.items.length - 1
}

export function moveDayItem(day: ItineraryDay, itemId: string, direction: MoveDirection): ItineraryDay {
  const index = day.items.findIndex((item) => item.id === itemId)
  if (index < 0) return day
  if (!canMoveDayItem(day, itemId, direction)) return day

  const targetIndex = direction === "up" ? index - 1 : index + 1
  const items = [...day.items]
  const [moved] = items.splice(index, 1)
  items.splice(targetIndex, 0, moved)

  return { ...day, items }
}

export function markDayManual(draft: ItineraryDraft, dayNumber: number): ItineraryDraft {
  const manualDayNumbers = draft.manualDayNumbers ?? []
  if (manualDayNumbers.includes(dayNumber)) return draft
  return { ...draft, manualDayNumbers: [...manualDayNumbers, dayNumber] }
}

export function clearDayManual(draft: ItineraryDraft, dayNumber: number): ItineraryDraft {
  if (!draft.manualDayNumbers?.includes(dayNumber)) return draft
  return {
    ...draft,
    manualDayNumbers: draft.manualDayNumbers.filter((n) => n !== dayNumber),
  }
}

export function applyManualReorderToDraft(
  draft: ItineraryDraft,
  dayNumber: number,
  itemId: string,
  direction: MoveDirection,
): ItineraryDraft {
  const dayIndex = draft.days.findIndex((day) => day.dayNumber === dayNumber)
  if (dayIndex < 0) return draft

  const reorderedDay = moveDayItem(draft.days[dayIndex], itemId, direction)
  const timedDay = recalculateDayTimes(reorderedDay)
  const days = [...draft.days]
  days[dayIndex] = timedDay

  return markDayManual(
    {
      ...draft,
      days,
      updatedAt: new Date().toISOString(),
    },
    dayNumber,
  )
}

export function poiIdsInDayOrder(day: ItineraryDay): string[] {
  return day.items.map((item) => item.poiId)
}
