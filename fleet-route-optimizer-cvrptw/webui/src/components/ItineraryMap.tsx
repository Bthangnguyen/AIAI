"use client"

import L from "leaflet"
import { JourneyPlayback } from "@/components/JourneyPlayback"
import { useEffect, useMemo, useState } from "react"
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet"
import { getPoi } from "@/lib/mockItineraryFallback"
import { formatCurrency } from "@/lib/format"
import type { ItineraryDay, ItineraryDraft, ItineraryItem, POI } from "@/types/trip"

interface ItineraryMapProps {
  itineraryDraft: ItineraryDraft
  selectedPoiId: string | null
  hoveredPoiId: string | null
  onSelectPoi: (poiId: string) => void
  selectedDay: number | "all"
  showRouteLines: boolean
  onFitBoundsRequest: number
  isJourneyPlaying?: boolean
  onJourneyStepChange?: (poiId: string, stepIndex: number) => void
  onJourneyFinish?: () => void
  onOsrmDegradedChange?: (degraded: boolean) => void
}

const dayColors = ["#ff385c", "#60a5fa", "#22c55e", "#f59e0b", "#a78bfa"]

export function ItineraryMap({ itineraryDraft, selectedPoiId, hoveredPoiId, onSelectPoi, selectedDay, showRouteLines, onFitBoundsRequest, isJourneyPlaying, onJourneyStepChange, onJourneyFinish, onOsrmDegradedChange }: ItineraryMapProps) {
  const [osrmFailures, setOsrmFailures] = useState(0)
  const visibleDays = useMemo(() => itineraryDraft.days.filter((day) => selectedDay === "all" || day.dayNumber === selectedDay), [itineraryDraft.days, selectedDay])
  const markers = useMemo(() => flattenMarkers(visibleDays), [visibleDays])
  const center: [number, number] = markers[0] ? [markers[0].poi.lat, markers[0].poi.lng] : [16.4667, 107.5900]

  useEffect(() => {
    setOsrmFailures(0)
    onOsrmDegradedChange?.(false)
  }, [itineraryDraft.id, onOsrmDegradedChange])

  useEffect(() => {
    onOsrmDegradedChange?.(osrmFailures > 0)
  }, [osrmFailures, onOsrmDegradedChange])

  const reportOsrmFailure = () => setOsrmFailures((value) => value + 1)

  return (
    <MapContainer center={center} zoom={13} scrollWheelZoom className="h-full w-full">
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <FitBounds markers={markers} signal={onFitBoundsRequest} />
      <PanToSelected markers={markers} selectedPoiId={selectedPoiId} />
      {showRouteLines ? <DayRouteLayer days={visibleDays} onOsrmFailure={reportOsrmFailure} /> : null}
      {markers.map((marker) => {
        const selected = marker.poi.id === selectedPoiId
        const hovered = marker.poi.id === hoveredPoiId
        const dayStopIndex = marker.day.items.findIndex((it) => it.id === marker.item.id) + 1
        return (
          <Marker
            key={`${marker.day.dayNumber}-${marker.item.id}`}
            position={[marker.poi.lat, marker.poi.lng]}
            icon={markerIcon(dayStopIndex, marker.day.dayNumber, selected, hovered, marker.poi)}
            eventHandlers={{ click: () => onSelectPoi(marker.poi.id) }}
          >
            <Popup>
              <MapMarkerPopup marker={marker} />
            </Popup>
          </Marker>
        )
      })}
      {isJourneyPlaying && onJourneyStepChange && onJourneyFinish ? (
        <JourneyPlayback
          days={itineraryDraft.days}
          isPlaying={isJourneyPlaying}
          onStepChange={onJourneyStepChange}
          onFinish={onJourneyFinish}
          selectedDay={selectedDay}
        />
      ) : null}
    </MapContainer>
  )
}

const ROUTE_CACHE = new Map<string, [number, number][]>()

interface DayRoadRoutePolylineProps {
  dayNumber: number
  color: string
  positions: [number, number][]
  onOsrmFailure?: () => void
}

