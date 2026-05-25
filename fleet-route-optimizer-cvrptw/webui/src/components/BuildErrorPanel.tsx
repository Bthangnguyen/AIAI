"use client"

import { AlertTriangle, RotateCcw } from "lucide-react"

interface BuildErrorPanelProps {
  message?: string
  onRetry: () => void
}

export function BuildErrorPanel({ message, onRetry }: BuildErrorPanelProps) {
  return (
    <div className="relative z-20 flex min-h-[320px] flex-col items-center justify-center rounded-3xl border border-red-200 bg-red-50/90 p-10 text-center">
      <AlertTriangle className="h-10 w-10 text-red-500" />
      <p className="mt-4 text-lg font-black text-red-950">Không tạo được lịch trình</p>
      <p className="mt-2 max-w-md text-sm text-red-900/70">
        {message ?? "Backend không phản hồi hoặc lịch trình không khả thi. Kiểm tra Gateway (:8001) và thử lại."}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-5 inline-flex items-center gap-2 rounded-full bg-red-600 px-5 py-2.5 text-sm font-black text-white hover:bg-red-700"
      >
        <RotateCcw className="h-4 w-4" />
        Thử lại
      </button>
    </div>
  )
}
