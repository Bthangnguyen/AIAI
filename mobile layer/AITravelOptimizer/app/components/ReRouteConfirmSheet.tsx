/**
 * ReRouteConfirmSheet — BottomSheet confirmation for re-routing.
 *
 * Shows remaining stops with checkboxes to optionally exclude POIs.
 * User confirms to trigger solver.
 */
import React, { useState, useMemo, useCallback } from "react"
import {
  View,
  Text,
  StyleSheet,
} from "react-native"
import { TouchableOpacity } from "react-native-gesture-handler"
import BottomSheet, { BottomSheetView, BottomSheetScrollView } from "@gorhom/bottom-sheet"
import { useSafeAreaInsets } from "react-native-safe-area-context"
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
  bottomSheetRef,
  remainingStops,
  onConfirm,
  onClose,
}) => {
  const [excludedIds, setExcludedIds] = useState<Set<string>>(new Set())
  const snapPoints = useMemo(() => ["55%", "80%"], [])
  const insets = useSafeAreaInsets()

  const toggleExclude = useCallback((poiId: string) => {
    setExcludedIds((prev) => {
      const next = new Set(prev)
      if (next.has(poiId)) {
        next.delete(poiId)
      } else {
        next.add(poiId)
      }
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
      ref={bottomSheetRef}
      index={-1}
      snapPoints={snapPoints}
      enablePanDownToClose
      onClose={onClose}
      backgroundStyle={styles.sheetBg}
      handleIndicatorStyle={styles.handle}
    >
      <BottomSheetView style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>🔄 Re-optimize route</Text>
          <Text style={styles.subtitle}>
            {activeCount} of {remainingStops.length} stops will be re-optimized
          </Text>
        </View>

        {/* Stop list */}
        <BottomSheetScrollView style={styles.listContainer} showsVerticalScrollIndicator={false} nestedScrollEnabled>
          {remainingStops.map((stop) => {
            const isExcluded = excludedIds.has(stop.poi_id)
            return (
              <TouchableOpacity
                key={stop.poi_id}
                style={[styles.stopItem, isExcluded && styles.stopExcluded]}
                onPress={() => toggleExclude(stop.poi_id)}
                activeOpacity={0.7}
              >
                <View style={[styles.checkbox, isExcluded && styles.checkboxExcluded]}>
                  <Text style={styles.checkmark}>{isExcluded ? "✕" : "✓"}</Text>
                </View>
                <View style={styles.stopInfo}>
                  <Text
                    style={[styles.stopName, isExcluded && styles.stopNameExcluded]}
                    numberOfLines={1}
                  >
                    {stop.poi_name}
                  </Text>
                  <Text style={styles.stopTime}>
                    {minutesToHHMM(stop.arrival_time_min)} — {minutesToHHMM(stop.departure_time_min)}
                    {" · "}
                    {stop.visit_duration_min} min
                  </Text>
                </View>
                {stop.entrance_fee > 0 && (
                  <Text style={styles.fee}>
                    {(stop.entrance_fee / 1000).toFixed(0)}k₫
                  </Text>
                )}
              </TouchableOpacity>
            )
          })}
        </BottomSheetScrollView>

        {/* Actions */}
        <View style={[styles.actions, { paddingBottom: Math.max(insets.bottom, spacing.md) }]}>
          <TouchableOpacity
            style={styles.cancelBtn}
            onPress={onClose}
            activeOpacity={0.7}
          >
            <Text style={styles.cancelText}>Cancel</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.confirmBtn, activeCount === 0 && styles.confirmDisabled]}
            onPress={handleConfirm}
            disabled={activeCount === 0}
            activeOpacity={0.8}
          >
            <Text style={styles.confirmText}>
              Re-route {activeCount} stops
            </Text>
          </TouchableOpacity>
        </View>
      </BottomSheetView>
    </BottomSheet>
  )
}

const styles = StyleSheet.create({
  sheetBg: {
    backgroundColor: colors.palette.figmaWhite,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
  },
  handle: {
    backgroundColor: colors.palette.figmaGrayLight,
    width: 40,
  },
  container: {
    flex: 1,
    paddingHorizontal: spacing.lg,
  },
  header: {
    paddingBottom: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.palette.figmaGrayLight,
  },
  title: {
    fontFamily: typography.primary.bold,
    fontSize: 20,
    color: colors.palette.figmaPrimaryBlack,
    marginBottom: 4,
  },
  subtitle: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: colors.palette.figmaGrayMedium,
  },
  listContainer: {
    flex: 1,
    marginTop: spacing.sm,
  },
  stopItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
    paddingHorizontal: spacing.sm,
    borderRadius: 12,
    marginBottom: 4,
  },
  stopExcluded: {
    opacity: 0.5,
    backgroundColor: colors.palette.figmaGrayLight,
  },
  checkbox: {
    width: 28,
    height: 28,
    borderRadius: 8,
    backgroundColor: colors.palette.figmaPrimaryBlack,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 12,
  },
  checkboxExcluded: {
    backgroundColor: colors.palette.figmaGrayMedium,
  },
  checkmark: {
    color: colors.palette.figmaWhite,
    fontSize: 14,
    fontWeight: "bold",
  },
  stopInfo: {
    flex: 1,
  },
  stopName: {
    fontFamily: typography.primary.semiBold,
    fontSize: 14,
    color: colors.palette.figmaPrimaryBlack,
  },
  stopNameExcluded: {
    textDecorationLine: "line-through",
    color: colors.palette.figmaGrayMedium,
  },
  stopTime: {
    fontFamily: typography.primary.normal,
    fontSize: 12,
    color: colors.palette.figmaGrayMedium,
    marginTop: 2,
  },
  fee: {
    fontFamily: typography.primary.medium,
    fontSize: 12,
    color: colors.palette.figmaGrayDark,
  },
  actions: {
    flexDirection: "row",
    gap: spacing.md,
    paddingVertical: spacing.md,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.palette.figmaGrayLight,
  },
  cancelBtn: {
    flex: 1,
    height: 48,
    borderRadius: 24,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1.5,
    borderColor: colors.palette.figmaGrayLight,
  },
  cancelText: {
    fontFamily: typography.primary.medium,
    fontSize: 14,
    color: colors.palette.figmaGrayDark,
  },
  confirmBtn: {
    flex: 2,
    height: 48,
    borderRadius: 24,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.palette.figmaPrimaryBlack,
  },
  confirmDisabled: {
    opacity: 0.4,
  },
  confirmText: {
    fontFamily: typography.primary.semiBold,
    fontSize: 14,
    color: colors.palette.figmaWhite,
  },
})
