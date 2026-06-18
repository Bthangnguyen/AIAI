"use client"

import { useEffect, useState } from "react"
import { AITripChatPanel, type AIMessage } from "@/components/AITripChatPanel"
import { AddPlaceModal } from "@/components/AddPlaceModal"
import { ItineraryPreviewPanel } from "@/components/ItineraryPreviewPanel"
import { TripControlPanel } from "@/components/TripControlPanel"
import { TripToolbar } from "@/components/TripToolbar"
import type { BuildStatus, BuilderMode, ItineraryDraft, POI, PreviewMode, TripIntent } from "@/types/trip"
import type { MoveDirection } from "@/lib/reorderDayItems"

interface BuilderWorkspaceProps {
  draft: ItineraryDraft | null
  intent?: TripIntent
  messages: AIMessage[]
  pendingEditPlan?: any
  isRunning: boolean
  activeStep: number

  mode: BuilderMode
  viewMode: PreviewMode
  status: BuildStatus
  selectedPoiId: string | null
  hoveredPoiId: string | null
  selectedDay: number | "all"
  showRouteLines: boolean
  showCost: boolean
  showCategories: boolean
  fitSignal: number
  requiresLodgingSelection?: boolean
  streamDetails?: Record<number, string>
  onModeChange: (mode: BuilderMode) => void
  onViewModeChange: (mode: PreviewMode) => void
  onBack: () => void
  onSaveDraft: () => void
  onReset: () => void
  onSavedTrips: () => void
  onMobilePhase: () => void
  onSendMessage: (message: string) => void
  onChooseSuggestedPlace?: (dayNumber: number, poi: POI) => void
  onRebuild: () => void
  onSelectPoi: (poiId: string) => void
  onHoverPoi: (poiId: string | null) => void
  onSelectedDayChange: (day: number | "all") => void
  onShowRouteLinesChange: (value: boolean) => void
  onShowCostChange: (value: boolean) => void
  onShowCategoriesChange: (value: boolean) => void
  onFitMap: () => void
  onSetLodgingBase?: (lat: number, lon: number, name?: string) => void
  onAddPoi: (dayNumber: number, poi: POI) => void
  onRemovePlace: (dayNumber: number, itemId: string) => void
  onMovePlace: (dayNumber: number, itemId: string, direction: MoveDirection) => void
  onApplyManualOrder?: (dayNumber: number) => void
  onOptimizeDay: (dayNumber: number) => void
  buildErrorMessage?: string | null
  onRetryBuild?: () => void
  onSuggestFix?: (fix: string) => void
  osrmDegraded?: boolean
  onOsrmDegradedChange?: (degraded: boolean) => void
  onStartDateChange?: (date: string) => void
}

type MobileTab = "chat" | "preview" | "control"

export function BuilderWorkspace(props: BuilderWorkspaceProps) {
  const [mobileTab, setMobileTab] = useState<MobileTab>(props.draft ? "preview" : "chat")
  const [modalDay, setModalDay] = useState<number | null>(null)

  useEffect(() => {
    if (props.draft) setMobileTab("preview")
  }, [props.draft])

  function openAddPlace(dayNumber?: number) {
    const target = dayNumber ?? props.draft?.days[0]?.dayNumber ?? 1
    setModalDay(target)
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-orange-50 text-orange-950">
      <TripToolbar draft={props.draft} viewMode={props.viewMode} onViewModeChange={props.onViewModeChange} onBack={props.onBack} onSave={props.onSaveDraft} onReset={props.onReset} onRebuild={props.onRebuild} onSavedTrips={props.onSavedTrips} onMobilePhase={props.onMobilePhase} />

      <div className="grid h-12 grid-cols-3 border-b border-orange-200 bg-white text-xs font-black md:hidden">
        {(["chat", "preview", "control"] as MobileTab[]).map((tab) => <button key={tab} type="button" onClick={() => setMobileTab(tab)} className={mobileTab === tab ? "bg-orange-100 text-orange-700" : "text-orange-950/55"}>{tab === "chat" ? "Chat" : tab === "preview" ? "Preview" : "Control"}</button>)}
      </div>

      <main className="min-h-0 flex-1 overflow-hidden md:grid md:grid-cols-[420px_minmax(0,1fr)_320px]">
        <div className={`${mobileTab === "chat" ? "block" : "hidden"} h-full min-h-0 border-r border-orange-200 md:block`}>
          <AITripChatPanel messages={props.messages} draft={props.draft} intent={props.intent} isRunning={props.isRunning} status={props.status} onSend={props.onSendMessage} onViewItinerary={() => { props.onViewModeChange("timeline"); setMobileTab("preview") }} onAddPlace={() => openAddPlace()} onSaveDraft={props.onSaveDraft} pendingEditPlan={props.pendingEditPlan} onChooseSuggestedPlace={props.onChooseSuggestedPlace} />
        </div>

        <div className={`${mobileTab === "preview" ? "block" : "hidden"} h-full min-h-0 min-w-0 md:block`}>
          <ItineraryPreviewPanel draft={props.draft} status={props.status} viewMode={props.viewMode} selectedPoiId={props.selectedPoiId} hoveredPoiId={props.hoveredPoiId} selectedDay={props.selectedDay} showRouteLines={props.showRouteLines} fitSignal={props.fitSignal} requiresLodgingSelection={props.requiresLodgingSelection} onViewModeChange={props.onViewModeChange} onRebuild={props.onRebuild} onSelectPoi={props.onSelectPoi} onHoverPoi={props.onHoverPoi} onSaveDraft={props.onSaveDraft} onAddPlace={(dayNumber) => openAddPlace(dayNumber)} onRemovePlace={props.onRemovePlace} onMovePlace={props.onMovePlace} onApplyManualOrder={props.onApplyManualOrder} onOptimizeDay={props.onOptimizeDay} buildErrorMessage={props.buildErrorMessage} onRetryBuild={props.onRetryBuild} onSuggestFix={props.onSuggestFix} osrmDegraded={props.osrmDegraded} onOsrmDegradedChange={props.onOsrmDegradedChange} onSetLodgingBase={props.onSetLodgingBase} />
        </div>

        <div className={`${mobileTab === "control" ? "block" : "hidden"} h-full min-h-0 md:block`}>
          <TripControlPanel draft={props.draft} status={props.status} selectedDay={props.selectedDay} showRouteLines={props.showRouteLines} showCost={props.showCost} showCategories={props.showCategories} onSelectedDayChange={props.onSelectedDayChange} onShowRouteLinesChange={props.onShowRouteLinesChange} onShowCostChange={props.onShowCostChange} onShowCategoriesChange={props.onShowCategoriesChange} onSaveDraft={props.onSaveDraft} onAddPlace={() => openAddPlace()} onRebuild={props.onRebuild} onReset={props.onReset} onFitMap={props.onFitMap} onStartDateChange={props.onStartDateChange} />
        </div>
      </main>

      {props.draft && modalDay ? <AddPlaceModal draft={props.draft} defaultDay={modalDay} isOpen onClose={() => setModalDay(null)} onAdd={(dayNumber, poi) => { props.onAddPoi(dayNumber, poi); setModalDay(null) }} /> : null}
    </div>
  )
}


