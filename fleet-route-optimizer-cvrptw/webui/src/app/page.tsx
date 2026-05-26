"use client"

import { useEffect, useRef, useState } from "react"
import { BuilderWorkspace } from "@/components/BuilderWorkspace"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { HomePage } from "@/components/HomePage"
import { MobilePhasePage } from "@/components/MobilePhasePage"
import { MockAuthModal } from "@/components/MockAuthModal"
import { SavedTripsPage } from "@/components/SavedTripsPage"
import { Toast, type ToastVariant } from "@/components/Toast"
import { buildItineraryViaStream } from "@/lib/buildItinerary"
import { buildFollowUpQuestion } from "@/lib/clarification"
import { searchPois, getPoi } from "@/lib/mockItineraryFallback"
import { searchPoisBackend, reRouteDay, POI_CACHE, chatProcess } from "@/lib/api"
import { processReRouteResult } from "@/lib/reRouteFlow"
import { getSavedDrafts, saveDraft } from "@/lib/storage"
import type { AIMessage } from "@/components/AITripChatPanel"
import { fetchPlanAlternatives } from "@/lib/planAlternatives"
import { applyPlanVariant, planStyleLabel } from "@/lib/applyPlanVariant"
import { applyManualReorderToDraft, clearDayManual, poiIdsInDayOrder } from "@/lib/reorderDayItems"
import type { MoveDirection } from "@/lib/reorderDayItems"
import type { BuildStatus, BuilderMode, FollowUpQuestion, ItineraryDraft, ItineraryItem, POI, PreviewMode, TripIntent } from "@/types/trip"
import type { PlanVariant } from "@/types/plan"

type Screen = "home" | "builder" | "saved" | "mobile"

interface UndoState {
  dayNumber: number
  item: ItineraryItem
  index: number
}

interface ChatContractPayload {
  destination: string | null
  budget_max: number | null
  radius_km: number
  num_days: number
  tags: string[]
  locked_pois: string[]
}

