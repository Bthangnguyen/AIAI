"use client"

import { useEffect, useRef, useState } from "react"
import { ChevronDown, ChevronLeft, Download, FolderOpen, Lock, MoreHorizontal, RefreshCw, RotateCcw, Save, Share2, Smartphone } from "lucide-react"
import type { ItineraryDraft, PreviewMode } from "@/types/trip"

interface TripToolbarProps {
  draft: ItineraryDraft | null
  viewMode: PreviewMode
  onViewModeChange: (mode: PreviewMode) => void
  onBack: () => void
  onSave: () => void
  onReset: () => void
  onRebuild: () => void
  onSavedTrips: () => void
  onMobilePhase: () => void
}

export function TripToolbar({ draft, viewMode, onViewModeChange, onBack, onSave, onReset, onRebuild, onSavedTrips, onMobilePhase }: TripToolbarProps) {
  const title = draft ? `${draft.destination} ${draft.days.length} ngày` : "Untitled Trip"
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    function handlePointerDown(event: PointerEvent) {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false)
    }
    window.addEventListener("pointerdown", handlePointerDown)
    return () => window.removeEventListener("pointerdown", handlePointerDown)
  }, [menuOpen])

  return (
    <div className="relative flex h-14 items-center border-b border-orange-200 bg-white px-4 text-orange-950 shadow-sm">
      <div className="flex items-center gap-3">
        <button type="button" onClick={onBack} className="rounded-lg p-1.5 text-orange-950/60 transition hover:bg-orange-100 hover:text-orange-700" aria-label="Back">
          <ChevronLeft size={20} />
        </button>
        <button type="button" className="flex max-w-[220px] items-center gap-2 rounded-lg px-2.5 py-1.5 transition hover:bg-orange-50">
          <span className="truncate text-[15px] font-black text-orange-950">{title}</span>
          <Lock size={12} className="shrink-0 text-orange-500" />
          <ChevronDown size={14} className="shrink-0 text-orange-500" />
        </button>
      </div>

      <div className="absolute left-1/2 top-1/2 hidden -translate-x-1/2 -translate-y-1/2 md:block">
        <div className="flex items-center rounded-xl border border-orange-200 bg-orange-50 p-1">
          {(["timeline", "map", "split"] as PreviewMode[]).map((mode) => (
            <button key={mode} type="button" onClick={() => onViewModeChange(mode)} className={`rounded-lg px-4 py-1.5 text-sm font-black transition ${viewMode === mode ? "bg-white text-orange-700 shadow-sm" : "text-orange-950/55 hover:text-orange-700"}`}>
              {mode === "timeline" ? "Preview" : mode === "map" ? "Map" : "Split"}
            </button>
          ))}
        </div>
      </div>

      <div className="ml-auto flex items-center gap-2">
        <button type="button" onClick={onSave} className="hidden items-center gap-2 rounded-lg border border-orange-300 px-4 py-2 text-sm font-black text-orange-700 transition hover:bg-orange-50 sm:flex">
          <Save size={14} /> Lưu nháp
        </button>
        <button type="button" disabled className="hidden items-center gap-2 rounded-lg bg-orange-500 px-4 py-2 text-sm font-black text-white opacity-70 sm:flex">
          <Share2 size={14} /> Chia sẻ
        </button>
        <div ref={menuRef} className="relative">
          <button type="button" onClick={() => setMenuOpen((value) => !value)} className="rounded-lg p-2 text-orange-950/60 transition hover:bg-orange-100 hover:text-orange-700" aria-label="More actions" aria-expanded={menuOpen}>
            <MoreHorizontal size={20} />
          </button>
          {menuOpen ? (
            <div className="absolute right-0 top-full z-50 mt-2 w-60 rounded-xl border border-orange-200 bg-white py-1.5 shadow-2xl shadow-orange-950/10">
              <button type="button" disabled={!draft} className="flex w-full items-center gap-3 px-4 py-2.5 text-sm font-bold text-orange-950/65 hover:bg-orange-50 disabled:cursor-not-allowed disabled:opacity-40" onClick={() => { setMenuOpen(false); onRebuild() }}><RefreshCw size={16} /> Tạo option khác</button>
              <button type="button" className="flex w-full items-center gap-3 px-4 py-2.5 text-sm font-bold text-orange-950/65 hover:bg-orange-50" onClick={() => { setMenuOpen(false); console.log(JSON.stringify(draft, null, 2)) }}><Download size={16} /> Export JSON</button>
              <button type="button" className="flex w-full items-center gap-3 px-4 py-2.5 text-sm font-bold text-orange-950/65 hover:bg-orange-50" onClick={() => { setMenuOpen(false); onReset() }}><RotateCcw size={16} /> Reset Draft</button>
              <button type="button" className="flex w-full items-center gap-3 px-4 py-2.5 text-sm font-bold text-orange-950/65 hover:bg-orange-50" onClick={() => { setMenuOpen(false); onSavedTrips() }}><FolderOpen size={16} /> Saved Trips</button>
              <button type="button" className="flex w-full items-center gap-3 px-4 py-2.5 text-sm font-bold text-orange-950/65 hover:bg-orange-50" onClick={() => { setMenuOpen(false); onMobilePhase() }}><Smartphone size={16} /> Mobile Phase</button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
