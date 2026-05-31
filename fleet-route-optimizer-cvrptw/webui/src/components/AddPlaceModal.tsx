"use client"

import { CircleOff, Plus, Search, X } from "lucide-react"
import { useEffect, useState, useMemo } from "react"
import { formatCurrency } from "@/lib/planner"
import { searchPoisBackend, POI_CACHE } from "@/lib/api"
import { HUE_POIS } from "@/data/huePois"
import type { ItineraryDraft, POI } from "@/types/trip"

interface AddPlaceModalProps {
  draft: ItineraryDraft
  defaultDay: number
  isOpen: boolean
  onClose: () => void
  onAdd: (dayNumber: number, poi: POI) => void
}

const POI_TABS = [
  { id: "all", name: "Tất cả" },
  { id: "culture", name: "Văn hóa & Lịch sử" },
  { id: "food", name: "Ẩm thực" },
  { id: "cafe", name: "Cà phê & Trà" },
  { id: "nature", name: "Thiên nhiên & Cảnh quan" },
  { id: "hotel", name: "Lưu trú" },
]

function matchesTab(poi: POI, tabId: string): boolean {
  if (tabId === "all") return true
  const category = (poi.category || "").toLowerCase()
  const tags = (poi.tags || []).map((t) => t.toLowerCase())
  const name = poi.name.toLowerCase()
  const desc = poi.description.toLowerCase()

  if (tabId === "culture") {
    return (
      category.includes("di tích") ||
      category.includes("tâm linh") ||
      category.includes("văn hóa") ||
      category.includes("cultural") ||
      category.includes("temple") ||
      category.includes("monument") ||
      tags.some((t) => t.includes("chùa") || t.includes("lịch sử") || t.includes("văn hóa") || t.includes("kiến trúc") || t.includes("lăng") || t.includes("cổ kính"))
    )
  }
  if (tabId === "food") {
    return (
      category.includes("ẩm thực") ||
      category.includes("ăn chay") ||
      category.includes("món ăn") ||
      category.includes("food") ||
      category.includes("restaurant") ||
      category.includes("quán") ||
      tags.some((t) => t.includes("ăn") || t.includes("đặc sản") || t.includes("bún bò") || t.includes("chợ") || t.includes("bánh"))
    )
  }
  if (tabId === "cafe") {
    return (
      category.includes("cafe") ||
      category.includes("cà phê") ||
      category.includes("trà") ||
      category.includes("coffee") ||
      category.includes("tea") ||
      tags.some((t) => t.includes("cafe") || t.includes("cà phê") || t.includes("muối") || t.includes("trà") || t.includes("uống"))
    )
  }
  if (tabId === "nature") {
    return (
      category.includes("cảnh quan") ||
      category.includes("biển") ||
      category.includes("sông") ||
      category.includes("núi") ||
      category.includes("nature") ||
      category.includes("scenic") ||
      category.includes("cảnh") ||
      tags.some((t) => t.includes("sông") || t.includes("hoàng hôn") || t.includes("thư giãn") || t.includes("biển") || t.includes("cảnh") || t.includes("đồi"))
    )
  }
  if (tabId === "hotel") {
    return (
      category.includes("hotel") ||
      category.includes("lưu trú") ||
      category.includes("khách sạn") ||
      category.includes("homestay") ||
      tags.some((t) => t.includes("khách sạn") || t.includes("hotel") || t.includes("lưu trú") || t.includes("homestay") || t.includes("resort"))
    )
  }
  return false
}

function getAllKnownPois(): POI[] {
  const allList: POI[] = []
  
  // Offline POIs
  HUE_POIS.forEach((poi) => {
    if (!allList.some((x) => x.id === poi.id)) {
      allList.push(poi)
    }
  })

  // POI Cache
  POI_CACHE.forEach((poi, id) => {
    if (!allList.some((x) => x.id === id)) {
      allList.push(poi)
    }
  })

  return allList
}

