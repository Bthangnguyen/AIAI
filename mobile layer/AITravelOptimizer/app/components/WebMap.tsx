import React from "react"
import { View, Text, StyleSheet, Dimensions, Pressable } from "react-native"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { LinearGradient } from "expo-linear-gradient"

export const WebMap = ({
  dayStops = [],
  selectedDayIndex = 0,
  selectedStopId = null,
  onMarkerPress,
}: any) => {
  return (
    <LinearGradient
      colors={[colors.palette.deepSlate, "#121829", "#1a233d"]}
      style={StyleSheet.absoluteFill}
    >
      <View style={$container}>
        {/* Map Header Preview Status */}
        <View style={$statusCard}>
          <Text style={$statusIcon}>🗺️</Text>
          <View style={$statusTextContainer}>
            <Text style={$statusTitle}>Bản Đồ Chạy Thử (Expo Go)</Text>
            <Text style={$statusSubtitle}>
              Bản đồ tương tác Mapbox yêu cầu build file .APK để chạy trên điện thoại.
            </Text>
          </View>
        </View>

        {/* Visual Map Route Mockup (Futuristic Blueprint Layout) */}
        <View style={$blueprintMap}>
          {dayStops.length === 0 ? (
            <View style={$emptyState}>
              <Text style={$emptyText}>Chưa có địa điểm nào cho ngày này.</Text>
              <Text style={$emptySubtext}>Hãy thêm địa điểm từ Trợ lý ảo AI Chat!</Text>
            </View>
          ) : (
            <View style={$blueprintRouteContainer}>
              {/* Vertical dashed line representing route */}
              <View style={$blueprintLine} />

              {dayStops.map((stop: any, idx: number) => {
                const isSelected = selectedStopId === stop.poi_id
                return (
                  <Pressable
                    key={stop.poi_id}
                    onPress={() => onMarkerPress && onMarkerPress(stop)}
                    style={[
                      $blueprintStopCard,
                      isSelected && $blueprintStopCardActive,
                    ]}
                  >
                    <View style={[$blueprintBadge, isSelected && $blueprintBadgeActive]}>
                      <Text style={$blueprintBadgeText}>{idx + 1}</Text>
                    </View>
                    <View style={$blueprintStopInfo}>
                      <Text style={$blueprintStopName} numberOfLines={1}>
                        {stop.name}
                      </Text>
                      <Text style={$blueprintStopDetails}>
                        📍 {stop.location.latitude.toFixed(4)}, {stop.location.longitude.toFixed(4)}
                      </Text>
                    </View>
                    {isSelected && (
                      <View style={$activeIndicator}>
                        <Text style={$activeIndicatorText}>ĐANG CHỌN</Text>
                      </View>
                    )}
                  </Pressable>
                )
              })}
            </View>
          )}
        </View>

        {/* Action instruction to proceed with APK */}
        <View style={$actionNote}>
          <Text style={$actionNoteText}>
            💡 Mẹo: Bạn vẫn có thể sử dụng Trợ lý Chat, thay đổi lịch trình, kéo thả thứ tự thoải mái. Sau khi ưng ý UI/UX, chúng ta sẽ bắt đầu build .apk để test Mapbox hoàn chỉnh nhé!
          </Text>
        </View>
      </View>
    </LinearGradient>
  )
}

const $container: any = {
  flex: 1,
  padding: spacing.md,
  paddingTop: spacing.xxl + spacing.lg,
  justifyContent: "space-between",
}

const $statusCard: any = {
  flexDirection: "row",
  backgroundColor: "rgba(255, 255, 255, 0.08)",
  borderRadius: 16,
  padding: spacing.md,
  alignItems: "center",
  borderWidth: 1,
  borderColor: colors.palette.glassBorder,
}

const $statusIcon: any = {
  fontSize: 32,
  marginRight: spacing.md,
}

const $statusTextContainer: any = {
  flex: 1,
}

