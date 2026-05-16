import React, { useEffect, useMemo } from "react"
import { View, StyleSheet, Dimensions } from "react-native"
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
}

export const WebMap = ({
  dayStops,
  hotelLocations,
  routeGeoJSON,
  selectedDayIndex,
  selectedStopId,
  cameraBounds,
  onMarkerPress,
}: WebMapProps) => {
  
  // Custom Hotel Icon
  const hotelIcon = useMemo(() => {
    return L.divIcon({
      html: `<div style="width: 36px; height: 36px; background: white; border-radius: 18px; display: flex; justify-content: center; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.2); font-size: 20px;">🏨</div>`,
      className: "",
      iconSize: [36, 36],
      iconAnchor: [18, 18],
    })
  }, [])

  // Create POI Icon function
  const createPoiIcon = (idx: number, isActive: boolean) => {
    const size = isActive ? 40 : 32
    const border = isActive ? "3px solid white" : "2px solid white"
    return L.divIcon({
      html: `<div style="width: ${size}px; height: ${size}px; background: ${colors.tint}; border-radius: ${size / 2}px; border: ${border}; display: flex; justify-content: center; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.2); color: white; font-weight: bold; font-family: sans-serif; font-size: 14px;">${idx + 1}</div>`,
      className: "",
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
    })
  }

  // Parse GeoJSON coordinates for Leaflet polyline (Leaflet expects [lat, lng])
  const polylinePositions = useMemo(() => {
    if (!routeGeoJSON || !routeGeoJSON.features) return []
    const features = routeGeoJSON.features.filter((f: any) => f.properties.dayIndex === selectedDayIndex)
    if (features.length === 0) return []
    
    // Extract coords and flip [lng, lat] to [lat, lng]
    const coords = features[0].geometry.coordinates
    return coords.map((c: [number, number]) => [c[1], c[0]] as [number, number])
  }, [routeGeoJSON, selectedDayIndex])

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

        {/* Route Line */}
        {polylinePositions.length > 0 && (
          <Polyline
            positions={polylinePositions}
            pathOptions={{ color: colors.tint, weight: 4, opacity: 0.8 }}
          />
        )}

        {/* Hotels */}
        {hotelLocations.filter(h => h.dayIndex === selectedDayIndex).map((hotel, i) => (
          <Marker
            key={`hotel-${i}`}
            position={[hotel.location.latitude, hotel.location.longitude]}
            icon={hotelIcon}
          />
        ))}

        {/* POIs */}
        {dayStops.map((stop, idx) => {
          const isActive = selectedStopId === stop.poi_id
          return (
            <Marker
              key={`poi-${stop.poi_id}`}
              position={[stop.location.latitude, stop.location.longitude]}
              icon={createPoiIcon(idx, isActive)}
              eventHandlers={{
                click: () => onMarkerPress(stop),
              }}
            >
              <Popup>{stop.poi_name}</Popup>
            </Marker>
          )
        })}
      </MapContainer>
    </View>
  )
}
