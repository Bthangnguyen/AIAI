"use client"

import { useEffect, useState } from "react"
import { BuilderWorkspace } from "@/components/BuilderWorkspace"
import { HomePage } from "@/components/HomePage"
import { MobilePhasePage } from "@/components/MobilePhasePage"
import { MockAuthModal } from "@/components/MockAuthModal"
import { SavedTripsPage } from "@/components/SavedTripsPage"
import { Toast } from "@/components/Toast"
import { getSavedDrafts, saveDraft } from "@/lib/storage"
import { addPoiToDay, extractTripIntent, generateItineraryDraft, getNextFollowUpQuestion, lightenItinerary, reduceCost, removeItemFromDay, restoreItemToDay, searchPois } from "@/lib/planner"
import type { AIMessage } from "@/components/AITripChatPanel"
import type { BuildStatus, BuilderMode, FollowUpQuestion, ItineraryDraft, ItineraryItem, POI, PreviewMode, TripIntent } from "@/types/trip"

type Screen = "home" | "builder" | "saved" | "mobile"

interface UndoState {
  dayNumber: number
  item: ItineraryItem
  index: number
}

const delay = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms))

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
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [undoState, setUndoState] = useState<UndoState | null>(null)

  useEffect(() => {
    setSavedDrafts(getSavedDrafts())
  }, [])

  useEffect(() => {
    if (!toastMessage) return
    const timer = window.setTimeout(() => {
      setToastMessage(null)
      setUndoState(null)
    }, 5200)
    return () => window.clearTimeout(timer)
  }, [toastMessage])

  async function runBuildSteps() {
    setIsRunning(true)
    setStatus("building")
    for (let index = 0; index < 4; index += 1) {
      setActiveStep(index)
      await delay(360)
    }
    setIsRunning(false)
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
    setScreen("home")
    await runBuildSteps()

    const nextIntent = extractTripIntent(cleanPrompt)
    handleIntentResult(nextIntent, mode, true)
  }

  function handleIntentResult(nextIntent: TripIntent, nextMode: BuilderMode, fromHome = false) {
    const nextQuestion = getNextFollowUpQuestion(nextIntent)
    setIntent(nextIntent)
    setFollowUp(nextQuestion)
    setScreen("builder")

    if (nextQuestion) {
      setStatus("empty")
      setMessages((items) => [...items, { role: "assistant", content: `Mình cần thêm một chút thông tin: ${nextQuestion.question}` }])
      return
    }

    if (nextMode === "plan" && fromHome) {
      setStatus("empty")
      setMessages((items) => [...items, { role: "assistant", content: `Đã phân tích: ${nextIntent.destination}, ${nextIntent.days} ngày, ngân sách khoảng ${nextIntent.budget?.toLocaleString("vi-VN")}đ. Chuyển sang Build khi bạn muốn tạo bản nháp.` }])
      return
    }

    const nextDraft = generateItineraryDraft(nextIntent)
    setDraft(nextDraft)
    setStatus("live")
    setViewMode("split")
    setSelectedPoiId(nextDraft.days[0]?.items[0]?.poiId ?? null)
    setMessages((items) => [...items, { role: "assistant", content: `Đã tạo bản nháp ${nextDraft.destination} ${nextDraft.days.length} ngày. Mình đã đặt các điểm lên timeline và bản đồ mock OpenStreetMap.` }])
    setToastMessage("Đã tạo lịch trình nháp.")
  }

  async function handleChatSend(message: string) {
    if (isRunning) return
    setMessages((items) => [...items, { role: "user", content: message }])

    if (followUp) {
      await runBuildSteps()
      const nextIntent = extractTripIntent(message, intent)
      handleIntentResult(nextIntent, "build")
      return
    }

    const normalized = normalize(message)
    if (draft && (normalized.includes("giam chi phi") || normalized.includes("tiet kiem"))) {
      const nextDraft = reduceCost(draft)
      setDraft(nextDraft)
      setMessages((items) => [...items, { role: "assistant", content: "Mình đã giảm chi phí bằng cách ưu tiên các điểm có cost thấp hơn trong từng ngày." }])
      setToastMessage("Đã tối ưu lịch trình theo chi phí.")
      return
    }

    if (draft && (normalized.includes("di nhe") || normalized.includes("nhe hon"))) {
      const nextDraft = lightenItinerary(draft)
      setDraft(nextDraft)
      setMessages((items) => [...items, { role: "assistant", content: "Mình đã làm lịch trình nhẹ hơn, giảm số điểm mỗi ngày để có thêm thời gian nghỉ." }])
      setToastMessage("Đã làm lịch trình nhẹ hơn.")
      return
    }

    if (draft && normalized.includes("them")) {
      const match = searchPois(message).find((poi) => !draft.days.some((day) => day.items.some((item) => item.poiId === poi.id)))
      if (match) {
        handleAddPoi(draft.days[0]?.dayNumber ?? 1, match)
        setMessages((items) => [...items, { role: "assistant", content: `Đã thêm ${match.name} vào lịch trình và cập nhật bản đồ.` }])
        return
      }
    }

    await runBuildSteps()
    const nextIntent = extractTripIntent(message, intent)
    handleIntentResult(nextIntent, mode)
  }

  function handleSaveDraft() {
    if (!draft) return
    const next = saveDraft(draft)
    setSavedDrafts(next)
    setToastMessage("Đã lưu lịch trình nháp.")
    setUndoState(null)
  }

  function handleAddPoi(dayNumber: number, poi: POI) {
    if (!draft) return
    const nextDraft = addPoiToDay(draft, dayNumber, poi)
    setDraft(nextDraft)
    setSelectedPoiId(poi.id)
    setFitSignal((value) => value + 1)
    setToastMessage("Đã thêm địa điểm và cập nhật bản đồ.")
    setUndoState(null)
  }

  function handleRemovePlace(dayNumber: number, itemId: string) {
    if (!draft) return
    const result = removeItemFromDay(draft, dayNumber, itemId)
    if (!result.removed) return
    setDraft(result.draft)
    setUndoState({ dayNumber, item: result.removed, index: result.index })
    setToastMessage("Đã xóa địa điểm.")
    if (selectedPoiId === result.removed.poiId) setSelectedPoiId(null)
  }

  function handleUndoRemove() {
    if (!draft || !undoState) return
    setDraft(restoreItemToDay(draft, undoState.dayNumber, undoState.item, undoState.index))
    setSelectedPoiId(undoState.item.poiId)
    setUndoState(null)
    setToastMessage(null)
    setFitSignal((value) => value + 1)
  }

  function handleOptimizeDay(dayNumber: number) {
    setStatus("resolving")
    window.setTimeout(() => setStatus(draft ? "live" : "empty"), 520)
    setToastMessage(`Đã tối ưu lại ngày ${dayNumber}.`)
    setUndoState(null)
  }

  async function handleRebuild() {
    if (!intent) return
    await runBuildSteps()
    handleIntentResult(intent, "build")
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
    setSelectedPoiId(null)
    setHoveredPoiId(null)
    setPrompt("")
  }

  function backHome() {
    setScreen("home")
  }

  if (screen === "saved") return <SavedTripsPage drafts={savedDrafts} onOpenDraft={openSavedDraft} onCreateNew={() => setScreen("home")} onBack={backHome} />
  if (screen === "mobile") return <MobilePhasePage onBack={backHome} />
  if (screen === "builder") {
    return (
      <>
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
          onAddPoi={handleAddPoi}
          onRemovePlace={handleRemovePlace}
          onOptimizeDay={handleOptimizeDay}
        />
        <Toast message={toastMessage} actionLabel={undoState ? "Hoàn tác" : undefined} onAction={undoState ? handleUndoRemove : undefined} onClose={() => { setToastMessage(null); setUndoState(null) }} />
      </>
    )
  }

  return (
    <>
      <HomePage prompt={prompt} mode={mode} isLoading={isRunning} progressStep={activeStep} onPromptChange={setPrompt} onModeChange={setMode} onSubmit={handleHomeSubmit} onAuthClick={() => setShowAuthModal(true)} onNav={(target) => setScreen(target === "demo" ? "home" : target)} />
      <MockAuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} onContinue={() => void continueAfterMockAuth()} />
      <Toast message={toastMessage} actionLabel={undoState ? "Hoàn tác" : undefined} onAction={undoState ? handleUndoRemove : undefined} onClose={() => { setToastMessage(null); setUndoState(null) }} />
    </>
  )
}

function normalize(value: string): string {
  return value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d")
}
