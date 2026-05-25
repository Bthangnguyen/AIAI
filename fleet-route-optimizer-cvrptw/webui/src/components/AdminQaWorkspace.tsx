"use client"

import dynamic from "next/dynamic"
import { useCallback, useEffect, useMemo, useState } from "react"
import { AlertTriangle, Loader2, MapPinned } from "lucide-react"
import {
  QA_ISSUE_LABELS,
  duplicateGroupClass,
  fetchPoiQaList,
  fetchPoiQaSummary,
  qaCardTone,
} from "@/lib/adminQa"
import { formatLatLng, formatMinutesFromMidnight } from "@/lib/adminFormat"
import type { AdminPoiQaRow } from "@/lib/adminQa"
import type { PoiQaIssueType, PoiQaSummary } from "@/types/admin"

const AdminPoiMap = dynamic(() => import("@/components/AdminPoiMap").then((mod) => mod.AdminPoiMap), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[420px] items-center justify-center rounded-2xl border border-orange-200 bg-white text-sm text-orange-950/60">
      Đang tải bản đồ...
    </div>
  ),
})

const ISSUE_ORDER: PoiQaIssueType[] = [
  "wrong_coords",
  "duplicates",
  "missing_hours",
  "missing_duration",
  "missing_embedding",
]

const CARD_TONE_CLASS = {
  ok: "border-emerald-200 bg-emerald-50 text-emerald-900",
  warn: "border-amber-200 bg-amber-50 text-amber-950",
  danger: "border-red-200 bg-red-50 text-red-950",
} as const

