"use client"

import { Map, Plus, RefreshCw, RotateCcw, Save, Calendar } from "lucide-react"
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
  onStartDateChange?: (date: string) => void
}

export function TripControlPanel({
  draft,
  status,
  selectedDay,
  showRouteLines,
  showCost,
  showCategories,
  onSelectedDayChange,
  onShowRouteLinesChange,
  onShowCostChange,
  onShowCategoriesChange,
  onSaveDraft,
  onAddPlace,
  onRebuild,
  onReset,
  onFitMap,
  onStartDateChange,
}: TripControlPanelProps) {
  const totals = draftTotals(draft)

  return (
    <aside className="flex h-full flex-col overflow-y-auto border-l border-orange-200 bg-white p-4">
      {/* Status Section */}
      <section className="rounded-2xl border border-orange-200 bg-white p-4">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-orange-400">Trạng thái hành trình</p>
        <div className="mt-3 flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full ${status === "live" ? "bg-success" : status === "building" ? "bg-warning" : status === "resolving" ? "bg-blue" : "bg-muted-2"}`} />
          <span className="text-sm font-black text-orange-950">
            {status === "live" ? "Đã sẵn sàng" : status === "empty" ? "Chưa có dữ liệu" : "Đang tính toán tối ưu..."}
          </span>
        </div>
        <div className="mt-4 grid gap-3 text-sm">
          <Metric label="Cập nhật cuối" value={draft ? formatDateTime(draft.updatedAt) : "--"} />
          <Metric label="Số địa điểm" value={`${totals.poiCount}`} />
          <Metric label="Dự chi ước tính" value={formatCurrency(totals.estimatedCost)} />
          <Metric label="Tổng số ngày" value={draft ? `${draft.days.length} ngày` : "--"} />
        </div>
      </section>

      {/* Date & Map Controls */}
      <section className="mt-4 rounded-2xl border border-orange-200 bg-white p-4">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-orange-400">Lập lịch & Bản đồ</p>
        
        <label className="mt-3.5 flex items-center gap-1.5 text-xs font-bold text-orange-950/60">
          <Calendar className="h-3.5 w-3.5 text-orange-500" /> Ngày khởi hành thực tế
        </label>
        <input 
          type="date" 
          value={draft?.startDate || ""} 
          onChange={(event) => onStartDateChange?.(event.target.value)} 
          className="mt-2 w-full rounded-xl border border-orange-200 bg-orange-50/50 px-3 py-2 text-sm text-orange-950 font-bold outline-none cursor-pointer hover:bg-orange-100/50 transition focus:border-orange-400"
        />

        <label className="mt-4 block text-xs font-bold text-orange-950/60">Xem theo ngày dừng chân</label>
        <select 
          value={selectedDay} 
          onChange={(event) => onSelectedDayChange(event.target.value === "all" ? "all" : Number(event.target.value))} 
          className="mt-2 w-full rounded-xl border border-orange-200 bg-orange-100 px-3 py-2 text-sm font-bold text-orange-950 outline-none cursor-pointer hover:bg-orange-200 transition"
        >
          <option value="all">Tất cả các ngày</option>
          {draft?.days.map((day) => (
            <option key={day.dayNumber} value={day.dayNumber}>
              Ngày {day.dayNumber}
            </option>
          ))}
        </select>

        <div className="mt-4 space-y-3">
          <Toggle label="Vẽ đường đi (Lộ trình)" checked={showRouteLines} onChange={onShowRouteLinesChange} />
          <Toggle label="Hiển thị chi phí điểm" checked={showCost} onChange={onShowCostChange} />
          <Toggle label="Hiển thị nhãn danh mục" checked={showCategories} onChange={onShowCategoriesChange} />
        </div>
        
        <button 
          type="button" 
          onClick={onFitMap} 
          disabled={!draft} 
          className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-orange-300 bg-orange-50 px-3 py-2 text-xs font-bold text-orange-950 hover:bg-orange-100 transition disabled:opacity-40"
        >
          <Map size={14} /> Căn chỉnh bản đồ vừa vặn
        </button>
      </section>

      {/* Actions */}
      <section className="mt-4 rounded-2xl border border-orange-200 bg-white p-4">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-orange-400">Công cụ lịch trình</p>
        <div className="mt-3 grid gap-2">
          <Action icon={<Save size={14} />} label="Lưu lịch trình nháp" onClick={onSaveDraft} disabled={!draft} />
          <Action icon={<Plus size={14} />} label="Thêm địa điểm thủ công" onClick={onAddPlace} disabled={!draft} />
          <Action icon={<RefreshCw size={14} />} label="Tính toán lại toàn bộ" onClick={onRebuild} disabled={!draft} />
          <Action icon={<RotateCcw size={14} />} label="Đặt lại từ đầu (Reset)" onClick={onReset} />
        </div>
      </section>


    </aside>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-orange-950/60">{label}</span>
      <span className="font-black text-orange-950">{value}</span>
    </div>
  )
}

function Action({ icon, label, onClick, disabled }: { icon: React.ReactNode; label: string; onClick: () => void; disabled?: boolean }) {
  return (
    <button 
      type="button" 
      onClick={onClick} 
      disabled={disabled} 
      className="inline-flex items-center gap-2 rounded-xl bg-orange-50 border border-orange-200 px-3 py-2 text-xs font-bold text-orange-950 transition hover:bg-orange-100 hover:text-orange-900 disabled:cursor-not-allowed disabled:opacity-40"
    >
      {icon}
      {label}
    </button>
  )
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <label className="flex items-center justify-between gap-3 text-xs font-bold text-orange-950/65 cursor-pointer">
      {label}
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-4 w-4 accent-travel cursor-pointer" />
    </label>
  )
}
