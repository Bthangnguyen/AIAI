"use client"

import { Expand, RefreshCw } from "lucide-react"
import { ItineraryArtifact } from "@/components/ItineraryArtifact"
import { ItineraryMapPanel } from "@/components/ItineraryMapPanel"
import { RouteComparisonPanel } from "@/components/RouteComparisonPanel"
import type { BuildStatus, ItineraryDraft, PreviewMode } from "@/types/trip"

interface ItineraryPreviewPanelProps {
  draft: ItineraryDraft | null
  status: BuildStatus
  viewMode: PreviewMode
  selectedPoiId: string | null
  hoveredPoiId: string | null
  selectedDay: number | "all"
  showRouteLines: boolean
  fitSignal: number
  onViewModeChange: (mode: PreviewMode) => void
  onRebuild: () => void
  onSelectPoi: (poiId: string) => void
  onHoverPoi: (poiId: string | null) => void
  onSaveDraft: () => void
  onAddPlace: (dayNumber: number) => void
  onRemovePlace: (dayNumber: number, itemId: string) => void
  onOptimizeDay: (dayNumber: number) => void
}

export function ItineraryPreviewPanel({ draft, status, viewMode, selectedPoiId, hoveredPoiId, selectedDay, showRouteLines, fitSignal, onViewModeChange, onRebuild, onSelectPoi, onHoverPoi, onSaveDraft, onAddPlace, onRemovePlace, onOptimizeDay }: ItineraryPreviewPanelProps) {
  return (
    <div className="flex h-full min-w-0 flex-col bg-orange-50">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-orange-200 px-4">
        <div className="flex items-center gap-2 text-xs font-bold text-orange-950/60">
          <span className={`h-2 w-2 rounded-full ${status === "building" ? "bg-warning" : status === "resolving" ? "bg-blue" : status === "live" ? "bg-success" : "bg-muted-2"}`} />
          {status === "building" ? "Đang tạo" : status === "resolving" ? "Đang tối ưu" : status === "live" ? "Bản nháp" : "Chưa có lịch trình"}
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={onRebuild} className="rounded-lg p-2 text-orange-950/60 transition hover:bg-white-2 hover:text-orange-950" aria-label="Rebuild"><RefreshCw size={15} /></button>
          <div className="hidden rounded-lg border border-orange-200 bg-white p-1 sm:flex">
            {(["timeline", "map", "split", "compare"] as PreviewMode[]).map((mode) => (
              <button key={mode} type="button" onClick={() => onViewModeChange(mode)} className={`rounded-md px-2.5 py-1 text-[11px] font-bold ${viewMode === mode ? "bg-white-2 text-orange-950" : "text-orange-950/60"}`}>
                {mode === "timeline" ? "Timeline" : mode === "map" ? "Map" : mode === "split" ? "Split" : "⚡ Compare"}
              </button>
            ))}
          </div>
          <button type="button" className="rounded-lg p-2 text-orange-950/60 transition hover:bg-white-2 hover:text-orange-950" aria-label="Fullscreen"><Expand size={15} /></button>
        </div>
      </div>

      <div className="custom-scrollbar relative flex-1 overflow-auto bg-[radial-gradient(circle_at_center,rgba(249,115,22,0.14)_0,transparent_34rem)] p-4">
        <div className="pointer-events-none absolute inset-0 opacity-[0.08] [background-image:linear-gradient(#fb923c_1px,transparent_1px),linear-gradient(90deg,#fb923c_1px,transparent_1px)] [background-size:32px_32px]" />
        {status === "building" || status === "resolving" ? <BuildingOverlay /> : null}
        {!draft ? <EmptyPreview /> : null}
        {draft && viewMode === "split" ? (
          <div className="relative z-10 grid min-h-full w-full gap-4 xl:grid-cols-[minmax(420px,0.95fr)_minmax(420px,1.05fr)]">
            <ItineraryArtifact draft={draft} selectedPoiId={selectedPoiId} onSelectPoi={onSelectPoi} onHoverPoi={onHoverPoi} onSaveDraft={onSaveDraft} onAddPlace={onAddPlace} onRemovePlace={onRemovePlace} onOptimizeDay={onOptimizeDay} />
            <ItineraryMapPanel draft={draft} selectedPoiId={selectedPoiId} hoveredPoiId={hoveredPoiId} selectedDay={selectedDay} showRouteLines={showRouteLines} fitSignal={fitSignal} onSelectPoi={onSelectPoi} />
          </div>
        ) : null}
        {draft && viewMode === "timeline" ? (
          <div className="relative z-10 w-full"><ItineraryArtifact draft={draft} selectedPoiId={selectedPoiId} onSelectPoi={onSelectPoi} onHoverPoi={onHoverPoi} onSaveDraft={onSaveDraft} onAddPlace={onAddPlace} onRemovePlace={onRemovePlace} onOptimizeDay={onOptimizeDay} /></div>
        ) : null}
        {draft && viewMode === "map" ? (
          <div className="relative z-10 h-full min-h-[560px] w-full"><ItineraryMapPanel draft={draft} selectedPoiId={selectedPoiId} hoveredPoiId={hoveredPoiId} selectedDay={selectedDay} showRouteLines={showRouteLines} fitSignal={fitSignal} onSelectPoi={onSelectPoi} /></div>
        ) : null}
        {draft && viewMode === "compare" ? (
          <div className="relative z-10 w-full"><RouteComparisonPanel draft={draft} /></div>
        ) : null}
      </div>
    </div>
  )
}

function EmptyPreview() {
  return (
    <div className="relative z-10 flex h-full min-h-[520px] items-center justify-center text-center">
      <div className="rounded-[32px] border border-dashed border-orange-200 bg-white/80 p-10 shadow-2xl shadow-orange-950/10">
        <p className="text-xl font-black text-orange-950">Chưa có lịch trình</p>
        <p className="mt-3 max-w-md text-sm leading-6 text-orange-950/60">Nhập mô tả chuyến đi để TripFlow đặt các điểm lên bản đồ.</p>
      </div>
    </div>
  )
}

function BuildingOverlay() {
  return (
    <div className="absolute inset-0 z-20 flex items-center justify-center bg-bg/40 backdrop-blur-[2px]">
      <div className="rounded-3xl border border-orange-200 bg-white/95 p-5 shadow-2xl">
        <p className="text-sm font-black text-orange-950">Building updates...</p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs text-orange-950/60">
          <span className="rounded-full bg-white-2 px-3 py-1">Đang thêm Đại Nội Huế</span>
          <span className="rounded-full bg-white-2 px-3 py-1">Đang thêm Cafe Muối</span>
          <span className="rounded-full bg-white-2 px-3 py-1">Đang tối ưu ngày 1</span>
        </div>
      </div>
    </div>
  )
}

