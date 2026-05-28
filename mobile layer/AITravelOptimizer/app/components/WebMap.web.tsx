import React, { useEffect, useMemo } from "react"
import { View, StyleSheet } from "react-native"
import "leaflet/dist/leaflet.css"
import { MapContainer, TileLayer, Marker, Polyline, Popup, useMap } from "react-leaflet"
import L from "leaflet"
import { TravelItineraryStop } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"

// Map component bounds updater
const MapBoundsUpdater = ({ bounds }: { bounds: { ne: [number, number]; sw: [number, number] } | null }) => {
  const map = useMap()
  useEffect(() => {
    if (bounds) {
      const leafletBounds = L.latLngBounds(
        [bounds.sw[1], bounds.sw[0]], // [lat, lng]
        [bounds.ne[1], bounds.ne[0]]
      )
      map.fitBounds(leafletBounds, { padding: [50, 50] })
    }
  }, [bounds, map])
  return null
}

interface WebMapProps {
  dayStops: TravelItineraryStop[]
  hotelLocations: { dayIndex: number; location: { latitude: number; longitude: number } }[]
  routeGeoJSON: any
  selectedDayIndex: number
  selectedStopId: string | null
  cameraBounds: { ne: [number, number]; sw: [number, number] } | null
  onMarkerPress: (stop: TravelItineraryStop) => void
  itinerary?: any // Full itinerary passed from screen
}

// Day Colors Palette (Standard color coding by day)
const DAY_COLORS = [
  "#3b82f6", // Blue (Day 1)
  "#f97316", // Orange (Day 2)
  "#10b981", // Green (Day 3)
  "#8b5cf6", // Purple (Day 4)
  "#ec4899", // Pink (Day 5)
  "#06b6d4", // Cyan (Day 6)
  "#eab308", // Yellow (Day 7)
]

const getCategoryEmoji = (category: string) => {
  const c = (category || "").toLowerCase()
  if (c === "food") return "🍜"
  if (c === "cafe") return "☕"
  if (c === "culture") return "🏛️"
  if (c === "nature") return "🌳"
  if (c === "nightlife") return "🍻"
  if (c === "shopping") return "🛍️"
  if (c === "art") return "🎨"
  if (c === "wellness") return "💆"
  if (c === "adventure") return "🧗"
  if (c === "hotel") return "🏨"
  return "📍"
}

