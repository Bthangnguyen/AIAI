/**
 * ActiveTripScreen - JIT Navigation & Real-time Re-route (Screen 5)
 * Design: Minimal dark + Fatigue bar + Big action buttons
 */
import React, { useState, useRef, useEffect } from "react"
import {
  View,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Animated,
  Dimensions,
  StatusBar,
  Alert,
} from "react-native"
import { Text } from "@/components/Text"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

const { width, height } = Dimensions.get("window")

const MOCK_STOPS = [
  { id: "1", name: "Đại Nội Huế", category: "Cung điện", time: "08:00", duration: "2h 30m", distance: "0km", emoji: "🏯", status: "completed" },
  { id: "2", name: "☕ Nghỉ ngơi - Café Sân Vườn", category: "Điểm nghỉ", time: "10:30", duration: "20 phút", distance: "0.3km", emoji: "☕", status: "rest" },
  { id: "3", name: "Lăng Tự Đức", category: "Lịch sử", time: "11:00", duration: "1h 30m", distance: "5.2km", emoji: "⛩️", status: "current" },
  { id: "4", name: "🌡️ Nghỉ trưa tránh nắng", category: "Cảnh báo", time: "12:30", duration: "1h 30m", distance: "0km", emoji: "🏠", status: "warning" },
  { id: "5", name: "Cơm hến Đông Ba", category: "Ẩm thực", time: "14:00", duration: "45 phút", distance: "8.1km", emoji: "🍜", status: "upcoming" },
  { id: "6", name: "Phá Tam Giang hoàng hôn", category: "Thiên nhiên", time: "17:00", duration: "2h", distance: "12km", emoji: "🌅", status: "upcoming" },
]

const FATIGUE_LEVEL = 58 // out of 100

