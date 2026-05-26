import type { ItineraryDraft } from "@/types/trip"

const STORAGE_KEY = "tripflow-saved-drafts"

export function getSavedDrafts(): ItineraryDraft[] {
  if (typeof window === "undefined") return []
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as ItineraryDraft[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveDraft(draft: ItineraryDraft): ItineraryDraft[] {
  const existing = getSavedDrafts()
  const now = new Date().toISOString()
  const nextDraft: ItineraryDraft = {
    ...draft,
    updatedAt: now,
    createdAt: draft.createdAt || now,
  }
  const index = existing.findIndex((item) => item.id === nextDraft.id)
  const next =
    index >= 0
      ? existing.map((item, i) => (i === index ? nextDraft : item))
      : [nextDraft, ...existing]
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  }
  return next
}
