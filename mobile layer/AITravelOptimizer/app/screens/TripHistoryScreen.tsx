/**
 * TripHistoryScreen - Dark Royal Hue Design
 * List of past/upcoming trips with glass cards
 */
import React, { useState } from "react"
import {
  View, StyleSheet, ScrollView, Image, TouchableOpacity, StatusBar, Dimensions,
} from "react-native"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { useNavigation } from "@react-navigation/native"
import type { NativeStackNavigationProp } from "@react-navigation/native-stack"
import { Text } from "@/components/Text"
import { MOCK_TRIP_HISTORY, MockTripHistory } from "@/constants/mockUser"
import { MockTripService } from "@/services/mock/mockTripService"
import { AppStackParamList } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

const { width } = Dimensions.get("window")
type Nav = NativeStackNavigationProp<AppStackParamList>

const STATUS_CONFIG = {
  completed: { color: colors.palette.jadeGreen, label: "✅ Đã hoàn thành", bg: colors.palette.jadeGreen + "20" },
  upcoming: { color: colors.palette.imperialGold, label: "🗓️ Sắp tới", bg: colors.palette.imperialGold + "20" },
  draft: { color: "rgba(255,255,255,0.4)", label: "✏️ Nháp", bg: "rgba(255,255,255,0.08)" },
}

const FILTER_TABS = ["Tất cả", "Sắp tới", "Đã đi", "Nháp"] as const
type FilterTab = typeof FILTER_TABS[number]

