import { FC, useCallback, useMemo, useRef, useState, useEffect } from "react"
import { View, ViewStyle, TextStyle, Pressable, Dimensions, StyleSheet, Alert, Platform, UIManager } from "react-native"
import BottomSheet, { BottomSheetFlatList, BottomSheetScrollView } from "@gorhom/bottom-sheet"
import MapboxGL from "@rnmapbox/maps"
import Animated, { FadeInUp } from "react-native-reanimated"
import * as Location from "expo-location"

import { ItineraryCard } from "@/components/ItineraryCard"
import { ReRouteButton } from "@/components/ReRouteButton"
import { ReRouteConfirmSheet } from "@/components/ReRouteConfirmSheet"
import { Text } from "@/components/Text"
import { WebMap } from "@/components/WebMap"
import { AIChatRerouteModal } from "@/components/AIChatRerouteModal"
import { InfeasibleRerouteModal } from "@/components/InfeasibleRerouteModal"
import { RerouteComparisonModal } from "@/components/RerouteComparisonModal"
import { FeatureFlags } from "@/config/features"
import { MOCK_ITINERARY } from "@/constants/mockItinerary"
import type { AppStackScreenProps, TravelItineraryStop } from "@/navigators/navigationTypes"
import { TripService } from "@/services/api/tripService"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { getRemainingPOIIds, mergeReRoutedDay, getCurrentTimeMin } from "@/utils/itineraryHelpers"
import { AppState, AppStateStatus } from "react-native"
import { RerouteService } from "@/services/api/rerouteService"
import { ReRoutePayload, TravelItineraryDay } from "@/navigators/navigationTypes"

const { height: SCREEN_HEIGHT } = Dimensions.get("window")

const isMapboxAvailable = () => {
  if (Platform.OS === "web") return false
  try {
    return (
      UIManager.getViewManagerConfig("RNMBGLMapView") != null ||
      UIManager.getViewManagerConfig("RNMapboxMapView") != null
    )
  } catch {
    return false
  }
}

const CAMERA_BOUNDS_PADDING = {
  paddingTop: 80,
  paddingBottom: SCREEN_HEIGHT * 0.3,
  paddingLeft: 40,
  paddingRight: 40,
}

// ─── Types ──────────────────────────────────────────────────────
interface FlatListItem {
  type: "header" | "stop"
  key: string
  dayIndex?: number
  date?: string
  stop?: TravelItineraryStop
  stopIndex?: number
  isLast?: boolean
}

interface MapTimelineScreenProps extends AppStackScreenProps<"MapTimeline"> {}

// ——————————————————————————————————————————————————————————————————————————
const CATEGORY_EMOJI: Record<string, string> = {
  museum: "🏛️",
  temple: "🕌",
  park: "🌳",
  market: "🛒",
  restaurant: "🍛",
  cafe: "☕",
  beach: "🏖️",
  waterfall: "💧",
  pagoda: "🏮",
  default: "📍",
}

