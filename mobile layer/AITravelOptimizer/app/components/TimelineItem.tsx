/**
 * TimelineItem - Dark Royal Hue Design
 */
import React from "react"
import { View, Text, StyleSheet, ViewStyle } from "react-native"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

interface TimelineItemProps {
  time: string
  stopName: string
  activity?: string
  isFirst?: boolean
  isLast?: boolean
  isActive?: boolean
  style?: ViewStyle
  testID?: string
}

export const formatTimeMins = (totalMins: number): string => {
  const h = Math.floor(totalMins / 60)
  const m = totalMins % 60
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`
}

export const TimelineItem: React.FC<TimelineItemProps> = ({
  time, stopName, activity,
  isFirst = false, isLast = false, isActive = false,
  style, testID,
}) => (
  <View style={[styles.container, style]} testID={testID}>
    <View style={styles.timeColumn}>
      <Text style={[styles.time, isActive && styles.timeActive]}>{time}</Text>
    </View>
    <View style={styles.lineColumn}>
      {!isFirst && <View style={styles.lineTop} />}
      <View style={[styles.dot, isActive && styles.dotActive]} />
      {!isLast && <View style={styles.lineBottom} />}
    </View>
    <View style={styles.contentColumn}>
      <Text style={[styles.stopName, isActive && styles.stopNameActive]} numberOfLines={1}>{stopName}</Text>
      {activity && <Text style={styles.activity} numberOfLines={2}>{activity}</Text>}
    </View>
  </View>
)

const styles = StyleSheet.create({
  container: { flexDirection: "row", minHeight: 64 },
  timeColumn: { width: 52, paddingTop: 2, alignItems: "flex-end", paddingRight: spacing.sm },
  time: { fontFamily: typography.primary.semiBold, fontSize: 13, color: "rgba(255,255,255,0.5)" },
  timeActive: { color: colors.palette.imperialGold },
  lineColumn: { width: 20, alignItems: "center" },
  lineTop: { width: 2, flex: 1, backgroundColor: "rgba(255,255,255,0.12)", maxHeight: 8 },
  dot: {
    width: 10, height: 10, borderRadius: 5,
    backgroundColor: "rgba(255,255,255,0.3)",
    borderWidth: 2, borderColor: colors.palette.deepSlate,
  },
  dotActive: {
    backgroundColor: colors.palette.imperialGold,
    borderColor: colors.palette.deepSlate,
    shadowColor: colors.palette.imperialGold,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8, shadowRadius: 4, elevation: 4,
  },
  lineBottom: { width: 2, flex: 1, backgroundColor: "rgba(255,255,255,0.12)" },
  contentColumn: { flex: 1, paddingLeft: spacing.sm, paddingBottom: spacing.md },
  stopName: { fontFamily: typography.primary.semiBold, fontSize: 14, color: "rgba(255,255,255,0.85)", marginBottom: 2 },
  stopNameActive: { color: "#FFFFFF" },
  activity: { fontFamily: typography.primary.normal, fontSize: 12, color: "rgba(255,255,255,0.4)", lineHeight: 18 },
})