export const ActiveTripScreen: React.FC = () => {
  const [fatigue, setFatigue] = useState(FATIGUE_LEVEL)
  const [stops, setStops] = useState(MOCK_STOPS)
  const [isReRouting, setIsReRouting] = useState(false)
  const [skippedIds, setSkippedIds] = useState<string[]>([])
  const insets = useSafeAreaInsets()
  const fatigueAnim = useRef(new Animated.Value(FATIGUE_LEVEL / 100)).current
  const reRouteScale = useRef(new Animated.Value(1)).current
  const pulseAnim = useRef(new Animated.Value(1)).current
  const scrollRef = useRef<ScrollView>(null)

  useEffect(() => {
    // Fatigue slowly increases
    const interval = setInterval(() => {
      setFatigue((prev) => {
        const next = Math.min(prev + 0.3, 100)
        Animated.timing(fatigueAnim, {
          toValue: next / 100,
          duration: 800,
          useNativeDriver: false,
        }).start()
        return next
      })
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    // Pulse current stop
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.08, duration: 800, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 800, useNativeDriver: true }),
      ])
    ).start()
  }, [])

  const getFatigueColor = () => {
    if (fatigue < 40) return colors.palette.jadeGreen
    if (fatigue < 70) return colors.palette.imperialGold
    return colors.palette.sunsetOrange
  }

  const getFatigueLabel = () => {
    if (fatigue < 40) return "Sức bền tốt 💪"
    if (fatigue < 70) return "Vừa sức 😊"
    return "Mệt nhiều rồi! 😓"
  }

  const handleSkipStop = () => {
    const currentIdx = stops.findIndex((s) => s.status === "current")
    if (currentIdx < 0) return
    const skippedStop = stops[currentIdx]
    setSkippedIds((prev) => [...prev, skippedStop.id])
    const newStops = stops.map((s, i) => {
      if (i === currentIdx) return { ...s, status: "skipped" as const }
      if (i === currentIdx + 1) return { ...s, status: "current" as const }
      return s
    })
    // Animate
    Animated.sequence([
      Animated.timing(reRouteScale, { toValue: 0.95, duration: 150, useNativeDriver: true }),
      Animated.timing(reRouteScale, { toValue: 1, duration: 150, useNativeDriver: true }),
    ]).start()
    setStops(newStops as typeof stops)
    setTimeout(() => scrollRef.current?.scrollTo({ y: 0, animated: true }), 300)
  }

  const handleReRoute = () => {
    setIsReRouting(true)
    Alert.alert(
      "🤖 TripFlow AI Re-route",
      "AI đang tính lại lộ trình từ vị trí GPS hiện tại của bạn...",
      [
        {
          text: "Hủy",
          onPress: () => setIsReRouting(false),
          style: "cancel",
        },
        {
          text: "Xác nhận",
          onPress: () => {
            setTimeout(() => setIsReRouting(false), 2000)
          },
        },
      ]
    )
  }

  const currentStop = stops.find((s) => s.status === "current")
  const completedCount = stops.filter((s) => s.status === "completed").length
  const totalCount = stops.length

  const getStatusStyle = (status: string) => {
    switch (status) {
      case "completed": return { nodeColor: colors.palette.jadeGreen, opacity: 0.6 }
      case "current": return { nodeColor: colors.palette.imperialGold, opacity: 1 }
      case "rest": return { nodeColor: colors.palette.royalPurple, opacity: 0.9 }
      case "warning": return { nodeColor: colors.palette.sunsetOrange, opacity: 0.9 }
      case "skipped": return { nodeColor: "rgba(255,255,255,0.2)", opacity: 0.4 }
      default: return { nodeColor: "rgba(255,255,255,0.2)", opacity: 0.8 }
    }
  }

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <LinearGradient
        colors={[colors.palette.deepSlate, "#0d1117", "#111827"]}
        style={StyleSheet.absoluteFillObject}
      />

      {/* TOP STATUS BAR */}
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
          <Text style={styles.progressText}>{completedCount}/{totalCount} điểm</Text>
        </View>
      </View>

      {/* CURRENT STOP HERO */}
      {currentStop && (
        <Animated.View style={[styles.currentStopHero, { transform: [{ scale: pulseAnim }] }]}>
          <LinearGradient
            colors={[colors.palette.imperialGold + "30", "rgba(255,184,0,0.08)"]}
            style={styles.currentStopGradient}
          >
            <View style={styles.currentStopHeader}>
              <Text style={styles.currentStopEmoji}>{currentStop.emoji}</Text>
              <View style={styles.currentStopInfo}>
                <Text style={styles.currentStopLabel}>Đang tham quan</Text>
                <Text style={styles.currentStopName} numberOfLines={1}>{currentStop.name}</Text>
                <Text style={styles.currentStopMeta}>{currentStop.time} · {currentStop.duration} · {currentStop.distance}</Text>
              </View>
              <View style={styles.currentPulseDot} />
            </View>
          </LinearGradient>
        </Animated.View>
      )}

      {/* FATIGUE BAR */}
      <View style={styles.fatigueSection}>
        <View style={styles.fatigueHeader}>
          <Text style={styles.fatigueLabel}>Chỉ số mệt mỏi (Fatigue)</Text>
          <Text style={[styles.fatigueStatus, { color: getFatigueColor() }]}>{getFatigueLabel()}</Text>
        </View>
        <View style={styles.fatigueTrack}>
          <Animated.View
            style={[
              styles.fatigueFill,
              {
                width: fatigueAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: ["0%", "100%"],
                }),
                backgroundColor: getFatigueColor(),
              },
            ]}
          />
          <View style={[styles.fatigueThumb, { left: `${fatigue}%` as any, backgroundColor: getFatigueColor() }]} />
        </View>
        <View style={styles.fatigueScale}>
          <Text style={styles.fatigueScaleText}>🟢 Thoải mái</Text>
          <Text style={styles.fatigueScaleText}>🟡 Vừa</Text>
          <Text style={styles.fatigueScaleText}>🔴 Mệt</Text>
        </View>
      </View>

      {/* TIMELINE SCROLL */}
      <ScrollView
        ref={scrollRef}
        style={styles.timelineScroll}
        contentContainerStyle={styles.timelineContent}
        showsVerticalScrollIndicator={false}
      >
        {stops.map((stop, idx) => {
          const { nodeColor, opacity } = getStatusStyle(stop.status)
          const isCurrent = stop.status === "current"
          const isWarning = stop.status === "warning"
          const isRest = stop.status === "rest"
          const isSkipped = stop.status === "skipped"

          return (
            <View key={stop.id} style={[styles.timelineRow, { opacity }]}>
              {/* Node column */}
              <View style={styles.nodeCol}>
                <View style={[styles.node, { backgroundColor: nodeColor }, isCurrent && styles.nodeActive]}>
                  <Text style={styles.nodeEmoji}>{stop.emoji}</Text>
                </View>
                {idx < stops.length - 1 && (
                  <View style={[styles.connector, { backgroundColor: nodeColor + "40" }]} />
                )}
              </View>

              {/* Card */}
              <Animated.View style={[
                styles.stopCard,
                isCurrent && styles.stopCardCurrent,
                isWarning && styles.stopCardWarning,
                isRest && styles.stopCardRest,
                isSkipped && styles.stopCardSkipped,
              ]}>
                <View style={styles.stopCardRow}>
                  <View style={styles.stopCardInfo}>
                    {isWarning && (
                      <View style={styles.warningBadge}>
                        <Text style={styles.warningBadgeText}>⚠️ Cảnh báo</Text>
                      </View>
                    )}
                    {isRest && (
                      <View style={styles.restBadge}>
                        <Text style={styles.restBadgeText}>☕ Điểm nghỉ</Text>
                      </View>
                    )}
                    {isSkipped && (
                      <View style={styles.skippedBadge}>
                        <Text style={styles.skippedBadgeText}>⏭ Đã bỏ qua</Text>
                      </View>
                    )}
                    <Text style={[styles.stopName, isSkipped && { textDecorationLine: "line-through" }]}>
                      {stop.name}
                    </Text>
                    <Text style={styles.stopMeta}>{stop.time} · {stop.duration}</Text>
                    {!isSkipped && stop.distance !== "0km" && (
                      <Text style={styles.stopDistance}>📍 {stop.distance} từ điểm trước</Text>
                    )}
                  </View>
                  {isCurrent && (
                    <View style={styles.currentBadge}>
                      <Text style={styles.currentBadgeText}>Hiện tại</Text>
                    </View>
                  )}
                </View>
              </Animated.View>
            </View>
          )
        })}
      </ScrollView>

      {/* BOTTOM ACTION BUTTONS */}
      <View style={[styles.bottomActions, { paddingBottom: insets.bottom + 12 }]}>
        <Animated.View style={{ transform: [{ scale: reRouteScale }] }}>
          <TouchableOpacity
            style={styles.reRouteBtn}
            onPress={handleReRoute}
            disabled={isReRouting}
          >
            <LinearGradient
              colors={[colors.palette.royalPurple, colors.palette.royalPurpleLight]}
              style={styles.reRouteBtnGradient}
            >
              <Text style={styles.reRouteBtnText}>
                {isReRouting ? "⏳ Đang tính..." : "🤖 Re-route Co-Pilot"}
              </Text>
            </LinearGradient>
          </TouchableOpacity>
        </Animated.View>

        <TouchableOpacity style={styles.skipBtn} onPress={handleSkipStop}>
          <LinearGradient
            colors={[colors.palette.sunsetOrange + "CC", colors.palette.sunsetOrange]}
            style={styles.skipBtnGradient}
          >
            <Text style={styles.skipBtnText}>⏭ Bỏ điểm này</Text>
          </LinearGradient>
        </TouchableOpacity>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingBottom: 12,
  },
  logoRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  logoIconWrap: {
    width: 32,
    height: 32,
    borderRadius: 10,
    backgroundColor: colors.palette.sunsetOrange,
    justifyContent: "center",
    alignItems: "center",
  },
  logoIconText: { fontSize: 16 },
  logoText: { fontFamily: typography.primary.bold, fontSize: 18, color: "#FFFFFF" },
  liveIndicator: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.palette.sunsetOrange + "25",
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderWidth: 1,
    borderColor: colors.palette.sunsetOrange + "60",
    gap: 4,
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.palette.sunsetOrange,
  },
  liveText: { fontFamily: typography.primary.semiBold, fontSize: 10, color: colors.palette.sunsetOrange },
  progressPill: {
    backgroundColor: "rgba(255,255,255,0.08)",
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.12)",
  },
  progressText: { fontFamily: typography.primary.medium, fontSize: 13, color: "rgba(255,255,255,0.8)" },
  currentStopHero: {
    marginHorizontal: spacing.lg,
    marginBottom: spacing.md,
    borderRadius: 16,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.palette.imperialGold + "50",
  },
  currentStopGradient: { padding: spacing.md },
  currentStopHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  currentStopEmoji: { fontSize: 32 },
  currentStopInfo: { flex: 1 },
  currentStopLabel: { fontFamily: typography.primary.normal, fontSize: 11, color: colors.palette.imperialGold, textTransform: "uppercase", letterSpacing: 1 },
  currentStopName: { fontFamily: typography.primary.bold, fontSize: 16, color: "#FFFFFF", marginTop: 2 },
  currentStopMeta: { fontFamily: typography.primary.normal, fontSize: 12, color: "rgba(255,255,255,0.5)", marginTop: 2 },
  currentPulseDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: colors.palette.imperialGold,
    shadowColor: colors.palette.imperialGold,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 6,
    elevation: 4,
  },
  fatigueSection: {
    marginHorizontal: spacing.lg,
    marginBottom: spacing.md,
  },
  fatigueHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  fatigueLabel: { fontFamily: typography.primary.normal, fontSize: 12, color: "rgba(255,255,255,0.5)" },
  fatigueStatus: { fontFamily: typography.primary.semiBold, fontSize: 13 },
  fatigueTrack: {
    height: 8,
    backgroundColor: "rgba(255,255,255,0.1)",
    borderRadius: 4,
    overflow: "hidden",
    position: "relative",
  },
  fatigueFill: {
    position: "absolute",
    top: 0,
    left: 0,
    bottom: 0,
    borderRadius: 4,
  },
  fatigueThumb: {
    position: "absolute",
    top: -3,
    width: 14,
    height: 14,
    borderRadius: 7,
    marginLeft: -7,
    borderWidth: 2,
    borderColor: "#FFFFFF",
  },
  fatigueScale: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 4,
  },
  fatigueScaleText: { fontFamily: typography.primary.normal, fontSize: 10, color: "rgba(255,255,255,0.3)" },
  timelineScroll: { flex: 1 },
  timelineContent: {
    paddingHorizontal: spacing.lg,
    paddingBottom: 20,
  },
  timelineRow: {
    flexDirection: "row",
    minHeight: 80,
  },
  nodeCol: {
    width: 44,
    alignItems: "center",
  },
  node: {
    width: 36,
    height: 36,
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
  },
  nodeActive: {
    shadowColor: colors.palette.imperialGold,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.7,
    shadowRadius: 8,
    elevation: 6,
  },
  nodeEmoji: { fontSize: 18 },
  connector: { width: 2, flex: 1, marginVertical: 4, borderRadius: 1 },
  stopCard: {
    flex: 1,
    backgroundColor: "rgba(255,255,255,0.05)",
    borderRadius: 16,
    padding: spacing.md,
    marginLeft: spacing.sm,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  stopCardCurrent: {
    borderColor: colors.palette.imperialGold + "60",
    backgroundColor: "rgba(255,184,0,0.08)",
  },
  stopCardWarning: {
    borderColor: colors.palette.sunsetOrange + "60",
    backgroundColor: "rgba(255,107,107,0.08)",
  },
  stopCardRest: {
    borderColor: colors.palette.royalPurple + "60",
    backgroundColor: "rgba(108,42,123,0.08)",
  },
  stopCardSkipped: {
    borderColor: "rgba(255,255,255,0.05)",
    backgroundColor: "rgba(255,255,255,0.02)",
  },
  stopCardRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  stopCardInfo: { flex: 1 },
  warningBadge: {
    alignSelf: "flex-start",
    backgroundColor: colors.palette.sunsetOrange + "30",
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
    marginBottom: 4,
  },
  warningBadgeText: { fontFamily: typography.primary.semiBold, fontSize: 10, color: colors.palette.sunsetOrange },
  restBadge: {
    alignSelf: "flex-start",
    backgroundColor: colors.palette.royalPurple + "30",
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
    marginBottom: 4,
  },
  restBadgeText: { fontFamily: typography.primary.semiBold, fontSize: 10, color: colors.palette.royalPurpleLight },
  skippedBadge: {
    alignSelf: "flex-start",
    backgroundColor: "rgba(255,255,255,0.08)",
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
    marginBottom: 4,
  },
  skippedBadgeText: { fontFamily: typography.primary.semiBold, fontSize: 10, color: "rgba(255,255,255,0.4)" },
  stopName: { fontFamily: typography.primary.semiBold, fontSize: 14, color: "#FFFFFF" },
  stopMeta: { fontFamily: typography.primary.normal, fontSize: 12, color: "rgba(255,255,255,0.45)", marginTop: 2 },
  stopDistance: { fontFamily: typography.primary.normal, fontSize: 11, color: "rgba(255,255,255,0.35)", marginTop: 2 },
  currentBadge: {
    backgroundColor: colors.palette.imperialGold + "30",
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  currentBadgeText: { fontFamily: typography.primary.semiBold, fontSize: 11, color: colors.palette.imperialGold },
  bottomActions: {
    paddingHorizontal: spacing.md,
    paddingTop: 8,
    gap: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: "rgba(255,255,255,0.06)",
  },
  reRouteBtn: { borderRadius: 16, overflow: "hidden" },
  reRouteBtnGradient: { paddingVertical: 16, alignItems: "center" },
  reRouteBtnText: { fontFamily: typography.primary.semiBold, fontSize: 16, color: "#FFFFFF", letterSpacing: 0.3 },
  skipBtn: { borderRadius: 16, overflow: "hidden" },
  skipBtnGradient: { paddingVertical: 14, alignItems: "center" },
  skipBtnText: { fontFamily: typography.primary.semiBold, fontSize: 15, color: "#FFFFFF" },
})