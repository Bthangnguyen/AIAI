import { Plus, RefreshCw } from "lucide-react"
import { TimelinePlaceCard } from "@/components/TimelinePlaceCard"
import { getPoi } from "@/lib/mockItineraryFallback"
import { formatCurrency } from "@/lib/format"
import type { ItineraryDay } from "@/types/trip"

interface TimelineDayCardProps {
  day: ItineraryDay
  selectedPoiId: string | null
  onSelectPoi: (poiId: string) => void
  onHoverPoi: (poiId: string | null) => void
  onRemovePlace: (dayNumber: number, itemId: string) => void
  onAddPlace: (dayNumber: number) => void
  onOptimizeDay: (dayNumber: number) => void
}

export function TimelineDayCard({ day, selectedPoiId, onSelectPoi, onHoverPoi, onRemovePlace, onAddPlace, onOptimizeDay }: TimelineDayCardProps) {
  const totals = day.items.reduce(
    (acc, item) => {
      const poi = getPoi(item.poiId)
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
          <p className="text-xs font-black uppercase tracking-[0.18em] text-travel">{day.title}</p>
          <h3 className="mt-1 text-lg font-black text-orange-950">Ngày {day.dayNumber}</h3>
          <p className="mt-1 text-xs text-orange-950/60">
            {day.items.length} điểm đến · ~{Math.max(1, Math.round(totals.duration / 60))} giờ · ước tính {formatCurrency(totals.cost)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
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
            <TimelinePlaceCard item={item} selected={selectedPoiId === item.poiId} onSelect={() => onSelectPoi(item.poiId)} onHover={(hovered) => onHoverPoi(hovered ? item.poiId : null)} onRemove={() => onRemovePlace(day.dayNumber, item.id)} />
          </div>
        ))}
      </div>
    </section>
  )
}

