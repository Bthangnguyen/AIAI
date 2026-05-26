"use client"

import { useEffect, useMemo, useState } from "react"
import { ArrowDown, Shuffle, Sparkles } from "lucide-react"
import type { ItineraryDraft } from "@/types/trip"
import { getOptimizedRoute, getRandomRoute, type RouteStats } from "@/lib/routeComparison"

interface RouteComparisonPanelProps {
  draft: ItineraryDraft
}

export function RouteComparisonPanel({ draft }: RouteComparisonPanelProps) {
  const optimized = useMemo(() => getOptimizedRoute(draft.days), [draft])
  const [random, setRandom] = useState<RouteStats | null>(null)

  useEffect(() => {
    setRandom(getRandomRoute(draft.days))
  }, [draft])

  if (!random) return null

  const savings = random.totalDistanceKm > 0 ? Math.round(((random.totalDistanceKm - optimized.totalDistanceKm) / random.totalDistanceKm) * 100) : 0
  const savedKm = Math.round((random.totalDistanceKm - optimized.totalDistanceKm) * 10) / 10

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-black text-orange-950">So sánh Trước / Sau Tối ưu hóa</h2>
        <p className="mt-1 text-sm text-orange-950/60">Thuật toán CVRPTW + OSRM tối ưu hóa lộ trình du lịch thực tế</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Random Route */}
        <div className="rounded-2xl border-2 border-red-200 bg-red-50/50 p-5">
          <div className="flex items-center gap-2 text-red-600">
            <Shuffle className="h-5 w-5" />
            <h3 className="text-lg font-black">Đi ngẫu nhiên</h3>
          </div>
          <p className="mt-1 text-xs text-red-500/70">Không tối ưu, đi theo thứ tự bất kỳ</p>
          <div className="mt-4 text-4xl font-black text-red-700">{random.totalDistanceKm} km</div>
          <div className="mt-3 space-y-1">
            {random.orderedPois.slice(0, 6).map((poi, i) => (
              <div key={`rand-${poi.id}-${i}`} className="flex items-center gap-2 text-xs text-red-700/60">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-red-200 text-[10px] font-bold">{i + 1}</span>
                <span className="truncate">{poi.name}</span>
              </div>
            ))}
            {random.orderedPois.length > 6 ? <p className="text-xs text-red-400">+{random.orderedPois.length - 6} điểm khác...</p> : null}
          </div>
        </div>

        {/* Optimized Route */}
        <div className="rounded-2xl border-2 border-green-300 bg-green-50/50 p-5 ring-2 ring-green-200/50">
          <div className="flex items-center gap-2 text-green-600">
            <Sparkles className="h-5 w-5" />
            <h3 className="text-lg font-black">Tối ưu bằng OR-Tools</h3>
          </div>
          <p className="mt-1 text-xs text-green-500/70">CVRPTW + OSRM routing thực tế tại Huế</p>
          <div className="mt-4 text-4xl font-black text-green-700">{optimized.totalDistanceKm} km</div>
          <div className="mt-3 space-y-1">
            {optimized.orderedPois.slice(0, 6).map((poi, i) => (
              <div key={`opt-${poi.id}-${i}`} className="flex items-center gap-2 text-xs text-green-700/60">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-green-200 text-[10px] font-bold">{i + 1}</span>
                <span className="truncate">{poi.name}</span>
              </div>
            ))}
            {optimized.orderedPois.length > 6 ? <p className="text-xs text-green-400">+{optimized.orderedPois.length - 6} điểm khác...</p> : null}
          </div>
        </div>
      </div>

      {/* Savings Banner */}
      <div className="flex items-center justify-center gap-4 rounded-2xl bg-gradient-to-r from-green-500 to-emerald-600 p-5 text-white shadow-xl">
        <ArrowDown className="h-8 w-8 animate-bounce" />
        <div className="text-center">
          <p className="text-3xl font-black">Tiết kiệm {savings}%</p>
          <p className="text-sm font-bold text-white/80">Giảm {savedKm} km quãng đường di chuyển</p>
        </div>
        <ArrowDown className="h-8 w-8 animate-bounce" />
      </div>

      <div className="text-center">
        <button
          type="button"
          onClick={() => setRandom(getRandomRoute(draft.days))}
          className="rounded-xl border border-orange-200 bg-white px-6 py-2.5 text-sm font-bold text-orange-700 shadow transition hover:bg-orange-50"
        >
          <Shuffle className="mr-2 inline h-4 w-4" /> Xáo trộn lại để so sánh
        </button>
      </div>
    </div>
  )
}
