"use client"

import { useEffect, useMemo, useState, useRef } from "react"
import { createRoot } from "react-dom/client"
import mapboxgl from "mapbox-gl"
import "mapbox-gl/dist/mapbox-gl.css"

import { JourneyPlayback } from "@/components/JourneyPlayback"
import { getPoi } from "@/lib/mockItineraryFallback"
import { formatCurrency } from "@/lib/format"
import { getPOIImage } from "@/lib/poiImages"
import type { ItineraryDay, ItineraryDraft, ItineraryItem, POI } from "@/types/trip"

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN || ""

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
const ROUTE_CACHE = new Map<string, [number, number][]>()

export function ItineraryMap({
  itineraryDraft,
  selectedPoiId,
  hoveredPoiId,
  onSelectPoi,
  selectedDay,
  showRouteLines,
  onFitBoundsRequest,
  isJourneyPlaying,
  onJourneyStepChange,
  onJourneyFinish,
  onOsrmDegradedChange
}: ItineraryMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const activeMarkersRef = useRef<mapboxgl.Marker[]>([])
  const activeRootsRef = useRef<any[]>([])
  const [mapLoaded, setMapLoaded] = useState(false)
  const [osrmFailures, setOsrmFailures] = useState(0)

  const visibleDays = useMemo(
    () => itineraryDraft.days.filter((day) => selectedDay === "all" || day.dayNumber === selectedDay),
    [itineraryDraft.days, selectedDay]
  )
  const markers = useMemo(() => flattenMarkers(visibleDays), [visibleDays])

  // Reset OSRM failures when draft changes
  useEffect(() => {
    setOsrmFailures(0)
    onOsrmDegradedChange?.(false)
  }, [itineraryDraft.id, onOsrmDegradedChange])

  useEffect(() => {
    onOsrmDegradedChange?.(osrmFailures > 0)
  }, [osrmFailures, onOsrmDegradedChange])

  const reportOsrmFailure = () => setOsrmFailures((value) => value + 1)

  // 1. Initialize Mapbox Map
  useEffect(() => {
    if (!mapContainerRef.current) return

    const initialCenter: [number, number] = markers[0] ? [markers[0].poi.lng, markers[0].poi.lat] : [107.5900, 16.4667]

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: "mapbox://styles/mapbox/streets-v11",
      center: initialCenter,
      zoom: 13,
      pitch: 0, // Flat 2D rendering as requested
      bearing: 0,
      antialias: true
    })

    mapRef.current = map

    map.addControl(new mapboxgl.NavigationControl(), "top-right")

    map.on("load", () => {
      setMapLoaded(true)
    })

    return () => {
      // Cleanup all popup roots on unmount
      activeRootsRef.current.forEach(root => root.unmount())
      activeRootsRef.current = []
      map.remove()
    }
  }, [])

  // 2. Render and Manage Markers & Popups
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return
    const map = mapRef.current

    // Cleanup existing markers and roots
    activeMarkersRef.current.forEach(m => m.remove())
    activeMarkersRef.current = []
    activeRootsRef.current.forEach(root => root.unmount())
    activeRootsRef.current = []

    markers.forEach((marker) => {
      const selected = marker.poi.id === selectedPoiId
      const hovered = marker.poi.id === hoveredPoiId
      const dayStopIndex = marker.day.items.findIndex((it) => it.id === marker.item.id) + 1

      // Create Custom HTML element for Marker Pin
      const el = document.createElement("div")
      el.className = "custom-mapbox-marker cursor-pointer"
      el.style.width = "36px"
      el.style.height = "45px"
      el.style.transformOrigin = "bottom center"
      el.innerHTML = markerIconHTML(dayStopIndex, marker.day.dayNumber, selected, hovered, marker.poi)

      el.addEventListener("click", (e) => {
        e.stopPropagation()
        onSelectPoi(marker.poi.id)
      })

      // Create Popup DOM Container and Render React Component inside it
      const popupDOM = document.createElement("div")
      const root = createRoot(popupDOM)
      root.render(<MapMarkerPopup marker={marker} />)
      activeRootsRef.current.push(root)

      const scale = selected ? 1.25 : hovered ? 1.15 : 1.0
      const popup = new mapboxgl.Popup({
        offset: [0, -38 * scale],
        closeButton: true,
        closeOnClick: false,
        className: "custom-mapbox-popup"
      }).setDOMContent(popupDOM)

      // Bind Mapbox Marker
      const mapboxMarker = new mapboxgl.Marker({
        element: el,
        anchor: "bottom"
      })
        .setLngLat([marker.poi.lng, marker.poi.lat])
        .setPopup(popup)
        .addTo(map)

      if (selected) {
        mapboxMarker.togglePopup()
      }

      activeMarkersRef.current.push(mapboxMarker)

    })
  }, [mapLoaded, markers, selectedPoiId, hoveredPoiId])

  // 3. Draw Road Routing Lines (OSRM Polyline integration)
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return
    const map = mapRef.current

    // Clean up all existing route lines
    const cleanupRoutes = () => {
      const style = map.getStyle()
      if (style && style.sources) {
        Object.keys(style.sources).forEach((sourceId) => {
          if (sourceId.startsWith("route-source-day-")) {
            const layerId = sourceId.replace("route-source-", "route-layer-")
            if (map.getLayer(layerId)) map.removeLayer(layerId)
            map.removeSource(sourceId)
          }
        })
      }
    }

    cleanupRoutes()

    if (!showRouteLines) return

    visibleDays.forEach((day, index) => {
      const positions = day.items
        .map((item) => getPoi(item.poiId))
        .filter((poi): poi is POI => Boolean(poi))
        .map((poi) => [poi.lat, poi.lng] as [number, number])

      if (positions.length < 2) return

      const coordsString = positions.map(([lat, lng]) => `${lng},${lat}`).join(";")
      const cacheKey = `${day.dayNumber}-${coordsString}`
      const dayColor = dayColors[(day.dayNumber - 1) % dayColors.length]

      const drawRoute = (coords: [number, number][]) => {
        const sourceId = `route-source-day-${day.dayNumber}`
        const layerId = `route-layer-day-${day.dayNumber}`
        const mapboxCoords = coords.map(([lat, lng]) => [lng, lat])

        const geojson: GeoJSON.Feature = {
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: mapboxCoords
          }
        }

        if (map.getSource(sourceId)) {
          (map.getSource(sourceId) as mapboxgl.GeoJSONSource).setData(geojson)
        } else {
          map.addSource(sourceId, {
            type: "geojson",
            data: geojson
          })

          map.addLayer({
            id: layerId,
            type: "line",
            source: sourceId,
            layout: {
              "line-join": "round",
              "line-cap": "round"
            },
            paint: {
              "line-color": dayColor,
              "line-width": 4.5,
              "line-opacity": 0.85
            }
          })
        }
      }

      if (ROUTE_CACHE.has(cacheKey)) {
        drawRoute(ROUTE_CACHE.get(cacheKey)!)
      } else {
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
              ROUTE_CACHE.set(cacheKey, coords)
              if (mapRef.current && mapRef.current.getSource(`route-source-day-${day.dayNumber}`) === undefined) {
                drawRoute(coords)
              }
            }
          })
          .catch((err) => {
            console.warn("OSRM routing failed, using straight-line fallback:", err)
            reportOsrmFailure()
            drawRoute(positions) // Straight line fallback
          })
      }
    })
  }, [mapLoaded, visibleDays, showRouteLines])

  // 4. Handle Fit Bounds request
  useEffect(() => {
    if (!mapLoaded || !mapRef.current || !markers.length) return
    const map = mapRef.current

    const bounds = new mapboxgl.LngLatBounds()
    markers.forEach(m => bounds.extend([m.poi.lng, m.poi.lat]))

    map.fitBounds(bounds, {
      padding: { top: 50, bottom: 50, left: 50, right: 50 },
      maxZoom: 14.5,
      duration: 1000
    })
  }, [mapLoaded, markers, onFitBoundsRequest])

  // 5. Handle Pan to selected Marker
  useEffect(() => {
    if (!mapLoaded || !mapRef.current || !selectedPoiId) return
    const map = mapRef.current

    const active = markers.find(m => m.poi.id === selectedPoiId)
    if (active) {
      map.flyTo({
        center: [active.poi.lng, active.poi.lat],
        zoom: Math.max(map.getZoom(), 14.5),
        speed: 1.2,
        duration: 800,
        essential: true
      })
    }
  }, [mapLoaded, selectedPoiId, markers])

  return (
    <div className="relative h-full w-full">
      <div ref={mapContainerRef} className="h-full w-full" />
      {isJourneyPlaying && onJourneyStepChange && onJourneyFinish ? (
        <JourneyPlayback
          days={itineraryDraft.days}
          isPlaying={isJourneyPlaying}
          onStepChange={onJourneyStepChange}
          onFinish={onJourneyFinish}
          selectedDay={selectedDay}
          map={mapRef.current}
        />
      ) : null}
    </div>
  )
}

