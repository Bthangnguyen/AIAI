/**
 * ActiveTripScreen - Live Navigation & GPS Re-route (JIT)
 *
 * Reads locked itinerary from Zustand store.
 * visitedPOIIds are persisted via MMKV — survive app restarts.
 *
 * Primary action: Re-route from current GPS + time.
 *   - User opens tab (foreground, no background tracking)
 *   - Presses "Tái định tuyến"
 *   - App reads GPS + current time
 *   - Sends to backend: depot = user GPS, remaining POIs, hotel return fixed
 *   - Backend solver returns optimised day route
 *   - UI updates with new order
 */
import React, { useState, useRef, useEffect, useCallback, useMemo } from "react"
import {
  View,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Animated,
  Dimensions,
  StatusBar,
  Alert,
  ActivityIndicator,
  Platform,
} from "react-native"
import { Text } from "@/components/Text"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { useIsFocused } from "@react-navigation/native"
import * as Location from "expo-location"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { useTripStore } from "@/store/useTripStore"
import { TripService } from "@/services/api/tripService"
import { getRemainingPOIIds, getCurrentTimeMin, mergeReRoutedDay, minutesToHHMM, getTripTimeDelta } from "@/utils/itineraryHelpers"
import type { TravelItineraryStop, TravelItineraryDay } from "@/navigators/navigationTypes"

const { width } = Dimensions.get("window")

const CATEGORY_EMOJI: Record<string, string> = {
  food: "🍜",
  cafe: "☕",
  culture: "🏛️",
  nature: "🌳",
  nightlife: "🍻",
  shopping: "🛍️",
  art: "🎨",
  wellness: "💆",
  adventure: "🧗",
  hotel: "🏨",
  default: "📍",
}

const STATUS_COLORS = {
  early: colors.palette.jadeGreen,
  "on-time": colors.palette.imperialGold,
  late: "#EF4444",
} as const

