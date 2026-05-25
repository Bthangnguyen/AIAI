import type { ItineraryDay, ItineraryDraft } from "@/types/trip"

export type MoveDirection = "up" | "down"

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
  const days = [...draft.days]
  days[dayIndex] = reorderedDay

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
