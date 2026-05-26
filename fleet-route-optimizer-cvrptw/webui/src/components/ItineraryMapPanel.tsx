"use client"

import dynamic from "next/dynamic"
import { useState } from "react"
import { MapPinned, Play, Square } from "lucide-react"
import type { ItineraryDraft } from "@/types/trip"

const ItineraryMap = dynamic(() => import("@/components/ItineraryMap").then((mod) => mod.ItineraryMap), {
  ssr: false,
  loading: () => <div className="flex h-full items-center justify-center text-sm text-orange-950/60">Đang tải bản đồ...</div>,
})

interface ItineraryMapPanelProps {
  draft: ItineraryDraft | null
  selectedPoiId: string | null
  hoveredPoiId: string | null
  selectedDay: number | "all"
  showRouteLines: boolean
  fitSignal: number
  onSelectPoi: (poiId: string) => void
  onOsrmDegradedChange?: (degraded: boolean) => void
}

export function ItineraryMapPanel({ draft, selectedPoiId, hoveredPoiId, selectedDay, showRouteLines, fitSignal, onSelectPoi, onOsrmDegradedChange }: ItineraryMapPanelProps) {
  const [isJourneyPlaying, setIsJourneyPlaying] = useState(false)
  if (!draft) {
    return (
      <div className="flex h-full min-h-[360px] items-center justify-center rounded-3xl border border-dashed border-orange-200 bg-white/60 p-8 text-center">
        <div>
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-100 text-orange-950/60"><MapPinned className="h-6 w-6" /></div>
          <h3 className="mt-4 text-lg font-black text-orange-950">Chưa có lịch trình</h3>
          <p className="mt-2 max-w-sm text-sm leading-6 text-orange-950/60">Nhập mô tả chuyến đi để TripFlow đặt các điểm lên bản đồ.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative h-full min-h-[360px] overflow-hidden rounded-3xl border border-orange-200 bg-white">
      <div className="relative h-full w-full">
        <div className="absolute right-3 top-3 z-[1000] flex gap-2">
          <button
            type="button"
            onClick={() => setIsJourneyPlaying(!isJourneyPlaying)}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-black shadow-lg backdrop-blur transition ${
              isJourneyPlaying
                ? "bg-red-500 text-white hover:bg-red-600"
                : "bg-white/90 text-orange-700 hover:bg-orange-50"
            }`}
          >
            {isJourneyPlaying ? <><Square className="h-3.5 w-3.5" /> Dừng</> : <><Play className="h-3.5 w-3.5" /> Phát hành trình</>}
          </button>
        </div>
        <ItineraryMap
          itineraryDraft={draft}
          selectedPoiId={selectedPoiId}
          hoveredPoiId={hoveredPoiId}
          onSelectPoi={onSelectPoi}
          selectedDay={selectedDay}
          showRouteLines={showRouteLines}
          onFitBoundsRequest={fitSignal}
          isJourneyPlaying={isJourneyPlaying}
          onJourneyStepChange={(poiId) => onSelectPoi(poiId)}
          onJourneyFinish={() => setIsJourneyPlaying(false)}
          onOsrmDegradedChange={onOsrmDegradedChange}
        />
      </div>
      <MapLegend draft={draft} />
    </div>
  )
}

function MapLegend({ draft }: { draft: ItineraryDraft }) {
  const colors = ["#ff385c", "#60a5fa", "#22c55e", "#f59e0b", "#a78bfa"]
  return (
    <div className="pointer-events-none absolute bottom-4 left-4 z-[500] rounded-2xl border border-orange-200 bg-orange-50/85 p-3 text-xs shadow-2xl backdrop-blur">
      <p className="mb-2 font-black text-orange-950">Route layers</p>
      <div className="space-y-1.5">
        {draft.days.map((day, index) => (
          <div key={day.dayNumber} className="flex items-center gap-2 text-orange-950/60">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: colors[index % colors.length] }} />
            Ngày {day.dayNumber}
          </div>
        ))}
      </div>
    </div>
  )
}