export const ActiveTripScreen: React.FC = () => {
  const itinerary = useTripStore((s) => s.currentItinerary)
  const setCurrentItinerary = useTripStore((s) => s.setCurrentItinerary)
  const isFocused = useIsFocused()

  // ─── Persisted visited POIs (Zustand + MMKV) ──────────────────────────────
  const visitedPOIIds = useTripStore((s) => s.visitedPOIIds)
  const markVisited = useTripStore((s) => s.markVisited)
  const visitedIds = useMemo(() => new Set(visitedPOIIds), [visitedPOIIds])

  const insets = useSafeAreaInsets()

  const [currentDayIndex, setCurrentDayIndex] = useState(0)
  const [isReRouting, setIsReRouting] = useState(false)
  const [gpsCoords, setGpsCoords] = useState<{ lat: number; lon: number } | null>(null)
  const [gpsLoading, setGpsLoading] = useState(false)
  const [gpsError, setGpsError] = useState<string | null>(null)
  const [lastReRouteDepot, setLastReRouteDepot] = useState<{ lat: number; lon: number } | null>(null)

  const scrollRef = useRef<ScrollView>(null)
  const pulseAnim = useRef(new Animated.Value(1)).current

  // ─── Dynamically sync currentDayIndex with itinerary (handles 1-indexed) ───
  useEffect(() => {
    if (itinerary?.days && itinerary.days.length > 0) {
      const hasCurrentDay = itinerary.days.some((d) => d.day_index === currentDayIndex)
      if (!hasCurrentDay) {
        setCurrentDayIndex(itinerary.days[0].day_index)
      }
    }
  }, [itinerary, currentDayIndex])

  // Pulse animation for current stop
  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.06, duration: 900, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 900, useNativeDriver: true }),
      ])
    ).start()
  }, [])

  // ─── GPS auto-fetch when screen becomes focused (foreground only) ──────────
  const fetchGPS = useCallback(async () => {
    setGpsLoading(true)
    setGpsError(null)
    try {
      const { status } = await Location.requestForegroundPermissionsAsync()
      if (status !== "granted") {
        setGpsError("Cần quyền truy cập vị trí")
        setGpsLoading(false)
        return null
      }
      const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High })
      const coords = { lat: loc.coords.latitude, lon: loc.coords.longitude }
      setGpsCoords(coords)
      setGpsLoading(false)
      return coords
    } catch (e: any) {
      setGpsError(e?.message || "Không lấy được vị trí")
      setGpsLoading(false)
      return null
    }
  }, [])

  // Auto-fetch GPS when screen is focused
  useEffect(() => {
    if (isFocused && itinerary) {
      fetchGPS()
    }
  }, [isFocused, itinerary, fetchGPS])

  // ─── No itinerary guard ─────────────────────────────────────────────────────
  if (!itinerary || !itinerary.days || itinerary.days.length === 0) {
    return (
      <View style={styles.root}>
        <StatusBar barStyle="dark-content" backgroundColor="transparent" translucent />
        <LinearGradient
          colors={[colors.palette.appCream, "#FFFFFF"]}
          style={StyleSheet.absoluteFillObject}
        />
        <View style={[styles.emptyContainer, { paddingTop: insets.top + 40 }]}>
          <Text style={styles.emptyIcon}>🗺️</Text>
          <Text style={styles.emptyTitle}>Chưa có lộ trình</Text>
          <Text style={styles.emptySubtitle}>
            Hãy tạo lộ trình ở Trang chủ, sau đó nhấn "Khóa lộ trình" để bắt đầu chuyến đi.
          </Text>
        </View>
      </View>
    )
  }

  const currentDay: TravelItineraryDay | undefined = itinerary.days.find(
    (d: TravelItineraryDay) => d.day_index === currentDayIndex
  )
  const stops = currentDay?.stops || []
  const totalDays = itinerary.num_days || itinerary.days.length

  // Determine first unvisited stop as "current"
  const currentStopIndex = stops.findIndex((s) => !visitedIds.has(s.poi_id))
  const currentStop = currentStopIndex >= 0 ? stops[currentStopIndex] : null
  const completedCount = stops.filter((s) => visitedIds.has(s.poi_id)).length
  const totalStopsInDay = stops.length

  // ─── Trip time delta (early / on-time / late) ─────────────────────────────
  const tripStatus = useMemo(() => {
    if (!currentStop) return null
    const nowMin = getCurrentTimeMin()
    const travelEst = currentStop.travel_time_from_prev_min || 0
    return getTripTimeDelta(currentStop, nowMin, travelEst)
  }, [currentStop])

  // ─── Mark as arrived ─────────────────────────────────────────────────────────
  const handleArrived = useCallback((poiId: string) => {
    markVisited(poiId)
  }, [markVisited])

  // ─── RE-ROUTE: Main JIT action ──────────────────────────────────────────────
  const handleReRoute = useCallback(async () => {
    setIsReRouting(true)

    // 1. Get current GPS (foreground only)
    const coords = await fetchGPS()
    if (!coords) {
      setIsReRouting(false)
      Alert.alert("Lỗi GPS", gpsError || "Không thể lấy vị trí hiện tại")
      return
    }

    // 2. Calculate remaining POI IDs (exclude visited)
    const remainingIds = getRemainingPOIIds(itinerary, currentDayIndex, Array.from(visitedIds))
    if (remainingIds.length === 0) {
      setIsReRouting(false)
      Alert.alert("Hoàn thành", "Bạn đã hoàn thành tất cả điểm trong ngày!")
      return
    }

    // 3. Call backend re-route API
    //    depot = user's current GPS position
    //    hotel return point stays the same (end depot = hotel)
    try {
      const result = await TripService.reRoute({
        current_lat: coords.lat,
        current_lon: coords.lon,
        current_time_min: getCurrentTimeMin(),
        remaining_poi_ids: remainingIds,
        day_index: currentDayIndex,
        original_itinerary: itinerary,
      })

      if (result.status === "success" && result.day) {
        const updated = mergeReRoutedDay(itinerary, result.day)
        setCurrentItinerary(updated)
        setLastReRouteDepot(coords)
        Alert.alert(
          "✅ Đã tái định tuyến",
          `Lộ trình đã được tối ưu lại từ vị trí hiện tại với ${remainingIds.length} điểm còn lại.`
        )
      } else {
        Alert.alert("Lỗi", result.message || "Không thể tái định tuyến")
      }
    } catch (e: any) {
      Alert.alert("Lỗi kết nối", e?.message || "Re-route request failed")
    } finally {
      setIsReRouting(false)
    }
  }, [itinerary, currentDayIndex, visitedIds, fetchGPS, gpsError, setCurrentItinerary])

  // ─── Render ─────────────────────────────────────────────────────────────────
  const getStopStatus = (index: number, poiId: string) => {
    if (visitedIds.has(poiId)) return "completed"
    if (index === currentStopIndex) return "current"
    return "upcoming"
  }

  return (
    <View style={styles.root}>
      <StatusBar barStyle="dark-content" backgroundColor="transparent" translucent />
      <LinearGradient
        colors={[colors.palette.appCream, "#FFFFFF"]}
        style={StyleSheet.absoluteFillObject}
      />

      {/* TOP BAR */}
      <View style={[styles.topBar, { paddingTop: insets.top + 8 }]}>
        <View style={styles.logoRow}>
          <View style={styles.logoIconWrap}>
            <Text style={styles.logoIconText}>📍</Text>
          </View>
          <Text style={styles.logoText}>TripFlow</Text>
          <View style={styles.liveIndicator}>
            <View style={styles.liveDot} />
            <Text style={styles.liveText}>LIVE</Text>
          </View>
        </View>
        <View style={styles.progressPill}>
          <Text style={styles.progressText}>
            {completedCount}/{totalStopsInDay} điểm
          </Text>
        </View>
      </View>

      {/* DAY SELECTOR */}
      {totalDays > 1 && (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.daySelector}
        >
          {itinerary.days.map((d: TravelItineraryDay) => (
            <TouchableOpacity
              key={d.day_index}
              style={[
                styles.dayChip,
                d.day_index === currentDayIndex && styles.dayChipActive,
              ]}
              onPress={() => setCurrentDayIndex(d.day_index)}
            >
              <Text
                style={[
                  styles.dayChipText,
                  d.day_index === currentDayIndex && styles.dayChipTextActive,
                ]}
              >
                Ngày {d.day_index + 1}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      {/* TRIP STATUS SUMMARY CARD */}
      {currentStop && tripStatus && (
        <View style={styles.statusCard}>
          <LinearGradient
            colors={["rgba(255,255,255,0.8)", "rgba(255,255,255,0.5)"]}
            style={styles.statusCardGradient}
          >
            <View style={styles.statusCardLeft}>
              <Text style={styles.statusCardLabel}>Điểm tiếp theo</Text>
              <Text style={styles.statusCardName} numberOfLines={1}>{currentStop.poi_name}</Text>
              <Text style={styles.statusCardTime}>
                🕐 Dự kiến: {minutesToHHMM(currentStop.arrival_time_min)}
                {currentStop.travel_time_from_prev_min > 0 && ` · 🚗 ${currentStop.travel_time_from_prev_min} phút`}
              </Text>
            </View>
            <View style={[styles.statusBadge, { backgroundColor: STATUS_COLORS[tripStatus.status] + "20" }]}>
              <Text style={[styles.statusBadgeText, { color: STATUS_COLORS[tripStatus.status] }]}>
                {tripStatus.status === "early" && `⏰ Sớm ${tripStatus.deltaMin}′`}
                {tripStatus.status === "on-time" && "✅ Đúng giờ"}
                {tripStatus.status === "late" && `⚠️ Trễ ${tripStatus.deltaMin}′`}
              </Text>
            </View>
          </LinearGradient>
        </View>
      )}

      {/* GPS STATUS */}
      <View style={styles.gpsBar}>
        <Text style={styles.gpsText}>
          {gpsLoading ? "📡 Đang lấy GPS..." :
           gpsCoords ? `📡 ${gpsCoords.lat.toFixed(5)}, ${gpsCoords.lon.toFixed(5)}` :
           gpsError ? `❌ ${gpsError}` : "📡 Chưa có GPS"}
        </Text>
        <View style={styles.gpsRight}>
          <Text style={styles.gpsTime}>
            ⏰ {new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}
          </Text>
          <TouchableOpacity style={styles.gpsRefreshBtn} onPress={fetchGPS} disabled={gpsLoading}>
            <Text style={styles.gpsRefreshText}>🔄</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* LAST REROUTE DEPOT INFO */}
      {lastReRouteDepot && (
        <View style={styles.depotInfo}>
          <Text style={styles.depotInfoText}>
            🗺️ Lộ trình tính từ: {lastReRouteDepot.lat.toFixed(5)}, {lastReRouteDepot.lon.toFixed(5)}
          </Text>
        </View>
      )}

      {/* TIMELINE */}
      <ScrollView
        ref={scrollRef}
        style={styles.timelineScroll}
        contentContainerStyle={styles.timelineContent}
        showsVerticalScrollIndicator={false}
      >
        {stops.map((stop, idx) => {
          const status = getStopStatus(idx, stop.poi_id)
          const isCurrent = status === "current"
          const isCompleted = status === "completed"

          return (
            <View
              key={stop.poi_id}
              style={[styles.timelineRow, isCompleted && { opacity: 0.5 }]}
            >
              {/* Node column */}
              <View style={styles.nodeCol}>
                <View
                  style={[
                    styles.node,
                    isCompleted && styles.nodeCompleted,
                    isCurrent && styles.nodeCurrent,
                  ]}
                >
                  <Text style={styles.nodeEmoji}>
                    {isCompleted ? "✓" : (CATEGORY_EMOJI[(stop.category || "").toLowerCase()] || "📍")}
                  </Text>
                </View>
                {idx < stops.length - 1 && (
                  <View
                    style={[
                      styles.connector,
                      isCompleted && { backgroundColor: colors.palette.jadeGreen + "60" },
                    ]}
                  />
                )}
              </View>

              {/* Card */}
              <Animated.View
                style={[
                  styles.stopCard,
                  isCurrent && styles.stopCardCurrent,
                  isCompleted && styles.stopCardCompleted,
                  isCurrent && { transform: [{ scale: pulseAnim }] },
                ]}
              >
                <View style={styles.stopCardRow}>
                  <View style={styles.stopCardInfo}>
                    {isCurrent && (
                      <View style={styles.currentBadge}>
                        <Text style={styles.currentBadgeText}>📍 Điểm tiếp theo</Text>
                      </View>
                    )}
                    {isCompleted && (
                      <View style={styles.completedBadge}>
                        <Text style={styles.completedBadgeText}>✅ Đã đến</Text>
                      </View>
                    )}
                    <Text
                      style={[
                        styles.stopName,
                        isCompleted && { textDecorationLine: "line-through" },
                      ]}
                      numberOfLines={1}
                    >
                      {stop.poi_name}
                    </Text>
                    <Text style={styles.stopMeta}>
                      {minutesToHHMM(stop.arrival_time_min)} → {minutesToHHMM(stop.departure_time_min)}
                      {" · "}
                      {stop.visit_duration_min} phút
                    </Text>
                    {stop.travel_time_from_prev_min > 0 && (
                      <Text style={styles.stopDistance}>
                        🚗 {stop.travel_time_from_prev_min} phút di chuyển
                      </Text>
                    )}
                  </View>

                  {/* Arrived button */}
                  {isCurrent && (
                    <TouchableOpacity
                      style={styles.arrivedBtn}
                      onPress={() => handleArrived(stop.poi_id)}
                    >
                      <LinearGradient
                        colors={[colors.palette.jadeGreen, "#34d399"]}
                        style={styles.arrivedBtnGradient}
                      >
                        <Text style={styles.arrivedBtnText}>Đã đến</Text>
                      </LinearGradient>
                    </TouchableOpacity>
                  )}
                </View>
              </Animated.View>
            </View>
          )
        })}
      </ScrollView>

      {/* BOTTOM: RE-ROUTE BUTTON */}
      <View style={[styles.bottomActions, { paddingBottom: insets.bottom + 12 }]}>
        <TouchableOpacity
          style={styles.reRouteBtn}
          onPress={handleReRoute}
          disabled={isReRouting || gpsLoading}
        >
          <LinearGradient
            colors={
              isReRouting
                ? ["rgba(31,41,55,0.06)", "rgba(31,41,55,0.04)"]
                : [colors.palette.appOrange, colors.palette.appOrangeDark]
            }
            style={styles.reRouteBtnGradient}
          >
            {isReRouting || gpsLoading ? (
              <View style={styles.reRouteLoadingRow}>
                <ActivityIndicator color="#FFFFFF" size="small" />
                <Text style={styles.reRouteBtnText}>
                  {gpsLoading ? "Đang lấy GPS..." : "Đang tái định tuyến..."}
                </Text>
              </View>
            ) : (
              <Text style={styles.reRouteBtnText}>
                🤖 Tái định tuyến từ vị trí hiện tại
              </Text>
            )}
          </LinearGradient>
        </TouchableOpacity>

        <Text style={styles.reRouteHint}>
          Sử dụng GPS + thời gian hiện tại để tối ưu lại lộ trình · Hotel return giữ nguyên
        </Text>
      </View>
    </View>
  )
}

// ─── Styles ──────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.palette.appCream },
  emptyContainer: {
    flex: 1, alignItems: "center", justifyContent: "center",
    paddingHorizontal: spacing.xl,
  },
  emptyIcon: { fontSize: 64, marginBottom: spacing.lg },
  emptyTitle: {
    fontFamily: typography.primary.bold, fontSize: 22, color: colors.palette.appInk,
    marginBottom: spacing.sm, textAlign: "center",
  },
  emptySubtitle: {
    fontFamily: typography.primary.normal, fontSize: 14,
    color: colors.palette.appMuted, textAlign: "center", lineHeight: 22,
  },
  topBar: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: spacing.lg, paddingBottom: 12,
  },
  logoRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  logoIconWrap: {
    width: 32, height: 32, borderRadius: 10,
    backgroundColor: "rgba(255, 255, 255, 0.65)",
    borderWidth: 1.5, borderColor: "rgba(255, 255, 255, 0.9)",
    justifyContent: "center", alignItems: "center",
  },
  logoIconText: { fontSize: 16 },
  logoText: { fontFamily: typography.primary.bold, fontSize: 18, color: colors.palette.appInk },
  liveIndicator: {
    flexDirection: "row", alignItems: "center",
    backgroundColor: "rgba(249,115,22,0.08)",
    borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3,
    borderWidth: 1, borderColor: "rgba(249,115,22,0.15)", gap: 4,
  },
  liveDot: {
    width: 6, height: 6, borderRadius: 3, backgroundColor: colors.palette.appOrangeDark,
  },
  liveText: { fontFamily: typography.primary.semiBold, fontSize: 10, color: colors.palette.appOrangeDark },
  progressPill: {
    backgroundColor: "rgba(255,255,255,0.8)", borderRadius: 20,
    paddingHorizontal: 12, paddingVertical: 6,
    borderWidth: 1, borderColor: colors.palette.appLine,
  },
  progressText: { fontFamily: typography.primary.medium, fontSize: 13, color: colors.palette.appInk },

  // Day selector
  daySelector: {
    paddingHorizontal: spacing.lg, paddingBottom: spacing.sm, gap: 8,
  },
  dayChip: {
    paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.8)",
    borderWidth: 1, borderColor: colors.palette.appLine,
  },
  dayChipActive: {
    backgroundColor: "rgba(249, 115, 22, 0.12)",
    borderColor: colors.palette.appOrange,
  },
  dayChipText: {
    fontFamily: typography.primary.medium, fontSize: 13, color: colors.palette.appMuted,
  },
  dayChipTextActive: {
    color: colors.palette.appOrangeDark, fontFamily: typography.primary.semiBold,
  },

  // Trip Status Card
  statusCard: {
    marginHorizontal: spacing.lg, marginBottom: spacing.sm,
    borderRadius: 16, overflow: "hidden",
    borderWidth: 1.5, borderColor: "rgba(255, 255, 255, 0.9)",
  },
  statusCardGradient: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    padding: spacing.md,
  },
  statusCardLeft: { flex: 1, marginRight: spacing.sm },
  statusCardLabel: {
    fontFamily: typography.primary.normal, fontSize: 11,
    color: colors.palette.appMuted, marginBottom: 2,
  },
  statusCardName: {
    fontFamily: typography.primary.semiBold, fontSize: 15, color: colors.palette.appInk,
    marginBottom: 4,
  },
  statusCardTime: {
    fontFamily: typography.primary.normal, fontSize: 12,
    color: colors.palette.appMuted,
  },
  statusBadge: {
    borderRadius: 10, paddingHorizontal: 10, paddingVertical: 6,
    borderWidth: 1, borderColor: "rgba(31,41,55,0.1)",
  },
  statusBadgeText: {
    fontFamily: typography.primary.semiBold, fontSize: 12,
  },

  // GPS bar
  gpsBar: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    marginHorizontal: spacing.lg, marginBottom: spacing.xs,
    backgroundColor: "rgba(255, 255, 255, 0.75)", borderRadius: 10,
    paddingHorizontal: spacing.md, paddingVertical: 6,
    borderWidth: 1, borderColor: "rgba(249, 115, 22, 0.12)",
  },
  gpsText: {
    fontFamily: typography.primary.normal, fontSize: 11, color: colors.palette.appMuted,
    flex: 1,
  },
  gpsRight: { flexDirection: "row", alignItems: "center", gap: 8 },
  gpsTime: {
    fontFamily: typography.primary.semiBold, fontSize: 11, color: colors.palette.jadeGreen,
  },
  gpsRefreshBtn: {
    width: 24, height: 24, borderRadius: 6,
    backgroundColor: "rgba(255, 255, 255, 0.8)",
    justifyContent: "center", alignItems: "center",
  },
  gpsRefreshText: { fontSize: 12 },

  // Depot info
  depotInfo: {
    marginHorizontal: spacing.lg, marginBottom: spacing.sm,
    backgroundColor: "rgba(249, 115, 22, 0.06)",
    borderRadius: 8, paddingHorizontal: spacing.md, paddingVertical: 5,
    borderWidth: 1, borderColor: "rgba(249, 115, 22, 0.15)",
  },
  depotInfoText: {
    fontFamily: typography.primary.normal, fontSize: 11,
    color: colors.palette.appMuted,
  },

  // Timeline
  timelineScroll: { flex: 1 },
  timelineContent: { paddingHorizontal: spacing.lg, paddingBottom: 20 },
  timelineRow: { flexDirection: "row", minHeight: 80 },
  nodeCol: { width: 44, alignItems: "center" },
  node: {
    width: 36, height: 36, borderRadius: 18,
    justifyContent: "center", alignItems: "center",
    backgroundColor: "rgba(255, 255, 255, 0.6)",
    borderWidth: 1.5, borderColor: "rgba(255, 255, 255, 0.9)",
    ...Platform.select({
      web: {
        backdropFilter: "blur(15px)",
        WebkitBackdropFilter: "blur(15px)",
      } as any
    }),
  },
  nodeCompleted: { backgroundColor: colors.palette.jadeGreen, borderColor: colors.palette.jadeGreen },
  nodeCurrent: {
    backgroundColor: colors.palette.imperialGold,
    borderColor: colors.palette.imperialGold,
    shadowColor: colors.palette.imperialGold,
    shadowOffset: { width: 0, height: 0 }, shadowOpacity: 0.7, shadowRadius: 8, elevation: 6,
  },
  nodeEmoji: { fontSize: 16, color: "#FFFFFF" },
  connector: {
    width: 2, flex: 1, marginVertical: 4, borderRadius: 1,
    backgroundColor: "rgba(255, 255, 255, 0.8)",
  },

  // Stop cards
  stopCard: {
    flex: 1, backgroundColor: "rgba(255, 255, 255, 0.58)",
    borderRadius: 16, padding: spacing.md,
    marginLeft: spacing.sm, marginBottom: spacing.sm,
    borderWidth: 1.5, borderColor: "rgba(255, 255, 255, 0.9)",
    ...Platform.select({
      web: {
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
      } as any
    }),
    shadowColor: "#1F2937",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.03,
    shadowRadius: 10,
    elevation: 2,
  },
  stopCardCurrent: {
    borderColor: "rgba(249, 115, 22, 0.4)",
    backgroundColor: "rgba(255, 255, 255, 0.75)",
  },
  stopCardCompleted: {
    borderColor: "rgba(255, 255, 255, 0.5)",
    backgroundColor: "rgba(255, 255, 255, 0.35)",
  },
  stopCardRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  stopCardInfo: { flex: 1 },
  currentBadge: {
    alignSelf: "flex-start",
    backgroundColor: "rgba(249, 115, 22, 0.15)",
    borderRadius: 6, paddingHorizontal: 8, paddingVertical: 2, marginBottom: 4,
  },
  currentBadgeText: {
    fontFamily: typography.primary.semiBold, fontSize: 10, color: colors.palette.appOrangeDark,
  },
  completedBadge: {
    alignSelf: "flex-start",
    backgroundColor: colors.palette.jadeGreen + "20",
    borderRadius: 6, paddingHorizontal: 8, paddingVertical: 2, marginBottom: 4,
  },
  completedBadgeText: {
    fontFamily: typography.primary.semiBold, fontSize: 10, color: colors.palette.jadeGreen,
  },
  stopName: { fontFamily: typography.primary.semiBold, fontSize: 14, color: colors.palette.appInk },
  stopMeta: {
    fontFamily: typography.primary.normal, fontSize: 12,
    color: colors.palette.appMuted, marginTop: 2,
  },
  stopDistance: {
    fontFamily: typography.primary.normal, fontSize: 11,
    color: "rgba(31, 41, 55, 0.4)", marginTop: 2,
  },

  // Arrived button
  arrivedBtn: { borderRadius: 12, overflow: "hidden" },
  arrivedBtnGradient: { paddingHorizontal: 14, paddingVertical: 10, borderRadius: 12 },
  arrivedBtnText: { fontFamily: typography.primary.semiBold, fontSize: 13, color: "#FFFFFF" },

  // Bottom actions
  bottomActions: {
    paddingHorizontal: spacing.md, paddingTop: 8,
    borderTopWidth: 1, borderTopColor: "rgba(249, 115, 22, 0.12)",
  },
  reRouteBtn: { borderRadius: 16, overflow: "hidden" },
  reRouteBtnGradient: { paddingVertical: 16, alignItems: "center" },
  reRouteLoadingRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  reRouteBtnText: {
    fontFamily: typography.primary.semiBold, fontSize: 16,
    color: "#FFFFFF", letterSpacing: 0.3,
  },
  reRouteHint: {
    fontFamily: typography.primary.normal, fontSize: 11,
    color: colors.palette.appMuted, textAlign: "center", marginTop: 6,
  },
})