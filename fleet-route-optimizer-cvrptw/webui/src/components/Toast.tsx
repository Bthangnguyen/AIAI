"use client"

import { CheckCircle2, RotateCcw, X } from "lucide-react"

interface ToastProps {
  message: string | null
  actionLabel?: string
  onAction?: () => void
  onClose: () => void
}

export function Toast({ message, actionLabel, onAction, onClose }: ToastProps) {
  if (!message) return null

  return (
    <div className="fixed bottom-5 left-1/2 z-[1100] w-[calc(100%-2rem)] max-w-xl -translate-x-1/2 rounded-full border border-orange-300 bg-white px-5 py-3 text-orange-950 shadow-2xl shadow-orange-950/10">
      <div className="flex items-center gap-3">
        <CheckCircle2 className="h-5 w-5 shrink-0 text-success" />
        <p className="min-w-0 flex-1 text-sm font-medium">{message}</p>
        {actionLabel && onAction ? (
          <button type="button" onClick={onAction} className="inline-flex items-center gap-1 rounded-full bg-white px-3 py-1.5 text-sm font-black text-orange-950 transition hover:bg-orange-600">
            <RotateCcw className="h-4 w-4" />
            {actionLabel}
          </button>
        ) : null}
        <button type="button" onClick={onClose} className="rounded-full p-1 text-orange-950/60 transition hover:bg-orange-100 hover:text-orange-950" aria-label="Đóng thông báo">
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}