function DayRoadRoutePolyline({ dayNumber, color, positions, onOsrmFailure }: DayRoadRoutePolylineProps) {
  const [routePositions, setRoutePositions] = useState<[number, number][]>(positions)

  useEffect(() => {
    if (positions.length < 2) {
      setRoutePositions(positions)
      return
    }

    const coordsString = positions.map(([lat, lng]) => `${lng},${lat}`).join(";")
    const cacheKey = `${dayNumber}-${coordsString}`

    if (ROUTE_CACHE.has(cacheKey)) {
      setRoutePositions(ROUTE_CACHE.get(cacheKey)!)
      return
    }

    setRoutePositions(positions)

    let isMounted = true
    const url = `https://router.project-osrm.org/route/v1/driving/${coordsString}?overview=full&geometries=geojson`

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`OSRM HTTP error: ${res.status}`)
        return res.json()
      })
      .then((data) => {
        if (data.code === "Ok" && data.routes?.[0]?.geometry?.coordinates) {
          const coords = data.routes[0].geometry.coordinates.map(
            ([lng, lat]: [number, number]) => [lat, lng] as [number, number]
          )
          if (isMounted) {
            ROUTE_CACHE.set(cacheKey, coords)
            setRoutePositions(coords)
          }
        }
      })
      .catch((err) => {
        console.warn("OSRM routing failed, using straight-line fallback:", err)
        onOsrmFailure?.()
      })

    return () => {
      isMounted = false
    }
  }, [positions, dayNumber, onOsrmFailure])

  return (
    <Polyline
      positions={routePositions}
      pathOptions={{
        color: color,
        weight: 4,
        opacity: 0.82,
      }}
    />
  )
}

function DayRouteLayer({ days, onOsrmFailure }: { days: ItineraryDay[]; onOsrmFailure?: () => void }) {
  return (
    <>
      {days.map((day, index) => {
        const positions = day.items
          .map((item) => getPoi(item.poiId))
          .filter((poi): poi is POI => Boolean(poi))
          .map((poi) => [poi.lat, poi.lng] as [number, number])
        if (positions.length < 2) return null
        return (
          <DayRoadRoutePolyline
            key={day.dayNumber}
            dayNumber={day.dayNumber}
            color={dayColors[index % dayColors.length]}
            positions={positions}
            onOsrmFailure={onOsrmFailure}
          />
        )
      })}
    </>
  )
}

function getPoiCategoryInfo(poi: POI) {
  const category = (poi.category || "").toLowerCase()
  const tags = (poi.tags || []).map((t) => t.toLowerCase())
  
  const matches = (keywords: string[]) => {
    return keywords.some((k) => category.includes(k) || tags.some((t) => t.includes(k)))
  }

  // 1. Food/Dining
  if (matches(["restaurant", "food", "dining", "ẩm thực", "nhà hàng", "ăn chay", "món ăn", "ăn uống", "bbq", "quán ăn", "lẩu", "nướng"])) {
    return {
      name: "Ẩm thực",
      bgClass: "bg-amber-100/90 text-amber-800 border-amber-200",
      iconColor: "#d97706",
      path: `<path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2" /><path d="M7 2v20" /><path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7" />`
    }
  }
  
  // 2. Cultural/Historic
  if (matches(["historic", "history", "temple", "pagoda", "culture", "lịch sử", "di tích", "chùa", "lăng", "đại nội", "đền", "tượng đài", "danh nhân", "văn hóa", "thánh đường", "nhà thờ"])) {
    return {
      name: "Di tích & Văn hóa",
      bgClass: "bg-purple-100/90 text-purple-800 border-purple-200",
      iconColor: "#7c3aed",
      path: `<path d="m12 2-10 7v13h20V9L12 2Z" /><path d="M9 22v-8h6v8" />`
    }
  }

  // 3. Cafe
  if (matches(["cafe", "coffee", "cà phê", "trà", "quán trà", "nước uống", "sinh tố", "juice"])) {
    return {
      name: "Cà phê & Trà",
      bgClass: "bg-orange-900/10 text-orange-950 border-orange-900/20",
      iconColor: "#854d0e",
      path: `<path d="M17 8h1a4 4 0 1 1 0 8h-1" /><path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z" /><path d="M6 2v2" /><path d="M10 2v2" /><path d="M14 2v2" />`
    }
  }

  // 4. Nature/Scenic
  if (matches(["nature", "scenic", "river", "park", "thiên nhiên", "sông", "núi", "công viên", "cảnh quan", "suối", "đầm phá", "cồn", "biển", "bãi biển"])) {
    return {
      name: "Thiên nhiên & Cảnh quan",
      bgClass: "bg-emerald-100/90 text-emerald-800 border-emerald-200",
      iconColor: "#059669",
      path: `<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 3.5 1 9.8A7 7 0 0 1 11 20Z" /><path d="M19 2c-2.26 4.33-5.27 7.14-8 8" />`
    }
  }

  // 5. Spa/Wellness
  if (matches(["spa", "wellness", "trị liệu", "sức khỏe", "massage", "xông hơi"])) {
    return {
      name: "Sức khỏe & Thư giãn",
      bgClass: "bg-rose-100/90 text-rose-800 border-rose-200",
      iconColor: "#db2777",
      path: `<path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" /><path d="M12 6a6 6 0 0 0-6 6c0 3 3 4 6 8 3-4 6-5 6-8a6 6 0 0 0-6-6z" />`
    }
  }

  // 6. Shopping/Market
  if (matches(["shopping", "market", "chợ", "mua sắm", "lưu niệm", "siêu thị", "plaza"])) {
    return {
      name: "Mua sắm",
      bgClass: "bg-pink-100/90 text-pink-800 border-pink-200",
      iconColor: "#c026d3",
      path: `<path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" /><path d="M3 6h18" /><path d="M16 10a4 4 0 0 1-8 0" />`
    }
  }

  // 7. Stay
  if (matches(["hotel", "stay", "khách sạn", "resort", "homestay", "accommodation", "nhà nghỉ", "hostel"])) {
    return {
      name: "Lưu trú",
      bgClass: "bg-blue-100/90 text-blue-800 border-blue-200",
      iconColor: "#2563eb",
      path: `<path d="M2 4v16" /><path d="M2 20h20" /><path d="M22 14v6" /><path d="M2 11h20" /><path d="M6 11V9a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />`
    }
  }

  // 8. General/Default
  return {
    name: poi.category || "Địa điểm",
    bgClass: "bg-teal-100/90 text-teal-800 border-teal-200",
    iconColor: "#0d9488",
    path: `<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />`
  }
}

