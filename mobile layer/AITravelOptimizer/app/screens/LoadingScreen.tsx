/**
 * LoadingScreen - AI Processing & Plan Comparison (3 Options)
 * Screen 2+3: Loading animation -> 3-plan comparison (Balanced/Chill/Budget)
 */
import React, { useEffect, useRef, useState } from "react"
import {
  View,
  StyleSheet,
  Animated,
  Dimensions,
  TouchableOpacity,
  ScrollView,
  StatusBar,
} from "react-native"
import { Text } from "@/components/Text"
import { LinearGradient } from "expo-linear-gradient"
import { NativeStackScreenProps } from "@react-navigation/native-stack"
import { AppStackParamList } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { useSafeAreaInsets } from "react-native-safe-area-context"

const { width } = Dimensions.get("window")
const CARD_WIDTH = width * 0.78

const PLAN_DATA = [
  {
    id: "balanced",
    title: "Cân Bằng",
    subtitle: "Balanced",
    emoji: "⚖️",
    color: colors.palette.royalPurple,
    colorLight: colors.palette.royalPurpleLight,
    fatigueIndex: 14,
    fatigueMax: 20,
    diversityScore: 87,
    budget: "850.000₫",
    stops: 8,
    days: 3,
    highlights: ["Đại Nội", "Lăng Tự Đức", "Phố cổ Gia Hội", "Cơm hến Đông Ba"],
    badge: "⭐ Phổ biến nhất",
    badgeColor: colors.palette.imperialGold,
  },
  {
    id: "chill",
    title: "Thư Thái",
    subtitle: "Chill Mode",
    emoji: "🌿",
    color: colors.palette.jadeGreen,
    colorLight: "#33C48F",
    fatigueIndex: 8,
    fatigueMax: 20,
    diversityScore: 72,
    budget: "650.000₫",
    stops: 5,
    days: 3,
    highlights: ["Vườn An Hiên", "Thiền Viện", "Sông Hương hoàng hôn", "Chè Huế"],
    badge: "💚 Nhẹ nhàng nhất",
    badgeColor: colors.palette.jadeGreen,
  },
  {
    id: "budget",
    title: "Tiết Kiệm",
    subtitle: "Budget",
    emoji: "💰",
    color: colors.palette.imperialGold,
    colorLight: colors.palette.imperialGoldLight,
    fatigueIndex: 16,
    fatigueMax: 20,
    diversityScore: 95,
    budget: "420.000₫",
    stops: 10,
    days: 3,
    highlights: ["Cầu Trường Tiền", "Cung An Định", "Chợ Đông Ba", "Bánh mì Huế"],
    badge: "💰 Tiết kiệm nhất",
    badgeColor: colors.palette.sunsetOrange,
  },
]

const LOADING_STEPS = [
  { text: "Phân tích ý định du lịch...", icon: "🧠" },
  { text: "Tối ưu hóa tuyến đường OSRM...", icon: "🗺️" },
  { text: "Kiểm tra thời tiết & nắng nóng...", icon: "☀️" },
  { text: "Tính toán Fatigue Index...", icon: "⚡" },
  { text: "Chèn điểm nghỉ tự động...", icon: "☕" },
  { text: "Tạo 3 phương án lộ trình...", icon: "✨" },
]

type Props = NativeStackScreenProps<AppStackParamList, "Loading">

type PlanData = typeof PLAN_DATA[number]

