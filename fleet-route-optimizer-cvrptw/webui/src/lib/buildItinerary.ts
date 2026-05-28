import { mapLayer4ResultToDraft, cachePoisFromResponse } from "@/lib/api"
import { streamTripPlan, type StreamEvent } from "@/lib/streamApi"
import type { ItineraryDraft, TripIntent } from "@/types/trip"

const STAGE_LABELS: Record<string, string> = {
  intent_extraction_started: "Đang phân tích ý định...",
  intent_extraction_completed: "Đã trích xuất thông tin chuyến đi.",
  poi_search_started: "Đang tìm điểm tham quan...",
  poi_search_completed: "Đã chọn POI phù hợp.",
  optimization_started: "Đang tối ưu lịch trình (OR-Tools)...",
  optimization_completed: "Tối ưu hoàn tất.",
  validation_completed: "Đang kiểm tra chất lượng lịch trình...",
  narrative_completed: "Hoàn tất!",
  // Backend step names
  l2_done: "Đã trích xuất thông tin chuyến đi.",
  l3_done: "Đã chọn POI phù hợp.",
}

export interface StreamBuildCallbacks {
  onStep?: (stepIndex: number, detail: string) => void
  onValidationNotes?: (notes: string[]) => void
}

function stageToStepIndex(stage: string): number {
  if (stage === "l2_done" || stage.startsWith("intent")) return 0
  if (stage === "l3_done" || stage.startsWith("poi")) return 1
  if (stage.startsWith("optimization")) return 2
  if (stage === "validation_completed" || stage === "narrative_completed") return 3
  return 1
}

export function buildItineraryViaStream(
  rawPrompt: string,
  intent: TripIntent,
  callbacks: StreamBuildCallbacks = {},
): Promise<ItineraryDraft> {
  return new Promise((resolve, reject) => {
    let settled = false
    const timeout = window.setTimeout(() => {
      if (!settled) {
        settled = true
        reject(new Error("Yêu cầu quá lâu — thử lại"))
      }
    }, 120_000)

    const finish = (fn: () => void) => {
      if (settled) return
      settled = true
      window.clearTimeout(timeout)
      fn()
    }

    streamTripPlan({
      userPrompt: rawPrompt,
      numDays: intent.days,
      budget: intent.budget,
      destination: intent.destination,
      interests: intent.interests,
      onEvent: (event: StreamEvent) => {
        // Backend sends "step" field, frontend expects "stage"
        const stage = event.stage ?? event.step ?? ""
        const label = STAGE_LABELS[stage] ?? stage
        if (stage) {
          callbacks.onStep?.(stageToStepIndex(stage), label)
        }

        if (stage === "l3_done" && Array.isArray(event.pois)) {
          cachePoisFromResponse(event.pois as any[])
        }

        if (stage === "validation_completed" && event.validation_notes) {
          callbacks.onValidationNotes?.(event.validation_notes)
        }

        // Handle error events from backend
        if (stage === "error" || event.error_code) {
          finish(() => reject(new Error(event.message ?? "Không thể tạo lịch trình")))
          return
        }

        // Handle final result: backend sends it as a top-level object with "days" array
        // Format: {"status": "success", "num_days": 3, "days": [...], ...}
        if (event.days && Array.isArray(event.days)) {
          callbacks.onStep?.(3, "Hoàn tất!")
          const result = event as unknown as Parameters<typeof mapLayer4ResultToDraft>[0]
          const destination = intent.destination ?? "Huế"
          finish(() => resolve(mapLayer4ResultToDraft(result, intent, destination)))
          return
        }

        // Legacy format: event.stage === "narrative_completed" with event.result
        if (stage === "narrative_completed" && event.result) {
          const result = event.result as unknown as Parameters<typeof mapLayer4ResultToDraft>[0]
          const destination = intent.destination ?? "Huế"
          finish(() => resolve(mapLayer4ResultToDraft(result, intent, destination)))
        }
      },
      onError: (error) => finish(() => reject(error)),
      onDone: () => finish(() => reject(new Error("Luồng SSE kết thúc mà chưa có lịch trình"))),
    })
  })
}
