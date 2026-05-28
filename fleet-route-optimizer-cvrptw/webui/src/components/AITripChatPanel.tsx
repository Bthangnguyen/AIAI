"use client"

import { ChevronDown, ChevronRight, Loader2, Send, Sparkles } from "lucide-react"
import { useState } from "react"
import { draftTotals } from "@/lib/mockItineraryFallback"
import { formatCurrency } from "@/lib/format"
import type { BuildStatus, ItineraryDraft, TripIntent } from "@/types/trip"

export interface AIMessage {
  role: "user" | "assistant"
  content: string
}

interface AITripChatPanelProps {
  messages: AIMessage[]
  draft: ItineraryDraft | null
  intent?: TripIntent
  isRunning: boolean
  status: BuildStatus
  onSend: (message: string) => void
  onViewItinerary: () => void
  onAddPlace: () => void
  onSaveDraft: () => void
}

const quickActions = ["Thêm cafe muối", "Giảm chi phí", "Đi nhẹ hơn", "Thêm món chay"]


export function AITripChatPanel({ messages, draft, intent, isRunning, status, onSend, onViewItinerary, onAddPlace, onSaveDraft }: AITripChatPanelProps) {
  const [input, setInput] = useState("")

  const [expanded, setExpanded] = useState(true)
  const totals = draftTotals(draft)
  const showThinking = isRunning && status !== "building"

  function submit(text = input) {
    if (!text.trim() || isRunning) return
    onSend(text.trim())
    setInput("")
  }



  return (
    <div className="flex h-full min-h-0 flex-col bg-white">
      <div className="flex shrink-0 items-center justify-between border-b border-orange-200 px-4 py-3">
        <div>
          <p className="text-sm font-black text-orange-950">AI Trip Chat</p>
          <p className="text-[11px] text-orange-950/60">Chat / Analysis</p>
        </div>
        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em] ${showThinking ? "border-blue-200 bg-blue-50 text-blue-700" : "border-orange-200 bg-white text-orange-950/60"}`}>
          {showThinking ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
          Agent
        </span>
      </div>

      <div className="custom-scrollbar min-h-0 flex-1 space-y-6 overflow-y-auto p-4">
        {messages.length === 0 && !showThinking ? (
          <div className="flex h-full items-center justify-center text-orange-950/45">
            <div className="max-w-[280px] text-center">
              <div className="mx-auto mb-4 flex h-10 w-10 items-center justify-center rounded-2xl bg-orange-500 text-white">
                <Sparkles className="h-5 w-5" />
              </div>
              <p className="text-sm font-semibold text-orange-950">Bạn muốn xây lịch trình nào?</p>
              <p className="mt-2 text-xs leading-relaxed text-orange-950/45">Mô tả chuyến đi, TripFlow sẽ tạo bản nháp có thể chỉnh sửa.</p>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div key={`${message.role}-${index}`}>
              {message.role === "user" ? (
                <div className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl rounded-tr-sm border border-orange-300 bg-orange-100 px-4 py-2.5 text-[13px] leading-relaxed text-orange-950">{message.content}</div>
                </div>
              ) : (
                <div>
                  <div className="mb-2 flex items-center gap-2">
                    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-orange-500 text-white">
                      <Sparkles className="h-3 w-3 text-orange-950" />
                    </div>
                    <span className="flex items-center gap-1.5 text-sm font-bold text-orange-950">TripFlow <span className="rounded bg-blue/20 px-1.5 py-0.5 text-[10px] text-blue">Agent</span></span>
                  </div>
                  <div className="pl-8 text-[13px] leading-relaxed text-orange-950/75">{message.content}</div>
                </div>
              )}
            </div>
          ))
        )}

        {showThinking ? (
          <div>
            <div className="mb-2 flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-500 text-white shadow-sm shadow-blue-500/20">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              </div>
              <span className="flex items-center gap-1.5 text-sm font-bold text-orange-950">
                TripFlow <span className="rounded bg-blue/20 px-1.5 py-0.5 text-[10px] text-blue">đang chạy</span>
              </span>
            </div>
            <div className="pl-8 text-[13px] leading-relaxed text-orange-950/60">Đang xử lý yêu cầu của bạn...</div>
          </div>
        ) : null}


        {draft ? (
          <button type="button" onClick={() => setExpanded((value) => !value)} className="w-full rounded-xl border border-orange-300 bg-white text-left transition hover:bg-orange-50">
            <div className="flex items-center justify-between px-4 py-3">
              <div>
                <p className="text-sm font-semibold text-orange-950">Updated itinerary</p>
                <p className="mt-1 text-xs text-orange-950/45">{draft.days.length} ngày · {totals.poiCount} địa điểm · {formatCurrency(totals.estimatedCost)}</p>
              </div>
              {expanded ? <ChevronDown size={18} className="text-orange-950/45" /> : <ChevronRight size={18} className="text-orange-950/45" />}
            </div>
            {expanded ? (
              <div className="border-t border-orange-200 px-4 pb-4 pt-3">
                <div className="grid gap-2 text-xs text-orange-950/55">
                  <span>Destination: {draft.destination}</span>
                  <span>Days: {draft.days.length}</span>
                  <span>Tags: {draft.tags.join(", ") || "balanced"}</span>
                  <span>POI count: {totals.poiCount}</span>
                  <span>Budget: {intent?.budget ? formatCurrency(intent.budget) : "Chưa rõ"}</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" onClick={onViewItinerary} className="rounded-lg bg-white px-3 py-1.5 text-xs font-bold text-orange-950">View itinerary</button>
                  <button type="button" onClick={onAddPlace} className="rounded-lg bg-orange-100 px-3 py-1.5 text-xs font-bold text-white">Add place</button>
                  <button type="button" onClick={onSaveDraft} className="rounded-lg bg-orange-100 px-3 py-1.5 text-xs font-bold text-white">Save draft</button>
                </div>
              </div>
            ) : null}
          </button>
        ) : null}
      </div>

      <div className="shrink-0 border-t border-orange-200 p-3">
        <div className="mb-2 flex flex-wrap gap-2">
          {quickActions.map((action) => (
            <button key={action} type="button" onClick={() => submit(action)} className="rounded-full bg-white px-3 py-1 text-[11px] font-medium text-orange-950/60 transition hover:bg-orange-100 hover:text-orange-700">
              {action}
            </button>
          ))}
        </div>
        <div className="rounded-xl border border-orange-200 bg-white p-3 focus-within:border-orange-300">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault()
                submit()
              }
            }}
            placeholder="Nhắn TripFlow để chỉnh lịch trình..."
            className="h-12 w-full resize-none bg-transparent py-1 text-[13px] leading-relaxed text-orange-950 outline-none placeholder:text-orange-950/45"
            disabled={isRunning}
          />
          <div className="mt-2 flex items-center justify-end px-1">
            <button type="button" onClick={() => submit()} disabled={isRunning || !input.trim()} className={`rounded-lg p-2 ${input.trim() && !isRunning ? "bg-orange-500 text-white" : "bg-orange-100 text-orange-950/60-2"}`}>
              {isRunning ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

