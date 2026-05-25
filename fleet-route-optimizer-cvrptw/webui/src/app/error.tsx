"use client"

import { AlertTriangle, RotateCcw } from "lucide-react"

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-orange-50 p-8 text-center">
      <AlertTriangle className="h-12 w-12 text-red-500" />
      <div>
        <h1 className="text-2xl font-black text-orange-950">Không thể tải trang</h1>
        <p className="mt-2 max-w-lg text-sm text-orange-950/70">{error.message}</p>
      </div>
      <button
        type="button"
        onClick={reset}
        className="inline-flex items-center gap-2 rounded-full bg-orange-600 px-5 py-2.5 text-sm font-black text-white hover:bg-orange-700"
      >
        <RotateCcw className="h-4 w-4" />
        Tải lại
      </button>
    </div>
  )
}
