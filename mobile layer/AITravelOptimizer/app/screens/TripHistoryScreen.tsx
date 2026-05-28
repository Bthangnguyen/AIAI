import React from "react"
import { View, StyleSheet, ScrollView, TouchableOpacity, StatusBar, Platform } from "react-native"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { useNavigation } from "@react-navigation/native"
import type { NativeStackNavigationProp } from "@react-navigation/native-stack"

import { AppIcon } from "@/components/AppIcon"
import { Text } from "@/components/Text"
import { AppStackParamList } from "@/navigators/navigationTypes"
import { useTripStore } from "@/store/useTripStore"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

type Nav = NativeStackNavigationProp<AppStackParamList>

export const TripHistoryScreen: React.FC = () => {
  const navigation = useNavigation<Nav>()
  const insets = useSafeAreaInsets()
  const lockedTrips = useTripStore((state) => state.lockedTripHistory)

  const totalPois = lockedTrips.reduce((acc, trip) => acc + trip.poiCount, 0)
  const totalDays = lockedTrips.reduce((acc, trip) => acc + trip.totalDays, 0)

  return (
    <View style={styles.root}>
      <StatusBar barStyle="dark-content" backgroundColor="transparent" translucent />
      <LinearGradient colors={[colors.palette.appCream, "#FFFFFF"]} style={StyleSheet.absoluteFillObject} />

      <View style={[styles.header, { paddingTop: insets.top + 16 }]}>
        <View>
          <Text style={styles.eyebrow}>TripFlow</Text>
          <Text style={styles.headerTitle}>Lịch sử chuyến đi</Text>
          <Text style={styles.headerSub}>Chỉ lưu các chuyến đã khóa để bắt đầu di chuyển.</Text>
        </View>
      </View>

      <View style={styles.statsRow}>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{lockedTrips.length}</Text>
          <Text style={styles.statLabel}>Đã khóa</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{totalDays}</Text>
          <Text style={styles.statLabel}>Ngày đi</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{totalPois}</Text>
          <Text style={styles.statLabel}>Điểm đến</Text>
        </View>
      </View>

      <ScrollView
        contentContainerStyle={[styles.listContent, { paddingBottom: insets.bottom + 100 }]}
        showsVerticalScrollIndicator={false}
      >
        {lockedTrips.length === 0 ? (
          <View style={styles.emptyState}>
            <View style={styles.emptyIconWrap}>
              <AppIcon name="lock" size={34} color={colors.palette.appOrange} />
            </View>
            <Text style={styles.emptyTitle}>Chưa có chuyến đã khóa</Text>
            <Text style={styles.emptySub}>
              Lên lịch trình ở Trang chủ, kiểm tra tuyến đường, rồi bấm Khóa lộ trình để lưu vào lịch sử.
            </Text>
            <TouchableOpacity
              style={styles.primaryButton}
              onPress={() => navigation.navigate("MainTabs", { screen: "Explore" })}
            >
              <Text style={styles.primaryButtonText}>Tạo chuyến đi mới</Text>
            </TouchableOpacity>
          </View>
        ) : (
          lockedTrips.map((trip) => (
            <TouchableOpacity
              key={trip.id}
              style={styles.card}
              onPress={() => navigation.navigate("MapTimeline", { itinerary: trip.itinerary })}
              activeOpacity={0.86}
              testID={`locked-trip-${trip.id}`}
            >
              <View style={styles.cardIcon}>
                <AppIcon name="route" size={24} color="#FFFFFF" />
              </View>
              <View style={styles.cardBody}>
                <View style={styles.cardHeader}>
                  <Text style={styles.destination} numberOfLines={1}>
                    {trip.destination}
                  </Text>
                  <View style={styles.lockedBadge}>
                    <AppIcon name="lock" size={12} color={colors.palette.appOrangeDark} />
                    <Text style={styles.lockedBadgeText}>Đã khóa</Text>
                  </View>
                </View>
                <Text style={styles.cardDate}>Khởi hành {trip.startDate}</Text>
                <View style={styles.cardStats}>
                  <Text style={styles.cardStatText}>{trip.totalDays} ngày</Text>
                  <View style={styles.dot} />
                  <Text style={styles.cardStatText}>{trip.poiCount} điểm</Text>
                  <View style={styles.dot} />
                  <Text style={styles.cardStatText}>GPS sẵn sàng</Text>
                </View>
              </View>
              <AppIcon name="check" size={18} color={colors.palette.appOrangeDark} />
            </TouchableOpacity>
          ))
        )}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.palette.appCream },
  header: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
  },
  eyebrow: {
    fontFamily: typography.primary.semiBold,
    fontSize: 12,
    color: colors.palette.appOrangeDark,
    textTransform: "uppercase",
  },
  headerTitle: {
    fontFamily: typography.primary.bold,
    fontSize: 28,
    color: colors.palette.appInk,
    marginTop: 4,
  },
  headerSub: {
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: colors.palette.appMuted,
    marginTop: 6,
    lineHeight: 21,
  },
  statsRow: {
    flexDirection: "row",
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    marginBottom: spacing.md,
  },
  statCard: {
    flex: 1,
    backgroundColor: "rgba(255, 255, 255, 0.58)",
    borderRadius: 16,
    padding: spacing.md,
    borderWidth: 1.5,
    borderColor: "rgba(255, 255, 255, 0.9)",
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
  statValue: {
    fontFamily: typography.primary.bold,
    fontSize: 24,
    color: colors.palette.appOrangeDark,
  },
  statLabel: {
    fontFamily: typography.primary.medium,
    fontSize: 12,
    color: colors.palette.appMuted,
    marginTop: 2,
  },
  listContent: { padding: spacing.lg, gap: spacing.md },
  emptyState: {
    alignItems: "center",
    paddingTop: 84,
    gap: spacing.md,
  },
  emptyIconWrap: {
    width: 76,
    height: 76,
    borderRadius: 24,
    backgroundColor: colors.palette.appOrangeSoft,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: colors.palette.appLine,
  },
  emptyTitle: {
    fontFamily: typography.primary.bold,
    fontSize: 20,
    color: colors.palette.appInk,
    textAlign: "center",
  },
  emptySub: {
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: colors.palette.appMuted,
    textAlign: "center",
    lineHeight: 22,
    paddingHorizontal: spacing.md,
  },
  primaryButton: {
    marginTop: spacing.sm,
    backgroundColor: colors.palette.appOrange,
    borderRadius: 16,
    paddingHorizontal: 22,
    paddingVertical: 13,
  },
  primaryButtonText: {
    fontFamily: typography.primary.bold,
    fontSize: 14,
    color: "#FFFFFF",
  },
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    backgroundColor: "rgba(255, 255, 255, 0.58)",
    borderRadius: 18,
    padding: spacing.md,
    borderWidth: 1.5,
    borderColor: "rgba(255, 255, 255, 0.9)",
    ...Platform.select({
      web: {
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
      } as any
    }),
    shadowColor: "#1F2937",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.04,
    shadowRadius: 14,
    elevation: 2,
  },
  cardIcon: {
    width: 48,
    height: 48,
    borderRadius: 16,
    backgroundColor: colors.palette.appOrange,
    alignItems: "center",
    justifyContent: "center",
  },
  cardBody: { flex: 1, minWidth: 0 },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  destination: {
    flex: 1,
    fontFamily: typography.primary.bold,
    fontSize: 16,
    color: colors.palette.appInk,
  },
  lockedBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.palette.appOrangeSoft,
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  lockedBadgeText: {
    fontFamily: typography.primary.semiBold,
    fontSize: 11,
    color: colors.palette.appOrangeDark,
  },
  cardDate: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: colors.palette.appMuted,
    marginTop: 4,
  },
  cardStats: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 8,
    flexWrap: "wrap",
  },
  cardStatText: {
    fontFamily: typography.primary.medium,
    fontSize: 12,
    color: colors.palette.appInk,
  },
  dot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.palette.appLine,
  },
})