export function AdminQaWorkspace() {
  const [summary, setSummary] = useState<PoiQaSummary | null>(null)
  const [selectedIssue, setSelectedIssue] = useState<PoiQaIssueType | null>(null)
  const [items, setItems] = useState<AdminPoiQaRow[]>([])
  const [selectedUuid, setSelectedUuid] = useState<string | null>(null)
  const [fitSignal, setFitSignal] = useState(0)
  const [loadingSummary, setLoadingSummary] = useState(true)
  const [loadingList, setLoadingList] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    setLoadingSummary(true)
    void fetchPoiQaSummary(controller.signal)
      .then(setSummary)
      .catch((err) => {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : "Không tải được QA summary")
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingSummary(false)
      })
    return () => controller.abort()
  }, [])

  const loadIssueList = useCallback(async (issue: PoiQaIssueType, signal?: AbortSignal) => {
    setLoadingList(true)
    setError(null)
    try {
      const result = await fetchPoiQaList({ issue, limit: 100, offset: 0, signal })
      setItems(result.items)
      setFitSignal((value) => value + 1)
      setSelectedUuid(result.items[0]?.uuid ?? null)
    } catch (err) {
      if (signal?.aborted) return
      setError(err instanceof Error ? err.message : "Không tải được danh sách POI lỗi")
      setItems([])
      setSelectedUuid(null)
    } finally {
      if (!signal?.aborted) setLoadingList(false)
    }
  }, [])

  useEffect(() => {
    if (!selectedIssue) {
      setItems([])
      setSelectedUuid(null)
      return
    }
    const controller = new AbortController()
    void loadIssueList(selectedIssue, controller.signal)
    return () => controller.abort()
  }, [selectedIssue, loadIssueList])

  const selectedPoi = useMemo(
    () => items.find((poi) => poi.uuid === selectedUuid) ?? null,
    [items, selectedUuid],
  )

  const mapPois = useMemo(
    () =>
      items.map((poi) => ({
        uuid: poi.uuid,
        name: poi.name,
        category: poi.category,
        tags: poi.tags,
        latitude: poi.latitude,
        longitude: poi.longitude,
        visitDurationMin: poi.visitDurationMin,
        openTime: poi.openTime,
        closeTime: poi.closeTime,
        hasEmbedding: poi.hasEmbedding,
      })),
    [items],
  )

  return (
    <div className="flex h-[calc(100vh-3rem)] min-h-[640px] flex-col gap-4">
      <header>
        <p className="text-xs font-black uppercase tracking-[0.2em] text-orange-400">Data QA</p>
        <h2 className="mt-1 text-2xl font-black">Kiểm tra chất lượng POI</h2>
        <p className="mt-1 text-sm text-orange-950/60">
          {loadingSummary ? "Đang tải summary..." : "Chọn một loại issue để lọc bảng và bản đồ"}
        </p>
      </header>

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
      ) : null}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {ISSUE_ORDER.map((issue) => {
          const count = summary?.[issue] ?? 0
          const tone = qaCardTone(count)
          const active = selectedIssue === issue
          return (
            <button
              key={issue}
              type="button"
              data-testid={`qa-card-${issue}`}
              onClick={() => setSelectedIssue(issue)}
              className={`rounded-2xl border px-4 py-4 text-left shadow-sm transition hover:scale-[1.01] ${CARD_TONE_CLASS[tone]} ${
                active ? "ring-2 ring-orange-400" : ""
              }`}
            >
              <p className="text-xs font-bold uppercase tracking-wide opacity-70">{QA_ISSUE_LABELS[issue]}</p>
              <p className="mt-2 text-3xl font-black">{loadingSummary ? "…" : count}</p>
            </button>
          )
        })}
      </section>

      {!selectedIssue ? (
        <div className="flex flex-1 items-center justify-center rounded-2xl border border-dashed border-orange-200 bg-white/70 p-8 text-center text-sm text-orange-950/60">
          <div>
            <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-orange-400" />
            Chọn một card issue ở trên để xem POI bị ảnh hưởng.
          </div>
        </div>
      ) : (
        <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <section className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-orange-200 bg-white shadow-sm">
            <div className="border-b border-orange-100 px-4 py-3 text-xs font-bold uppercase tracking-wide text-orange-950/50">
              POI lỗi — {QA_ISSUE_LABELS[selectedIssue]}
            </div>
            <div className="min-h-0 flex-1 overflow-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="sticky top-0 bg-orange-50 text-xs uppercase tracking-wide text-orange-950/55">
                  <tr>
                    <th className="px-4 py-3 font-bold">Tên</th>
                    <th className="px-4 py-3 font-bold">Category</th>
                    <th className="px-4 py-3 font-bold">Lat/Lng</th>
                    <th className="px-4 py-3 font-bold">Duration</th>
                    <th className="px-4 py-3 font-bold">Open/Close</th>
                    <th className="px-4 py-3 font-bold">Embed</th>
                  </tr>
                </thead>
                <tbody>
                  {loadingList ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-10 text-center text-orange-950/55">
                        <span className="inline-flex items-center gap-2">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Đang tải POI lỗi...
                        </span>
                      </td>
                    </tr>
                  ) : null}
                  {!loadingList && !items.length ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-10 text-center text-orange-950/55">
                        Không có POI nào cho issue này.
                      </td>
                    </tr>
                  ) : null}
                  {items.map((poi) => {
                    const selected = poi.uuid === selectedUuid
                    const groupClass = duplicateGroupClass(poi.duplicateGroup)
                    return (
                      <tr
                        key={poi.uuid}
                        data-testid="admin-qa-row"
                        onClick={() => setSelectedUuid(poi.uuid)}
                        className={`cursor-pointer border-t border-orange-100 transition hover:bg-orange-50/70 ${
                          selected ? "bg-yellow-50" : groupClass
                        }`}
                      >
                        <td className="px-4 py-3 font-semibold text-orange-950">{poi.name}</td>
                        <td className="px-4 py-3 text-orange-950/70">{poi.category}</td>
                        <td className="px-4 py-3 font-mono text-xs text-orange-950/65">
                          {formatLatLng(poi.latitude, poi.longitude)}
                        </td>
                        <td className="px-4 py-3 text-orange-950/70">{poi.visitDurationMin} phút</td>
                        <td className="px-4 py-3 text-orange-950/70">
                          {formatMinutesFromMidnight(poi.openTime)} – {formatMinutesFromMidnight(poi.closeTime)}
                        </td>
                        <td className="px-4 py-3 text-center text-base">{poi.hasEmbedding ? "✓" : "✗"}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <section className="flex min-h-[420px] min-w-0 flex-col overflow-hidden rounded-2xl border border-orange-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-orange-100 px-4 py-3">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-orange-950/50">
                <MapPinned className="h-4 w-4" />
                Bản đồ POI lỗi
              </div>
              {selectedPoi ? (
                <p className="truncate text-sm font-semibold text-orange-950">{selectedPoi.name}</p>
              ) : null}
            </div>
            <div className="min-h-0 flex-1 p-3">
              <AdminPoiMap pois={mapPois} selectedUuid={selectedUuid} fitSignal={fitSignal} />
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
