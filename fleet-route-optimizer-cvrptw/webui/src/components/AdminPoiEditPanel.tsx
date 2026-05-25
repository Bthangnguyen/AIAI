"use client"

import { Loader2 } from "lucide-react"
import { POI_CATEGORY_OPTIONS } from "@/lib/adminPois"
import type { AdminPoiRow } from "@/types/admin"

interface AdminPoiEditPanelProps {
  poi: AdminPoiRow
  category: string
  tagsText: string
  saving: boolean
  onCategoryChange: (value: string) => void
  onTagsTextChange: (value: string) => void
  onSave: () => void
  onClose: () => void
}

export function AdminPoiEditPanel({
  poi,
  category,
  tagsText,
  saving,
  onCategoryChange,
  onTagsTextChange,
  onSave,
  onClose,
}: AdminPoiEditPanelProps) {
  const categoryOptions = Array.from(new Set([...POI_CATEGORY_OPTIONS, poi.category, category].filter(Boolean)))

  return (
    <aside
      data-testid="admin-poi-edit-panel"
      className="absolute inset-y-0 right-0 z-20 flex w-full max-w-md flex-col border-l border-orange-200 bg-white shadow-2xl"
    >
      <div className="border-b border-orange-100 px-5 py-4">
        <p className="text-xs font-black uppercase tracking-[0.2em] text-orange-400">Chỉnh sửa POI</p>
        <h3 className="mt-1 text-lg font-black text-orange-950">{poi.name}</h3>
      </div>

      <div className="flex flex-1 flex-col gap-5 overflow-auto px-5 py-5">
        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wide text-orange-950/55">Category</span>
          <select
            value={category}
            onChange={(event) => onCategoryChange(event.target.value)}
            className="mt-2 w-full rounded-xl border border-orange-200 bg-white px-3 py-2.5 text-sm font-medium text-orange-950 outline-none ring-orange-300 focus:ring-2"
          >
            {categoryOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-xs font-bold uppercase tracking-wide text-orange-950/55">Tags</span>
          <input
            value={tagsText}
            onChange={(event) => onTagsTextChange(event.target.value)}
            placeholder="lịch sử, unesco, văn hóa"
            className="mt-2 w-full rounded-xl border border-orange-200 bg-white px-3 py-2.5 text-sm font-medium text-orange-950 outline-none ring-orange-300 focus:ring-2"
          />
          <p className="mt-2 text-xs text-orange-950/55">Phân tách bằng dấu phẩy.</p>
        </label>
      </div>

      <div className="flex gap-3 border-t border-orange-100 px-5 py-4">
        <button
          type="button"
          onClick={onClose}
          disabled={saving}
          className="flex-1 rounded-xl border border-orange-200 px-4 py-2.5 text-sm font-bold text-orange-950 transition hover:bg-orange-50 disabled:opacity-50"
        >
          Hủy
        </button>
        <button
          type="button"
          onClick={onSave}
          disabled={saving}
          className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-orange-500 px-4 py-2.5 text-sm font-black text-white transition hover:bg-orange-600 disabled:bg-orange-200"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Lưu
        </button>
      </div>
    </aside>
  )
}
