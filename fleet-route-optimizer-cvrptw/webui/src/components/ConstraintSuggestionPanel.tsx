"use client"

import { AlertCircle, Lightbulb } from "lucide-react"
import type { ValidationNote } from "@/types/trip"

interface ConstraintSuggestionPanelProps {
  notes: ValidationNote[]
  droppedPoiCount?: number
  budgetUsed?: number
  budgetMax?: number
  onSuggestFix: (fix: string) => void
}

export function ConstraintSuggestionPanel({
  notes,
  droppedPoiCount = 0,
  budgetUsed,
  budgetMax,
  onSuggestFix,
}: ConstraintSuggestionPanelProps) {
  const warnings = notes.filter((n) => n.severity === "warning" || n.severity === "error")
  if (!warnings.length && droppedPoiCount === 0) return null

  const chips: string[] = []
  if (droppedPoiCount > 0) chips.push(`Bớt ${droppedPoiCount} điểm tham quan`)
  if (budgetUsed != null && budgetMax != null && budgetUsed > budgetMax) {
    chips.push("Tăng ngân sách hoặc chọn điểm rẻ hơn")
  }
  for (const note of warnings) {
    if (note.suggestedFix) chips.push(note.suggestedFix)
  }
  if (!chips.length) chips.push("Giảm số ngày hoặc bớt POI trong ngày")

  return (
    <div className="relative z-20 mb-4 rounded-2xl border border-amber-300 bg-amber-50/95 p-4 shadow-lg">
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-black text-amber-950">Gợi ý chỉnh lịch trình</p>
          {warnings.length ? (
            <ul className="mt-2 space-y-1 text-xs text-amber-900/80">
              {warnings.map((note, index) => (
                <li key={`${note.message}-${index}`}>{note.message}</li>
              ))}
            </ul>
          ) : null}
          {droppedPoiCount > 0 ? (
            <p className="mt-2 text-xs text-amber-900/80">
              Hệ thống đã bỏ qua {droppedPoiCount} điểm do giới hạn thời gian hoặc ngân sách.
            </p>
          ) : null}
          <div className="mt-3 flex flex-wrap gap-2">
            {chips.map((chip) => (
              <button
                key={chip}
                type="button"
                onClick={() => onSuggestFix(chip)}
                className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-white px-3 py-1 text-[11px] font-bold text-amber-950 hover:bg-amber-100"
              >
                <Lightbulb className="h-3 w-3" />
                {chip}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
