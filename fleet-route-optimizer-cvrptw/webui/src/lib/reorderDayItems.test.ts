import { describe, expect, it } from "vitest"
import { applyManualReorderToDraft, canMoveDayItem, moveDayItem } from "@/lib/reorderDayItems"
import type { ItineraryDay, ItineraryDraft } from "@/types/trip"

const sampleDay: ItineraryDay = {
  dayNumber: 1,
  title: "Ngày 1",
  items: [
    { id: "a", poiId: "p1", time: "08:00", note: "A" },
    { id: "b", poiId: "p2", time: "09:00", note: "B" },
    { id: "c", poiId: "p3", time: "10:00", note: "C" },
  ],
}

const sampleDraft: ItineraryDraft = {
  id: "d1",
  destination: "Huế",
  days: [sampleDay],
  tags: [],
  createdAt: "2026-01-01T00:00:00.000Z",
  updatedAt: "2026-01-01T00:00:00.000Z",
  status: "draft",
  intent: { interests: [], lockedPoiNames: [], rawPrompt: "test" },
}

describe("moveDayItem", () => {
  it("moves item down within day", () => {
    const next = moveDayItem(sampleDay, "a", "down")
    expect(next.items.map((i) => i.poiId)).toEqual(["p2", "p1", "p3"])
  })

  it("moves item up within day", () => {
    const next = moveDayItem(sampleDay, "b", "up")
    expect(next.items.map((i) => i.poiId)).toEqual(["p2", "p1", "p3"])
  })

  it("does not move first item up", () => {
    const next = moveDayItem(sampleDay, "a", "up")
    expect(next.items.map((i) => i.poiId)).toEqual(["p1", "p2", "p3"])
  })

  it("does not move last item down", () => {
    const next = moveDayItem(sampleDay, "c", "down")
    expect(next.items.map((i) => i.poiId)).toEqual(["p1", "p2", "p3"])
  })
})

describe("canMoveDayItem", () => {
  it("blocks up on first and down on last", () => {
    expect(canMoveDayItem(sampleDay, "a", "up")).toBe(false)
    expect(canMoveDayItem(sampleDay, "a", "down")).toBe(true)
    expect(canMoveDayItem(sampleDay, "c", "down")).toBe(false)
  })
})

describe("applyManualReorderToDraft", () => {
  it("updates day items and marks day manual", () => {
    const next = applyManualReorderToDraft(sampleDraft, 1, "a", "down")
    expect(next.days[0].items.map((i) => i.poiId)).toEqual(["p2", "p1", "p3"])
    expect(next.manualDayNumbers).toEqual([1])
    expect(next.updatedAt).not.toBe(sampleDraft.updatedAt)
  })

  it("accumulates manual day numbers without duplicates", () => {
    let next = applyManualReorderToDraft(sampleDraft, 1, "a", "down")
    next = applyManualReorderToDraft(next, 1, "b", "down")
    expect(next.manualDayNumbers).toEqual([1])
  })
})