function MapMarkerPopup({ marker }: { marker: MarkerEntry }) {
  const categoryInfo = getPoiCategoryInfo(marker.poi)
  const dayStopIndex = marker.day.items.findIndex((it) => it.id === marker.item.id) + 1
  
  return (
    <div className="p-0.5 min-w-[245px] max-w-[290px] font-sans antialiased text-sm">
      {/* Header Info */}
      <div className="flex items-center justify-between gap-2 border-b border-orange-100/60 pb-1.5 mb-2">
        <div className="flex items-center gap-1.5">
          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold border ${categoryInfo.bgClass}`}>
            <svg viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round" className="w-2.5 h-2.5" dangerouslySetInnerHTML={{ __html: categoryInfo.path }} />
            {categoryInfo.name}
          </span>
        </div>
        
        {/* Rating Badge */}
        {marker.poi.rating > 0 && (
          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-700 text-[10px] font-bold border border-amber-500/20">
            ⭐ {marker.poi.rating.toFixed(1)}
          </span>
        )}
      </div>

      {/* Place Title & Day/Time */}
      <div className="mb-2">
        <p className="font-extrabold text-[14.5px] leading-snug text-orange-950 mb-0.5 hover:text-travel transition-colors">
          {dayStopIndex}. {marker.poi.name}
        </p>
        <p className="text-[11px] font-semibold text-orange-800/70 flex items-center gap-1">
          <span>📅 Ngày {marker.day.dayNumber}</span>
          <span>•</span>
          <span className="font-extrabold text-travel flex items-center gap-0.5">🕒 {marker.item.time}</span>
        </p>
      </div>

      {/* Description */}
      {marker.poi.description && (
        <p className="text-xs text-orange-950/75 leading-relaxed mb-2.5 line-clamp-3 bg-orange-50/50 p-2 rounded-lg border border-orange-100/30">
          {marker.poi.description}
        </p>
      )}

      {/* Stats/Metrics grid */}
      <div className="grid grid-cols-2 gap-2 mb-2.5 bg-orange-50/80 p-2 rounded-lg border border-orange-100/40">
        <div className="flex items-center gap-2 text-xs text-orange-900/80">
          <span className="text-base">⏱️</span>
          <div>
            <p className="text-[9px] text-orange-900/40 uppercase font-extrabold tracking-wider leading-none">Thời lượng</p>
            <p className="font-extrabold text-orange-950 mt-0.5">{marker.poi.estimatedDurationMinutes} phút</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-orange-900/80">
          <span className="text-base">💰</span>
          <div>
            <p className="text-[9px] text-orange-900/40 uppercase font-extrabold tracking-wider leading-none">Chi phí</p>
            <p className="font-extrabold text-orange-950 mt-0.5">
              {marker.poi.id.startsWith("__meal_") 
                ? "Tự túc" 
                : marker.poi.id.startsWith("__food_walk_") || marker.poi.id.startsWith("__rest_break_") || marker.poi.estimatedCost === 0 
                  ? "Miễn phí" 
                  : formatCurrency(marker.poi.estimatedCost)}
            </p>
          </div>
        </div>
      </div>

      {/* Tags */}
      {marker.poi.tags && marker.poi.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1 pt-1.5 border-t border-orange-100/30">
          {marker.poi.tags.slice(0, 3).map((tag) => (
            <span key={tag} className="px-1.5 py-0.5 rounded bg-orange-100/40 text-orange-950/65 text-[9px] font-bold border border-orange-200/20">
              #{tag}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function FitBounds({ markers, signal }: { markers: MarkerEntry[]; signal: number }) {
  const map = useMap()
  useEffect(() => {
    if (!markers.length) return
    const bounds = L.latLngBounds(markers.map((marker) => [marker.poi.lat, marker.poi.lng]))
    map.fitBounds(bounds, { padding: [34, 34], maxZoom: 14 })
  }, [map, markers, signal])
  return null
}

function PanToSelected({ markers, selectedPoiId }: { markers: MarkerEntry[]; selectedPoiId: string | null }) {
  const map = useMap()
  useEffect(() => {
    if (!selectedPoiId) return
    const marker = markers.find((entry) => entry.poi.id === selectedPoiId)
    if (marker) map.flyTo([marker.poi.lat, marker.poi.lng], Math.max(map.getZoom(), 14), { duration: 0.65 })
  }, [map, markers, selectedPoiId])
  return null
}

interface MarkerEntry {
  day: ItineraryDay
  item: ItineraryItem
  poi: POI
}

function flattenMarkers(days: ItineraryDay[]): MarkerEntry[] {
  return days.flatMap((day) => day.items.map((item) => ({ day, item, poi: getPoi(item.poiId) })).filter((entry): entry is MarkerEntry => Boolean(entry.poi)))
}

function markerIcon(order: number, dayNumber: number, selected: boolean, hovered: boolean, poi: POI) {
  const categoryInfo = getPoiCategoryInfo(poi)
  const dayColors = ["#ff385c", "#60a5fa", "#22c55e", "#f59e0b", "#a78bfa"]
  const dayColor = dayColors[(dayNumber - 1) % dayColors.length]
  const glowColor = selected ? "#ea580c" : hovered ? "#f97316" : dayColor
  
  const scale = selected ? 1.25 : hovered ? 1.15 : 1.0
  const zIndex = selected ? 1000 : hovered ? 500 : 0
  const markerSize: [number, number] = [36 * scale, 45 * scale]
  const anchor: [number, number] = [18 * scale, 43 * scale]
  
  const shadowOpacity = selected ? "0.45" : hovered ? "0.35" : "0.22"
  const strokeWidth = selected ? "2.5" : hovered ? "2.0" : "1.5"
  
  const html = `
    <div style="
      width: 100%;
      height: 100%;
      transform: scale(${scale});
      transform-origin: bottom center;
      transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      filter: drop-shadow(0px ${selected ? '6px' : '4px'} ${selected ? '8px' : '6px'} rgba(0,0,0,${selected ? '0.3' : '0.18'}));
    ">
      <svg width="100%" height="100%" viewBox="0 0 32 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <!-- Glow / Shadow behind the pin -->
        <path d="M16 38C16 38 29 24 29 15C29 7.82 23.18 2 16 2C8.82 2 3 7.82 3 15C3 24 16 38 16 38Z" fill="${glowColor}" opacity="${shadowOpacity}" />
        
        <!-- Pin Body -->
        <path d="M16 37C16 37 28 23.5 28 14.5C28 7.6 22.4 2 15.5 2C8.6 2 3 7.6 3 14.5C3 23.5 16 37 16 37Z" 
          fill="${dayColor}" 
          stroke="${selected ? '#ffffff' : hovered ? '#ffffff' : '#ffffff'}" 
          stroke-width="${strokeWidth}" 
        />
        
        <!-- White Inner Circle -->
        <circle cx="15.5" cy="14.5" r="7.5" fill="#ffffff" />
        
        <!-- Category Icon Inside Circle -->
        <g transform="translate(9.5, 8.5) scale(0.5)" stroke="${categoryInfo.iconColor}" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
          ${categoryInfo.path}
        </g>
        
        <!-- Sequence Number Badge (top right) -->
        <circle cx="25.5" cy="6.5" r="6" fill="#ffffff" stroke="${dayColor}" stroke-width="1.2" />
        <text x="25.5" y="8.8" font-size="7" font-weight="900" fill="${dayColor}" font-family="Be Vietnam Pro, sans-serif" text-anchor="middle">${order}</text>
      </svg>
    </div>
  `
  
  return L.divIcon({
    className: "custom-leaflet-marker",
    html: html,
    iconSize: markerSize,
    iconAnchor: anchor,
    popupAnchor: [0, -42 * scale],
  })
}

