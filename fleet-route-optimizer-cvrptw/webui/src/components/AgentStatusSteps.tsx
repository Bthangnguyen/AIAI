import { Check, Loader2, Zap } from "lucide-react"

const steps = [
  "Đang phân tích yêu cầu",
  "Đang chọn địa điểm",
  "Đang chia theo ngày",
  "Đang hoàn thiện bản nháp",
]

export function AgentStatusSteps({ activeIndex }: { activeIndex: number }) {
  return (
    <div className="space-y-2 rounded-xl border border-orange-200 bg-white p-3">
      {steps.map((label, index) => {
        const done = index < activeIndex
        const active = index === activeIndex
        return (
          <div key={label} className={`flex items-center gap-2 text-xs ${done ? "text-success" : active ? "text-blue" : "text-orange-400"}`}>
            {done ? <Check className="h-3.5 w-3.5" /> : active ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
            <span>{label}</span>
          </div>
        )
      })}
    </div>
  )
}

