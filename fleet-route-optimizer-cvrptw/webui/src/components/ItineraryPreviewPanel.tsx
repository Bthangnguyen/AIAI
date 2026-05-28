"use client"

import { Expand, RefreshCw } from "lucide-react"
import { BuildErrorPanel } from "@/components/BuildErrorPanel"
import { ConstraintSuggestionPanel } from "@/components/ConstraintSuggestionPanel"
import { ItineraryArtifact } from "@/components/ItineraryArtifact"
import { ItineraryMapPanel } from "@/components/ItineraryMapPanel"
import type { BuildStatus, ItineraryDraft, PreviewMode } from "@/types/trip"
import type { MoveDirection } from "@/lib/reorderDayItems"

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
  onMovePlace: (dayNumber: number, itemId: string, direction: MoveDirection) => void
  onApplyManualOrder?: (dayNumber: number) => void
  onOptimizeDay: (dayNumber: number) => void
  buildErrorMessage?: string | null
  onRetryBuild?: () => void
  onSuggestFix?: (fix: string) => void
  osrmDegraded?: boolean
  onOsrmDegradedChange?: (degraded: boolean) => void
}

export function ItineraryPreviewPanel({ draft, status, viewMode, selectedPoiId, hoveredPoiId, selectedDay, showRouteLines, fitSignal, onViewModeChange, onRebuild, onSelectPoi, onHoverPoi, onSaveDraft, onAddPlace, onRemovePlace, onMovePlace, onApplyManualOrder, onOptimizeDay, buildErrorMessage, onRetryBuild, onSuggestFix, osrmDegraded, onOsrmDegradedChange }: ItineraryPreviewPanelProps) {
  return (
    <div className="flex h-full min-w-0 flex-col bg-orange-50">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-orange-200 px-4">
        <div className="flex items-center gap-2 text-xs font-bold text-orange-950/60">
          <span className={`h-2 w-2 rounded-full ${status === "building" ? "bg-warning" : status === "resolving" ? "bg-blue" : status === "error" ? "bg-red-500" : status === "live" ? "bg-success" : "bg-muted-2"}`} />
          {status === "building" ? "Đang tạo" : status === "resolving" ? "Đang tối ưu" : status === "error" ? "Lỗi tạo lịch" : status === "live" ? "Bản nháp" : "Chưa có lịch trình"}
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={onRebuild} className="rounded-lg p-2 text-orange-950/60 transition hover:bg-white-2 hover:text-orange-950" aria-label="Rebuild"><RefreshCw size={15} /></button>
          <div className="hidden rounded-lg border border-orange-200 bg-white p-1 sm:flex">
            {(["timeline", "map", "split"] as PreviewMode[]).map((mode) => (
              <button key={mode} type="button" onClick={() => onViewModeChange(mode)} className={`rounded-md px-2.5 py-1 text-[11px] font-bold ${viewMode === mode ? "bg-white-2 text-orange-950" : "text-orange-950/60"}`}>
                {mode === "timeline" ? "Timeline" : mode === "map" ? "Map" : "Split"}
              </button>
            ))}
          </div>
          <button type="button" className="rounded-lg p-2 text-orange-950/60 transition hover:bg-white-2 hover:text-orange-950" aria-label="Fullscreen"><Expand size={15} /></button>
        </div>
      </div>

      <div className="custom-scrollbar relative flex-1 overflow-auto bg-[radial-gradient(circle_at_center,rgba(249,115,22,0.14)_0,transparent_34rem)] p-4">
        <div className="pointer-events-none absolute inset-0 opacity-[0.08] [background-image:linear-gradient(#fb923c_1px,transparent_1px),linear-gradient(90deg,#fb923c_1px,transparent_1px)] [background-size:32px_32px]" />
        {status === "building" ? <BuildingOverlay /> : null}
        {status === "error" && onRetryBuild ? <BuildErrorPanel message={buildErrorMessage ?? undefined} onRetry={onRetryBuild} /> : null}
        {!draft && status !== "error" ? <EmptyPreview /> : null}
        {draft && onSuggestFix ? (
          <ConstraintSuggestionPanel
            notes={draft.validationNotes ?? []}
            droppedPoiCount={draft.droppedPoiCount}
            budgetUsed={draft.budgetUsed ?? draft.optimizationStats?.budgetUsed}
            budgetMax={draft.optimizationStats?.budgetMax ?? draft.budget}
            onSuggestFix={onSuggestFix}
          />
        ) : null}
        {osrmDegraded ? (
          <div className="relative z-20 mb-4 rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-900">
            Đường trên bản đồ đang dùng đường thẳng (OSRM không phản hồi).
          </div>
        ) : null}
        {draft && viewMode === "split" ? (
          <div className="relative z-10 grid min-h-full w-full gap-4 xl:grid-cols-[minmax(420px,0.95fr)_minmax(420px,1.05fr)]">
            <ItineraryArtifact draft={draft} selectedPoiId={selectedPoiId} onSelectPoi={onSelectPoi} onHoverPoi={onHoverPoi} onSaveDraft={onSaveDraft} onAddPlace={onAddPlace} onRemovePlace={onRemovePlace} onMovePlace={onMovePlace} onApplyManualOrder={onApplyManualOrder} onOptimizeDay={onOptimizeDay} />
            <ItineraryMapPanel draft={draft} selectedPoiId={selectedPoiId} hoveredPoiId={hoveredPoiId} selectedDay={selectedDay} showRouteLines={showRouteLines} fitSignal={fitSignal} onSelectPoi={onSelectPoi} onOsrmDegradedChange={onOsrmDegradedChange} />
          </div>
        ) : null}
        {draft && viewMode === "timeline" ? (
          <div className="relative z-10 w-full"><ItineraryArtifact draft={draft} selectedPoiId={selectedPoiId} onSelectPoi={onSelectPoi} onHoverPoi={onHoverPoi} onSaveDraft={onSaveDraft} onAddPlace={onAddPlace} onRemovePlace={onRemovePlace} onMovePlace={onMovePlace} onApplyManualOrder={onApplyManualOrder} onOptimizeDay={onOptimizeDay} /></div>
        ) : null}
        {draft && viewMode === "map" ? (
          <div className="relative z-10 h-full min-h-[560px] w-full"><ItineraryMapPanel draft={draft} selectedPoiId={selectedPoiId} hoveredPoiId={hoveredPoiId} selectedDay={selectedDay} showRouteLines={showRouteLines} fitSignal={fitSignal} onSelectPoi={onSelectPoi} onOsrmDegradedChange={onOsrmDegradedChange} /></div>
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
      <div className="w-[min(420px,calc(100%-2rem))] rounded-3xl border border-orange-200 bg-white/95 p-5 shadow-2xl">
        <p className="text-sm font-black text-orange-950">Đang tạo lịch trình...</p>
        <p className="mt-1 text-xs leading-5 text-orange-950/55">TripFlow đang phân tích yêu cầu và tối ưu tuyến đi.</p>
        <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-orange-100">
          <div className="tripflow-loading-bar h-full rounded-full bg-orange-500" />
        </div>
      </div>
    </div>
  )
}