export const TripHistoryScreen: React.FC = () => {
  const navigation = useNavigation<Nav>()
  const insets = useSafeAreaInsets()
  const [activeFilter, setActiveFilter] = useState<FilterTab>("Tất cả")

  const filtered = MOCK_TRIP_HISTORY.filter((t) => {
    if (activeFilter === "Tất cả") return true
    if (activeFilter === "Sắp tới") return t.status === "upcoming"
    if (activeFilter === "Đã đi") return t.status === "completed"
    return t.status === "draft"
  })

  const handleTripPress = (_trip: MockTripHistory) => {
    navigation.navigate("MapTimeline", { itinerary: MockTripService.getMockItinerary() })
  }

  const totalTrips = MOCK_TRIP_HISTORY.length
  const completedTrips = MOCK_TRIP_HISTORY.filter((t) => t.status === "completed").length

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <LinearGradient
        colors={[colors.palette.deepSlate, "#111827", "#0f0a1e"]}
        style={StyleSheet.absoluteFillObject}
      />

      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <View style={styles.headerTop}>
          <View>
            <Text style={styles.headerTitle}>Lịch sử chuyến đi</Text>
            <Text style={styles.headerSub}>{totalTrips} chuyến · {completedTrips} đã hoàn thành</Text>
          </View>
          <TouchableOpacity style={styles.addBtn}>
            <LinearGradient
              colors={[colors.palette.royalPurple, colors.palette.royalPurpleLight]}
              style={styles.addBtnGradient}
            >
              <Text style={styles.addBtnText}>+ Mới</Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>

        {/* Stats row */}
        <View style={styles.statsRow}>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{completedTrips}</Text>
            <Text style={styles.statLabel}>Hoàn thành</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={[styles.statValue, { color: colors.palette.imperialGold }]}>
              {MOCK_TRIP_HISTORY.filter(t => t.status === "upcoming").length}
            </Text>
            <Text style={styles.statLabel}>Sắp tới</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={[styles.statValue, { color: colors.palette.jadeGreen }]}>
              {MOCK_TRIP_HISTORY.reduce((acc, t) => acc + (t.poiCount ?? 0), 0)}
            </Text>
            <Text style={styles.statLabel}>Di tích đã thăm</Text>
          </View>
        </View>

        {/* Filter tabs */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterScroll}>
          {FILTER_TABS.map((tab) => (
            <TouchableOpacity
              key={tab}
              style={[styles.filterTab, activeFilter === tab && styles.filterTabActive]}
              onPress={() => setActiveFilter(tab)}
            >
              <Text style={[styles.filterTabText, activeFilter === tab && styles.filterTabTextActive]}>
                {tab}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {/* Trip List */}
      <ScrollView
        contentContainerStyle={[styles.listContent, { paddingBottom: insets.bottom + 100 }]}
        showsVerticalScrollIndicator={false}
      >
        {filtered.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyEmoji}>🗺️</Text>
            <Text style={styles.emptyTitle}>Chưa có chuyến đi nào</Text>
            <Text style={styles.emptySub}>Hãy lên kế hoạch chuyến đi đầu tiên của bạn!</Text>
          </View>
        ) : (
          filtered.map((trip, idx) => {
            const config = STATUS_CONFIG[trip.status]
            return (
              <TouchableOpacity
                key={trip.id}
                style={styles.card}
                onPress={() => handleTripPress(trip)}
                activeOpacity={0.85}
                testID={`trip-card-${trip.id}`}
              >
                {/* Hero image */}
                <View style={styles.cardImageWrap}>
                  <Image source={{ uri: trip.photoUrl }} style={styles.cardImage} resizeMode="cover" />
                  <LinearGradient
                    colors={["transparent", "rgba(11,15,25,0.85)"]}
                    style={styles.cardImageGradient}
                  />
                  {/* Status badge */}
                  <View style={[styles.statusBadge, { backgroundColor: config.bg }]}>
                    <Text style={[styles.statusText, { color: config.color }]}>{config.label}</Text>
                  </View>
                  {/* Day count badge */}
                  <View style={styles.dayCountBadge}>
                    <Text style={styles.dayCountText}>{trip.totalDays ?? 3} ngày</Text>
                  </View>
                </View>

                {/* Card body */}
                <LinearGradient
                  colors={["rgba(255,255,255,0.06)", "rgba(255,255,255,0.03)"]}
                  style={styles.cardBody}
                >
                  <View style={styles.cardTop}>
                    <View style={styles.cardInfo}>
                      <Text style={styles.destination}>{trip.destination}</Text>
                      <Text style={styles.cardDate}>📅 {trip.startDate}</Text>
                    </View>
                    <View style={styles.cardArrow}>
                      <Text style={styles.cardArrowText}>→</Text>
                    </View>
                  </View>

                  {/* Stats row */}
                  <View style={styles.cardStats}>
                    <View style={styles.cardStatItem}>
                      <Text style={styles.cardStatIcon}>📍</Text>
                      <Text style={styles.cardStatText}>{trip.poiCount ?? 8} điểm</Text>
                    </View>
                    <View style={styles.cardStatDot} />
                    <View style={styles.cardStatItem}>
                      <Text style={styles.cardStatIcon}>⏱️</Text>
                      <Text style={styles.cardStatText}>{trip.totalDays ?? 3} ngày</Text>
                    </View>
                    <View style={styles.cardStatDot} />
                    <View style={styles.cardStatItem}>
                      <Text style={styles.cardStatIcon}>💰</Text>
                      <Text style={styles.cardStatText}>{"~850K VND"}</Text>
                    </View>
                  </View>
                </LinearGradient>
              </TouchableOpacity>
            )
          })
        )}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(255,255,255,0.06)",
  },
  headerTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: spacing.md },
  headerTitle: { fontFamily: typography.primary.bold, fontSize: 24, color: "#FFFFFF" },
  headerSub: { fontFamily: typography.primary.normal, fontSize: 13, color: "rgba(255,255,255,0.45)", marginTop: 4 },
  addBtn: { borderRadius: 12, overflow: "hidden" },
  addBtnGradient: { paddingHorizontal: 16, paddingVertical: 10 },
  addBtnText: { fontFamily: typography.primary.semiBold, fontSize: 14, color: "#FFFFFF" },
  statsRow: {
    flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md,
  },
  statCard: {
    flex: 1, backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 12, padding: spacing.sm, alignItems: "center",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.08)",
  },
  statValue: { fontFamily: typography.primary.bold, fontSize: 22, color: "#FFFFFF" },
  statLabel: { fontFamily: typography.primary.normal, fontSize: 11, color: "rgba(255,255,255,0.4)", marginTop: 2 },
  filterScroll: { flexDirection: "row", gap: 8 },
  filterTab: {
    paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
  },
  filterTabActive: {
    backgroundColor: colors.palette.royalPurple + "40",
    borderColor: colors.palette.royalPurple,
  },
  filterTabText: { fontFamily: typography.primary.medium, fontSize: 13, color: "rgba(255,255,255,0.45)" },
  filterTabTextActive: { color: "#FFFFFF", fontFamily: typography.primary.semiBold },
  listContent: { padding: spacing.lg, gap: spacing.md },
  emptyState: { alignItems: "center", paddingTop: 80, gap: 12 },
  emptyEmoji: { fontSize: 60 },
  emptyTitle: { fontFamily: typography.primary.semiBold, fontSize: 18, color: "#FFFFFF" },
  emptySub: { fontFamily: typography.primary.normal, fontSize: 14, color: "rgba(255,255,255,0.4)", textAlign: "center" },
  card: { borderRadius: 20, overflow: "hidden", borderWidth: 1, borderColor: "rgba(255,255,255,0.1)" },
  cardImageWrap: { height: 180, position: "relative" },
  cardImage: { width: "100%", height: "100%" },
  cardImageGradient: { position: "absolute", bottom: 0, left: 0, right: 0, height: "60%" },
  statusBadge: {
    position: "absolute", top: 12, left: 12,
    borderRadius: 20, paddingHorizontal: 10, paddingVertical: 4,
    borderWidth: 1, borderColor: "rgba(255,255,255,0.15)",
  },
  statusText: { fontFamily: typography.primary.semiBold, fontSize: 11 },
  dayCountBadge: {
    position: "absolute", top: 12, right: 12,
    backgroundColor: "rgba(0,0,0,0.5)",
    borderRadius: 10, paddingHorizontal: 10, paddingVertical: 4,
    borderWidth: 1, borderColor: "rgba(255,255,255,0.15)",
  },
  dayCountText: { fontFamily: typography.primary.semiBold, fontSize: 11, color: "#FFFFFF" },
  cardBody: { padding: spacing.md },
  cardTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: spacing.sm },
  cardInfo: { flex: 1 },
  destination: { fontFamily: typography.primary.bold, fontSize: 18, color: "#FFFFFF", marginBottom: 4 },
  cardDate: { fontFamily: typography.primary.normal, fontSize: 13, color: "rgba(255,255,255,0.5)" },
  cardArrow: {
    width: 36, height: 36, borderRadius: 10,
    backgroundColor: "rgba(255,255,255,0.08)",
    justifyContent: "center", alignItems: "center",
  },
  cardArrowText: { fontSize: 18, color: "rgba(255,255,255,0.6)" },
  cardStats: { flexDirection: "row", alignItems: "center", gap: 8 },
  cardStatItem: { flexDirection: "row", alignItems: "center", gap: 4 },
  cardStatIcon: { fontSize: 13 },
  cardStatText: { fontFamily: typography.primary.normal, fontSize: 12, color: "rgba(255,255,255,0.5)" },
  cardStatDot: { width: 3, height: 3, borderRadius: 1.5, backgroundColor: "rgba(255,255,255,0.2)" },
})