export function AddPlaceModal({ draft, defaultDay, isOpen, onClose, onAdd }: AddPlaceModalProps) {
  const [query, setQuery] = useState("")
  const [targetDay, setTargetDay] = useState(defaultDay)
  const [searchResults, setSearchResults] = useState<POI[]>([])
  const [selectedTab, setSelectedTab] = useState("all")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setTargetDay(defaultDay)
      setQuery("")
      setSelectedTab("all")
      setSearchResults([])
    }
  }, [defaultDay, isOpen])

  useEffect(() => {
    let active = true
    if (!query.trim()) {
      setSearchResults([])
      setLoading(false)
      return
    }

    setLoading(true)
    const timer = setTimeout(async () => {
      try {
        const backendResults = await searchPoisBackend(query)
        if (!active) return
        setSearchResults(backendResults)
      } catch (e) {
        console.error("Vector search failed", e)
      } finally {
        if (active) setLoading(false)
      }
    }, 300)

    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [query])

  // Lọc POI theo Tab đã chọn
  const filteredPois = useMemo(() => {
    const sourceList = query.trim() ? searchResults : getAllKnownPois()
    return sourceList.filter((poi) => matchesTab(poi, selectedTab))
  }, [searchResults, query, selectedTab])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[1000] flex items-end bg-black/70 p-3 backdrop-blur-sm sm:items-center sm:justify-center sm:p-6">
      <section className="max-h-[90vh] w-full max-w-5xl overflow-hidden rounded-[32px] border border-orange-200 bg-white shadow-2xl shadow-orange-950/20 flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-orange-200 bg-white p-6 shrink-0">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.22em] text-travel">Thêm địa điểm</p>
            <h2 className="mt-2 text-2xl font-black text-orange-950 sm:text-3xl">Khám phá & Thêm vào Lịch trình</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-orange-950/60">
              Tìm kiếm địa điểm Huế bằng AI Vector Search, hoặc duyệt danh sách địa điểm có sẵn được phân loại cụ thể theo danh mục bên dưới.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-orange-100 text-orange-950/60 transition hover:bg-orange-200 hover:text-orange-950"
            aria-label="Đóng"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Search controls */}
        <div className="grid gap-4 p-5 sm:grid-cols-[1fr_12rem] shrink-0 border-b border-orange-100">
          <label className="relative">
            <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-orange-400" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="min-h-14 w-full rounded-2xl border border-orange-200 bg-white pl-12 pr-4 text-sm font-semibold text-orange-950 outline-none transition focus:border-orange-400"
              placeholder="Nhập địa điểm muốn tìm, ví dụ: 'quán cafe muối có không gian đẹp'..."
              autoFocus
            />
          </label>
          <select
            value={targetDay}
            onChange={(event) => setTargetDay(Number(event.target.value))}
            className="min-h-14 rounded-2xl border border-orange-200 bg-white px-4 text-sm font-black text-orange-950 outline-none transition focus:border-orange-400 cursor-pointer"
          >
            {draft.days.map((day) => (
              <option key={day.dayNumber} value={day.dayNumber}>
                Thêm vào Ngày {day.dayNumber}
              </option>
            ))}
          </select>
        </div>

        {/* Tab selection */}
        <div className="flex flex-wrap gap-2 px-6 py-3 border-b border-orange-50 bg-orange-50/30 overflow-x-auto shrink-0 scrollbar-none">
          {POI_TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setSelectedTab(tab.id)}
              className={`px-4 py-2 rounded-full text-xs font-bold transition whitespace-nowrap ${
                selectedTab === tab.id
                  ? "bg-travel text-white shadow-sm"
                  : "bg-white border border-orange-200 text-orange-950 hover:bg-orange-100"
              }`}
            >
              {tab.name}
            </button>
          ))}
        </div>

        {/* Results Container */}
        <div className="custom-scrollbar overflow-y-auto px-5 py-6 flex-1 bg-slate-50/50">
          {loading ? (
            <div className="flex min-h-[220px] flex-col items-center justify-center gap-3 py-8 text-center">
              <span className="h-8 w-8 animate-spin rounded-full border-4 border-orange-200 border-t-travel" />
              <p className="text-sm font-black text-orange-950/60">Đang tìm kiếm thông minh qua Vector Search...</p>
            </div>
          ) : filteredPois.length === 0 ? (
            <div className="rounded-[28px] border border-dashed border-orange-300 bg-white p-12 text-center">
              <CircleOff className="mx-auto h-12 w-12 text-travel/60" />
              <h3 className="mt-4 text-lg font-black text-orange-950">Không tìm thấy địa điểm nào</h3>
              <p className="mt-2 text-sm leading-6 text-orange-950/60">
                Thử thay đổi từ khóa tìm kiếm hoặc chọn danh mục phân loại khác.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {filteredPois.map((poi) => (
                <article
                  key={poi.id}
                  className="rounded-[24px] border border-orange-200 bg-white p-5 transition flex flex-col justify-between hover:border-travel/55 hover:shadow-md"
                >
                  <div>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <h3 className="text-base font-black text-orange-950 max-w-[75%]">{poi.name}</h3>
                      {poi.area && (
                        <span className="rounded-full bg-orange-100 px-2.5 py-0.5 text-[10px] font-black text-orange-950/60">
                          {poi.area}
                        </span>
                      )}
                    </div>
                    <p className="mt-2 text-xs leading-5 text-orange-950/70 line-clamp-3">{poi.description}</p>
                  </div>

                  <div>
                    <div className="mt-4 flex flex-wrap gap-1.5 text-[10px] font-bold text-orange-950/60">
                      <span className="rounded-full bg-travel/10 px-2.5 py-1 text-travel font-extrabold">{poi.category}</span>
                      <span className="rounded-full bg-orange-100 px-2.5 py-1">
                        {poi.estimatedCost === 0 ? "Miễn phí" : formatCurrency(poi.estimatedCost)}
                      </span>
                      <span className="rounded-full bg-orange-100 px-2.5 py-1">{poi.estimatedDurationMinutes} phút</span>
                      {poi.tags.slice(0, 2).map((tag) => (
                        <span key={tag} className="rounded-full bg-orange-100 px-2.5 py-1">
                          {tag}
                        </span>
                      ))}
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        onAdd(targetDay, poi)
                        onClose()
                      }}
                      className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-orange-50 border border-orange-200 px-4 py-3 text-xs font-black text-orange-950 transition hover:bg-travel hover:text-white hover:border-travel"
                    >
                      <Plus className="h-4 w-4" /> Thêm vào Ngày {targetDay}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
