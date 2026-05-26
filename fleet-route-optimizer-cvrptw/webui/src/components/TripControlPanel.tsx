"use client"

import { Map, Plus, RefreshCw, RotateCcw, Save, Smartphone } from "lucide-react"
import { draftTotals } from "@/lib/mockItineraryFallback"
import { formatCurrency, formatDateTime } from "@/lib/format"
import type { BuildStatus, ItineraryDraft } from "@/types/trip"

interface TripControlPanelProps {
  draft: ItineraryDraft | null
  status: BuildStatus
  selectedDay: number | "all"
  showRouteLines: boolean
  showCost: boolean
  showCategories: boolean
  onSelectedDayChange: (day: number | "all") => void
  onShowRouteLinesChange: (value: boolean) => void
  onShowCostChange: (value: boolean) => void
  onShowCategoriesChange: (value: boolean) => void
  onSaveDraft: () => void
  onAddPlace: () => void
  onRebuild: () => void
  onReset: () => void
  onFitMap: () => void
}

export function TripControlPanel({ draft, status, selectedDay, showRouteLines, showCost, showCategories, onSelectedDayChange, onShowRouteLinesChange, onShowCostChange, onShowCategoriesChange, onSaveDraft, onAddPlace, onRebuild, onReset, onFitMap }: TripControlPanelProps) {
  const totals = draftTotals(draft)

  return (
    <aside className="flex h-full flex-col overflow-y-auto border-l border-orange-200 bg-white p-4">
      <section className="rounded-2xl border border-orange-200 bg-white p-4">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-orange-400">Trip Status</p>
        <div className="mt-3 flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full ${status === "live" ? "bg-success" : status === "building" ? "bg-warning" : status === "resolving" ? "bg-blue" : "bg-muted-2"}`} />
          <span className="text-sm font-black text-orange-950">{status === "live" ? "Draft" : status === "empty" ? "Empty" : "Building"}</span>
        </div>
        <div className="mt-4 grid gap-3 text-sm">
          <Metric label="Last updated" value={draft ? formatDateTime(draft.updatedAt) : "--"} />
          <Metric label="POI count" value={`${totals.poiCount}`} />
          <Metric label="Estimated cost" value={formatCurrency(totals.estimatedCost)} />
          <Metric label="Days" value={draft ? `${draft.days.length}` : "--"} />
        </div>
      </section>

      <section className="mt-4 rounded-2xl border border-orange-200 bg-white p-4">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-orange-400">Actions</p>
        <div className="mt-3 grid gap-2">
          <Action icon={<Save size={15} />} label="Save Draft" onClick={onSaveDraft} disabled={!draft} />
          <Action icon={<Plus size={15} />} label="Add Place" onClick={onAddPlace} disabled={!draft} />
          <Action icon={<RefreshCw size={15} />} label="Rebuild Itinerary" onClick={onRebuild} disabled={!draft} />
          <Action icon={<RotateCcw size={15} />} label="Reset" onClick={onReset} />
        </div>
      </section>

      <section className="mt-4 rounded-2xl border border-orange-200 bg-white p-4">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-orange-400">Map Controls</p>
        <label className="mt-3 block text-xs font-bold text-orange-950/60">View</label>
        <select value={selectedDay} onChange={(event) => onSelectedDayChange(event.target.value === "all" ? "all" : Number(event.target.value))} className="mt-2 w-full rounded-xl border border-orange-200 bg-orange-100 px-3 py-2 text-sm text-orange-950 outline-none">
          <option value="all">All days</option>
          {draft?.days.map((day) => <option key={day.dayNumber} value={day.dayNumber}>Day {day.dayNumber}</option>)}
        </select>
        <div className="mt-4 space-y-3">
          <Toggle label="Show route line" checked={showRouteLines} onChange={onShowRouteLinesChange} />
          <Toggle label="Show estimated cost" checked={showCost} onChange={onShowCostChange} />
          <Toggle label="Show categories" checked={showCategories} onChange={onShowCategoriesChange} />
        </div>
        <button type="button" onClick={onFitMap} disabled={!draft} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-orange-300 bg-orange-100 px-3 py-2 text-sm font-bold text-orange-950 disabled:opacity-40">
          <Map size={15} /> Fit map to itinerary
        </button>
      </section>

      <section className="mt-4 rounded-2xl border border-travel/30 bg-travel/10 p-4">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm font-black text-orange-950">Active Trip Mode</p>
          <span className="rounded-full bg-travel/20 px-2 py-1 text-[10px] font-black text-travel">Sắp ra mắt</span>
        </div>
        <p className="mt-2 text-xs leading-5 text-orange-950/60">Tính năng này sẽ dùng GPS trên app mobile để tối ưu lại phần còn lại của ngày khi người dùng bỏ qua một điểm đến.</p>
        <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] font-bold text-orange-950/60">
          {['Next Location', 'Skip Stop', 'GPS Reroute', 'Reroute Current Day'].map((item) => <button key={item} disabled className="rounded-xl border border-orange-200 bg-white/70 px-2 py-2 opacity-60"><Smartphone className="mx-auto mb-1 h-3.5 w-3.5" />{item}</button>)}
        </div>
      </section>
    </aside>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="flex items-center justify-between gap-3"><span className="text-orange-950/60">{label}</span><span className="font-black text-orange-950">{value}</span></div>
}

function Action({ icon, label, onClick, disabled }: { icon: React.ReactNode; label: string; onClick: () => void; disabled?: boolean }) {
  return <button type="button" onClick={onClick} disabled={disabled} className="inline-flex items-center gap-2 rounded-xl bg-orange-100 px-3 py-2 text-sm font-bold text-orange-950 transition hover:bg-border-strong disabled:cursor-not-allowed disabled:opacity-40">{icon}{label}</button>
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <label className="flex items-center justify-between gap-3 text-sm text-orange-950/60">
      {label}
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-4 w-4 accent-travel" />
    </label>
  )
}

