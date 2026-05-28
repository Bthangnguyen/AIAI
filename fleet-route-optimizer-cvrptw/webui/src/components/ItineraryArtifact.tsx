import { Smartphone } from "lucide-react"
import { TimelineDayCard } from "@/components/TimelineDayCard"
import { TripStatsPanel } from "@/components/TripStatsPanel"
import { draftTotals } from "@/lib/mockItineraryFallback"
import { formatCurrency } from "@/lib/format"
import type { ItineraryDraft } from "@/types/trip"
import type { MoveDirection } from "@/lib/reorderDayItems"

interface ItineraryArtifactProps {
  draft: ItineraryDraft
  selectedPoiId: string | null
  onSelectPoi: (poiId: string) => void
  onHoverPoi: (poiId: string | null) => void
  onSaveDraft: () => void
  onAddPlace: (dayNumber: number) => void
  onRemovePlace: (dayNumber: number, itemId: string) => void
  onMovePlace: (dayNumber: number, itemId: string, direction: MoveDirection) => void
  onApplyManualOrder?: (dayNumber: number) => void
  onOptimizeDay: (dayNumber: number) => void
}

export function ItineraryArtifact({ draft, selectedPoiId, onSelectPoi, onHoverPoi, onSaveDraft, onAddPlace, onRemovePlace, onMovePlace, onApplyManualOrder, onOptimizeDay }: ItineraryArtifactProps) {
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
          <p className="mt-1 text-xs text-orange-950/60">Tọa độ trong bản đồ là mock/demo, không cam kết chính xác tuyệt đối.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={onSaveDraft} className="rounded-lg bg-orange-500 px-3 py-2 text-xs font-black text-white">Lưu nháp</button>
          <button type="button" disabled className="inline-flex cursor-not-allowed items-center gap-2 rounded-lg bg-orange-100 px-3 py-2 text-xs font-black text-orange-950/60">
            <Smartphone className="h-3.5 w-3.5" /> Xác nhận chuyến đi — Sắp ra mắt trên mobile
          </button>
        </div>
      </header>

      <section className="my-4 grid gap-3 rounded-2xl border border-orange-200 bg-orange-50 p-4 sm:grid-cols-3">
        <Metric label="Điểm đến" value={draft.destination} />
        <Metric label="Số ngày" value={`${draft.days.length} ngày`} />
        <Metric label="Ngân sách" value={draft.budget ? formatCurrency(draft.budget) : "Chưa rõ"} />
        <Metric label="Tags" value={draft.tags.join(", ") || "balanced"} />
        <Metric label="Tổng chi phí" value={formatCurrency(totals.estimatedCost)} />
        <Metric label="Trạng thái" value={enoughInfo ? "Đã đủ thông tin" : "Cần hỏi thêm"} />
      </section>

      {draft.optimizationStats ? <TripStatsPanel stats={draft.optimizationStats} draft={draft} /> : null}

      <div className="space-y-4">
        {draft.days.map((day) => (
          <TimelineDayCard
            key={day.dayNumber}
            day={day}
            selectedPoiId={selectedPoiId}
            isManualOrder={draft.manualDayNumbers?.includes(day.dayNumber)}
            onSelectPoi={onSelectPoi}
            onHoverPoi={onHoverPoi}
            onRemovePlace={onRemovePlace}
            onMovePlace={onMovePlace}
            onApplyManualOrder={onApplyManualOrder}
            onAddPlace={onAddPlace}
            onOptimizeDay={onOptimizeDay}
          />
        ))}
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-[10px] font-black uppercase tracking-[0.14em] text-orange-400">{label}</p>
      <p className="mt-1 truncate text-sm font-black text-orange-950">{value}</p>
    </div>
  )
}

