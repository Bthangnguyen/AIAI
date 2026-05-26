"use client"

import { Check, Loader2, Zap, Brain, Database, Cpu, MapPin } from "lucide-react"

export interface AgentStep {
  label: string
  detail?: string
  icon: any
}

const defaultSteps: AgentStep[] = [
  { label: "Phân tích ý định bằng AI", icon: Brain, detail: "" },
  { label: "Tìm kiếm địa điểm phù hợp", icon: Database, detail: "" },
  { label: "Tối ưu hóa bằng OR-Tools", icon: Cpu, detail: "" },
  { label: "Hoàn thiện lịch trình", icon: MapPin, detail: "" },
]

interface AgentStatusStepsProps {
  activeIndex: number
  steps?: AgentStep[]
  details?: Record<number, string>
}

export function AgentStatusSteps({ activeIndex, steps, details }: AgentStatusStepsProps) {
  const displaySteps = steps || defaultSteps
  return (
    <div className="space-y-1 rounded-2xl border border-orange-200 bg-gradient-to-b from-white to-orange-50/50 p-4">
      <p className="mb-2 text-[10px] font-black uppercase tracking-[0.2em] text-orange-400">Processing Pipeline</p>
      {displaySteps.map((step, index) => {
        const done = index < activeIndex
        const active = index === activeIndex
        const Icon = step.icon
        const detail = details?.[index] || step.detail
        return (
          <div key={step.label} className={`flex items-start gap-3 rounded-xl px-3 py-2 transition-all duration-300 ${active ? "bg-blue-50 ring-1 ring-blue-200" : done ? "bg-green-50/50" : ""}`}>
            <div className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg ${done ? "bg-green-500 text-white" : active ? "bg-blue-500 text-white" : "bg-orange-100 text-orange-400"}`}>
              {done ? <Check className="h-3.5 w-3.5" /> : active ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Icon className="h-3.5 w-3.5" />}
            </div>
            <div className="min-w-0 flex-1">
              <span className={`text-xs font-bold ${done ? "text-green-700" : active ? "text-blue-700" : "text-orange-950/40"}`}>{step.label}</span>
              {detail && (done || active) ? (
                <p className={`mt-0.5 text-[11px] ${active ? "text-blue-600" : "text-green-600"}`}>{detail}</p>
              ) : null}
            </div>
            {done ? <span className="mt-0.5 text-[10px] font-bold text-green-500">✓</span> : null}
          </div>
        )
      })}
    </div>
  )
}
