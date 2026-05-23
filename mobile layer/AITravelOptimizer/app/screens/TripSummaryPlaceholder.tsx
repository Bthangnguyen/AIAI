/**
 * TripSummaryPlaceholder — Wallet tab placeholder.
 * Shows active trip or empty state prompting user to plan.
 */
import React from "react"
import { View, Text, StyleSheet, SafeAreaView, Pressable } from "react-native"
import { useNavigation } from "@react-navigation/native"
import type { NativeStackNavigationProp } from "@react-navigation/native-stack"

import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { CTAButton } from "@/components/CTAButton"
import { AppStackParamList } from "@/navigators/navigationTypes"
import { useTripStore } from "@/store/useTripStore"

type Nav = NativeStackNavigationProp<AppStackParamList>

export const TripSummaryPlaceholder: React.FC = () => {
  const navigation = useNavigation<Nav>()
  const currentItinerary = useTripStore((state) => state.currentItinerary)
  const resetTrip = useTripStore((state) => state.resetTrip)

  const handleResume = () => {
    if (currentItinerary) {
      navigation.navigate("MapTimeline", { itinerary: currentItinerary })
    }
  }

  const handleReset = () => {
    resetTrip()
    navigation.navigate("ItineraryForm")
  }

  return (
    <SafeAreaView style={styles.safe}>
      {currentItinerary ? (
        <View style={styles.activeContainer}>
          <Text style={styles.emoji}>✈️</Text>
          <Text style={styles.activeTitle}>
            {currentItinerary.days?.[0]?.start_hotel_name ? `Trip from ${currentItinerary.days[0].start_hotel_name}` : "Active Travel Plan"}
          </Text>
          <Text style={styles.activeSubtitle}>
            {currentItinerary.num_days} Ngày · {currentItinerary.total_pois_visited} Địa điểm
          </Text>

          {/* Stats Box */}
          <View style={styles.statsBox}>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{currentItinerary.total_distance_km?.toFixed(1) || 0}km</Text>
              <Text style={styles.statLabel}>Khoảng cách</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statValue}>
                {currentItinerary.total_entrance_fee > 0 
                  ? `${(currentItinerary.total_entrance_fee / 1000).toFixed(0)}k₫`
                  : "Miễn phí"
                }
              </Text>
              <Text style={styles.statLabel}>Phí dự tính</Text>
            </View>
          </View>

          <CTAButton
            label="Xem lịch trình đang đi"
            onPress={handleResume}
            style={styles.cta}
          />
          
          <Pressable style={styles.resetBtn} onPress={handleReset}>
            <Text style={styles.resetText}>Xóa nháp & Lên lịch mới</Text>
          </Pressable>
        </View>
      ) : (
        <View style={styles.container}>
          <Text style={styles.emoji}>🗺️</Text>
          <Text style={styles.title}>No Active Trip</Text>
          <Text style={styles.subtitle}>
            Plan your next adventure and it will appear here with your full itinerary.
          </Text>
          <CTAButton
            label="Plan a Trip"
            onPress={() => navigation.navigate("ItineraryForm")}
            style={styles.cta}
          />
        </View>
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.palette.figmaWhite },
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.xxl,
  },
  activeContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.xxl,
  },
  emoji: { fontSize: 64, marginBottom: spacing.lg },
  title: {
    fontFamily: typography.primary.bold,
    fontSize: 22,
    color: colors.palette.figmaBlack,
    marginBottom: spacing.sm,
    textAlign: "center",
  },
  activeTitle: {
    fontFamily: typography.primary.bold,
    fontSize: 22,
    color: colors.palette.figmaBlack,
    marginBottom: spacing.xs,
    textAlign: "center",
  },
  subtitle: {
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: colors.palette.figmaGrayMedium,
    textAlign: "center",
    lineHeight: 22,
    marginBottom: spacing.xl,
  },
  activeSubtitle: {
    fontFamily: typography.primary.medium,
    fontSize: 15,
    color: colors.palette.figmaGrayMedium,
    marginBottom: spacing.xl,
    textAlign: "center",
  },
  statsBox: {
    flexDirection: "row",
    backgroundColor: colors.palette.figmaOffWhite,
    borderRadius: 16,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xl,
    alignItems: "center",
    justifyContent: "space-around",
    width: "100%",
    marginBottom: spacing.xl,
    borderWidth: 1,
    borderColor: colors.palette.figmaGrayLight,
  },
  statItem: {
    alignItems: "center",
  },
  statValue: {
    fontSize: 16,
    fontFamily: typography.primary.semiBold,
    color: colors.palette.figmaBlack,
  },
  statLabel: {
    fontSize: 11,
    fontFamily: typography.primary.normal,
    color: colors.palette.figmaGrayMedium,
    marginTop: 2,
  },
  statDivider: {
    width: 1,
    height: 24,
    backgroundColor: colors.palette.figmaGrayLight,
  },
  resetBtn: {
    marginTop: spacing.lg,
    paddingVertical: spacing.sm,
  },
  resetText: {
    fontFamily: typography.primary.medium,
    fontSize: 14,
    color: colors.palette.figmaBlue,
  },
  cta: { width: "100%" },
})
