import { Bike, Car, Footprints, Home, Plus, RefreshCw, Route } from "lucide-react"
import { TimelinePlaceCard } from "@/components/TimelinePlaceCard"
import { getPoi } from "@/lib/mockItineraryFallback"
import { POI_CACHE } from "@/lib/api"
import { formatCurrency } from "@/lib/format"
import { canMoveDayItem } from "@/lib/reorderDayItems"
import type { ItineraryDay, TransportLeg } from "@/types/trip"
import type { MoveDirection } from "@/lib/reorderDayItems"

interface TimelineDayCardProps {
  day: ItineraryDay
  selectedPoiId: string | null
  isManualOrder?: boolean
  startDate?: string
  onSelectPoi: (poiId: string) => void
  onHoverPoi: (poiId: string | null) => void
  onRemovePlace: (dayNumber: number, itemId: string) => void
  onMovePlace: (dayNumber: number, itemId: string, direction: MoveDirection) => void
  onApplyManualOrder?: (dayNumber: number) => void
  onAddPlace: (dayNumber: number) => void
  onOptimizeDay: (dayNumber: number) => void
}

function getFormattedDate(startDateStr: string, dayNumber: number): string {
  try {
    const date = new Date(startDateStr)
    date.setDate(date.getDate() + dayNumber - 1)
    const daysOfWeek = ["Chủ Nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"]
    const dayName = daysOfWeek[date.getDay()]
    const dd = String(date.getDate()).padStart(2, '0')
    const mm = String(date.getMonth() + 1).padStart(2, '0')
    const yyyy = date.getFullYear()
    return `${dayName}, ${dd}/${mm}/${yyyy}`
  } catch (e) {
    return ""
  }
}

function formatDistance(km?: number): string {
  if (!km) return "--"
  if (km < 1) return `${Math.round(km * 1000)} m`
  return `${km.toFixed(1)} km`
}

function formatTransportCost(leg?: TransportLeg): string {
  if (!leg) return ""
  if (leg.cost_policy === "time_only" || leg.cost_policy === "none") return "Đã có phương tiện"
  if (leg.cost_policy === "daily_rental") return "Đã tính trong phí thuê ngày"
  const cost = Number(leg.transport_cost || 0)
  return cost > 0 ? formatCurrency(cost) : "0đ"
}

function TransportIcon({ leg }: { leg?: TransportLeg }) {
  const mode = (leg?.icon || leg?.mode || "").toLowerCase()
  if (mode.includes("walk")) return <Footprints className="h-3.5 w-3.5" />
  if (mode.includes("car") || mode.includes("taxi")) return <Car className="h-3.5 w-3.5" />
  if (mode.includes("motorbike") || mode.includes("bike")) return <Bike className="h-3.5 w-3.5" />
  return <Route className="h-3.5 w-3.5" />
}

function TransportLegRow({ leg }: { leg?: TransportLeg }) {
  if (!leg) return null
  const label = leg.is_return_to_lodging ? "Quay ve cho o" : leg.mode_label || leg.mode || "Di chuyen"
  return (
    <div className="mb-3 ml-1 rounded-xl border border-orange-200 bg-orange-50/80 px-3 py-2 text-xs text-orange-950/70">
      <div className="flex flex-wrap items-center gap-2 font-bold">
        <span className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-1 text-orange-700">
          <TransportIcon leg={leg} />
          {label}
        </span>
        <span>{leg.travel_time_min ?? 0} phút</span>
        <span>·</span>
        <span>{formatDistance(leg.distance_km)}</span>
        <span>·</span>
        <span>{formatTransportCost(leg)}</span>
      </div>
      {leg.warning ? <p className="mt-1 font-semibold text-amber-700">{leg.warning}</p> : null}
    </div>
  )
}

export function TimelineDayCard({
  day,
  selectedPoiId,
  isManualOrder,
  startDate,
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
  const displayCost = Number(day.dayTotalCost ?? totals.cost)

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
          <h3 className="mt-1 text-lg font-black text-orange-950">
            Ngày {day.dayNumber} {startDate ? `— ${getFormattedDate(startDate, day.dayNumber)}` : ""}
          </h3>
          <p className="mt-1 text-xs text-orange-950/60">
            {day.items.filter(item => !item.poiId.startsWith("__")).length} điểm đến · ~{Math.max(1, Math.round(totals.duration / 60))} giờ · ước tính {formatCurrency(displayCost)}
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
        {day.startLodging ? (
          <div className="mb-2 flex items-center gap-2 rounded-xl bg-blue-50 px-3 py-2 text-xs font-bold text-blue-900">
            <Home className="h-3.5 w-3.5" />
            Xuất phát từ {String(day.startLodging.name || "chỗ ở")}
          </div>
        ) : null}
        {day.items.map((item, index) => {
          const leg = item.transport_from_prev || day.transportLegs?.[index]
          return (
            <div key={item.id} className="relative">
              <TransportLegRow leg={leg} />
              <span className="absolute -left-[4.35rem] top-14 rounded-full bg-white px-2 py-1 text-[10px] font-black text-orange-950">{item.time}</span>
              <span className="absolute -left-[1.35rem] top-[3.75rem] h-2.5 w-2.5 rounded-full bg-travel ring-4 ring-card" />
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
          )
        })}
        <TransportLegRow leg={day.transportLegs?.find((leg) => leg.is_return_to_lodging)} />
        {day.overnightStay ? (
          <div className="mt-3 flex items-center gap-2 rounded-xl bg-blue-50 px-3 py-2 text-xs font-bold text-blue-900">
            <Home className="h-3.5 w-3.5" />
            Nghỉ đêm tại {String(day.overnightStay.name || "chỗ ở")} · {Number(day.overnightStay.nightly_rate || 0) > 0 ? formatCurrency(Number(day.overnightStay.nightly_rate)) : "đã có chỗ ở"}
          </div>
        ) : null}
      </div>
    </section>
  )
}
