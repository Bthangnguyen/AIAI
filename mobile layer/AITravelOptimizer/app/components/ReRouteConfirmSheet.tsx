/**
 * ReRouteConfirmSheet - Dark Royal Hue BottomSheet
 */
import React, { useState, useMemo, useCallback } from "react"
import { View, Text, StyleSheet, TouchableOpacity } from "react-native"
import BottomSheet, { BottomSheetView, BottomSheetScrollView } from "@gorhom/bottom-sheet"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { LinearGradient } from "expo-linear-gradient"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import type { TravelItineraryStop } from "@/navigators/navigationTypes"
import { minutesToHHMM } from "@/utils/itineraryHelpers"

interface ReRouteConfirmSheetProps {
  bottomSheetRef: React.RefObject<BottomSheet | null>
  remainingStops: TravelItineraryStop[]
  onConfirm: (excludedIds: string[]) => void
  onClose: () => void
}

export const ReRouteConfirmSheet: React.FC<ReRouteConfirmSheetProps> = ({
  bottomSheetRef, remainingStops, onConfirm, onClose,
}) => {
  const [excludedIds, setExcludedIds] = useState<Set<string>>(new Set())
  const snapPoints = useMemo(() => ["55%", "80%"], [])
  const insets = useSafeAreaInsets()

  const toggleExclude = useCallback((poiId: string) => {
    setExcludedIds((prev) => {
      const next = new Set(prev)
      next.has(poiId) ? next.delete(poiId) : next.add(poiId)
      return next
    })
  }, [])

  const handleConfirm = useCallback(() => {
    onConfirm(Array.from(excludedIds))
    setExcludedIds(new Set())
  }, [excludedIds, onConfirm])

  const activeCount = remainingStops.length - excludedIds.size

  return (
    <BottomSheet
      ref={bottomSheetRef} index={-1} snapPoints={snapPoints}
      enablePanDownToClose onClose={onClose}
      backgroundStyle={styles.sheetBg}
      handleIndicatorStyle={styles.handle}
    >
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>🤖 Tối ưu lại lộ trình</Text>
          <Text style={styles.subtitle}>
            {activeCount}/{remainingStops.length} điểm sẽ được sắp xếp lại
          </Text>
        </View>

        {/* Stop list */}
        <BottomSheetScrollView style={styles.listContainer} showsVerticalScrollIndicator={false} nestedScrollEnabled>
          {remainingStops.map((stop) => {
            const isExcluded = excludedIds.has(stop.poi_id)
            return (
              <TouchableOpacity
                key={stop.poi_id}
                style={[styles.stopRow, isExcluded && styles.stopRowExcluded]}
                onPress={() => toggleExclude(stop.poi_id)}
                activeOpacity={0.75}
              >
                <View style={[styles.checkbox, isExcluded && styles.checkboxUnchecked]}>
                  {!isExcluded && <Text style={styles.checkmark}>✓</Text>}
                </View>
                <View style={styles.stopInfo}>
                  <Text style={[styles.stopName, isExcluded && styles.stopNameExcluded]} numberOfLines={1}>
                    {stop.poi_name}
                  </Text>
                  <Text style={styles.stopTime}>{minutesToHHMM(stop.arrival_time_min)}</Text>
                </View>
                {isExcluded && (
                  <View style={styles.skipBadge}>
                    <Text style={styles.skipBadgeText}>Bỏ qua</Text>
                  </View>
                )}
              </TouchableOpacity>
            )
          })}
        </BottomSheetScrollView>

        {/* Actions */}
        <View style={[styles.actions, { paddingBottom: insets.bottom + 16 }]}>
          <TouchableOpacity style={styles.cancelBtn} onPress={onClose}>
            <Text style={styles.cancelText}>Hủy</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.confirmBtn} onPress={handleConfirm}>
            <LinearGradient
              colors={[colors.palette.royalPurple, colors.palette.royalPurpleLight]}
              style={styles.confirmBtnGradient}
              start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
            >
              <Text style={styles.confirmText}>🤖 Tối ưu ngay ({activeCount} điểm)</Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>
      </View>
    </BottomSheet>
  )
}

const styles = StyleSheet.create({
  sheetBg: { backgroundColor: "#0e1320" },
  handle: { backgroundColor: "rgba(255,255,255,0.25)", width: 36 },
  container: { flex: 1 },
  header: {
    paddingHorizontal: spacing.lg, paddingVertical: spacing.md,
    borderBottomWidth: 1, borderBottomColor: "rgba(255,255,255,0.06)",
  },
  title: { fontFamily: typography.primary.bold, fontSize: 18, color: "#FFFFFF", marginBottom: 4 },
  subtitle: { fontFamily: typography.primary.normal, fontSize: 13, color: "rgba(255,255,255,0.45)" },
  listContainer: { flex: 1 },
  stopRow: {
    flexDirection: "row", alignItems: "center", gap: spacing.md,
    paddingHorizontal: spacing.lg, paddingVertical: spacing.md,
    borderBottomWidth: 1, borderBottomColor: "rgba(255,255,255,0.05)",
  },
  stopRowExcluded: { opacity: 0.5 },
  checkbox: {
    width: 24, height: 24, borderRadius: 8,
    backgroundColor: colors.palette.royalPurple,
    justifyContent: "center", alignItems: "center",
  },
  checkboxUnchecked: {
    backgroundColor: "rgba(255,255,255,0.08)",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.2)",
  },
  checkmark: { color: "#FFFFFF", fontSize: 14, fontFamily: typography.primary.bold },
  stopInfo: { flex: 1 },
  stopName: { fontFamily: typography.primary.semiBold, fontSize: 14, color: "#FFFFFF" },
  stopNameExcluded: { textDecorationLine: "line-through", color: "rgba(255,255,255,0.4)" },
  stopTime: { fontFamily: typography.primary.normal, fontSize: 12, color: "rgba(255,255,255,0.35)", marginTop: 2 },
  skipBadge: {
    backgroundColor: colors.palette.sunsetOrange + "25",
    borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3,
    borderWidth: 1, borderColor: colors.palette.sunsetOrange + "50",
  },
  skipBadgeText: { fontFamily: typography.primary.semiBold, fontSize: 11, color: colors.palette.sunsetOrange },
  actions: {
    flexDirection: "row", gap: spacing.sm,
    paddingHorizontal: spacing.lg, paddingTop: spacing.sm,
    borderTopWidth: 1, borderTopColor: "rgba(255,255,255,0.06)",
  },
  cancelBtn: {
    flex: 1, paddingVertical: 14, borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.06)",
    alignItems: "center", borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
  },
  cancelText: { fontFamily: typography.primary.semiBold, fontSize: 15, color: "rgba(255,255,255,0.6)" },
  confirmBtn: { flex: 2, borderRadius: 14, overflow: "hidden" },
  confirmBtnGradient: { paddingVertical: 14, alignItems: "center" },
  confirmText: { fontFamily: typography.primary.semiBold, fontSize: 15, color: "#FFFFFF" },
})