const formatTime = (minutes: number) => {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`
}

const formatFee = (fee: number) => {
  if (fee === 0) return "Miễn phí"
  return `${fee.toLocaleString("vi-VN")} ₫`
}

export const WebMap = ({
  dayStops,
  hotelLocations,
  routeGeoJSON,
  selectedDayIndex,
  selectedStopId,
  cameraBounds,
  onMarkerPress,
  itinerary,
}: WebMapProps) => {

  // Custom Hotel Icon
  const hotelIcon = useMemo(() => {
    return L.divIcon({
      html: `<div style="width: 36px; height: 36px; background: white; border-radius: 18px; display: flex; justify-content: center; align-items: center; box-shadow: 0 4px 8px rgba(0,0,0,0.25); font-size: 20px; border: 2px solid ${colors.palette.imperialGold};">🏨</div>`,
      className: "",
      iconSize: [36, 36],
      iconAnchor: [18, 18],
    })
  }, [])

  // Premium POI Icon Maker with Glassmorphism and Category Emojis
  const createPoiIcon = (idx: number, category: string, isActive: boolean) => {
    const size = isActive ? 44 : 36
    const border = isActive ? `3px solid ${colors.tint}` : "2px solid white"
    const bg = isActive ? "rgba(3, 115, 243, 0.95)" : "rgba(26, 35, 61, 0.9)"
    const emoji = getCategoryEmoji(category)
    return L.divIcon({
      html: `
        <div style="
          width: ${size}px;
          height: ${size}px;
          background: ${bg};
          border-radius: ${size / 2}px;
          border: ${border};
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          box-shadow: 0 4px 10px rgba(0,0,0,0.35);
          color: white;
          font-family: system-ui, sans-serif;
          transition: all 0.2s ease;
        ">
          <span style="font-size: ${isActive ? '15px' : '12px'}; line-height: 1.1;">${emoji}</span>
          <span style="font-size: ${isActive ? '11px' : '9px'}; font-weight: 800; margin-top: -1px; opacity: 0.95;">${idx + 1}</span>
        </div>
      `,
      className: "",
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
    })
  }

  // Handle Dispatch Events for custom HTML popups
  useEffect(() => {
    const handleViewDetail = (e: Event) => {
      const stop = (e as CustomEvent).detail as TravelItineraryStop
      if (stop) {
        onMarkerPress(stop)
      }
    }
    window.addEventListener("view-poi-detail", handleViewDetail)
    return () => window.removeEventListener("view-poi-detail", handleViewDetail)
  }, [onMarkerPress])

  // Extract Route Coordinates for all days to support multiday color coding
  const routeLines = useMemo(() => {
    const lines: { dayIndex: number; positions: [number, number][]; color: string }[] = []
    const totalDays = itinerary?.num_days || itinerary?.days?.length || 1

    for (let dIdx = 0; dIdx < totalDays; dIdx++) {
      let positions: [number, number][] = []
      const dayColor = DAY_COLORS[dIdx % DAY_COLORS.length]

      // 1. Try Mapbox GeoJSON first
      if (routeGeoJSON && routeGeoJSON.features) {
        const feature = routeGeoJSON.features.find((f: any) => f.properties.dayIndex === dIdx)
        if (feature && feature.geometry && feature.geometry.coordinates) {
          const coords = feature.geometry.coordinates
          positions = coords.map((c: [number, number]) => [c[1], c[0]] as [number, number])
        }
      }

      // 2. Fallback to straight-line connection if GeoJSON line is missing/empty
      if (positions.length === 0) {
        const dayData = itinerary?.days?.find((d: any) => d.day_index === dIdx + 1)
        const dayHotel = hotelLocations.find(h => h.dayIndex === dIdx + 1)
        
        if (dayData && dayData.stops && dayData.stops.length > 0) {
          if (dayHotel) {
            positions.push([dayHotel.location.latitude, dayHotel.location.longitude])
          }
          dayData.stops.forEach((stop: TravelItineraryStop) => {
            positions.push([stop.location.latitude, stop.location.longitude])
          })
          if (dayHotel) {
            positions.push([dayHotel.location.latitude, dayHotel.location.longitude])
          }
        } else if (dIdx + 1 === selectedDayIndex && dayStops.length > 0) {
          // If no itinerary was passed but dayStops is present
          if (dayHotel) {
            positions.push([dayHotel.location.latitude, dayHotel.location.longitude])
          }
          dayStops.forEach(stop => {
            positions.push([stop.location.latitude, stop.location.longitude])
          })
          if (dayHotel) {
            positions.push([dayHotel.location.latitude, dayHotel.location.longitude])
          }
        }
      }

      if (positions.length > 0) {
        lines.push({
          dayIndex: dIdx + 1,
          positions,
          color: dayColor,
        })
      }
    }
    return lines
  }, [routeGeoJSON, itinerary, hotelLocations, selectedDayIndex, dayStops])

  return (
    <View style={StyleSheet.absoluteFill}>
      <MapContainer
        center={[16.4637, 107.5909]} // Hue default
        zoom={13}
        style={{ width: "100%", height: "100%" }}
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {cameraBounds && <MapBoundsUpdater bounds={cameraBounds} />}

        {/* Dynamic Multi-day Route Lines */}
        {routeLines.map((line) => {
          const isCurrentDay = line.dayIndex === selectedDayIndex
          return (
            <Polyline
              key={`route-day-${line.dayIndex}`}
              positions={line.positions}
              pathOptions={{
                color: line.color,
                weight: isCurrentDay ? 5 : 2.5,
                opacity: isCurrentDay ? 0.9 : 0.45,
                dashArray: isCurrentDay ? undefined : "6, 6",
              }}
            />
          )
        })}

        {/* Hotels (Filtered by selected day for clarity) */}
        {hotelLocations.filter(h => h.dayIndex === selectedDayIndex).map((hotel, i) => (
          <Marker
            key={`hotel-${i}`}
            position={[hotel.location.latitude, hotel.location.longitude]}
            icon={hotelIcon}
          />
        ))}

        {/* Interactive POI Markers with Leaflet Popups */}
        {dayStops.map((stop, idx) => {
          const isActive = selectedStopId === stop.poi_id
          const stopCategory = stop.category || "default"
          return (
            <Marker
              key={`poi-${stop.poi_id}`}
              position={[stop.location.latitude, stop.location.longitude]}
              icon={createPoiIcon(idx, stopCategory, isActive)}
              eventHandlers={{
                click: () => onMarkerPress(stop),
              }}
            >
              <Popup closeButton={false}>
                <div style={{
                  fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                  color: "#1a233d",
                  minWidth: "180px",
                  maxWidth: "240px",
                  padding: "4px",
                }}>
                  <div style={{ fontWeight: 700, fontSize: "13.5px", marginBottom: "6px", lineHeight: 1.35, color: "#0f172a" }}>
                    {idx + 1}. {stop.poi_name}
                  </div>
                  <div style={{ fontSize: "11.5px", color: "#4b5563", marginBottom: "4px", display: "flex", alignItems: "center", gap: "4px" }}>
                    ⏱️ <span>{formatTime(stop.arrival_time_min)} - {formatTime(stop.departure_time_min)} ({stop.visit_duration_min} phút)</span>
                  </div>
                  <div style={{ fontSize: "11.5px", color: "#059669", fontWeight: 600, marginBottom: "8px" }}>
                    🎫 {formatFee(stop.entrance_fee)}
                  </div>
                  <button 
                    onClick={() => {
                      window.dispatchEvent(new CustomEvent('view-poi-detail', { detail: stop }));
                    }}
                    style={{
                      width: "100%",
                      background: "#0373f3",
                      color: "white",
                      border: "none",
                      padding: "6px 10px",
                      borderRadius: "6px",
                      fontWeight: 600,
                      fontSize: "11px",
                      cursor: "pointer",
                      textAlign: "center",
                      display: "block",
                      transition: "background 0.15s ease",
                    }}
                    onMouseOver={(e) => {
                      (e.currentTarget as HTMLButtonElement).style.background = '#025ec7';
                    }}
                    onMouseOut={(e) => {
                      (e.currentTarget as HTMLButtonElement).style.background = '#0373f3';
                    }}
                  >
                    Xem Chi Tiết ➔
                  </button>
                </div>
              </Popup>
            </Marker>
          )
        })}
      </MapContainer>
    </View>
  )
}
