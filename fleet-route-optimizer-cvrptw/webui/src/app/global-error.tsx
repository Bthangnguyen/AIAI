"use client"

import { AlertTriangle, RotateCcw } from "lucide-react"

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="vi">
      <body className="bg-orange-50 text-orange-950">
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-center">
          <AlertTriangle className="h-12 w-12 text-red-500" />
          <div>
            <h1 className="text-2xl font-black">Lỗi hệ thống</h1>
            <p className="mt-2 max-w-lg text-sm opacity-70">{error.message}</p>
          </div>
          <button
            type="button"
            onClick={reset}
            className="inline-flex items-center gap-2 rounded-full bg-orange-600 px-5 py-2.5 text-sm font-black text-white"
          >
            <RotateCcw className="h-4 w-4" />
            Thử lại
          </button>
        </div>
      </body>
    </html>
  )
}
