"use client"

import { CircleOff, Plus, Search, Star, X } from "lucide-react"
import { useEffect, useState } from "react"
import { formatCurrency, searchPois } from "@/lib/planner"
import { searchPoisBackend } from "@/lib/api"
import type { ItineraryDraft, POI } from "@/types/trip"

interface AddPlaceModalProps {
  draft: ItineraryDraft
  defaultDay: number
  isOpen: boolean
  onClose: () => void
  onAdd: (dayNumber: number, poi: POI) => void
}

export function AddPlaceModal({ draft, defaultDay, isOpen, onClose, onAdd }: AddPlaceModalProps) {
  const [query, setQuery] = useState("")
  const [targetDay, setTargetDay] = useState(defaultDay)
  const [results, setResults] = useState<POI[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setTargetDay(defaultDay)
      setQuery("")
      setResults(searchPois(""))
    }
  }, [defaultDay, isOpen])

  useEffect(() => {
    let active = true
    if (!query.trim()) {
      setResults(searchPois(""))
      setLoading(false)
      return
    }

    setLoading(true)
    const timer = setTimeout(async () => {
      try {
        const backendResults = await searchPoisBackend(query)
        if (!active) return
        if (backendResults && backendResults.length > 0) {
          setResults(backendResults)
        } else {
          // Fallback offline
          setResults(searchPois(query))
        }
      } catch (e) {
        console.error("Vector search failed, falling back to offline", e)
        if (active) {
          setResults(searchPois(query))
        }
      } finally {
        if (active) setLoading(false)
      }
    }, 300) // Debounce 300ms

    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [query])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[1000] flex items-end bg-black/70 p-3 backdrop-blur-sm sm:items-center sm:justify-center sm:p-6">
      <section className="max-h-[90vh] w-full max-w-5xl overflow-hidden rounded-[32px] border border-orange-200 bg-white shadow-2xl shadow-orange-950/20">
        <div className="flex items-start justify-between gap-4 border-b border-orange-200 bg-white p-6">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.22em] text-travel">Thêm địa điểm</p>
            <h2 className="mt-2 text-2xl font-black text-orange-950 sm:text-3xl">Bạn muốn thêm địa điểm nào?</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-orange-950/60">Tìm trong dữ liệu mock Huế theo tên, category, tag hoặc khu vực. Sau khi thêm, TripFlow sẽ cập nhật timeline và bản đồ.</p>
          </div>
          <button type="button" onClick={onClose} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-orange-100 text-orange-950/60 transition hover:bg-border-strong hover:text-orange-950" aria-label="Đóng">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="grid gap-4 p-5 sm:grid-cols-[1fr_12rem]">
          <label className="relative">
            <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-orange-400" />
            <input value={query} onChange={(event) => setQuery(event.target.value)} className="min-h-14 w-full rounded-2xl border border-orange-200 bg-white pl-12 pr-4 text-sm font-semibold text-orange-950 outline-none transition focus:border-orange-300" placeholder="Thêm một quán cafe muối gần trung tâm..." autoFocus />
          </label>
          <select value={targetDay} onChange={(event) => setTargetDay(Number(event.target.value))} className="min-h-14 rounded-2xl border border-orange-200 bg-white px-4 text-sm font-black text-orange-950 outline-none transition focus:border-orange-300">
            {draft.days.map((day) => <option key={day.dayNumber} value={day.dayNumber}>Ngày {day.dayNumber}</option>)}
          </select>
        </div>

        <div className="custom-scrollbar max-h-[52vh] overflow-y-auto px-5 pb-6">
          {loading ? (
            <div className="flex min-h-[160px] flex-col items-center justify-center gap-3 py-8 text-center">
              <span className="h-8 w-8 animate-spin rounded-full border-4 border-orange-200 border-t-orange-600" />
              <p className="text-sm font-black text-orange-950/60">Đang tìm kiếm thông minh qua Vector Search...</p>
            </div>
          ) : results.length === 0 ? (
            <div className="rounded-[28px] border border-dashed border-orange-300 bg-white p-8 text-center">
              <CircleOff className="mx-auto h-10 w-10 text-travel" />
              <h3 className="mt-3 text-xl font-black text-orange-950">Không tìm thấy địa điểm phù hợp trong dữ liệu mock.</h3>
              <p className="mt-2 text-sm leading-6 text-orange-950/60">Thử tìm bằng “cafe”, “chay”, “lăng”, “sông” hoặc “trung tâm”.</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {results.map((poi) => (
                <article key={poi.id} className="rounded-[24px] border border-orange-200 bg-white p-4 transition hover:border-orange-300">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-lg font-black text-orange-950">{poi.name}</h3>
                        <span className="rounded-full bg-orange-100 px-2 py-1 text-[10px] font-black text-orange-950/60">{poi.area}</span>
                      </div>
                      <p className="mt-1 text-sm leading-6 text-orange-950/60">{poi.description}</p>
                    </div>
                    <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-warning/15 px-2.5 py-1 text-xs font-black text-warning"><Star className="h-3 w-3 fill-warning" />{poi.rating}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-bold text-orange-950/60">
                    <span className="rounded-full bg-travel/15 px-3 py-1 text-travel">{poi.category}</span>
                    <span className="rounded-full bg-orange-100 px-3 py-1">{formatCurrency(poi.estimatedCost)}</span>
                    <span className="rounded-full bg-orange-100 px-3 py-1">{poi.estimatedDurationMinutes} phút</span>
                    {poi.tags.slice(0, 3).map((tag) => <span key={tag} className="rounded-full bg-orange-100 px-3 py-1">{tag}</span>)}
                  </div>
                  <button type="button" onClick={() => onAdd(targetDay, poi)} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-white px-4 py-3 text-sm font-black text-orange-950 transition hover:bg-orange-600">
                    <Plus className="h-4 w-4" /> Add to day {targetDay}
                  </button>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  )
}