interface MarkerEntry {
  day: ItineraryDay
  item: ItineraryItem
  poi: POI
}

function flattenMarkers(days: ItineraryDay[]): MarkerEntry[] {
  return days.flatMap((day) =>
    day.items
      .map((item) => ({ day, item, poi: getPoi(item.poiId) }))
      .filter((entry): entry is MarkerEntry => Boolean(entry.poi))
  )
}

function getPoiCategoryInfo(poi: POI) {
  const category = (poi.category || "").toLowerCase()
  const tags = (poi.tags || []).map((t) => t.toLowerCase())
  
  const matches = (keywords: string[]) => {
    return keywords.some((k) => category.includes(k) || tags.some((t) => t.includes(k)))
  }

  if (matches(["restaurant", "food", "dining", "ẩm thực", "nhà hàng", "ăn chay", "món ăn", "ăn uống", "bbq", "quán ăn", "lẩu", "nướng"])) {
    return {
      name: "Ẩm thực",
      bgClass: "bg-amber-100/90 text-amber-800 border-amber-200",
      iconColor: "#d97706",
      path: `<path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2" /><path d="M7 2v20" /><path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7" />`
    }
  }
  
  if (matches(["historic", "history", "temple", "pagoda", "culture", "lịch sử", "di tích", "chùa", "lăng", "đại nội", "đền", "tượng đài", "danh nhân", "văn hóa", "thánh đường", "nhà thờ"])) {
    return {
      name: "Di tích & Văn hóa",
      bgClass: "bg-purple-100/90 text-purple-800 border-purple-200",
      iconColor: "#7c3aed",
      path: `<path d="m12 2-10 7v13h20V9L12 2Z" /><path d="M9 22v-8h6v8" />`
    }
  }

  if (matches(["cafe", "coffee", "cà phê", "trà", "quán trà", "nước uống", "sinh tố", "juice"])) {
    return {
      name: "Cà phê & Trà",
      bgClass: "bg-orange-900/10 text-orange-950 border-orange-900/20",
      iconColor: "#854d0e",
      path: `<path d="M17 8h1a4 4 0 1 1 0 8h-1" /><path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z" /><path d="M6 2v2" /><path d="M10 2v2" /><path d="M14 2v2" />`
    }
  }

  if (matches(["nature", "scenic", "river", "park", "thiên nhiên", "sông", "núi", "công viên", "cảnh quan", "suối", "đầm phá", "cồn", "biển", "bãi biển"])) {
    return {
      name: "Thiên nhiên & Cảnh quan",
      bgClass: "bg-emerald-100/90 text-emerald-800 border-emerald-200",
      iconColor: "#059669",
      path: `<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 3.5 1 9.8A7 7 0 0 1 11 20Z" /><path d="M19 2c-2.26 4.33-5.27 7.14-8 8" />`
    }
  }

  if (matches(["spa", "wellness", "trị liệu", "sức khỏe", "massage", "xông hơi"])) {
    return {
      name: "Sức khỏe & Thư giãn",
      bgClass: "bg-rose-100/90 text-rose-800 border-rose-200",
      iconColor: "#db2777",
      path: `<path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" /><path d="M12 6a6 6 0 0 0-6 6c0 3 3 4 6 8 3-4 6-5 6-8a6 6 0 0 0-6-6z" />`
    }
  }

  if (matches(["shopping", "market", "chợ", "mua sắm", "lưu niệm", "siêu thị", "plaza"])) {
    return {
      name: "Mua sắm",
      bgClass: "bg-pink-100/90 text-pink-800 border-pink-200",
      iconColor: "#c026d3",
      path: `<path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" /><path d="M3 6h18" /><path d="M16 10a4 4 0 0 1-8 0" />`
    }
  }

  if (matches(["hotel", "stay", "khách sạn", "resort", "homestay", "accommodation", "nhà nghỉ", "hostel"])) {
    return {
      name: "Lưu trú",
      bgClass: "bg-blue-100/90 text-blue-800 border-blue-200",
      iconColor: "#2563eb",
      path: `<path d="M2 4v16" /><path d="M2 20h20" /><path d="M22 14v6" /><path d="M2 11h20" /><path d="M6 11V9a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />`
    }
  }

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
  const imageUrl = getPOIImage(marker.poi.name, categoryInfo.name)
  
  return (
    <div className="p-0.5 min-w-[245px] max-w-[290px] font-sans antialiased text-sm">
      <div className="flex items-center justify-between gap-2 border-b border-orange-100/60 pb-1.5 mb-2">
        <div className="flex items-center gap-1.5">
          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold border ${categoryInfo.bgClass}`}>
            <svg viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round" className="w-2.5 h-2.5" dangerouslySetInnerHTML={{ __html: categoryInfo.path }} />
            {categoryInfo.name}
          </span>
        </div>
      </div>

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

      {marker.poi.description && (
        <p className="text-xs text-orange-950/75 leading-relaxed mb-2.5 line-clamp-3 bg-orange-50/50 p-2 rounded-lg border border-orange-100/30">
          {marker.poi.description}
        </p>
      )}

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

function markerIconHTML(order: number, dayNumber: number, selected: boolean, hovered: boolean, poi: POI) {
  const categoryInfo = getPoiCategoryInfo(poi)
  const dayColor = dayColors[(dayNumber - 1) % dayColors.length]
  const glowColor = selected ? "#ea580c" : hovered ? "#f97316" : dayColor
  
  const scale = selected ? 1.25 : hovered ? 1.15 : 1.0
  const shadowOpacity = selected ? "0.45" : hovered ? "0.35" : "0.22"
  const strokeWidth = selected ? "2.5" : hovered ? "2.0" : "1.5"
  
  return `
    <div style="
      width: 100%;
      height: 100%;
      transform: scale(${scale});
      transform-origin: bottom center;
      transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      filter: drop-shadow(0px ${selected ? '6px' : '4px'} ${selected ? '8px' : '6px'} rgba(0,0,0,${selected ? '0.3' : '0.18'}));
    ">
      <svg width="100%" height="100%" viewBox="0 0 32 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 38C16 38 29 24 29 15C29 7.82 23.18 2 16 2C8.82 2 3 7.82 3 15C3 24 16 38 16 38Z" fill="${glowColor}" opacity="${shadowOpacity}" />
        <path d="M16 37C16 37 28 23.5 28 14.5C28 7.6 22.4 2 15.5 2C8.6 2 3 7.6 3 14.5C3 23.5 16 37 16 37Z" 
          fill="${dayColor}" 
          stroke="${selected ? '#ffffff' : hovered ? '#ffffff' : '#ffffff'}" 
          stroke-width="${strokeWidth}" 
        />
        <circle cx="15.5" cy="14.5" r="7.5" fill="#ffffff" />
        <g transform="translate(9.5, 8.5) scale(0.5)" stroke="${categoryInfo.iconColor}" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
          ${categoryInfo.path}
        </g>
        <circle cx="25.5" cy="6.5" r="6" fill="#ffffff" stroke="${dayColor}" stroke-width="1.2" />
        <text x="25.5" y="8.8" font-size="7" font-weight="900" fill="${dayColor}" font-family="Be Vietnam Pro, sans-serif" text-anchor="middle">${order}</text>
      </svg>
    </div>
  `
}
