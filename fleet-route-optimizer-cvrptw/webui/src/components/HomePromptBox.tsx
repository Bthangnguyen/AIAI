"use client"

import { ArrowUp, Loader2, Sparkles } from "lucide-react"
import type { BuilderMode } from "@/types/trip"

interface HomePromptBoxProps {
  prompt: string
  mode: BuilderMode
  isLoading: boolean
  onPromptChange: (value: string) => void
  onModeChange: (mode: BuilderMode) => void
  onSubmit: () => void
  onExample: () => void
}

export function HomePromptBox({ prompt, mode, isLoading, onPromptChange, onModeChange, onSubmit, onExample }: HomePromptBoxProps) {
  return (
    <div className="mx-auto mt-10 w-full max-w-4xl">
      <div className="rounded-[32px] border border-orange-200 bg-white/88 p-5 shadow-2xl shadow-orange-950/15 backdrop-blur-xl">
        <textarea
          value={prompt}
          onChange={(event) => onPromptChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault()
              onSubmit()
            }
          }}
          placeholder="Tôi muốn đi Huế 3 ngày, ngân sách 1 triệu, thích Đại Nội, cafe muối và ăn chay..."
          rows={4}
          disabled={isLoading}
          className="mb-5 w-full resize-none rounded-2xl border border-orange-100 bg-orange-50/80 px-5 py-4 text-left text-lg font-semibold text-orange-950 outline-none transition placeholder:text-orange-950/40 focus:border-orange-400 focus:bg-white sm:text-xl"
        />

        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button type="button" onClick={onExample} disabled={isLoading} className="flex h-10 w-10 items-center justify-center rounded-full bg-orange-100 text-orange-600 transition hover:bg-orange-500 hover:text-white" title="Try an example prompt">
              <Sparkles className="h-4 w-4" />
            </button>
            <div className="flex items-center rounded-full bg-orange-100 p-1">
              {(["plan", "build"] as BuilderMode[]).map((item) => (
                <button key={item} type="button" onClick={() => onModeChange(item)} disabled={isLoading} className={`rounded-full px-3 py-1.5 text-xs font-black transition-colors ${mode === item ? (item === "build" ? "bg-orange-500 text-white shadow-lg shadow-orange-500/20" : "bg-white text-orange-700") : "text-orange-950/55 hover:text-orange-700"}`}>
                  {item === "plan" ? "Plan" : "Build"}
                </button>
              ))}
            </div>
          </div>

          <button type="button" onClick={onSubmit} disabled={!prompt.trim() || isLoading} className="flex h-11 w-11 items-center justify-center rounded-full bg-orange-500 text-white shadow-lg shadow-orange-500/25 transition hover:bg-orange-600 disabled:bg-orange-100 disabled:text-orange-300" title="Build trip">
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </div>
  )
}

