import { Check, Loader2, Zap } from "lucide-react"

const steps = [
  "Đang phân tích nhu cầu",
  "Đang tạo workspace lịch trình",
  "Đang lọc địa điểm phù hợp",
  "Đang mở bản nháp",
]

export function BuildProgressSteps({ activeIndex }: { activeIndex: number }) {
  return (
    <div className="mx-auto mt-6 max-w-md space-y-3 text-left">
      {steps.map((label, index) => {
        const done = index < activeIndex
        const active = index === activeIndex
        return (
          <div key={label} className={`flex items-center gap-3 transition-opacity ${done || active ? "opacity-100" : "opacity-35"}`}>
            <div className="flex h-6 w-6 items-center justify-center">
              {done ? <Check className="h-4 w-4 text-success" /> : active ? <Loader2 className="h-4 w-4 animate-spin text-blue" /> : <Zap className="h-4 w-4 text-muted-2" />}
            </div>
            <span className={`text-sm ${done ? "text-success" : active ? "text-blue" : "text-muted-2"}`}>{label}</span>
          </div>
        )
      })}
    </div>
  )
}
