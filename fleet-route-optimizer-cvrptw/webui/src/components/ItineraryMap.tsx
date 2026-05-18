"use client"

import L from "leaflet"
import { useEffect, useMemo } from "react"
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet"
import { getPoi } from "@/lib/generateItinerary"
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
}

const dayColors = ["#ff385c", "#60a5fa", "#22c55e", "#f59e0b", "#a78bfa"]

export function ItineraryMap({ itineraryDraft, selectedPoiId, hoveredPoiId, onSelectPoi, selectedDay, showRouteLines, onFitBoundsRequest }: ItineraryMapProps) {
  const visibleDays = useMemo(() => itineraryDraft.days.filter((day) => selectedDay === "all" || day.dayNumber === selectedDay), [itineraryDraft.days, selectedDay])
  const markers = useMemo(() => flattenMarkers(visibleDays), [visibleDays])
  const center: [number, number] = markers[0] ? [markers[0].poi.lat, markers[0].poi.lng] : [16.4667, 107.5900]

  return (
    <MapContainer center={center} zoom={13} scrollWheelZoom className="h-full w-full">
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <FitBounds markers={markers} signal={onFitBoundsRequest} />
      <PanToSelected markers={markers} selectedPoiId={selectedPoiId} />
      {showRouteLines ? <DayRouteLayer days={visibleDays} /> : null}
      {markers.map((marker, index) => {
        const selected = marker.poi.id === selectedPoiId
        const hovered = marker.poi.id === hoveredPoiId
        return (
          <Marker
            key={`${marker.day.dayNumber}-${marker.item.id}`}
            position={[marker.poi.lat, marker.poi.lng]}
            icon={markerIcon(index + 1, marker.day.dayNumber, selected, hovered)}
            eventHandlers={{ click: () => onSelectPoi(marker.poi.id) }}
          >
            <Popup>
              <MapMarkerPopup marker={marker} />
            </Popup>
          </Marker>
        )
      })}
    </MapContainer>
  )
}

function DayRouteLayer({ days }: { days: ItineraryDay[] }) {
  return (
    <>
      {days.map((day, index) => {
        const positions = day.items
          .map((item) => getPoi(item.poiId))
          .filter((poi): poi is POI => Boolean(poi))
          .map((poi) => [poi.lat, poi.lng] as [number, number])
        if (positions.length < 2) return null
        return <Polyline key={day.dayNumber} positions={positions} pathOptions={{ color: dayColors[index % dayColors.length], weight: 4, opacity: 0.82 }} />
      })}
    </>
  )
}

function MapMarkerPopup({ marker }: { marker: MarkerEntry }) {
  return (
    <div className="min-w-[210px] text-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-black text-orange-950">{marker.poi.name}</p>
          <p className="mt-1 text-xs text-orange-950/60">Ngày {marker.day.dayNumber} · {marker.item.time}</p>
        </div>
        <span className="rounded-full bg-travel/15 px-2 py-1 text-[10px] font-black text-travel">{marker.poi.category}</span>
      </div>
      <p className="mt-2 text-xs leading-5 text-orange-950/60">{marker.poi.description}</p>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-orange-950/60">
        <span>{marker.poi.estimatedDurationMinutes} phút</span>
        <span>{formatCurrency(marker.poi.estimatedCost)}</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {marker.poi.tags.slice(0, 3).map((tag) => <span key={tag} className="rounded-full bg-orange-100 px-2 py-1 text-[10px] text-orange-950/60">{tag}</span>)}
      </div>
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

function markerIcon(order: number, dayNumber: number, selected: boolean, hovered: boolean) {
  const state = selected ? "selected" : hovered ? "hovered" : ""
  return L.divIcon({
    className: "",
    html: `<div class="trip-marker day-${dayNumber} ${state}">${order}</div>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -18],
  })
}