const $statusTitle: any = {
  color: colors.palette.neutral100,
  fontSize: 16,
  fontFamily: typography.primary.bold,
  marginBottom: 2,
}

const $statusSubtitle: any = {
  color: "rgba(255, 255, 255, 0.6)",
  fontSize: 12,
  fontFamily: typography.primary.normal,
}

const $blueprintMap: any = {
  flex: 1,
  marginVertical: spacing.lg,
  backgroundColor: "rgba(0, 0, 0, 0.25)",
  borderRadius: 20,
  padding: spacing.md,
  borderWidth: 1.5,
  borderStyle: "dashed",
  borderColor: "rgba(255, 255, 255, 0.15)",
  justifyContent: "center",
}

const $emptyState: any = {
  alignItems: "center",
  justifyContent: "center",
}

const $emptyText: any = {
  color: colors.palette.neutral100,
  fontSize: 16,
  fontFamily: typography.primary.medium,
  textAlign: "center",
  marginBottom: spacing.sm,
}

const $emptySubtext: any = {
  color: "rgba(255, 255, 255, 0.4)",
  fontSize: 13,
  fontFamily: typography.primary.normal,
  textAlign: "center",
}

const $blueprintRouteContainer: any = {
  flex: 1,
  paddingLeft: spacing.md,
  justifyContent: "center",
}

const $blueprintLine: any = {
  position: "absolute",
  left: spacing.md + 13,
  top: 30,
  bottom: 30,
  width: 2,
  backgroundColor: colors.palette.figmaBlue,
  opacity: 0.4,
}

const $blueprintStopCard: any = {
  flexDirection: "row",
  alignItems: "center",
  backgroundColor: "rgba(255, 255, 255, 0.04)",
  borderRadius: 12,
  padding: spacing.sm,
  marginVertical: spacing.sm,
  borderWidth: 1,
  borderColor: "transparent",
}

const $blueprintStopCardActive: any = {
  backgroundColor: "rgba(3, 115, 243, 0.15)",
  borderColor: colors.palette.figmaBlue,
}

const $blueprintBadge: any = {
  width: 26,
  height: 26,
  borderRadius: 13,
  backgroundColor: "rgba(255, 255, 255, 0.2)",
  justifyContent: "center",
  alignItems: "center",
  marginRight: spacing.md,
}

const $blueprintBadgeActive: any = {
  backgroundColor: colors.palette.figmaBlue,
}

const $blueprintBadgeText: any = {
  color: colors.palette.neutral100,
  fontSize: 12,
  fontFamily: typography.primary.bold,
}

const $blueprintStopInfo: any = {
  flex: 1,
}

const $blueprintStopName: any = {
  color: colors.palette.neutral100,
  fontSize: 14,
  fontFamily: typography.primary.medium,
}

const $blueprintStopDetails: any = {
  color: "rgba(255, 255, 255, 0.4)",
  fontSize: 11,
  fontFamily: typography.primary.normal,
  marginTop: 2,
}

const $activeIndicator: any = {
  backgroundColor: "rgba(104, 214, 202, 0.2)",
  paddingHorizontal: 6,
  paddingVertical: 2,
  borderRadius: 4,
  borderWidth: 0.5,
  borderColor: colors.palette.figmaTeal,
}

const $activeIndicatorText: any = {
  color: colors.palette.figmaTeal,
  fontSize: 9,
  fontFamily: typography.primary.bold,
}

const $actionNote: any = {
  backgroundColor: "rgba(255, 107, 107, 0.08)",
  borderRadius: 12,
  padding: spacing.md,
  borderWidth: 1,
  borderColor: "rgba(255, 107, 107, 0.2)",
}

const $actionNoteText: any = {
  color: colors.palette.sunsetOrangeLight,
  fontSize: 12,
  lineHeight: 18,
  fontFamily: typography.primary.normal,
}