export const LoadingScreen = ({ navigation, route }: Props) => {
  const [phase, setPhase] = useState<"loading" | "plans">("loading")
  const [loadingStep, setLoadingStep] = useState(0)
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null)
  const progressAnim = useRef(new Animated.Value(0)).current
  const fadeAnim = useRef(new Animated.Value(1)).current
  const rotateAnim = useRef(new Animated.Value(0)).current
  const insets = useSafeAreaInsets()

  // Spinner rotation
  useEffect(() => {
    Animated.loop(
      Animated.timing(rotateAnim, { toValue: 1, duration: 1200, useNativeDriver: true })
    ).start()
  }, [])

  // Loading steps cycle
  useEffect(() => {
    if (phase !== "loading") return
    const interval = setInterval(() => {
      setLoadingStep((prev) => {
        const next = prev + 1
        if (next >= LOADING_STEPS.length) {
          clearInterval(interval)
          setTimeout(() => {
            Animated.timing(fadeAnim, { toValue: 0, duration: 400, useNativeDriver: true }).start(() => {
              setPhase("plans")
              Animated.timing(fadeAnim, { toValue: 1, duration: 500, useNativeDriver: true }).start()
            })
          }, 600)
        }
        return Math.min(next, LOADING_STEPS.length - 1)
      })
      Animated.timing(progressAnim, {
        toValue: (loadingStep + 1) / LOADING_STEPS.length,
        duration: 800,
        useNativeDriver: false,
      }).start()
    }, 900)
    return () => clearInterval(interval)
  }, [phase, loadingStep])

  const spin = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "360deg"],
  })

  const handleSelectPlan = (planId: string) => {
    setSelectedPlan(planId)
    setTimeout(() => {
      navigation.navigate("MapTimeline", { itinerary: { status: 'ok', num_days: 3, days: [], total_pois_visited: 0, total_pois_dropped: 0, total_entrance_fee: 0, total_travel_min: 0, total_distance_km: 0, budget_used: 0 } })
    }, 600)
  }

  const RadialRing = ({ value, max, color, label }: { value: number; max: number; color: string; label: string }) => {
    const percent = (value / max) * 100
    return (
      <View style={styles.radialContainer}>
        <View style={styles.radialOuter}>
          <View style={[styles.radialInner, { borderColor: color + "40" }]}>
            <View style={[styles.radialFill, { borderColor: color, borderTopColor: "transparent", transform: [{ rotate: `${(percent / 100) * 360}deg` }] }]} />
            <View style={styles.radialCenter}>
              <Text style={[styles.radialValue, { color }]}>{value}</Text>
              <Text style={styles.radialMax}>/{max}</Text>
            </View>
          </View>
        </View>
        <Text style={styles.radialLabel}>{label}</Text>
      </View>
    )
  }

  if (phase === "loading") {
    return (
      <View style={styles.root}>
        <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
        <LinearGradient
          colors={[colors.palette.deepSlate, "#111827", "#1a0a2e"]}
          style={StyleSheet.absoluteFillObject}
        />
        <View style={[styles.loadingContainer, { paddingTop: insets.top + 40 }]}>
          {/* Logo */}
          <View style={styles.logoRow}>
            <View style={styles.logoIconWrap}>
              <Text style={styles.logoIconText}>📍</Text>
            </View>
            <Text style={styles.logoText}>TripFlow</Text>
          </View>

          {/* Spinner */}
          <Animated.View style={[styles.spinnerOuter, { transform: [{ rotate: spin }] }]}>
            <LinearGradient
              colors={[colors.palette.royalPurple, colors.palette.imperialGold, colors.palette.jadeGreen]}
              style={styles.spinnerGradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
            />
          </Animated.View>
          <View style={styles.spinnerInner}>
            <Text style={styles.spinnerIcon}>🤖</Text>
          </View>

          <Text style={styles.loadingTitle}>AI đang phân tích...</Text>
          <Text style={styles.loadingSubtitle}>"{route.params?.prompt?.slice(0, 50)}..."</Text>

          {/* Steps */}
          <View style={styles.stepsContainer}>
            {LOADING_STEPS.map((step, i) => (
              <Animated.View
                key={i}
                style={[
                  styles.stepRow,
                  { opacity: i <= loadingStep ? 1 : 0.25 },
                ]}
              >
                <View style={[
                  styles.stepDot,
                  i < loadingStep && { backgroundColor: colors.palette.jadeGreen },
                  i === loadingStep && { backgroundColor: colors.palette.imperialGold },
                  i > loadingStep && { backgroundColor: "rgba(255,255,255,0.15)" },
                ]}>
                  <Text style={{ fontSize: 10 }}>
                    {i < loadingStep ? "✓" : step.icon}
                  </Text>
                </View>
                <Text style={[
                  styles.stepText,
                  i === loadingStep && { color: "#FFFFFF" },
                ]}>{step.text}</Text>
              </Animated.View>
            ))}
          </View>

          {/* Progress bar */}
          <View style={styles.progressBar}>
            <Animated.View style={[
              styles.progressFill,
              {
                width: progressAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: ["0%", "100%"],
                }),
              },
            ]} />
          </View>
        </View>
      </View>
    )
  }

  // Plans comparison screen
  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <LinearGradient
        colors={[colors.palette.deepSlate, "#111827", "#0f0a1e"]}
        style={StyleSheet.absoluteFillObject}
      />
      <Animated.View style={[{ flex: 1, opacity: fadeAnim }, { paddingTop: insets.top + 12 }]}>
        {/* Header */}
        <View style={styles.plansHeader}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
            <Text style={styles.backBtnText}>←</Text>
          </TouchableOpacity>
          <View style={styles.plansHeaderCenter}>
            <Text style={styles.plansTitle}>3 Phương Án Lộ Trình</Text>
            <Text style={styles.plansSub}>Vuốt để xem chi tiết từng phương án</Text>
          </View>
          <View style={{ width: 40 }} />
        </View>

        <ScrollView
          horizontal
          pagingEnabled
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.plansScroll}
          decelerationRate="fast"
          snapToInterval={CARD_WIDTH + 16}
          snapToAlignment="center"
          contentOffset={{ x: (width - CARD_WIDTH) / 2 - 8, y: 0 }}
        >
          {PLAN_DATA.map((plan: PlanData) => (
            <View key={plan.id} style={styles.planCardWrap}>
              <LinearGradient
                colors={[plan.color + "25", "rgba(255,255,255,0.04)"]}
                style={[styles.planCard, selectedPlan === plan.id && styles.planCardSelected]}
              >
                {/* Badge */}
                <View style={[styles.planBadge, { backgroundColor: plan.badgeColor + "30" }]}>
                  <Text style={[styles.planBadgeText, { color: plan.badgeColor }]}>{plan.badge}</Text>
                </View>

                {/* Title */}
                <View style={styles.planTitleRow}>
                  <Text style={styles.planEmoji}>{plan.emoji}</Text>
                  <View>
                    <Text style={styles.planTitle}>{plan.title}</Text>
                    <Text style={[styles.planSubtitle, { color: plan.colorLight }]}>{plan.subtitle}</Text>
                  </View>
                </View>

                {/* Radial rings */}
                <View style={styles.ringsRow}>
                  <RadialRing
                    value={plan.fatigueIndex}
                    max={plan.fatigueMax}
                    color={plan.color}
                    label="Fatigue"
                  />
                  <RadialRing
                    value={plan.diversityScore}
                    max={100}
                    color={colors.palette.imperialGold}
                    label="Diversity %"
                  />
                </View>

                {/* Stats */}
                <View style={styles.statsRow}>
                  <View style={styles.statItem}>
                    <Text style={styles.statValue}>{plan.stops}</Text>
                    <Text style={styles.statLabel}>Điểm dừng</Text>
                  </View>
                  <View style={styles.statDivider} />
                  <View style={styles.statItem}>
                    <Text style={styles.statValue}>{plan.days}</Text>
                    <Text style={styles.statLabel}>Ngày</Text>
                  </View>
                  <View style={styles.statDivider} />
                  <View style={styles.statItem}>
                    <Text style={[styles.statValue, { color: plan.colorLight }]}>{plan.budget}</Text>
                    <Text style={styles.statLabel}>Chi phí</Text>
                  </View>
                </View>

                {/* Highlights */}
                <View style={styles.highlightsContainer}>
                  <Text style={styles.highlightsTitle}>Điểm nổi bật:</Text>
                  {plan.highlights.map((h, i) => (
                    <View key={i} style={styles.highlightRow}>
                      <View style={[styles.highlightDot, { backgroundColor: plan.color }]} />
                      <Text style={styles.highlightText}>{h}</Text>
                    </View>
                  ))}
                </View>

                {/* CTA */}
                <TouchableOpacity
                  style={styles.selectBtn}
                  onPress={() => handleSelectPlan(plan.id)}
                >
                  <LinearGradient
                    colors={[plan.color, plan.colorLight]}
                    style={styles.selectBtnGradient}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                  >
                    <Text style={styles.selectBtnText}>Chọn Phương Án Này →</Text>
                  </LinearGradient>
                </TouchableOpacity>
              </LinearGradient>
            </View>
          ))}
        </ScrollView>

        {/* Bottom tip */}
        <View style={styles.bottomTip}>
          <Text style={styles.bottomTipText}>
            💡 Bạn có thể chỉnh sửa thứ tự điểm dừng sau khi chọn
          </Text>
        </View>
      </Animated.View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  loadingContainer: {
    flex: 1,
    alignItems: "center",
    paddingHorizontal: spacing.xl,
  },
  logoRow: { flexDirection: "row", alignItems: "center", marginBottom: 40 },
  logoIconWrap: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: colors.palette.sunsetOrange,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 8,
  },
  logoIconText: { fontSize: 18 },
  logoText: {
    fontFamily: typography.primary.bold,
    fontSize: 22,
    color: "#FFFFFF",
  },
  spinnerOuter: {
    width: 100,
    height: 100,
    borderRadius: 50,
    borderWidth: 4,
    borderColor: "transparent",
    position: "absolute",
    top: 140,
  },
  spinnerGradient: {
    flex: 1,
    borderRadius: 50,
    opacity: 0.8,
  },
  spinnerInner: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "rgba(255,255,255,0.08)",
    borderWidth: 2,
    borderColor: "rgba(255,255,255,0.15)",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 30,
    marginTop: 10,
  },
  spinnerIcon: { fontSize: 40 },
  loadingTitle: {
    fontFamily: typography.primary.semiBold,
    fontSize: 22,
    color: "#FFFFFF",
    marginBottom: 8,
    textAlign: "center",
  },
  loadingSubtitle: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: "rgba(255,255,255,0.45)",
    marginBottom: 32,
    textAlign: "center",
    fontStyle: "italic",
  },
  stepsContainer: { width: "100%", gap: 10, marginBottom: 32 },
  stepRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  stepDot: {
    width: 28,
    height: 28,
    borderRadius: 8,
    justifyContent: "center",
    alignItems: "center",
  },
  stepText: {
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: "rgba(255,255,255,0.45)",
    flex: 1,
  },
  progressBar: {
    width: "100%",
    height: 4,
    backgroundColor: "rgba(255,255,255,0.1)",
    borderRadius: 2,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    backgroundColor: colors.palette.imperialGold,
    borderRadius: 2,
  },
  // Plans styles
  plansHeader: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.08)",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.12)",
  },
  backBtnText: {
    fontSize: 20,
    color: "#FFFFFF",
    fontFamily: typography.primary.bold,
  },
  plansHeaderCenter: { flex: 1, alignItems: "center" },
  plansTitle: {
    fontFamily: typography.primary.bold,
    fontSize: 18,
    color: "#FFFFFF",
    textAlign: "center",
  },
  plansSub: {
    fontFamily: typography.primary.normal,
    fontSize: 12,
    color: "rgba(255,255,255,0.45)",
    marginTop: 2,
  },
  plansScroll: {
    paddingHorizontal: (width - CARD_WIDTH) / 2,
    gap: 16,
    paddingVertical: 16,
  },
  planCardWrap: {
    width: CARD_WIDTH,
    borderRadius: 24,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.12)",
  },
  planCard: {
    padding: spacing.lg,
    borderRadius: 24,
  },
  planCardSelected: {
    borderWidth: 2,
    borderColor: colors.palette.imperialGold,
  },
  planBadge: {
    alignSelf: "flex-start",
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 4,
    marginBottom: spacing.md,
  },
  planBadgeText: {
    fontFamily: typography.primary.semiBold,
    fontSize: 12,
  },
  planTitleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginBottom: spacing.lg,
  },
  planEmoji: { fontSize: 36 },
  planTitle: {
    fontFamily: typography.primary.bold,
    fontSize: 20,
    color: "#FFFFFF",
  },
  planSubtitle: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    marginTop: 2,
  },
  ringsRow: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginBottom: spacing.lg,
  },
  radialContainer: { alignItems: "center", gap: 8 },
  radialOuter: { width: 80, height: 80, justifyContent: "center", alignItems: "center" },
  radialInner: {
    width: 70,
    height: 70,
    borderRadius: 35,
    borderWidth: 6,
    justifyContent: "center",
    alignItems: "center",
    overflow: "hidden",
  },
  radialFill: {
    position: "absolute",
    width: 70,
    height: 70,
    borderRadius: 35,
    borderWidth: 6,
  },
  radialCenter: { flexDirection: "row", alignItems: "baseline" },
  radialValue: { fontFamily: typography.primary.bold, fontSize: 16 },
  radialMax: { fontFamily: typography.primary.normal, fontSize: 10, color: "rgba(255,255,255,0.4)" },
  radialLabel: { fontFamily: typography.primary.normal, fontSize: 11, color: "rgba(255,255,255,0.5)" },
  statsRow: {
    flexDirection: "row",
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 14,
    padding: spacing.md,
    marginBottom: spacing.md,
    justifyContent: "space-around",
    alignItems: "center",
  },
  statItem: { alignItems: "center" },
  statValue: {
    fontFamily: typography.primary.bold,
    fontSize: 18,
    color: "#FFFFFF",
  },
  statLabel: {
    fontFamily: typography.primary.normal,
    fontSize: 11,
    color: "rgba(255,255,255,0.45)",
    marginTop: 2,
  },
  statDivider: {
    width: 1,
    height: 32,
    backgroundColor: "rgba(255,255,255,0.1)",
  },
  highlightsContainer: { marginBottom: spacing.lg },
  highlightsTitle: {
    fontFamily: typography.primary.semiBold,
    fontSize: 13,
    color: "rgba(255,255,255,0.6)",
    marginBottom: 8,
  },
  highlightRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 6,
  },
  highlightDot: { width: 6, height: 6, borderRadius: 3 },
  highlightText: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: "rgba(255,255,255,0.8)",
  },
  selectBtn: { borderRadius: 14, overflow: "hidden" },
  selectBtnGradient: {
    paddingVertical: 14,
    alignItems: "center",
  },
  selectBtnText: {
    fontFamily: typography.primary.semiBold,
    fontSize: 15,
    color: "#FFFFFF",
    letterSpacing: 0.3,
  },
  bottomTip: {
    paddingHorizontal: spacing.lg,
    paddingBottom: 20,
    alignItems: "center",
  },
  bottomTipText: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: "rgba(255,255,255,0.35)",
    textAlign: "center",
  },
})