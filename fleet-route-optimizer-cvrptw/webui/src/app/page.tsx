"use client"

import { useEffect, useState } from "react"
import { BuilderWorkspace } from "@/components/BuilderWorkspace"
import { HomePage } from "@/components/HomePage"
import { MobilePhasePage } from "@/components/MobilePhasePage"
import { MockAuthModal } from "@/components/MockAuthModal"
import { SavedTripsPage } from "@/components/SavedTripsPage"
import { Toast } from "@/components/Toast"
import { getSavedDrafts, saveDraft } from "@/lib/storage"
import { searchPois } from "@/lib/mockItineraryFallback"
import { generateRealItinerary, searchPoisBackend, reRouteDay, POI_CACHE, chatProcess } from "@/lib/api"
import { streamTripPlan, type StreamStep } from "@/lib/streamApi"
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
  const [streamDetails, setStreamDetails] = useState<Record<number, string>>({})

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
    
    setScreen("builder")
    setDraft(null)
    setIsRunning(true)
    setStatus("building")
    setActiveStep(1) // Phân tích Intent
    
    try {
      setStreamDetails({ 0: "Đang phân tích ý định đi du lịch..." })

      const emptyContract = {
        destination: null,
        budget_max: null,
        radius_km: 10.0,
        num_days: 1,
        tags: [],
        locked_pois: []
      }

      const res = await chatProcess(cleanPrompt, [], emptyContract)

      const updatedIntent: TripIntent = {
        destination: res.updated_contract.destination || undefined,
        days: res.updated_contract.num_days,
        budget: res.updated_contract.budget_max || undefined,
        interests: res.updated_contract.tags || [],
        lockedPoiNames: res.updated_contract.locked_pois || [],
        rawPrompt: cleanPrompt
      }
      setIntent(updatedIntent)

      if (res.status === "ready") {
        setStreamDetails(prev => ({ ...prev, 0: `Đã xác nhận đầy đủ thông tin: ${updatedIntent.destination}, ${updatedIntent.days} ngày.` }))
        await delay(500)
        
        setStreamDetails(prev => ({ ...prev, 1: "Đang tìm kiếm địa điểm và tối ưu lịch trình..." }))
        const nextDraft = await generateRealItinerary(
          cleanPrompt,
          updatedIntent.days,
          updatedIntent.budget,
          updatedIntent.destination || "Huế",
          updatedIntent.interests
        )

        setActiveStep(3)
        setStreamDetails(prev => ({ ...prev, 2: `Tối ưu: ${nextDraft.optimizationStats?.totalDistanceKm?.toFixed(1) || "?"} km` }))
        await delay(600)
        setStreamDetails(prev => ({ ...prev, 3: "Hoàn tất!" }))
        await delay(400)

        setDraft(nextDraft)
        setIntent(nextDraft.intent)
        setStatus("live")
        setViewMode("split")
        setSelectedPoiId(nextDraft.days[0]?.items[0]?.poiId ?? null)
        setMessages((items) => [
          ...items,
          { role: "assistant", content: res.reply },
          { role: "assistant", content: `Đã tạo lịch trình thực tế cho ${nextDraft.destination} trong ${nextDraft.days.length} ngày từ hệ thống AI.` }
        ])
        setToastMessage("Đã tự động tạo lịch trình thành công.")
      } else {
        setMessages((items) => [...items, { role: "assistant", content: res.reply }])
        setStatus("live")
        setStreamDetails({})
      }
    } catch (e: any) {
      setToastMessage("Lỗi kết nối Backend: " + e.message)
      setStatus("empty")
    } finally {
      setIsRunning(false)
    }
  }



  async function handleChatSend(message: string) {
    if (isRunning) return
    
    const userMsg = { role: "user" as const, content: message }
    setMessages((items) => [...items, userMsg])

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
      setStatus("building")
      setActiveStep(1)
      
      try {
        setStreamDetails({ 0: "AI đang phân tích ý định..." })
        
        const currentContract = {
          destination: intent?.destination || null,
          budget_max: intent?.budget || null,
          radius_km: 10.0,
          num_days: intent?.days || 1,
          tags: intent?.interests || [],
          locked_pois: intent?.lockedPoiNames || []
        }

        const historyList = messages.map(m => ({
          role: m.role,
          content: m.content
        }))

        const res = await chatProcess(message, historyList, currentContract)

        const updatedIntent: TripIntent = {
          destination: res.updated_contract.destination || undefined,
          days: res.updated_contract.num_days,
          budget: res.updated_contract.budget_max || undefined,
          interests: res.updated_contract.tags || [],
          lockedPoiNames: res.updated_contract.locked_pois || [],
          rawPrompt: intent?.rawPrompt ? `${intent.rawPrompt} ${message}` : message
        }
        setIntent(updatedIntent)

        if (res.status === "ready") {
          setStreamDetails(prev => ({ ...prev, 0: `Đã đủ thông tin: ${updatedIntent.destination}, ${updatedIntent.days} ngày.` }))
          await delay(500)
          
          setStreamDetails(prev => ({ ...prev, 1: "Đang tối ưu lịch trình qua OR-Tools..." }))
          
          const nextDraft = await generateRealItinerary(
            updatedIntent.rawPrompt,
            updatedIntent.days,
            updatedIntent.budget,
            updatedIntent.destination || "Huế",
            updatedIntent.interests
          )

          setActiveStep(3)
          setStreamDetails(prev => ({ ...prev, 2: `Tối ưu: ${nextDraft.optimizationStats?.totalDistanceKm?.toFixed(1) || "?"} km` }))
          await delay(600)
          setStreamDetails(prev => ({ ...prev, 3: "Hoàn tất!" }))
          await delay(400)

          setDraft(nextDraft)
          setIntent(nextDraft.intent)
          setStatus("live")
          setViewMode("split")
          setSelectedPoiId(nextDraft.days[0]?.items[0]?.poiId ?? null)
          setMessages((items) => [
            ...items,
            { role: "assistant", content: res.reply },
            { role: "assistant", content: `Đã tạo lịch trình thực tế cho ${nextDraft.destination} trong ${nextDraft.days.length} ngày từ hệ thống AI.` }
          ])
          setToastMessage("Đã tự động tạo lịch trình thành công.")
        } else {
          setMessages((items) => [...items, { role: "assistant", content: res.reply }])
          setStatus("live")
          setStreamDetails({})
        }
      } catch (e: any) {
        setToastMessage("Lỗi xử lý chat: " + e.message)
        setStatus("live")
      } finally {
        setIsRunning(false)
      }
      return
    }

    setIsRunning(true)
    setStatus("building")
    try {
      const nextDraft = await generateRealItinerary(
        (intent?.rawPrompt || "") + " " + message, 
        intent?.days, 
        intent?.budget, 
        intent?.destination, 
        intent?.interests
      )
      setDraft(nextDraft)
      setIntent(nextDraft.intent)
      setStatus("live")
      setFollowUp(null)
    } catch(e: any) {
      setToastMessage("Lỗi xử lý: " + e.message)
      setStatus("live")
    } finally { 
      setIsRunning(false) 
    }
  }

  function handleSaveDraft() {
    if (!draft) return
    const next = saveDraft(draft)
    setSavedDrafts(next)
    setToastMessage("Đã lưu lịch trình nháp.")
    setUndoState(null)
  }

  async function handleAddPoiBackend(dayNumber: number, poi: POI) {
    if (!draft) return
    setIsRunning(true)
    setStatus("resolving")
    try {
       const dayIndex = dayNumber - 1
       const day = draft.days[dayIndex]
       const remainingPoiIds = day.items.map(i => i.poiId).concat(poi.id)
       
       const originalItinerary = {
         days: draft.days.map(d => ({
           day_index: d.dayNumber - 1,
           date: `Day ${d.dayNumber}`,
           hotel_name: draft.destination + " Hotel",
           hotel_location: { latitude: 16.4637, longitude: 107.5905 },
           stops: d.items.map(item => ({
             poi_id: item.poiId,
             poi_name: POI_CACHE.get(item.poiId)?.name || "Unknown",
             location: { latitude: POI_CACHE.get(item.poiId)?.lat || 0, longitude: POI_CACHE.get(item.poiId)?.lng || 0 },
             visit_duration_min: POI_CACHE.get(item.poiId)?.estimatedDurationMinutes || 60
           }))
         }))
       }

       const result = await reRouteDay(
         16.4637, 107.5905,
         remainingPoiIds,
         originalItinerary,
         dayIndex,
         []
       )

       if (result.status === "error" || result.status === "infeasible" || !result.day) {
          setToastMessage("Không thể thêm điểm này vào lịch trình (hết thời gian).")
          setStatus("live")
          return
       }

       const newItems = result.day.stops
         .filter((stop: any) => !stop.poi_id.startsWith("hotel_day_"))
         .map((stop: any) => {
           const h = Math.floor(stop.arrival_time_min / 60)
           const m = stop.arrival_time_min % 60
           return {
             id: `${dayIndex}-${stop.poi_id}-${stop.arrival_time_min}`,
             poiId: stop.poi_id,
             time: `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`,
             note: ""
           }
         })

       const newDays = [...draft.days]
       newDays[dayIndex] = { ...newDays[dayIndex], items: newItems }
       
       setDraft({ ...draft, days: newDays })
       setSelectedPoiId(poi.id)
       setMessages((items) => [...items, { role: "assistant", content: `Đã thêm ${poi.name} và tối ưu lại (qua OR-Tools).` }])
       setToastMessage("Đã tối ưu lại lịch trình thành công.")
    } catch (e: any) {
       setToastMessage("Lỗi re-route: " + e.message)
    } finally {
       setIsRunning(false)
       setStatus("live")
    }
  }

  async function handleRemovePlaceBackend(dayNumber: number, itemId: string) {
    if (!draft) return
    const dayIndex = dayNumber - 1
    const day = draft.days[dayIndex]
    const itemToRemove = day.items.find(i => i.id === itemId)
    if (!itemToRemove) return
    
    setIsRunning(true)
    setStatus("resolving")
    try {
       const remainingPoiIds = day.items.filter(i => i.id !== itemId).map(i => i.poiId)
       
       const originalItinerary = {
         days: draft.days.map(d => ({
           day_index: d.dayNumber - 1,
           date: `Day ${d.dayNumber}`,
           hotel_name: draft.destination + " Hotel",
           hotel_location: { latitude: 16.4637, longitude: 107.5905 },
           stops: d.items.map(item => ({
             poi_id: item.poiId,
             poi_name: POI_CACHE.get(item.poiId)?.name || "Unknown",
             location: { latitude: POI_CACHE.get(item.poiId)?.lat || 0, longitude: POI_CACHE.get(item.poiId)?.lng || 0 },
             visit_duration_min: POI_CACHE.get(item.poiId)?.estimatedDurationMinutes || 60
           }))
         }))
       }

       const result = await reRouteDay(
         16.4637, 107.5905,
         remainingPoiIds,
         originalItinerary,
         dayIndex,
         [itemToRemove.poiId] // exclude this POI
       )

       if (result.status === "error" || result.status === "infeasible" || !result.day) {
          setToastMessage("Lỗi server khi tính lại route.")
          setStatus("live")
          return
       }

       const newItems = result.day.stops
         .filter((stop: any) => !stop.poi_id.startsWith("hotel_day_"))
         .map((stop: any) => {
           const h = Math.floor(stop.arrival_time_min / 60)
           const m = stop.arrival_time_min % 60
           return {
             id: `${dayIndex}-${stop.poi_id}-${stop.arrival_time_min}`,
             poiId: stop.poi_id,
             time: `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`,
             note: ""
           }
         })

       const newDays = [...draft.days]
       newDays[dayIndex] = { ...newDays[dayIndex], items: newItems }
       
       setDraft({ ...draft, days: newDays })
       setMessages((items) => [...items, { role: "assistant", content: `Đã xóa một địa điểm và tối ưu lại lịch trình.` }])
       setToastMessage("Đã cập nhật lại lịch trình.")
    } catch (e: any) {
       setToastMessage("Lỗi re-route: " + e.message)
    } finally {
       setIsRunning(false)
       setStatus("live")
    }
  }



  function handleOptimizeDay(dayNumber: number) {
    setStatus("resolving")
    window.setTimeout(() => setStatus(draft ? "live" : "empty"), 520)
    setToastMessage(`Đã tối ưu lại ngày ${dayNumber}.`)
    setUndoState(null)
  }

  async function handleRebuild() {
    if (!intent) return
    setIsRunning(true)
    setStatus("building")
    try {
      const nextDraft = await generateRealItinerary(intent.rawPrompt, intent.days, intent.budget, intent.destination, intent.interests)
      setDraft(nextDraft)
      setIntent(nextDraft.intent)
      setStatus("live")
      setToastMessage("Đã tạo lại lịch trình.")
    } catch (e: any) {
      setToastMessage("Lỗi tạo lại: " + e.message)
      setStatus("live")
    } finally {
      setIsRunning(false)
    }
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
          onAddPoi={handleAddPoiBackend}
          onRemovePlace={handleRemovePlaceBackend}
          onOptimizeDay={handleOptimizeDay}
          streamDetails={streamDetails}
        />
        <Toast message={toastMessage} onClose={() => { setToastMessage(null); setUndoState(null) }} />
      </>
    )
  }

  return (
    <>
      <HomePage prompt={prompt} mode={mode} isLoading={isRunning} progressStep={activeStep} onPromptChange={setPrompt} onModeChange={setMode} onSubmit={handleHomeSubmit} onAuthClick={() => setShowAuthModal(true)} onNav={(target) => setScreen(target === "demo" ? "home" : target)} />
      <MockAuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} onContinue={() => void continueAfterMockAuth()} />
      <Toast message={toastMessage} onClose={() => { setToastMessage(null); setUndoState(null) }} />
    </>
  )
}

function normalize(value: string): string {
  return value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/d/g, "d")
}
