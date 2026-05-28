import { ChevronDown, ChevronUp, Clock3, Star, Trash2 } from "lucide-react"
import { getPoi } from "@/lib/mockItineraryFallback"
import { POI_CACHE } from "@/lib/api"
import { formatCurrency } from "@/lib/format"
import type { ItineraryItem } from "@/types/trip"
import type { MoveDirection } from "@/lib/reorderDayItems"

interface TimelinePlaceCardProps {
  item: ItineraryItem
  selected: boolean
  canMoveUp: boolean
  canMoveDown: boolean
  onSelect: () => void
  onHover: (hovered: boolean) => void
  onRemove: () => void
  onMove: (direction: MoveDirection) => void
}

export function TimelinePlaceCard({
  item,
  selected,
  canMoveUp,
  canMoveDown,
  onSelect,
  onHover,
  onRemove,
  onMove,
}: TimelinePlaceCardProps) {
  const poi = getPoi(item.poiId) ?? POI_CACHE.get(item.poiId)
  if (!poi) return null

  return (
    <article onMouseEnter={() => onHover(true)} onMouseLeave={() => onHover(false)} onClick={onSelect} className={`cursor-pointer rounded-2xl border bg-white p-3 transition ${selected ? "border-travel shadow-[0_0_0_1px_rgba(255,56,92,0.45)]" : "border-orange-200 hover:border-orange-300"}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-travel/15 px-2.5 py-1 text-[11px] font-bold text-travel">{poi.category}</span>
            <span className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2.5 py-1 text-[11px] font-bold text-orange-950/70">
              <Star className="h-3 w-3 fill-warning text-warning" /> {poi.rating}
            </span>
          </div>
          <h4 className="mt-2 text-sm font-black text-orange-950">{poi.name}</h4>
          <p className="mt-1 text-xs leading-5 text-orange-950/60">{poi.description}</p>
        </div>
        <div className="flex shrink-0 flex-col gap-1">
          <button
            type="button"
            disabled={!canMoveUp}
            onClick={(event) => { event.stopPropagation(); onMove("up") }}
            className="rounded-lg p-1 text-orange-500 transition hover:bg-orange-100 disabled:cursor-not-allowed disabled:opacity-30"
            title="Di chuyển lên"
            aria-label="Di chuyển lên"
          >
            <ChevronUp className="h-4 w-4" />
          </button>
          <button
            type="button"
            disabled={!canMoveDown}
            onClick={(event) => { event.stopPropagation(); onMove("down") }}
            className="rounded-lg p-1 text-orange-500 transition hover:bg-orange-100 disabled:cursor-not-allowed disabled:opacity-30"
            title="Di chuyển xuống"
            aria-label="Di chuyển xuống"
          >
            <ChevronDown className="h-4 w-4" />
          </button>
          <button type="button" onClick={(event) => { event.stopPropagation(); onRemove() }} className="rounded-lg p-1 text-orange-400 transition hover:bg-orange-100 hover:text-travel" title="Xóa">
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
      <p className="mt-2 rounded-xl bg-white px-3 py-2 text-xs text-orange-950/70">{item.note}</p>
      <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-semibold text-orange-950/60">
        <span className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2.5 py-1"><Clock3 className="h-3 w-3" /> {poi.estimatedDurationMinutes} phút</span>
        <span className="rounded-full bg-orange-100 px-2.5 py-1">
          {poi.id.startsWith("__meal_") 
            ? "Tự túc" 
            : poi.id.startsWith("__food_walk_") || poi.id.startsWith("__rest_break_") || poi.estimatedCost === 0 
              ? "Miễn phí" 
              : formatCurrency(poi.estimatedCost)}
        </span>
        {poi.tags.slice(0, 3).map((tag: string) => <span key={tag} className="rounded-full bg-orange-100 px-2.5 py-1">{tag}</span>)}
      </div>
    </article>
  )
}
