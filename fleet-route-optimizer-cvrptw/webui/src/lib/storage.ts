import type { ItineraryDraft } from "@/types/trip"
import { db } from "@/lib/firebase"
import { collection, doc, getDocs, orderBy, query, setDoc } from "firebase/firestore"

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

export async function getSavedDraftsForUser(userId?: string | null): Promise<ItineraryDraft[]> {
  if (!userId || !db) return getSavedDrafts()
  const ref = collection(db, "users", userId, "drafts")
  const snapshot = await getDocs(query(ref, orderBy("updatedAt", "desc")))
  return snapshot.docs.map((item) => item.data().draft as ItineraryDraft).filter(Boolean)
}

export async function saveDraftForUser(draft: ItineraryDraft, userId?: string | null): Promise<ItineraryDraft[]> {
  if (!userId || !db) return saveDraft(draft)
  const now = new Date().toISOString()
  const nextDraft: ItineraryDraft = {
    ...draft,
    updatedAt: now,
    createdAt: draft.createdAt || now,
  }
  const safeDraft = JSON.parse(JSON.stringify(nextDraft)) as ItineraryDraft
  await setDoc(doc(db, "users", userId, "drafts", safeDraft.id), {
    draft: safeDraft,
    destination: safeDraft.destination,
    days: safeDraft.days.length,
    updatedAt: safeDraft.updatedAt,
    createdAt: safeDraft.createdAt,
  })
  return getSavedDraftsForUser(userId)
}