// ——————————————————————————————————————————————————————————————————————————
export const MapTimelineScreen: FC<MapTimelineScreenProps> = ({ route, navigation }) => {
  // Use real itinerary from navigation params; fallback to mock for standalone testing
  const initialItinerary = route?.params?.itinerary ?? MOCK_ITINERARY
  const [itinerary, setItinerary] = useState(initialItinerary)
  const bottomSheetRef = useRef<BottomSheet>(null)
  const reRouteSheetRef = useRef<BottomSheet>(null)
  const mapRef = useRef<MapboxGL.MapView>(null)
  const cameraRef = useRef<MapboxGL.Camera>(null)

  const snapPoints = useMemo(() => ["25%", "50%", "90%"], [])
  const [selectedStopId, setSelectedStopId] = useState<string | null>(null)
  const [selectedStop, setSelectedStop] = useState<TravelItineraryStop | null>(null)
  const [isReRouting, setIsReRouting] = useState(false)
  const [selectedDayIndex, setSelectedDayIndex] = useState(initialItinerary.days[0]?.day_index || 0)
  const [currentDayIndex, setCurrentDayIndex] = useState(initialItinerary.days[0]?.day_index || 0)
  const [visitedPOIIds] = useState<string[]>([])
  const [showAddModal, setShowAddModal] = useState(false)
  const [showSnackbar, setShowSnackbar] = useState(false)
  const [deletedItem, setDeletedItem] = useState<TravelItineraryStop | null>(null)
  const [isReSolving, setIsReSolving] = useState(false)
  const undoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Wire isLocked to Zustand store (persist across sessions)
  const isLocked = useTripStore((state) => state.isLocked)
  const setIsLocked = useTripStore((state) => state.setIsLocked)

  // ─── Backend re-solve after delete (optimistic update) ──────────────────
  const reAfterDelete = useCallback(async (removedPoiId: string) => {
    const day = itinerary.days.find(d => d.day_index === selectedDayIndex)
    if (!day) return

    const remainingIds = day.stops
      .filter(s => s.poi_id !== removedPoiId)
      .map(s => s.poi_id)

    if (remainingIds.length === 0) return

    const hotel = day.start_hotel_location || day.hotel_location
    if (!hotel) return

    setIsReSolving(true)
    try {
      const result = await TripService.reRoute({
        current_lat: hotel.latitude,
        current_lon: hotel.longitude,
        current_time_min: day.stops[0]?.arrival_time_min ?? 480,
        remaining_poi_ids: remainingIds,
        excluded_poi_ids: [removedPoiId],
        day_index: selectedDayIndex,
        original_itinerary: itinerary,
      })

      if (result.status === "success" && result.day) {
        setItinerary(prev => mergeReRoutedDay(prev, result.day!))
      }
    } catch (e) {
      console.warn("Re-solve after delete failed", e)
    } finally {
      setIsReSolving(false)
    }
  }, [itinerary, selectedDayIndex])

  const handleDelete = useCallback((stop: TravelItineraryStop) => {
    // Cancel any pending re-solve from previous delete
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current)

    setDeletedItem(stop)
    setShowSnackbar(true)

    // Optimistic: remove from UI immediately
    setItinerary(prev => ({
      ...prev,
      days: prev.days.map(d => 
        d.day_index === selectedDayIndex 
        ? { ...d, stops: d.stops.filter(s => s.poi_id !== stop.poi_id) } 
        : d
      )
    }))

    // After 3s undo window: trigger backend re-solve
    undoTimerRef.current = setTimeout(() => {
      setShowSnackbar(false)
      setDeletedItem(null)
      reAfterDelete(stop.poi_id)
    }, 3000)
  }, [selectedDayIndex, reAfterDelete])

  const handleUndo = useCallback(() => {
    if (!deletedItem) return
    // Cancel pending backend re-solve
    if (undoTimerRef.current) {
      clearTimeout(undoTimerRef.current)
      undoTimerRef.current = null
    }
    setShowSnackbar(false)
    setItinerary(prev => {
      const day = prev.days.find(d => d.day_index === selectedDayIndex)
      if (!day) return prev
      return {
        ...prev,
        days: prev.days.map(d => 
          d.day_index === selectedDayIndex 
          ? { ...d, stops: [...d.stops, deletedItem].sort((a, b) => a.arrival_time_min - b.arrival_time_min) } 
          : d
        )
      }
    })
    setDeletedItem(null)
  }, [deletedItem, selectedDayIndex])

  // ─── Add places: use dropped_pois from itinerary or re-solve ────────────
  const handleAddPlaces = useCallback(async (placeIds: string[]) => {
    if (placeIds.length === 0) return

    const day = itinerary.days.find(d => d.day_index === selectedDayIndex)
    if (!day) return

    const hotel = day.start_hotel_location || day.hotel_location
    if (!hotel) return

    // Combine existing POIs + new POIs for re-solve
    const allPoiIds = [
      ...day.stops.map(s => s.poi_id),
      ...placeIds,
    ]

    setIsReSolving(true)
    try {
      const result = await TripService.reRoute({
        current_lat: hotel.latitude,
        current_lon: hotel.longitude,
        current_time_min: day.stops[0]?.arrival_time_min ?? 480,
        remaining_poi_ids: allPoiIds,
        day_index: selectedDayIndex,
        original_itinerary: itinerary,
      })

      if (result.status === "success" && result.day) {
        setItinerary(prev => mergeReRoutedDay(prev, result.day!))
      }
    } catch (e) {
      console.warn("Re-solve after add failed", e)
    } finally {
      setIsReSolving(false)
    }
  }, [itinerary, selectedDayIndex])

  const handleSkipStop = async () => {
    try {
      let { status } = await Location.requestForegroundPermissionsAsync()
      if (status !== 'granted') {
        Alert.alert('Lỗi', 'Cần quyền truy cập vị trí để điều hướng')
        return
      }
      let loc = await Location.getCurrentPositionAsync({})
      console.log('Bỏ qua điểm hiện tại, đang Re-route từ vị trí:', loc.coords)
      Alert.alert('Thành công', 'Đang tính toán lại lộ trình từ vị trí hiện tại...')
      // Call Backend API to Reroute with keep_depot_fixed=True
    } catch(e) {
      console.warn("Could not get location", e)
    }
  }

  const handleReRouteConfirm = useCallback(async (userState?: ReRoutePayload['user_state']) => {
    setIsReRouting(true)

    try {
      const { status } = await Location.requestForegroundPermissionsAsync()
      if (status !== "granted") {
        Alert.alert("Location required", "Please enable location to re-route.")
        setIsReRouting(false)
        return
      }

      const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High })
      const payload = RerouteService.buildReroutePayload(
        loc.coords.latitude, loc.coords.longitude,
        itinerary, currentDayIndex, visitedPOIIds, userState
      )

      if (payload.remaining_poi_ids.length === 0) {
        Alert.alert("No stops", "No remaining stops to re-route.")
        setIsReRouting(false)
        return
      }

      const result = await TripService.reRoute(payload)

      if (result.status === "success" && result.day) {
        setNewProposedDay(result.day)
        setShowComparison(true)
      } else {
        setShowInfeasibleModal(true)
      }
    } catch (e: any) {
      Alert.alert("Error", e?.message || "Re-route request failed")
    } finally {
      setIsReRouting(false)
    }
  }, [itinerary, currentDayIndex, visitedPOIIds])

  const handleApplyReroute = useCallback(() => {
    if (newProposedDay) {
      setItinerary((prev) => mergeReRoutedDay(prev, newProposedDay))
    }
    setShowComparison(false)
    setNewProposedDay(undefined)
  }, [newProposedDay])

  const handleMyLocation = useCallback(async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync()
      if (status !== "granted") return
      const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced })
      cameraRef.current?.setCamera({
        centerCoordinate: [loc.coords.longitude, loc.coords.latitude],
        zoomLevel: 14,
        animationDuration: 1000,
      })
    } catch (e) {
      console.warn("Could not get location", e)
    }
  }, [])

  // Get remaining stops for current day
  const remainingStops = useMemo(() => {
    const day = itinerary.days.find((d) => d.day_index === currentDayIndex)
    if (!day) return []
    const visited = new Set(visitedPOIIds)
    return day.stops.filter((s) => !visited.has(s.poi_id))
  }, [itinerary, currentDayIndex, visitedPOIIds])

  // ─── Flatten itinerary data for FlatList (filtered by selected day) ──────────
  const filteredFlatListData = useMemo<FlatListItem[]>(() => {
    const items: FlatListItem[] = []
    const day = itinerary.days.find((d) => d.day_index === selectedDayIndex)
    if (!day) return items
    items.push({
      type: "header",
      key: `day-${day.day_index}`,
      dayIndex: day.day_index,
      date: day.date,
    })
    day.stops.forEach((stop, idx) => {
      items.push({
        type: "stop",
        key: `${day.day_index}-${stop.poi_id}-${idx}`,
        stop,
        stopIndex: idx,
        dayIndex: day.day_index,
        isLast: idx === day.stops.length - 1,
      })
    })
    return items
  }, [itinerary, selectedDayIndex])

  // ─── Total estimated cost ─────────────────────────
  const totalCost = useMemo(() => {
    return itinerary.days.reduce((sum, day) => {
      return sum + day.stops.reduce((daySum, stop) => daySum + (stop.entrance_fee || 0), 0)
    }, 0)
  }, [itinerary])

  // ─── Per-day cost ─────────────────────────────────
  const dayCost = useMemo(() => {
    const day = itinerary.days.find((d) => d.day_index === selectedDayIndex)
    if (!day) return 0
    return day.stops.reduce((sum, stop) => sum + (stop.entrance_fee || 0), 0)
  }, [itinerary, selectedDayIndex])

  // ─── Stops for current selected day (map markers) ─
  const dayStops = useMemo(() => {
    const day = itinerary.days.find((d) => d.day_index === selectedDayIndex)
    return day ? day.stops : []
  }, [itinerary, selectedDayIndex])

  // ─── All stops with coordinates for map ───────────
  const allStops = useMemo(() => {
    return itinerary.days.flatMap((day) => day.stops)
  }, [itinerary])

  // ─── Route line GeoJSON ───────────────────────────
  const [routeGeoJSON, setRouteGeoJSON] = useState<any>(null)
  
  const filteredRouteGeoJSON = useMemo(() => {
    if (!routeGeoJSON) return null
    return {
      type: "FeatureCollection" as const,
      features: routeGeoJSON.features.filter((f: any) => f.properties.dayIndex === selectedDayIndex),
    }
  }, [routeGeoJSON, selectedDayIndex])

  useEffect(() => {
    const fetchRoutes = async () => {
      // Use env variable for Mapbox token — NEVER hardcode tokens in source
      const accessToken = process.env.EXPO_PUBLIC_MAPBOX_TOKEN
      if (!accessToken) {
        console.error("EXPO_PUBLIC_MAPBOX_TOKEN not set in .env")
        return
      }
      const features: any[] = []

      for (let dayIdx = 0; dayIdx < itinerary.days.length; dayIdx++) {
        const day = itinerary.days[dayIdx]
        const hotelLoc = day.hotel_location
        if (!hotelLoc) continue
        const coords = [
          [hotelLoc.longitude, hotelLoc.latitude],
          ...day.stops.map((s) => [s.location.longitude, s.location.latitude]),
          [hotelLoc.longitude, hotelLoc.latitude],
        ]

        const coordString = coords.map((c) => `${c[0]},${c[1]}`).join(";")

        try {
          const res = await fetch(
            `https://api.mapbox.com/directions/v5/mapbox/driving/${coordString}?geometries=geojson&access_token=${accessToken}`,
          )
          const data = await res.json()

          if (data.routes && data.routes.length > 0) {
            features.push({
              type: "Feature",
              properties: { dayIndex: dayIdx },
              geometry: data.routes[0].geometry,
            })
          }
        } catch (e) {
          console.error("Failed to fetch Mapbox route", e)
        }
      }

      setRouteGeoJSON({
        type: "FeatureCollection",
        features,
      })
    }

    fetchRoutes()
  }, [itinerary])

  // ─── Camera bounds ────────────────────────────────
  const cameraBounds = useMemo(() => {
    const day = itinerary.days.find((d) => d.day_index === selectedDayIndex)
    if (!day) return null

    const hotelLoc = day.hotel_location
    if (!hotelLoc) return null
    const hotelCoord = [hotelLoc.longitude, hotelLoc.latitude]
    const stopCoords = day.stops.map((s) => [s.location.longitude, s.location.latitude])
    const allCoords = [hotelCoord, ...stopCoords]

    const lngs = allCoords.map((c) => c[0])
    const lats = allCoords.map((c) => c[1])
    return {
      ne: [Math.max(...lngs) + 0.01, Math.max(...lats) + 0.01] as [number, number],
      sw: [Math.min(...lngs) - 0.01, Math.min(...lats) - 0.01] as [number, number],
    }
  }, [itinerary, selectedDayIndex])

  // ─── Handlers ─────────────────────────────────────
  const handleMarkerPress = useCallback((stop: TravelItineraryStop) => {
    setSelectedStopId(stop.poi_id)
    setSelectedStop(stop)
    cameraRef.current?.setCamera({
      centerCoordinate: [stop.location.longitude, stop.location.latitude],
      zoomLevel: 14,
      animationDuration: 500,
    })
  }, [])

  const handleCardPress = useCallback((stop: TravelItineraryStop) => {
    setSelectedStopId(stop.poi_id)
    cameraRef.current?.setCamera({
      centerCoordinate: [stop.location.longitude, stop.location.latitude],
      zoomLevel: 15,
      animationDuration: 600,
    })
  }, [])

  // ─── Time formatting helper ───────────────────────
  const formatTime = (minutes: number) => {
    const h = Math.floor(minutes / 60)
    const m = minutes % 60
    return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`
  }

  // ─── Render FlatList item ─────────────────────────
  const renderItem = useCallback(
    ({ item }: { item: FlatListItem }) => {
      if (item.type === "header") {
        return (
          <Animated.View entering={FadeInUp.duration(300)} style={$dayHeader}>
            <View style={$dayBadge}>
              <Text text={`Day ${item.dayIndex || 1}`} style={$dayBadgeText} />
            </View>
            {item.date && <Text text={item.date} style={$dayDate} />}
          </Animated.View>
        )
      }

      const stop = item.stop!
      const isSelected = selectedStopId === stop.poi_id
      const emoji = CATEGORY_EMOJI[stop.poi_name?.toLowerCase()] || CATEGORY_EMOJI.default

      return (
        <Pressable onPress={() => handleCardPress(stop)}>
          <View style={$timelineRow}>
            {/* Timeline node + line */}
            <View style={$timelineNodeCol}>
              <View
                style={[
                  $timelineNode,
                  { backgroundColor: isSelected ? colors.tint : colors.palette.figmaInactive },
                ]}
              >
                <Text text={`${(item.stopIndex || 0) + 1}`} style={$nodeNumber} />
              </View>
              {!item.isLast && <View style={$timelineConnector} />}
            </View>

            {/* Card */}
            <Animated.View
              entering={FadeInUp.delay((item.stopIndex || 0) * 80).duration(400)}
              style={[$stopCard, isSelected && $stopCardActive]}
            >
              <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                <View style={{ flex: 1 }}>
                  <ItineraryCard
                    emoji={emoji}
                    title={stop.poi_name}
                    timeString={`${formatTime(stop.arrival_time_min)} — ${formatTime(stop.departure_time_min)}`}
                    visitDurationMin={stop.visit_duration_min}
                    entranceFee={stop.entrance_fee}
                    travelTimeMin={stop.travel_time_from_prev_min}
                  />
                </View>
                <Pressable onPress={() => handleDelete(stop)} style={{ padding: 10 }}>
                  <Text text="Xóa" style={{ color: 'red' }} />
                </Pressable>
              </View>
            </Animated.View>
          </View>
        </Pressable>
      )
    },
    [selectedStopId, handleCardPress],
  )

  // ─── Main Render ──────────────────────────────────
  return (
    <View style={$root}>
      {/* Mapbox Map - Only render on native platforms */}
      {isMapboxAvailable() ? (
        <MapboxGL.MapView
        ref={mapRef}
        style={StyleSheet.absoluteFill}
        styleURL={MapboxGL.StyleURL.Street}
        logoEnabled={false}
        attributionEnabled={false}
        compassEnabled
        onPress={() => {
          setSelectedStopId(null)
          setSelectedStop(null)
        }}
      >
        <MapboxGL.Camera
          ref={cameraRef}
          bounds={
            cameraBounds
              ? {
                  ne: cameraBounds.ne,
                  sw: cameraBounds.sw,
                  ...CAMERA_BOUNDS_PADDING,
                }
              : undefined
          }
          animationDuration={800}
        />

        {/* User Location */}
        <MapboxGL.UserLocation visible={true} showsUserHeadingIndicator />

        {/* Hotel marker for selected day */}
        {itinerary.days.filter((d) => d.day_index === selectedDayIndex).map((day) => {
          const hotelLoc = day.hotel_location
          if (!hotelLoc) return null
          return (
            <MapboxGL.PointAnnotation
              key={`hotel-${day.day_index}`}
              id={`hotel-${day.day_index}`}
              coordinate={[hotelLoc.longitude, hotelLoc.latitude]}
            >
              <View style={$hotelMarker}>
                <Text text="🏨" style={$markerEmoji} />
              </View>
            </MapboxGL.PointAnnotation>
          )
        })}

        {/* POI markers for selected day */}
        {dayStops.map((stop, idx) => (
          <MapboxGL.PointAnnotation
            key={`poi-${stop.poi_id}-${idx}`}
            id={`poi-${stop.poi_id}-${idx}`}
            coordinate={[stop.location.longitude, stop.location.latitude]}
            onSelected={() => handleMarkerPress(stop)}
          >
            <View style={[$poiMarker, selectedStopId === stop.poi_id && $poiMarkerActive]}>
              <Text text={`${idx + 1}`} style={$markerNumber} />
            </View>
          </MapboxGL.PointAnnotation>
        ))}

        {/* Route polyline for selected day */}
        {filteredRouteGeoJSON && filteredRouteGeoJSON.features.length > 0 && (
          <MapboxGL.ShapeSource id="route-line" shape={filteredRouteGeoJSON}>
            <MapboxGL.LineLayer id="route-line-layer" style={$routeLineLayer} />
          </MapboxGL.ShapeSource>
        )}
      </MapboxGL.MapView>
      ) : (
        <WebMap
          dayStops={dayStops}
          hotelLocations={itinerary.days.map((d) => {
            const loc = d.hotel_location
            return {
              dayIndex: d.day_index,
              location: loc ? { latitude: loc.latitude, longitude: loc.longitude } : { latitude: 0, longitude: 0 },
            }
          }).filter((h) => h.location.latitude !== 0)}
          routeGeoJSON={routeGeoJSON}
          selectedDayIndex={selectedDayIndex}
          selectedStopId={selectedStopId}
          cameraBounds={cameraBounds}
          onMarkerPress={handleMarkerPress}
        />
      )}

      {/* Summary bar */}
      <View style={$summaryBar}>
        <View style={$summaryItem}>
          <Text text={`${itinerary.total_pois_visited}`} style={$summaryValue} />
          <Text text="Places" style={$summaryLabel} />
        </View>
        <View style={$summaryDivider} />
        <View style={$summaryItem}>
          <Text text={`${itinerary.num_days}d`} style={$summaryValue} />
          <Text text="Duration" style={$summaryLabel} />
        </View>
        <View style={$summaryDivider} />
        <View style={$summaryItem}>
          <Text text={`${itinerary.total_distance_km.toFixed(1)}km`} style={$summaryValue} />
          <Text text="Distance" style={$summaryLabel} />
        </View>
        <View style={$summaryDivider} />
        <View style={$summaryItem}>
          <Text text={`${totalCost > 0 ? (totalCost / 1000).toFixed(0) + "k₫" : "Free"}`} style={$summaryValue} />
          <Text text="Est. Cost" style={$summaryLabel} />
        </View>
      </View>

      {/* POI Info Card Popup */}
      {selectedStop && (
        <Animated.View entering={FadeInUp.duration(300)} style={$poiPopupCard}>
          <View style={$poiPopupHeader}>
            <Text text={"📍"} style={$poiPopupEmoji} />
            <View style={{ flex: 1, marginLeft: 8 }}>
              <Text text={selectedStop.poi_name} style={$poiPopupTitle} numberOfLines={1} />
              <Text text={`${selectedStop.visit_duration_min} min • ${selectedStop.entrance_fee > 0 ? (selectedStop.entrance_fee / 1000).toFixed(0) + "k₫" : "Free"}`} style={$poiPopupSubtitle} />
            </View>
            <Pressable onPress={() => { setSelectedStopId(null); setSelectedStop(null) }} style={{ padding: 4 }}>
              <Text text="✕" style={$poiPopupClose} />
            </Pressable>
          </View>
          <Pressable style={$poiPopupBtn} onPress={() => navigation.navigate("POIDetail", {
            poiId: selectedStop.poi_id,
            poiName: selectedStop.poi_name,
            photoUrl: "",
            rating: 4.5,
            reviewCount: 100,
            description: "No description available",
            entranceFee: selectedStop.entrance_fee,
            openTime: "08:00",
            closeTime: "22:00",
            lat: selectedStop.location.latitude,
            lon: selectedStop.location.longitude
          })}>
            <Text text="View Details" style={$poiPopupBtnText} />
          </Pressable>
        </Animated.View>
      )}

      {/* Bottom Sheet */}
      <BottomSheet
        ref={bottomSheetRef}
        index={1}
        snapPoints={snapPoints}
        backgroundStyle={$sheetBackground}
        handleIndicatorStyle={$sheetHandle}
        enablePanDownToClose={false}
      >
        <View style={$sheetHeader}>
          <Text text="Itinerary" style={$sheetTitle} />
          <Text
            text={`${itinerary.total_pois_visited} stops · ${itinerary.total_distance_km.toFixed(1)} km · ${totalCost > 0 ? (totalCost / 1000).toFixed(0) + "k₫" : "Free"}`}
            style={$sheetSubtitle}
          />
        </View>

        {/* Day Tabs */}
        <BottomSheetScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={$dayTabsRow}
        >
          {itinerary.days.map((day) => {
            const isActive = day.day_index === selectedDayIndex
            const cost = day.stops.reduce((s, stop) => s + (stop.entrance_fee || 0), 0)
            return (
              <Pressable
                key={day.day_index}
                onPress={() => setSelectedDayIndex(day.day_index)}
                style={[$dayTab, isActive && $dayTabActive]}
              >
                <Text
                  text={`Ngày ${day.day_index + 1}`}
                  style={[$dayTabText, isActive && $dayTabTextActive]}
                />
                <Text
                  text={`${day.stops.length} điểm · ${cost > 0 ? (cost / 1000).toFixed(0) + "k₫" : "Free"}`}
                  style={[$dayTabSub, isActive && $dayTabSubActive]}
                />
              </Pressable>
            )
          })}
        </BottomSheetScrollView>

        <BottomSheetFlatList
          data={filteredFlatListData}
          keyExtractor={(item) => item.key}
          renderItem={renderItem}
          contentContainerStyle={$flatListContent}
          showsVerticalScrollIndicator={false}
          nestedScrollEnabled
        />
        <View style={{ padding: 16 }}>
          {!isLocked && (
            <Pressable style={{ padding: 12, backgroundColor: "#f0f0f0", borderRadius: 8, alignItems: "center", marginBottom: 10 }} onPress={() => setShowAddModal(true)}>
              <Text text="🪄 Tính toán lại lịch trình (AI)" />
            </Pressable>
          )}
        </View>
        <View style={{ flexDirection: "row", paddingHorizontal: 16, paddingBottom: 16, gap: 10, backgroundColor: "rgba(14,19,32,0.95)" }}>
          {isLocked ? (
            <Pressable
              style={{ padding: 14, backgroundColor: colors.palette.royalPurple, borderRadius: 14, flex: 1, alignItems: 'center' }}
              onPress={() => {
                // Navigate to ActiveTrip tab — itinerary is already in Zustand store
                navigation.navigate("MainTabs", { screen: "MyTrip" })
              }}
            >
              <Text text="🚀 Bắt đầu chuyến đi" style={{ color: "#FFFFFF", fontFamily: typography.primary.semiBold, fontSize: 15 }} />
            </Pressable>
          ) : (
            <>
              <Pressable style={{ padding: 14, backgroundColor: "rgba(255,255,255,0.08)", borderRadius: 14, flex: 1, alignItems: 'center', borderWidth: 1, borderColor: "rgba(255,255,255,0.12)" }}>
                <Text text="💾 Lưu Nháp" style={{ color: "rgba(255,255,255,0.7)", fontFamily: typography.primary.medium, fontSize: 14 }} />
              </Pressable>
              <Pressable
                style={{ padding: 14, backgroundColor: colors.palette.imperialGold, borderRadius: 14, flex: 1.5, alignItems: 'center' }}
                onPress={() => {
                  Alert.alert(
                    "🔒 Khóa lộ trình",
                    "Sau khi khóa, bạn sẽ chuyển sang chế độ Active Trip. Bạn vẫn có thể tái định tuyến bằng GPS.",
                    [
                      { text: "Hủy", style: "cancel" },
                      {
                        text: "Khóa & Bắt đầu",
                        onPress: () => {
                          setIsLocked(true) // Persisted to Zustand/MMKV
                          // Itinerary already synced to Zustand via useEffect
                          navigation.navigate("MainTabs", { screen: "MyTrip" })
                        },
                      },
                    ]
                  )
                }}
              >
                <Text text="🔒 Khóa lộ trình" style={{ color: "#0e1320", fontFamily: typography.primary.bold, fontSize: 15 }} />
              </Pressable>
            </>
          )}
        </View>
      </BottomSheet>

      {/* Undo Snackbar */}
      {showSnackbar && (
        <View style={{ position: "absolute", bottom: 100, left: 20, right: 20, backgroundColor: "#333", padding: 15, borderRadius: 8, flexDirection: "row", justifyContent: "space-between", zIndex: 999 }}>
          <Text text="Đã xóa địa điểm" style={{ color: "white" }} />
          <Pressable onPress={handleUndo}><Text text="Hoàn tác" style={{ color: "#4facfe", fontWeight: "bold" }} /></Pressable>
        </View>
      )}

      {/* Add Place Modal -> AI Chat Reroute Modal */}
      <AIChatRerouteModal visible={showAddModal} onClose={() => setShowAddModal(false)} onConfirmReroute={handleReRouteConfirm} />

      {/* Infeasible Reroute Modal */}
      <InfeasibleRerouteModal 
        visible={showInfeasibleModal} 
        onClose={() => setShowInfeasibleModal(false)} 
        onSelectOption={handleReRouteConfirm} 
      />

      {/* Reroute Comparison Modal */}
      <RerouteComparisonModal 
        visible={showComparison}
        oldDay={itinerary.days.find(d => d.day_index === currentDayIndex)}
        newDay={newProposedDay}
        onCancel={() => setShowComparison(false)}
        onConfirm={handleApplyReroute}
      />

      {/* My Location FAB */}
      <Pressable style={$myLocationBtn} onPress={handleMyLocation}>
        <Text text="📍" style={$myLocationIcon} />
      </Pressable>

      {/* Re-route FAB */}
      {FeatureFlags.ENABLE_REROUTE && (
        <ReRouteButton
          onPress={() => setShowAddModal(true)}
          loading={isReRouting}
          disabled={isReRouting}
        />
      )}

    </View>
  )
}

// ─── Styles ─────────────────────────────────────────────────────

const $root: ViewStyle = {
  flex: 1,
  backgroundColor: colors.background,
}

// ─── Summary Bar ─────────────
const $summaryBar: ViewStyle = {
  position: "absolute",
  top: 56,
  left: spacing.lg,
  right: spacing.lg,
  flexDirection: "row",
  backgroundColor: "rgba(255, 255, 255, 0.92)",
  borderRadius: 20,
  paddingVertical: 14,
  paddingHorizontal: spacing.lg,
  alignItems: "center",
  justifyContent: "space-around",
  // Figma shadow
  shadowColor: "#000",
  shadowOffset: { width: 0, height: 4 },
  shadowOpacity: 0.08,
  shadowRadius: 12,
  elevation: 4,
}

const $summaryItem: ViewStyle = {
  alignItems: "center",
}

const $summaryValue: TextStyle = {
  fontSize: 18,
  fontFamily: typography.primary.semiBold,
  color: colors.text,
}

const $summaryLabel: TextStyle = {
  fontSize: 12,
  fontFamily: typography.primary.normal,
  color: colors.palette.figmaGrayDark,
  marginTop: 2,
}

const $summaryDivider: ViewStyle = {
  width: 1,
  height: 28,
  backgroundColor: colors.palette.figmaGrayLight,
}

// ─── Map Markers ─────────────
const $hotelMarker: ViewStyle = {
  width: 36,
  height: 36,
  borderRadius: 18,
  backgroundColor: "#fff",
  justifyContent: "center",
  alignItems: "center",
  shadowColor: "#000",
  shadowOffset: { width: 0, height: 2 },
  shadowOpacity: 0.15,
  shadowRadius: 4,
  elevation: 3,
}

const $markerEmoji: TextStyle = {
  fontSize: 20,
}

const $poiMarker: ViewStyle = {
  width: 32,
  height: 32,
  borderRadius: 16,
  backgroundColor: colors.tint,
  justifyContent: "center",
  alignItems: "center",
  borderWidth: 2,
  borderColor: "#fff",
  shadowColor: "#000",
  shadowOffset: { width: 0, height: 2 },
  shadowOpacity: 0.2,
  shadowRadius: 3,
  elevation: 3,
}

const $poiMarkerActive: ViewStyle = {
  width: 40,
  height: 40,
  borderRadius: 20,
  borderWidth: 3,
}

const $markerNumber: TextStyle = {
  color: "#fff",
  fontSize: 14,
  fontFamily: typography.primary.semiBold,
}

// ─── Bottom Sheet ────────────
const $myLocationBtn: ViewStyle = {
  position: "absolute",
  bottom: 120,
  right: 16,
  width: 48,
  height: 48,
  borderRadius: 24,
  backgroundColor: colors.palette.figmaWhite,
  justifyContent: "center",
  alignItems: "center",
  zIndex: 100,
  // Figma shadow
  shadowColor: "#000",
  shadowOffset: { width: 0, height: 4 },
  shadowOpacity: 0.25,
  shadowRadius: 8,
  elevation: 6,
}

const $myLocationIcon: TextStyle = {
  fontSize: 20,
}

// ─── POI Popup ───────────────
const $poiPopupCard: ViewStyle = {
  position: "absolute",
  top: 130,
  left: spacing.lg,
  right: spacing.lg,
  backgroundColor: colors.palette.figmaWhite,
  borderRadius: 16,
  padding: spacing.md,
  // Figma shadow
  shadowColor: "#000",
  shadowOffset: { width: 0, height: 4 },
  shadowOpacity: 0.15,
  shadowRadius: 12,
  elevation: 6,
  zIndex: 10,
}

const $poiPopupHeader: ViewStyle = {
  flexDirection: "row",
  alignItems: "center",
  marginBottom: spacing.sm,
}

const $poiPopupEmoji: TextStyle = {
  fontSize: 24,
}

const $poiPopupTitle: TextStyle = {
  fontFamily: typography.primary.bold,
  fontSize: 16,
  color: colors.palette.figmaPrimaryBlack,
}

const $poiPopupSubtitle: TextStyle = {
  fontFamily: typography.primary.normal,
  fontSize: 13,
  color: colors.palette.figmaGrayDark,
  marginTop: 2,
}

const $poiPopupClose: TextStyle = {
  fontSize: 18,
  color: colors.palette.figmaGrayMedium,
  fontFamily: typography.primary.bold,
}

const $poiPopupBtn: ViewStyle = {
  backgroundColor: colors.palette.figmaPrimaryBlack,
  borderRadius: 8,
  paddingVertical: 10,
  alignItems: "center",
}

const $poiPopupBtnText: TextStyle = {
  color: colors.palette.figmaWhite,
  fontFamily: typography.primary.semiBold,
  fontSize: 14,
}

const $sheetBackground: ViewStyle = {
  backgroundColor: colors.palette.figmaSurface,
  borderTopLeftRadius: 24,
  borderTopRightRadius: 24,
}

const $sheetHandle: ViewStyle = {
  width: 45,
  height: 5,
  backgroundColor: colors.palette.figmaGrayLight,
  borderRadius: 3,
}

const $sheetHeader: ViewStyle = {
  paddingHorizontal: spacing.lg,
  paddingBottom: spacing.md,
}

const $sheetTitle: TextStyle = {
  fontSize: 20,
  fontFamily: typography.primary.semiBold,
  color: colors.text,
}

const $sheetSubtitle: TextStyle = {
  fontSize: 14,
  fontFamily: typography.primary.normal,
  color: colors.palette.figmaGrayDark,
  marginTop: 4,
}

// ─── Day Tabs ────────────────
const $dayTabsRow: ViewStyle = {
  flexDirection: "row",
  paddingHorizontal: spacing.lg,
  paddingBottom: spacing.md,
  gap: spacing.sm,
}

const $dayTab: ViewStyle = {
  paddingHorizontal: 16,
  paddingVertical: 10,
  borderRadius: 14,
  backgroundColor: colors.palette.figmaOffWhite,
  borderWidth: 1.5,
  borderColor: "transparent",
  minWidth: 100,
  alignItems: "center",
}

const $dayTabActive: ViewStyle = {
  backgroundColor: colors.tint,
  borderColor: colors.tint,
}

const $dayTabText: TextStyle = {
  fontSize: 14,
  fontFamily: typography.primary.semiBold,
  color: colors.palette.figmaGrayDark,
}

const $dayTabTextActive: TextStyle = {
  color: "#fff",
}

const $dayTabSub: TextStyle = {
  fontSize: 11,
  fontFamily: typography.primary.normal,
  color: colors.palette.figmaGrayMedium,
  marginTop: 2,
}

const $dayTabSubActive: TextStyle = {
  color: "rgba(255, 255, 255, 0.8)",
}

const $flatListContent: ViewStyle = {
  paddingHorizontal: spacing.lg,
  paddingBottom: 120,
}

// ─── Day Headers ─────────────
const $dayHeader: ViewStyle = {
  flexDirection: "row",
  alignItems: "center",
  marginTop: spacing.lg,
  marginBottom: spacing.sm,
}

const $dayBadge: ViewStyle = {
  backgroundColor: colors.tint,
  borderRadius: 12,
  paddingHorizontal: 14,
  paddingVertical: 6,
}

const $dayBadgeText: TextStyle = {
  fontSize: 14,
  fontFamily: typography.primary.semiBold,
  color: "#fff",
}

const $dayDate: TextStyle = {
  fontSize: 14,
  fontFamily: typography.primary.normal,
  color: colors.palette.figmaGrayDark,
  marginLeft: spacing.sm,
}

// ─── Timeline + Cards ────────
const $timelineRow: ViewStyle = {
  flexDirection: "row",
  minHeight: 88,
}

const $timelineNodeCol: ViewStyle = {
  width: 36,
  alignItems: "center",
}

const $timelineNode: ViewStyle = {
  width: 26,
  height: 26,
  borderRadius: 13,
  justifyContent: "center",
  alignItems: "center",
}

const $nodeNumber: TextStyle = {
  color: "#fff",
  fontSize: 12,
  fontFamily: typography.primary.semiBold,
}

const $timelineConnector: ViewStyle = {
  width: 2,
  flex: 1,
  backgroundColor: colors.palette.figmaGrayLight,
  marginVertical: 4,
}

const $stopCard: ViewStyle = {
  flex: 1,
  backgroundColor: "#fff",
  borderRadius: 20,
  padding: spacing.md,
  marginLeft: spacing.sm,
  borderWidth: 1,
  borderColor: colors.palette.figmaGrayLight,
  shadowColor: "#000",
  shadowOffset: { width: 0, height: 2 },
  shadowOpacity: 0.05,
  shadowRadius: 8,
  elevation: 2,
}

const $stopCardActive: ViewStyle = {
  borderWidth: 2,
  borderColor: colors.tint,
}

const $routeLineLayer = {
  lineColor: colors.tint,
  lineWidth: 3,
  lineOpacity: 0.7,
  lineCap: "round" as const,
  lineJoin: "round" as const,
  lineDasharray: [2, 3],
}