export default function Page() {
  const [screen, setScreen] = useState<Screen>("home")
  const [prompt, setPrompt] = useState("")
  const [mode, setMode] = useState<BuilderMode>("build")
  const [intent, setIntent] = useState<TripIntent | undefined>()
  const [followUp, setFollowUp] = useState<FollowUpQuestion | null>(null)
  const [draft, setDraft] = useState<ItineraryDraft | null>(null)
  const [savedDrafts, setSavedDrafts] = useState<ItineraryDraft[]>([])
  const [messages, setMessages] = useState<AIMessage[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [activeStep, setActiveStep] = useState(0)
  const [viewMode, setViewMode] = useState<PreviewMode>("split")
  const [status, setStatus] = useState<BuildStatus>("empty")
  const [selectedPoiId, setSelectedPoiId] = useState<string | null>(null)
  const [hoveredPoiId, setHoveredPoiId] = useState<string | null>(null)
  const [selectedDay, setSelectedDay] = useState<number | "all">("all")
  const [showRouteLines, setShowRouteLines] = useState(true)
  const [showCost, setShowCost] = useState(true)
  const [showCategories, setShowCategories] = useState(true)
  const [fitSignal, setFitSignal] = useState(0)
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [toastVariant, setToastVariant] = useState<ToastVariant>("success")
  const [buildErrorMessage, setBuildErrorMessage] = useState<string | null>(null)
  const [osrmDegraded, setOsrmDegraded] = useState(false)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [undoState, setUndoState] = useState<UndoState | null>(null)
  const [streamDetails, setStreamDetails] = useState<Record<number, string>>({})
  const [planVariants, setPlanVariants] = useState<PlanVariant[] | null>(null)
  const [planVariantsLoading, setPlanVariantsLoading] = useState(false)
  const [planVariantsError, setPlanVariantsError] = useState<string | null>(null)
  const alternativesFetchedForDraftId = useRef<string | null>(null)

  useEffect(() => {
    setSavedDrafts(getSavedDrafts())
  }, [])

  useEffect(() => {
    if (!draft || status !== "live") {
      setPlanVariants(null)
      setPlanVariantsError(null)
      alternativesFetchedForDraftId.current = null
      return
    }

    if (alternativesFetchedForDraftId.current === draft.id) {
      return
    }

    let cancelled = false
    setPlanVariantsLoading(true)
    setPlanVariantsError(null)

    void fetchPlanAlternatives(draft)
      .then((result) => {
        if (cancelled) return
        setPlanVariants(result.plans)
        alternativesFetchedForDraftId.current = draft.id
      })
      .catch((e) => {
        if (cancelled) return
        setPlanVariants(null)
        setPlanVariantsError(e instanceof Error ? e.message : String(e))
      })
      .finally(() => {
        if (!cancelled) setPlanVariantsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [draft, status])

  function handleApplyPlanVariant(variant: PlanVariant) {
    if (!draft) return
    const next = applyPlanVariant(draft, variant)
    setDraft(next)
    setViewMode("split")
    setSelectedPoiId(next.days[0]?.items[0]?.poiId ?? null)
    setFitSignal((value) => value + 1)
    showToast(`Đã áp dụng lộ trình ${planStyleLabel(variant.style)}.`, "success")
  }

  useEffect(() => {
    if (!toastMessage) return
    const timer = window.setTimeout(() => {
      setToastMessage(null)
      setUndoState(null)
    }, 5200)
    return () => window.clearTimeout(timer)
  }, [toastMessage])

  function showToast(message: string, variant: ToastVariant = "success") {
    setToastVariant(variant)
    setToastMessage(message)
  }

  function contractFromIntent(current?: TripIntent): ChatContractPayload {
    return {
      destination: current?.destination ?? null,
      budget_max: current?.budget ?? null,
      radius_km: 10.0,
      num_days: current?.days ?? 1,
      tags: current?.interests ?? [],
      locked_pois: current?.lockedPoiNames ?? [],
    }
  }

  function applyDraftSuccess(nextDraft: ItineraryDraft, assistantLines: string[]) {
    setDraft(nextDraft)
    setIntent(nextDraft.intent)
    setStatus("live")
    setBuildErrorMessage(null)
    setFollowUp(null)
    setOsrmDegraded(false)
    setViewMode("split")
    setSelectedPoiId(nextDraft.days[0]?.items[0]?.poiId ?? null)
    setMessages((items) => [...items, ...assistantLines.map((content) => ({ role: "assistant" as const, content }))])

    const hasWarnings =
      (nextDraft.validationNotes?.some((n) => n.severity !== "info") ?? false) ||
      (nextDraft.droppedPoiCount ?? 0) > 0
    if (hasWarnings) {
      showToast("Lịch trình đã tạo nhưng có cảnh báo — xem gợi ý bên preview.", "warning")
    } else {
      showToast("Đã tự động tạo lịch trình thành công.", "success")
    }
  }

  async function buildItineraryFromIntent(tripIntent: TripIntent): Promise<ItineraryDraft> {
    setStatus("building")
    setActiveStep(0)
    setStreamDetails({ 0: "Đang phân tích và tối ưu qua SSE..." })
    return buildItineraryViaStream(tripIntent.rawPrompt, tripIntent, {
      onStep: (stepIndex, detail) => {
        setActiveStep(stepIndex)
        setStreamDetails((prev) => ({ ...prev, [stepIndex]: detail }))
      },
    })
  }

  function handleClarifyingResponse(
    res: { reply: string; updated_contract: { destination?: string | null; budget_max?: number | null; num_days?: number } },
    updatedIntent: TripIntent,
  ) {
    setFollowUp(buildFollowUpQuestion(res.updated_contract, res.reply))
    setIntent(updatedIntent)
    setMessages((items) => [...items, { role: "assistant", content: res.reply }])
    setStatus("live")
    setStreamDetails({})
  }

  function handleHomeSubmit() {
    const cleanPrompt = prompt.trim()
    if (!cleanPrompt || isRunning) return
    setShowAuthModal(true)
  }

  async function continueAfterMockAuth() {
    const cleanPrompt = prompt.trim()
    if (!cleanPrompt || isRunning) return
    setShowAuthModal(false)
    setMessages([{ role: "user", content: cleanPrompt }])
    setScreen("builder")
    setDraft(null)
    setIsRunning(true)
    setBuildErrorMessage(null)

    try {
      const res = await chatProcess(cleanPrompt, [], contractFromIntent())
      const updatedIntent: TripIntent = {
        destination: res.updated_contract.destination || undefined,
        days: res.updated_contract.num_days,
        budget: res.updated_contract.budget_max || undefined,
        interests: res.updated_contract.tags || [],
        lockedPoiNames: res.updated_contract.locked_pois || [],
        rawPrompt: cleanPrompt,
      }

      if (res.status === "ready") {
        const nextDraft = await buildItineraryFromIntent(updatedIntent)
        applyDraftSuccess(nextDraft, [res.reply, `Đã tạo lịch trình thực tế cho ${nextDraft.destination} trong ${nextDraft.days.length} ngày.`])
      } else {
        handleClarifyingResponse(res, updatedIntent)
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e)
      setBuildErrorMessage(message)
      setStatus("error")
      showToast("Lỗi kết nối Backend: " + message, "error")
    } finally {
      setIsRunning(false)
    }
  }

  async function handleChatSend(message: string) {
    if (isRunning) return

    setMessages((items) => [...items, { role: "user", content: message }])
    const normalized = normalize(message)

    if (draft && normalized.includes("them")) {
      setIsRunning(true)
      const results = await searchPoisBackend(message)
      const match = results.find((poi) => !draft.days.some((day) => day.items.some((item) => item.poiId === poi.id)))
      setIsRunning(false)
      if (match) {
        await handleAddPoiBackend(draft.days[0]?.dayNumber ?? 1, match)
        return
      }
    }

    if (!draft) {
      setIsRunning(true)
      setBuildErrorMessage(null)

      try {
        const historyList = messages.map((m) => ({ role: m.role, content: m.content }))
        const res = await chatProcess(message, historyList, contractFromIntent(intent))
        const updatedIntent: TripIntent = {
          destination: res.updated_contract.destination || undefined,
          days: res.updated_contract.num_days,
          budget: res.updated_contract.budget_max || undefined,
          interests: res.updated_contract.tags || [],
          lockedPoiNames: res.updated_contract.locked_pois || [],
          rawPrompt: intent?.rawPrompt ? `${intent.rawPrompt} ${message}` : message,
        }

        if (res.status === "ready") {
          const nextDraft = await buildItineraryFromIntent(updatedIntent)
          applyDraftSuccess(nextDraft, [res.reply, `Đã tạo lịch trình thực tế cho ${nextDraft.destination} trong ${nextDraft.days.length} ngày.`])
        } else {
          handleClarifyingResponse(res, updatedIntent)
        }
      } catch (e) {
        const errMessage = e instanceof Error ? e.message : String(e)
        setBuildErrorMessage(errMessage)
        setStatus("error")
        showToast("Lỗi xử lý chat: " + errMessage, "error")
      } finally {
        setIsRunning(false)
      }
      return
    }

    setIsRunning(true)
    setStatus("building")
    try {
      const mergedIntent: TripIntent = {
        ...(intent ?? { interests: [], lockedPoiNames: [], rawPrompt: "" }),
        rawPrompt: `${intent?.rawPrompt || ""} ${message}`.trim(),
      }
      const nextDraft = await buildItineraryFromIntent(mergedIntent)
      applyDraftSuccess(nextDraft, [`Đã cập nhật lịch trình theo yêu cầu mới.`])
    } catch (e) {
      const errMessage = e instanceof Error ? e.message : String(e)
      showToast("Lỗi xử lý: " + errMessage, "error")
      setStatus("live")
    } finally {
      setIsRunning(false)
    }
  }

  function handleSaveDraft() {
    if (!draft) return
    const next = saveDraft(draft)
    setSavedDrafts(next)
    showToast("Đã lưu lịch trình nháp.", "success")
    setUndoState(null)
  }

  function buildOriginalItinerary(currentDraft: ItineraryDraft) {
    return {
      days: currentDraft.days.map((d) => ({
        day_index: d.dayNumber - 1,
        date: `Day ${d.dayNumber}`,
        hotel_name: currentDraft.destination + " Hotel",
        hotel_location: { latitude: 16.4637, longitude: 107.5905 },
        stops: d.items.map((item) => ({
          poi_id: item.poiId,
          poi_name: POI_CACHE.get(item.poiId)?.name || getPoi(item.poiId)?.name || "Unknown",
          location: {
            latitude: POI_CACHE.get(item.poiId)?.lat || getPoi(item.poiId)?.lat || 0,
            longitude: POI_CACHE.get(item.poiId)?.lng || getPoi(item.poiId)?.lng || 0,
          },
          visit_duration_min:
            POI_CACHE.get(item.poiId)?.estimatedDurationMinutes || getPoi(item.poiId)?.estimatedDurationMinutes || 60,
        })),
      })),
    }
  }

  async function runReRouteForDay(dayIndex: number, remainingPoiIds: string[], excludedPoiIds: string[] = []) {
    if (!draft) return null
    const result = await reRouteDay(
      16.4637,
      107.5905,
      remainingPoiIds,
      buildOriginalItinerary(draft),
      dayIndex,
      excludedPoiIds,
    )
    const interpreted = processReRouteResult(dayIndex, result)
    if (!interpreted.ok) {
      showToast(interpreted.message, interpreted.toastVariant)
      return null
    }
    return {
      items: interpreted.items,
      toastVariant: interpreted.toastVariant,
      message: interpreted.message,
    }
  }

  async function handleAddPoiBackend(dayNumber: number, poi: POI) {
    if (!draft) return
    setIsRunning(true)
    setStatus("resolving")
    try {
      const dayIndex = dayNumber - 1
      const day = draft.days[dayIndex]
      const remainingPoiIds = day.items.map((i) => i.poiId).concat(poi.id)
      const reroute = await runReRouteForDay(dayIndex, remainingPoiIds)
      if (!reroute) return

      const newDays = [...draft.days]
      newDays[dayIndex] = { ...newDays[dayIndex], items: reroute.items }
      setDraft({ ...draft, days: newDays })
      setSelectedPoiId(poi.id)
      setMessages((items) => [...items, { role: "assistant", content: `Đã thêm ${poi.name} và tối ưu lại (qua OR-Tools).` }])
      showToast(reroute.message, reroute.toastVariant)
    } catch (e) {
      showToast("Lỗi re-route: " + (e instanceof Error ? e.message : String(e)), "error")
    } finally {
      setIsRunning(false)
      setStatus("live")
    }
  }

  async function handleRemovePlaceBackend(dayNumber: number, itemId: string) {
    if (!draft) return
    const dayIndex = dayNumber - 1
    const day = draft.days[dayIndex]
    const itemToRemove = day.items.find((i) => i.id === itemId)
    if (!itemToRemove) return

    setIsRunning(true)
    setStatus("resolving")
    try {
      const remainingPoiIds = day.items.filter((i) => i.id !== itemId).map((i) => i.poiId)
      const reroute = await runReRouteForDay(dayIndex, remainingPoiIds, [itemToRemove.poiId])
      if (!reroute) return

      const newDays = [...draft.days]
      newDays[dayIndex] = { ...newDays[dayIndex], items: reroute.items }
      setDraft({ ...draft, days: newDays })
      setMessages((items) => [...items, { role: "assistant", content: "Đã xóa một địa điểm và tối ưu lại lịch trình." }])
      showToast(reroute.message, reroute.toastVariant)
    } catch (e) {
      showToast("Lỗi re-route: " + (e instanceof Error ? e.message : String(e)), "error")
    } finally {
      setIsRunning(false)
      setStatus("live")
    }
  }

  async function handleOptimizeDay(dayNumber: number) {
    if (!draft) return
    const dayIndex = dayNumber - 1
    const day = draft.days[dayIndex]
    if (!day?.items.length) return

    setIsRunning(true)
    setStatus("resolving")
    setUndoState(null)
    try {
      const remainingPoiIds = day.items.map((i) => i.poiId)
      const reroute = await runReRouteForDay(dayIndex, remainingPoiIds)
      if (!reroute) return

      const newDays = [...draft.days]
      newDays[dayIndex] = { ...newDays[dayIndex], items: reroute.items }
      setDraft(clearDayManual({ ...draft, days: newDays, updatedAt: new Date().toISOString() }, dayNumber))
      setMessages((items) => [...items, { role: "assistant", content: `Đã tối ưu lại ngày ${dayNumber}.` }])
      showToast(reroute.message, reroute.toastVariant)
    } catch (e) {
      showToast("Lỗi re-route: " + (e instanceof Error ? e.message : String(e)), "error")
    } finally {
      setIsRunning(false)
      setStatus("live")
    }
  }

  function handleMovePlace(dayNumber: number, itemId: string, direction: MoveDirection) {
    if (!draft) return
    const next = applyManualReorderToDraft(draft, dayNumber, itemId, direction)
    setDraft(next)
    setFitSignal((value) => value + 1)
  }

  async function handleApplyManualOrder(dayNumber: number) {
    if (!draft) return
    const dayIndex = dayNumber - 1
    const day = draft.days[dayIndex]
    if (!day?.items.length) return

    const orderedIds = poiIdsInDayOrder(day)
    setIsRunning(true)
    setStatus("resolving")
    try {
      const reroute = await runReRouteForDay(dayIndex, orderedIds)
      if (!reroute) return

      const newDays = [...draft.days]
      newDays[dayIndex] = { ...newDays[dayIndex], items: reroute.items }
      const resultOrder = reroute.items.map((item) => item.poiId)
      const orderPreserved = orderedIds.length === resultOrder.length && orderedIds.every((id, index) => id === resultOrder[index])

      let nextDraft: ItineraryDraft = {
        ...draft,
        days: newDays,
        updatedAt: new Date().toISOString(),
      }
      if (orderPreserved) {
        nextDraft = clearDayManual(nextDraft, dayNumber)
      }
      setDraft(nextDraft)
      setFitSignal((value) => value + 1)
      showToast(
        orderPreserved
          ? "Đã cập nhật lộ trình theo thứ tự thủ công."
          : "Đã cập nhật giờ — solver có thể đã điều chỉnh thứ tự.",
        orderPreserved ? "success" : "warning",
      )
    } catch (e) {
      showToast("Lỗi cập nhật lộ trình: " + (e instanceof Error ? e.message : String(e)), "error")
    } finally {
      setIsRunning(false)
      setStatus("live")
    }
  }

  async function handleRebuild() {
    if (!intent) return
    setIsRunning(true)
    setBuildErrorMessage(null)
    try {
      const nextDraft = await buildItineraryFromIntent(intent)
      applyDraftSuccess(nextDraft, ["Đã tạo lại lịch trình."])
    } catch (e) {
      const errMessage = e instanceof Error ? e.message : String(e)
      setBuildErrorMessage(errMessage)
      setStatus("error")
      showToast("Lỗi tạo lại: " + errMessage, "error")
    } finally {
      setIsRunning(false)
    }
  }

  function handleSuggestFix(fix: string) {
    void handleChatSend(fix)
  }

  function openSavedDraft(nextDraft: ItineraryDraft) {
    setDraft(nextDraft)
    setIntent(nextDraft.intent)
    setPrompt(nextDraft.intent.rawPrompt)
    setFollowUp(null)
    setMessages([{ role: "assistant", content: `Đã mở lại bản nháp ${nextDraft.destination} ${nextDraft.days.length} ngày.` }])
    setStatus("live")
    setScreen("builder")
    setSelectedPoiId(nextDraft.days[0]?.items[0]?.poiId ?? null)
    setFitSignal((value) => value + 1)
  }

  function resetDraft() {
    setDraft(null)
    setIntent(undefined)
    setFollowUp(null)
    setMessages([])
    setStatus("empty")
    setBuildErrorMessage(null)
    setOsrmDegraded(false)
    setSelectedPoiId(null)
    setHoveredPoiId(null)
    setPrompt("")
  }

  function backHome() {
    setScreen("home")
  }

  if (screen === "saved") {
    return <SavedTripsPage drafts={savedDrafts} onOpenDraft={openSavedDraft} onCreateNew={() => setScreen("home")} onBack={backHome} />
  }
  if (screen === "mobile") {
    return <MobilePhasePage onBack={backHome} />
  }
  if (screen === "builder") {
    return (
      <>
        <ErrorBoundary fallbackTitle="Lỗi workspace — thử tải lại panel">
          <BuilderWorkspace
            draft={draft}
            intent={intent}
            messages={messages}
            isRunning={isRunning}
            activeStep={activeStep}
            followUp={followUp}
            mode={mode}
            viewMode={viewMode}
            status={status}
            selectedPoiId={selectedPoiId}
            hoveredPoiId={hoveredPoiId}
            selectedDay={selectedDay}
            showRouteLines={showRouteLines}
            showCost={showCost}
            showCategories={showCategories}
            fitSignal={fitSignal}
            buildErrorMessage={buildErrorMessage}
            onRetryBuild={handleRebuild}
            onSuggestFix={handleSuggestFix}
            osrmDegraded={osrmDegraded}
            onOsrmDegradedChange={setOsrmDegraded}
            planVariants={planVariants}
            planVariantsLoading={planVariantsLoading}
            planVariantsError={planVariantsError}
            onApplyPlanVariant={handleApplyPlanVariant}
            onModeChange={setMode}
            onViewModeChange={setViewMode}
            onBack={backHome}
            onSaveDraft={handleSaveDraft}
            onReset={resetDraft}
            onSavedTrips={() => setScreen("saved")}
            onMobilePhase={() => setScreen("mobile")}
            onSendMessage={handleChatSend}
            onRebuild={handleRebuild}
            onSelectPoi={setSelectedPoiId}
            onHoverPoi={setHoveredPoiId}
            onSelectedDayChange={setSelectedDay}
            onShowRouteLinesChange={setShowRouteLines}
            onShowCostChange={setShowCost}
            onShowCategoriesChange={setShowCategories}
            onFitMap={() => setFitSignal((value) => value + 1)}
            onAddPoi={handleAddPoiBackend}
            onRemovePlace={handleRemovePlaceBackend}
            onMovePlace={handleMovePlace}
            onApplyManualOrder={handleApplyManualOrder}
            onOptimizeDay={handleOptimizeDay}
            streamDetails={streamDetails}
          />
        </ErrorBoundary>
        <Toast variant={toastVariant} message={toastMessage} onClose={() => { setToastMessage(null); setUndoState(null) }} />
      </>
    )
  }

  return (
    <>
      <HomePage
        prompt={prompt}
        mode={mode}
        isLoading={isRunning}
        progressStep={activeStep}
        onPromptChange={setPrompt}
        onModeChange={setMode}
        onSubmit={handleHomeSubmit}
        onAuthClick={() => setShowAuthModal(true)}
        onNav={(target) => setScreen(target === "demo" ? "home" : target)}
      />
      <MockAuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} onContinue={() => void continueAfterMockAuth()} />
      <Toast variant={toastVariant} message={toastMessage} onClose={() => { setToastMessage(null); setUndoState(null) }} />
    </>
  )
}

function normalize(value: string): string {
  return value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/d/g, "d")
}
