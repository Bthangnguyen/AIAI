/**
 * useTripPipeline — React hook that wires LoadingScreen to either:
 *  - MockTripService (when FeatureFlags.USE_MOCK_BACKEND = true)
 *  - TripService real SSE (when false)
 *
 * Normalizes the two different API shapes into a single event contract.
 */
import { useCallback, useEffect, useRef, useState } from "react"
import * as Notifications from "expo-notifications"
import { FeatureFlags } from "@/config/features"
import { TripService } from "@/services/api/tripService"
import { MockTripService } from "@/services/mock/mockTripService"
import { useTripStore } from "@/store/useTripStore"
import type { TravelItinerary } from "@/navigators/navigationTypes"

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
})

export type StepStatus = "pending" | "active" | "done" | "error"

export interface PipelineStep {
  id: string
  label: string
  detail: string
  status: StepStatus
}

export interface LogEntry {
  id: number
  message: string
  type: "info" | "success" | "error"
  timestamp: number
}

const INITIAL_STEPS: PipelineStep[] = [
  {
    id: "l2",
    label: "Analyzing Intent",
    detail: "NLP extracting preferences…",
    status: "pending",
  },
  {
    id: "l3",
    label: "Finding Places",
    detail: "Spatial search for POIs…",
    status: "pending",
  },
  {
    id: "l4",
    label: "Optimizing Route",
    detail: "OR-Tools solver running…",
    status: "pending",
  },
]

interface UseTripPipelineOptions {
  prompt: string
  hotelLat?: number
  hotelLon?: number
  hotelName?: string
  numDays?: number
  onItinerary: (itinerary: TravelItinerary) => void
}

interface UseTripPipelineResult {
  steps: PipelineStep[]
  logs: LogEntry[]
  errorMsg: string | null
}

