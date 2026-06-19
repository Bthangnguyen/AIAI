import { TimelineDayCard } from "@/components/TimelineDayCard"
import { draftTotals } from "@/lib/mockItineraryFallback"
import { formatCurrency } from "@/lib/format"
import type { ItineraryDraft } from "@/types/trip"
import type { MoveDirection } from "@/lib/reorderDayItems"
import { getPoi } from "@/lib/mockItineraryFallback"
import { POI_CACHE } from "@/lib/api"


interface ItineraryArtifactProps {
  draft: ItineraryDraft
  selectedPoiId: string | null
  onSelectPoi: (poiId: string) => void
  onHoverPoi: (poiId: string | null) => void
  onSaveDraft: () => void
  onAddPlace: (dayNumber: number) => void
  onRemovePlace: (dayNumber: number, itemId: string) => void
  onMovePlace: (dayNumber: number, itemId: string, direction: MoveDirection) => void
  onReorderPlace?: (dayNumber: number, draggedItemId: string, targetItemId: string) => void
  onApplyManualOrder?: (dayNumber: number) => void
  onOptimizeDay: (dayNumber: number) => void
}

export function ItineraryArtifact({ draft, selectedPoiId, onSelectPoi, onHoverPoi, onSaveDraft, onAddPlace, onRemovePlace, onMovePlace, onReorderPlace, onApplyManualOrder, onOptimizeDay }: ItineraryArtifactProps) {
  const totals = draftTotals(draft)
  const enoughInfo = Boolean(draft.intent.destination && draft.intent.days && draft.intent.budget)

  return (
    <div className="mx-auto w-full max-w-4xl rounded-[28px] border border-orange-200 bg-white p-4 shadow-2xl shadow-orange-950/10">
      <header className="flex flex-col gap-3 border-b border-orange-200 pb-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-black text-orange-950">Lịch trình nháp</h2>
            <span className="rounded-full bg-travel/15 px-3 py-1 text-xs font-black text-travel">Draft</span>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-y-1.5 gap-x-3 text-xs font-bold text-orange-950/60">
            <span className="inline-flex items-center gap-1">📍 {draft.destination}</span>
            <span>·</span>
            <span>📅 {draft.days.length} ngày</span>
            <span>·</span>
            <span>💰 Ngân sách: {draft.budget ? formatCurrency(draft.budget) : "Chưa rõ"}</span>
            <span>·</span>
            <span className="rounded-md bg-orange-100 px-2 py-0.5 text-[10px] text-orange-800 font-extrabold uppercase tracking-wider">{draft.tags.join(", ") || "balanced"}</span>
            <span>·</span>
            <span className={`rounded-md px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider ${enoughInfo ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>
              {enoughInfo ? "Đủ thông tin" : "Thiếu thông tin"}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={onSaveDraft} className="rounded-lg bg-orange-500 px-3 py-2 text-xs font-black text-white">Lưu nháp</button>
        </div>
      </header>

      <div className="my-4 grid gap-4 md:grid-cols-2">
        {draft.costSummary ? <CostBreakdown summary={draft.costSummary} lodgingPlan={draft.lodgingPlan} /> : null}
        {draft.optimizationStats ? <OptimizationStatsCard stats={draft.optimizationStats} draft={draft} /> : null}
      </div>

      <div className="space-y-4">
        {draft.days.map((day) => (
          <TimelineDayCard
            key={day.dayNumber}
            day={day}
            selectedPoiId={selectedPoiId}
            startDate={draft.startDate}
            isManualOrder={draft.manualDayNumbers?.includes(day.dayNumber)}
            onSelectPoi={onSelectPoi}
            onHoverPoi={onHoverPoi}
            onRemovePlace={onRemovePlace}
            onMovePlace={onMovePlace}
            onReorderPlace={onReorderPlace}
            onApplyManualOrder={onApplyManualOrder}
            onAddPlace={onAddPlace}
            onOptimizeDay={onOptimizeDay}
          />
        ))}
      </div>
    </div>
  )
}

function CostBreakdown({ summary, lodgingPlan }: { summary: Record<string, any>; lodgingPlan?: Record<string, any> }) {
  const partySize = Number(summary.party_size || 1)
  const perPersonCost = Number(summary.per_person_cost || 0)
  const groupTotalCost = Number(summary.group_total_cost || summary.estimated_total_cost || 0)
  const budgetPerPerson = Number(summary.budget_per_person || 0)
  const isGroupTrip = partySize > 1
  const rows = [
    { label: "Vé tham quan", value: Number(summary.poi_ticket_cost || 0), bg: "bg-cyan-500", text: "text-cyan-600" },
    { label: "Ăn uống/cafe", value: Number(summary.food_and_drink_cost || 0), bg: "bg-amber-500", text: "text-amber-600" },
    { label: "Di chuyển", value: Number(summary.local_transport_cost || 0), bg: "bg-indigo-500", text: "text-indigo-600" },
    { label: "Chỗ nghỉ", value: Number(summary.lodging_cost || 0), bg: "bg-emerald-500", text: "text-emerald-600" },
    { label: "Dự phòng", value: Number(summary.misc_buffer || 0), bg: "bg-purple-500", text: "text-purple-600" },
  ]
  const totalSum = rows.reduce((sum, r) => sum + r.value, 0) || 1
  const remaining = typeof summary.budget_remaining === "number" ? summary.budget_remaining : null

  return (
    <section className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">Chi phí dự kiến</p>
        {remaining !== null && (
          <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${remaining < 0 ? "bg-red-100 text-red-750" : "bg-green-100 text-green-705"}`}>
            {remaining < 0 ? "Vượt ngân sách" : "Trong ngân sách"}
          </span>
        )}
      </div>

      <div className="mt-3">
        <span className="text-2xl font-black text-orange-950">
          {isGroupTrip && perPersonCost > 0 ? `${formatCurrency(perPersonCost)}/người` : formatCurrency(groupTotalCost)}
        </span>
      </div>

      {isGroupTrip && (
        <p className="mt-1 text-[11px] font-bold text-slate-500">
          Tổng nhóm: {formatCurrency(groupTotalCost)} ({partySize} người)
        </p>
      )}

      {remaining !== null && (
        <p className={`mt-1 text-xs font-semibold ${remaining < 0 ? "text-red-650" : "text-green-700"}`}>
          {remaining < 0 ? "Vượt " : "Tiết kiệm "}
          {formatCurrency(Math.abs(remaining))}
        </p>
      )}

      {lodgingPlan && (
        <div className="mt-3 rounded-xl bg-orange-50/50 border border-orange-100 p-2.5 text-xs text-orange-900 font-bold">
          🏠 Chỗ nghỉ: Nghỉ {lodgingPlan.nights || 0} đêm tại {lodgingPlan.name || "chỗ nghỉ"}
          {Number(lodgingPlan.nightly_rate || 0) > 0 ? ` (${formatCurrency(Number(lodgingPlan.nightly_rate))}/đêm)` : " (đã có sẵn)"}
        </div>
      )}

      {/* Stacked Percentage bar */}
      <div className="mt-4 h-3.5 w-full overflow-hidden rounded-full bg-slate-100 flex">
        {rows.map((row) => {
          const percentage = (row.value / totalSum) * 100
          if (percentage <= 0) return null
          return (
            <div 
              key={row.label}
              className={`${row.bg} h-full transition-all duration-500`}
              style={{ width: `${percentage}%` }}
              title={`${row.label}: ${percentage.toFixed(1)}%`}
            />
          )
        })}
      </div>

      {/* Detailed breakdown list with individual progress bars */}
      <div className="mt-4 space-y-3 flex-1 flex flex-col justify-center">
        {rows.map((row) => {
          const percentage = (row.value / totalSum) * 105 ? (row.value / totalSum) * 100 : 0
          return (
            <div key={row.label}>
              <div className="flex items-center justify-between text-xs font-bold text-slate-600">
                <div className="flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${row.bg}`} />
                  <span>{row.label}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-[10px] ${row.text}`}>{percentage.toFixed(1)}%</span>
                  <span className="text-orange-950 font-black">{formatCurrency(row.value)}</span>
                </div>
              </div>
              <div className="mt-1 h-1.5 w-full rounded-full bg-slate-50 overflow-hidden">
                <div 
                  className={`h-full ${row.bg} rounded-full`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function formatMinutesShort(minutes: number): string {
  if (!minutes || minutes <= 0) return "--"
  const hours = Math.floor(minutes / 60)
  const mins = Math.round(minutes % 60)
  return `${hours}h${mins.toString().padStart(2, "0")}`
}

function parseTimeToMinutes(value: string): number {
  const match = value.match(/^(\d{1,2}):(\d{2})$/)
  if (!match) return 0
  return Number(match[1]) * 60 + Number(match[2])
}

function deriveAverageDayMinutes(draft?: ItineraryDraft): number {
  if (!draft?.days.length) return 0
  const spans = draft.days.map((day) => {
    if (!day.items.length) return 0
    const first = Math.min(...day.items.map((item) => parseTimeToMinutes(item.time)))
    const last = Math.max(...day.items.map((item) => {
      const poi = getPoi(item.poiId) ?? POI_CACHE.get(item.poiId)
      return parseTimeToMinutes(item.time) + (poi?.estimatedDurationMinutes ?? 0)
    }))
    return Math.max(0, last - first)
  })
  return Math.round(spans.reduce((sum, value) => sum + value, 0) / Math.max(1, spans.length))
}

function deriveAverageTravelMinutes(draft?: ItineraryDraft): number {
  if (!draft?.days.length) return 0
  const totalTravel = draft.days.reduce((sum, day) => {
    return sum + day.items.reduce((daySum, item) => {
      if (item.travel_time_from_prev_min !== undefined) {
        return daySum + item.travel_time_from_prev_min
      }
      const match = item.note.match(/di chuyển tiếp\s+(\d+)\s+phút/i)
      return daySum + (match ? Number(match[1]) : 0)
    }, 0)
  }, 0)
  return Math.round(totalTravel / Math.max(1, draft.days.length))
}

function OptimizationStatsCard({ stats, draft }: { stats: any; draft: ItineraryDraft }) {
  const avgTotalTime = stats.avgTotalTimePerVehicleMin || deriveAverageDayMinutes(draft)
  const avgTravelTime = stats.avgTravelTimePerVehicleMin || deriveAverageTravelMinutes(draft)

  return (
    <section className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">Tối ưu hóa hành trình</p>
        <span className="rounded-full bg-green-105 px-2.5 py-0.5 text-[10px] font-bold text-green-700">
          Tối ưu {stats.saturationPercent}%
        </span>
      </div>

      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="text-2xl font-black text-orange-950">
          {stats.totalDistanceKm?.toFixed(1)} km
        </span>
        <span className="text-xs font-bold text-slate-400">tổng di chuyển</span>
      </div>

      <p className="mt-1 text-xs font-bold text-slate-500">
        Phục vụ: {stats.customersServed || 0}/{stats.totalPoisAvailable || 0} địa điểm
      </p>

      <div className="mt-3 rounded-xl bg-green-50/50 border border-green-100 p-2.5 text-xs text-green-800 font-bold flex items-center justify-between">
        <span>⚡ Động cơ OR-Tools: Tối ưu 100%</span>
        <span>⏱️ Solver: {stats.solverTimeSeconds || 0.1}s</span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 flex-1 items-center">
        <div className="rounded-xl border border-slate-100 p-3 bg-slate-50/30">
          <p className="text-[10px] font-black uppercase tracking-wider text-slate-400">Thời gian đi/ngày</p>
          <p className="mt-1 text-base font-black text-orange-950">{formatMinutesShort(avgTotalTime)}</p>
          <p className="mt-0.5 text-[9px] font-bold text-slate-400">Trung bình các ngày</p>
        </div>
        <div className="rounded-xl border border-slate-100 p-3 bg-slate-50/30">
          <p className="text-[10px] font-black uppercase tracking-wider text-slate-400">Thời gian di chuyển</p>
          <p className="mt-1 text-base font-black text-orange-950">~{formatMinutesShort(avgTravelTime)}</p>
          <p className="mt-0.5 text-[9px] font-bold text-slate-400">Trung bình di chuyển</p>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-[11px] font-bold text-slate-500">
        <span>Bão hòa: {stats.saturationPercent}%</span>
        <span>Số ngày: {stats.vehiclesUsed}/{stats.totalVehicles}</span>
      </div>
    </section>
  )
}

