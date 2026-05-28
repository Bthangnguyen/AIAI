import { Plus, RefreshCw, Route } from "lucide-react"
import { TimelinePlaceCard } from "@/components/TimelinePlaceCard"
import { getPoi } from "@/lib/mockItineraryFallback"
import { POI_CACHE } from "@/lib/api"
import { formatCurrency } from "@/lib/format"
import { canMoveDayItem } from "@/lib/reorderDayItems"
import type { ItineraryDay } from "@/types/trip"
import type { MoveDirection } from "@/lib/reorderDayItems"

interface TimelineDayCardProps {
  day: ItineraryDay
  selectedPoiId: string | null
  isManualOrder?: boolean
  onSelectPoi: (poiId: string) => void
  onHoverPoi: (poiId: string | null) => void
  onRemovePlace: (dayNumber: number, itemId: string) => void
  onMovePlace: (dayNumber: number, itemId: string, direction: MoveDirection) => void
  onApplyManualOrder?: (dayNumber: number) => void
  onAddPlace: (dayNumber: number) => void
  onOptimizeDay: (dayNumber: number) => void
}

export function TimelineDayCard({
  day,
  selectedPoiId,
  isManualOrder,
  onSelectPoi,
  onHoverPoi,
  onRemovePlace,
  onMovePlace,
  onApplyManualOrder,
  onAddPlace,
  onOptimizeDay,
}: TimelineDayCardProps) {
  const totals = day.items.reduce(
    (acc, item) => {
      const poi = getPoi(item.poiId) ?? POI_CACHE.get(item.poiId)
      if (!poi) return acc
      acc.cost += poi.estimatedCost
      acc.duration += poi.estimatedDurationMinutes
      return acc
    },
    { cost: 0, duration: 0 },
  )

  return (
    <section className="rounded-2xl border border-orange-200 bg-white p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs font-black uppercase tracking-[0.18em] text-travel">{day.title}</p>
            {isManualOrder ? (
              <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-black uppercase tracking-wide text-violet-700">
                Thủ công
              </span>
            ) : null}
          </div>
          <h3 className="mt-1 text-lg font-black text-orange-950">Ngày {day.dayNumber}</h3>
          <p className="mt-1 text-xs text-orange-950/60">
            {day.items.filter(item => !item.poiId.startsWith("__")).length} điểm đến · ~{Math.max(1, Math.round(totals.duration / 60))} giờ · ước tính {formatCurrency(totals.cost)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {isManualOrder && onApplyManualOrder ? (
            <button
              type="button"
              onClick={() => onApplyManualOrder(day.dayNumber)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-violet-300 bg-violet-50 px-3 py-2 text-xs font-bold text-violet-800"
            >
              <Route className="h-3.5 w-3.5" /> Cập nhật lộ trình
            </button>
          ) : null}
          <button type="button" onClick={() => onAddPlace(day.dayNumber)} className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-xs font-bold text-orange-950">
            <Plus className="h-3.5 w-3.5" /> Thêm địa điểm
          </button>
          <button type="button" onClick={() => onOptimizeDay(day.dayNumber)} className="inline-flex items-center gap-1.5 rounded-lg bg-orange-100 px-3 py-2 text-xs font-bold text-orange-950">
            <RefreshCw className="h-3.5 w-3.5" /> Tối ưu lại ngày này
          </button>
        </div>
      </div>
      <div className="mt-4 space-y-3 border-l border-dashed border-orange-300 pl-4">
        {day.items.map((item) => (
          <div key={item.id} className="relative">
            <span className="absolute -left-[4.35rem] top-4 rounded-full bg-white px-2 py-1 text-[10px] font-black text-orange-950">{item.time}</span>
            <span className="absolute -left-[1.35rem] top-5 h-2.5 w-2.5 rounded-full bg-travel ring-4 ring-card" />
            <TimelinePlaceCard
              item={item}
              selected={selectedPoiId === item.poiId}
              canMoveUp={canMoveDayItem(day, item.id, "up")}
              canMoveDown={canMoveDayItem(day, item.id, "down")}
              onSelect={() => onSelectPoi(item.poiId)}
              onHover={(hovered) => onHoverPoi(hovered ? item.poiId : null)}
              onRemove={() => onRemovePlace(day.dayNumber, item.id)}
              onMove={(direction) => onMovePlace(day.dayNumber, item.id, direction)}
            />
          </div>
        ))}
      </div>
    </section>
  )
}
