"use client"

import dynamic from "next/dynamic"
import { useCallback, useEffect, useMemo, useState } from "react"
import { Loader2, MapPinned, Pencil, Search } from "lucide-react"
import { AdminPoiEditPanel } from "@/components/AdminPoiEditPanel"
import { Toast } from "@/components/Toast"
import { fetchAdminPois, parseTagsInput, updateAdminPoi } from "@/lib/adminPois"
import { formatLatLng, formatMinutesFromMidnight } from "@/lib/adminFormat"
import type { AdminPoiRow } from "@/types/admin"

const AdminPoiMap = dynamic(() => import("@/components/AdminPoiMap").then((mod) => mod.AdminPoiMap), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[420px] items-center justify-center rounded-2xl border border-orange-200 bg-white text-sm text-orange-950/60">
      Đang tải bản đồ...
    </div>
  ),
})

const PAGE_SIZE = 2000

export function AdminPoisWorkspace() {
  const [query, setQuery] = useState("")
  const [debouncedQuery, setDebouncedQuery] = useState("")
  const [items, setItems] = useState<AdminPoiRow[]>([])
  const [total, setTotal] = useState(0)
  const [selectedUuid, setSelectedUuid] = useState<string | null>(null)
  const [editingPoi, setEditingPoi] = useState<AdminPoiRow | null>(null)
  const [editCategory, setEditCategory] = useState("")
  const [editTagsText, setEditTagsText] = useState("")
  const [saving, setSaving] = useState(false)
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [toastVariant, setToastVariant] = useState<"success" | "error">("success")
  const [fitSignal, setFitSignal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 300)
    return () => window.clearTimeout(timer)
  }, [query])

  const loadPois = useCallback(async (search: string, signal?: AbortSignal) => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchAdminPois({ limit: PAGE_SIZE, offset: 0, q: search, signal })
      setItems(result.items)
      setTotal(result.total)
      setFitSignal((value) => value + 1)
      setSelectedUuid((current) => {
        if (current && result.items.some((poi) => poi.uuid === current)) return current
        return result.items[0]?.uuid ?? null
      })
      setEditingPoi((current) => {
        if (!current) return null
        return result.items.find((poi) => poi.uuid === current.uuid) ?? null
      })
    } catch (err) {
      if (signal?.aborted) return
      setError(err instanceof Error ? err.message : "Không tải được danh sách POI")
      setItems([])
      setTotal(0)
      setSelectedUuid(null)
      setEditingPoi(null)
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void loadPois(debouncedQuery, controller.signal)
    return () => controller.abort()
  }, [debouncedQuery, loadPois])

  const selectedPoi = useMemo(
    () => items.find((poi) => poi.uuid === selectedUuid) ?? null,
    [items, selectedUuid],
  )

  const openEditor = (poi: AdminPoiRow) => {
    setEditingPoi(poi)
    setEditCategory(poi.category)
    setEditTagsText(poi.tags.join(", "))
    setSelectedUuid(poi.uuid)
  }

  const closeEditor = () => {
    if (saving) return
    setEditingPoi(null)
  }

  const handleSave = async () => {
    if (!editingPoi) return
    setSaving(true)
    try {
      const updated = await updateAdminPoi(editingPoi.uuid, {
        category: editCategory,
        tags: parseTagsInput(editTagsText),
      })
      setItems((current) => current.map((poi) => (poi.uuid === updated.uuid ? updated : poi)))
      setEditingPoi(updated)
      setEditCategory(updated.category)
      setEditTagsText(updated.tags.join(", "))
      setToastVariant("success")
      setToastMessage(`Đã lưu ${updated.name}`)
    } catch (err) {
      setToastVariant("error")
      setToastMessage(err instanceof Error ? err.message : "Không lưu được POI")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="relative flex h-[calc(100vh-3rem)] min-h-[640px] flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.2em] text-orange-400">POI Admin</p>
          <h2 className="mt-1 text-2xl font-black">Danh sách POI</h2>
          <p className="mt-1 text-sm text-orange-950/60">
            {loading ? "Đang tải..." : `${total} POI trong cơ sở dữ liệu`}
          </p>
        </div>
        <label className="relative min-w-[240px] flex-1 sm:max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-orange-400" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tìm theo tên POI..."
            className="w-full rounded-xl border border-orange-200 bg-white py-2.5 pl-10 pr-3 text-sm font-medium text-orange-950 outline-none ring-orange-300 transition focus:ring-2"
          />
        </label>
      </header>

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <section className="relative flex min-h-0 flex-col overflow-hidden rounded-2xl border border-orange-200 bg-white shadow-sm">
          <div className="border-b border-orange-100 px-4 py-3 text-xs font-bold uppercase tracking-wide text-orange-950/50">
            Bảng POI
          </div>
          <div className="min-h-0 flex-1 overflow-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="sticky top-0 bg-orange-50 text-xs uppercase tracking-wide text-orange-950/55">
                <tr>
                  <th className="px-4 py-3 font-bold">Tên</th>
                  <th className="px-4 py-3 font-bold">Category</th>
                  <th className="px-4 py-3 font-bold">Tags</th>
                  <th className="px-4 py-3 font-bold">Lat/Lng</th>
                  <th className="px-4 py-3 font-bold">Duration</th>
                  <th className="px-4 py-3 font-bold">Open/Close</th>
                  <th className="px-4 py-3 font-bold">Embed</th>
                  <th className="px-4 py-3 font-bold">Edit</th>
                </tr>
              </thead>
              <tbody>
                {loading && !items.length ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-10 text-center text-orange-950/55">
                      <span className="inline-flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Đang tải danh sách POI...
                      </span>
                    </td>
                  </tr>
                ) : null}
                {!loading && !items.length ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-10 text-center text-orange-950/55">
                      Không có POI phù hợp.
                    </td>
                  </tr>
                ) : null}
                {items.map((poi) => {
                  const selected = poi.uuid === selectedUuid
                  return (
                    <tr
                      key={poi.uuid}
                      data-testid="admin-poi-row"
                      onClick={() => setSelectedUuid(poi.uuid)}
                      className={`cursor-pointer border-t border-orange-100 transition hover:bg-orange-50/70 ${
                        selected ? "bg-yellow-50" : ""
                      }`}
                    >
                      <td className="px-4 py-3 font-semibold text-orange-950">{poi.name}</td>
                      <td className="px-4 py-3 text-orange-950/70">{poi.category}</td>
                      <td className="px-4 py-3 text-orange-950/60">{poi.tags.join(", ") || "—"}</td>
                      <td className="px-4 py-3 font-mono text-xs text-orange-950/65">
                        {formatLatLng(poi.latitude, poi.longitude)}
                      </td>
                      <td className="px-4 py-3 text-orange-950/70">{poi.visitDurationMin} phút</td>
                      <td className="px-4 py-3 text-orange-950/70">
                        {formatMinutesFromMidnight(poi.openTime)} – {formatMinutesFromMidnight(poi.closeTime)}
                      </td>
                      <td className="px-4 py-3 text-center text-base">{poi.hasEmbedding ? "✓" : "✗"}</td>
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          aria-label={`Edit ${poi.name}`}
                          data-testid="admin-poi-edit-button"
                          onClick={(event) => {
                            event.stopPropagation()
                            openEditor(poi)
                          }}
                          className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-orange-200 text-orange-700 transition hover:bg-orange-50"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {editingPoi ? (
            <AdminPoiEditPanel
              poi={editingPoi}
              category={editCategory}
              tagsText={editTagsText}
              saving={saving}
              onCategoryChange={setEditCategory}
              onTagsTextChange={setEditTagsText}
              onSave={() => void handleSave()}
              onClose={closeEditor}
            />
          ) : null}
        </section>

        <section className="flex min-h-[420px] min-w-0 flex-col overflow-hidden rounded-2xl border border-orange-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-orange-100 px-4 py-3">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-orange-950/50">
              <MapPinned className="h-4 w-4" />
              Bản đồ POI
            </div>
            {selectedPoi ? (
              <p className="truncate text-sm font-semibold text-orange-950">{selectedPoi.name}</p>
            ) : null}
          </div>
          <div className="min-h-0 flex-1 p-3">
            <AdminPoiMap pois={items} selectedUuid={selectedUuid} fitSignal={fitSignal} />
          </div>
        </section>
      </div>

      <Toast message={toastMessage} variant={toastVariant} onClose={() => setToastMessage(null)} />
    </div>
  )
}
