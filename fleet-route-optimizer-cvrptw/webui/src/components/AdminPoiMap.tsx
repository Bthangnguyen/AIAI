"use client"

import L from "leaflet"
import { useEffect } from "react"
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet"
import type { AdminPoiRow } from "@/types/admin"

interface AdminPoiMapProps {
  pois: AdminPoiRow[]
  selectedUuid: string | null
  fitSignal: number
}

export function AdminPoiMap({ pois, selectedUuid, fitSignal }: AdminPoiMapProps) {
  const center: [number, number] = pois[0] ? [pois[0].latitude, pois[0].longitude] : [16.4667, 107.59]

  return (
    <MapContainer center={center} zoom={13} scrollWheelZoom className="h-full w-full rounded-2xl">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitAdminBounds pois={pois} signal={fitSignal} />
      <FlyToSelected pois={pois} selectedUuid={selectedUuid} />
      {pois.map((poi) => {
        const selected = poi.uuid === selectedUuid
        return (
          <Marker
            key={poi.uuid}
            position={[poi.latitude, poi.longitude]}
            icon={adminMarkerIcon(selected)}
          >
            <Popup>
              <div className="min-w-[180px]">
                <p className="text-sm font-black text-orange-950">{poi.name}</p>
                <p className="mt-1 text-xs text-orange-950/65">{poi.category}</p>
                {poi.tags.length ? (
                  <p className="mt-2 text-[11px] text-orange-950/55">{poi.tags.join(", ")}</p>
                ) : null}
              </div>
            </Popup>
          </Marker>
        )
      })}
    </MapContainer>
  )
}

function FitAdminBounds({ pois, signal }: { pois: AdminPoiRow[]; signal: number }) {
  const map = useMap()
  useEffect(() => {
    if (!pois.length) return
    const bounds = L.latLngBounds(pois.map((poi) => [poi.latitude, poi.longitude]))
    map.fitBounds(bounds, { padding: [34, 34], maxZoom: 14 })
  }, [map, pois, signal])
  return null
}

function FlyToSelected({ pois, selectedUuid }: { pois: AdminPoiRow[]; selectedUuid: string | null }) {
  const map = useMap()
  useEffect(() => {
    if (!selectedUuid) return
    const poi = pois.find((entry) => entry.uuid === selectedUuid)
    if (poi) map.flyTo([poi.latitude, poi.longitude], Math.max(map.getZoom(), 15), { duration: 0.65 })
  }, [map, pois, selectedUuid])
  return null
}

function adminMarkerIcon(selected: boolean) {
  const color = selected ? "#eab308" : "#ea580c"
  const ring = selected ? "box-shadow:0 0 0 3px rgba(234,179,8,0.45);" : ""
  return L.divIcon({
    className: "",
    html: `<div style="width:14px;height:14px;border-radius:9999px;background:${color};border:2px solid white;${ring}"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
    popupAnchor: [0, -10],
  })
}