export const useTripPipeline = ({
  prompt,
  hotelLat,
  hotelLon,
  hotelName,
  numDays,
  onItinerary,
}: UseTripPipelineOptions): UseTripPipelineResult => {
  const [steps, setSteps] = useState<PipelineStep[]>(INITIAL_STEPS)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const itineraryRef = useRef<TravelItinerary | null>(null)
  const logIdRef = useRef(0)

  const setOriginalPrompt = useTripStore((state) => state.setOriginalPrompt)
  const setSseStage = useTripStore((state) => state.setSseStage)
  const setExtractedConstraints = useTripStore((state) => state.setExtractedConstraints)
  const setCurrentItinerary = useTripStore((state) => state.setCurrentItinerary)

  const updateStep = useCallback((stepId: string, status: StepStatus) => {
    setSteps((prev) => prev.map((s) => (s.id === stepId ? { ...s, status } : s)))
  }, [])

  const addLog = useCallback((message: string, type: LogEntry["type"] = "info") => {
    logIdRef.current += 1
    setLogs((prev) => [
      ...prev,
      { id: logIdRef.current, message, type, timestamp: Date.now() },
    ])
  }, [])

  useEffect(() => {
    let cancelled = false
    updateStep("l2", "active")
    addLog("🚀 Starting AI trip planning…")

    // Save prompt to offline storage
    setOriginalPrompt(prompt)
    setSseStage("intent_extraction_started")

    // ─── Pre-flight health check (real backend only) ─────────────────────────
    if (!FeatureFlags.USE_MOCK_BACKEND) {
      TripService.checkHealth().then(({ ready, message }) => {
        if (cancelled) return
        if (!ready) {
          addLog(`⚠️ Server: ${message}`, "error")
        } else {
          addLog("✓ Server connected", "info")
        }
      })
    }

    // ─── MOCK BACKEND ─────────────────────────────────────────────────────────
    if (FeatureFlags.USE_MOCK_BACKEND) {
      const controller = MockTripService.planTripStream(prompt, hotelLat, hotelLon)

      const sub = controller.subscribe((event) => {
        const data = event.data as any
        if (event.event === "status") {
          addLog(data?.message || "Processing…", "info")
        } else if (event.event === "l2_done") {
          updateStep("l2", "done")
          updateStep("l3", "active")
          setExtractedConstraints(data)
          addLog(
            `✓ Intent analyzed — ${(data?.tags || []).length} preference tags`,
            "success",
          )
        } else if (event.event === "l3_done") {
          updateStep("l3", "done")
          updateStep("l4", "active")
          addLog(
            `✓ Found ${data?.pois_found || "?"} places`,
            "success",
          )
        } else if (event.event === "l4_result") {
          updateStep("l4", "done")
          const itinerary = event.data as unknown as TravelItinerary
          itineraryRef.current = itinerary
          setCurrentItinerary(itinerary)
          addLog(
            `✓ Route optimized — ${itinerary?.total_pois_visited || "?"} POIs across ${itinerary?.num_days || "?"} days`,
            "success",
          )
          
          // Trigger Push Notification
          Notifications.scheduleNotificationAsync({
            content: {
              title: "Hành trình đã sẵn sàng! ✈️",
              body: "AI đã tạo xong lịch trình tối ưu của bạn. Nhấn để xem ngay.",
              sound: true,
            },
            trigger: null, // trigger immediately
          })

          // Navigate after short delay so user sees final state
          setTimeout(() => onItinerary(itinerary), 600)
        } else if (event.event === "error") {
          updateStep("l2", "error")
          updateStep("l3", "error")
          updateStep("l4", "error")
          setErrorMsg(data?.message || "An error occurred")
          addLog(`✗ ${data?.message}`, "error")
          setSseStage("error")
        }
      })

      return () => {
        cancelled = true
        controller.cancel()
      }
    }

    // ─── REAL BACKEND ─────────────────────────────────────────────────────────
    // Timeout: abort if no itinerary within 2 minutes
    const TIMEOUT_MS = 120_000
    const timeoutTimer = setTimeout(() => {
      if (!itineraryRef.current) {
        setErrorMsg("Request timed out — server took too long.")
        addLog("⏱ Connection timed out after 2 minutes", "error")
        updateStep("l4", "error")
        setSseStage("error")
      }
    }, TIMEOUT_MS)

    const es = TripService.planTripStream(
      prompt,
      hotelLat,
      hotelLon,
      hotelName,
      numDays,
      (data: any) => {
        if (data.stage) {
          setSseStage(data.stage)
        }

        if (data.stage === "intent_extraction_started") {
          updateStep("l2", "active")
          addLog("🚀 Analyzing intent and extracting constraints...", "info")
        } else if (data.stage === "intent_extraction_completed") {
          updateStep("l2", "done")
          updateStep("l3", "active")
          if (data.contract) {
            setExtractedConstraints(data.contract)
            const tags = data.contract.tags || []
            const locked = data.contract.locked_pois || []
            addLog(`✓ Intent analyzed successfully. Prefers: ${tags.join(", ") || "none"}`, "success")
            if (locked.length) {
              addLog(`🔒 Locked POIs: ${locked.join(", ")}`, "info")
            }
          }
        } else if (data.stage === "poi_search_started") {
          addLog("🔍 Querying database for relevant POIs...", "info")
        } else if (data.stage === "poi_search_completed") {
          updateStep("l3", "done")
          updateStep("l4", "active")
          addLog(`✓ Found ${data.pois_found || 0} matching places (${data.locked_count || 0} locked).`, "success")
        } else if (data.stage === "optimization_started") {
          addLog("⚙️ Optimization routing solver started (OR-Tools)...", "info")
        } else if (data.stage === "optimization_completed") {
          addLog("✓ Route optimization finished.", "success")
        } else if (data.stage === "validation_completed") {
          const notes = data.validation_notes || []
          addLog(`✓ Quality validator executed (${notes.length} issues found).`, "success")
          notes.forEach((note: string) => addLog(`📋 Warning: ${note}`, "info"))
        } else if (data.stage === "narrative_completed") {
          updateStep("l4", "done")
          clearTimeout(timeoutTimer)
          if (data.result) {
            const itinerary = data.result as TravelItinerary
            itineraryRef.current = itinerary
            setCurrentItinerary(itinerary)
            addLog(
              `✓ Itinerary generation complete! Sắp xếp ${itinerary.total_pois_visited || "?"} địa điểm trong ${itinerary.num_days || "?"} ngày.`,
              "success",
            )

            // Trigger Push Notification
            Notifications.scheduleNotificationAsync({
              content: {
                title: "Hành trình đã sẵn sàng! ✈️",
                body: "AI đã tạo xong lịch trình tối ưu của bạn. Nhấn để xem ngay.",
                sound: true,
              },
              trigger: null,
            })
          }
        } else if (data.stage === "error") {
          setErrorMsg(data.message || "An error occurred")
          addLog(`✗ ${data.message}`, "error")
          updateStep("l2", "error")
          updateStep("l3", "error")
          updateStep("l4", "error")
        }
      },
      (error: any) => {
        clearTimeout(timeoutTimer)
        setErrorMsg(error?.message || "Connection lost")
        addLog("Connection error", "error")
        setSseStage("error")
      },
      () => {
        clearTimeout(timeoutTimer)
        if (itineraryRef.current) {
          // Navigate after short delay so user sees final state
          setTimeout(() => onItinerary(itineraryRef.current!), 600)
        } else {
          setErrorMsg("No itinerary received from server")
          addLog("Stream ended without itinerary data", "error")
          setSseStage("error")
        }
      },
    )

    return () => {
      cancelled = true
      clearTimeout(timeoutTimer)
      es.close()
    }
  }, [])

  return { steps, logs, errorMsg }
}
