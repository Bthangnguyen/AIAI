/**
 * TimelineItem — Figma "Itinerary page" stop entry.
 * Time text | Vertical line + dot | Stop name + activity.
 */
import React from "react"
import { View, Text, StyleSheet, ViewStyle } from "react-native"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

interface TimelineItemProps {
  time: string // "12:30"
  stopName: string
  activity?: string
  isFirst?: boolean
  isLast?: boolean
  style?: ViewStyle
  testID?: string
}

// Helper: format arrival_time_min → "HH:MM"
export const formatTimeMins = (totalMins: number): string => {
  const h = Math.floor(totalMins / 60)
  const m = totalMins % 60
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`
}

export const TimelineItem: React.FC<TimelineItemProps> = ({
  time,
  stopName,
  activity,
  isFirst = false,
  isLast = false,
  style,
  testID,
}) => {
  return (
    <View style={[styles.container, style]} testID={testID}>
      {/* Time column */}
      <View style={styles.timeColumn}>
        <Text style={styles.time}>{time}</Text>
      </View>

      {/* Line + dot column */}
      <View style={styles.lineColumn}>
        {/* Top connector line */}
        {!isFirst && <View style={styles.lineTop} />}
        {/* Dot */}
        <View style={styles.dot} />
        {/* Bottom connector line */}
        {!isLast && <View style={styles.lineBottom} />}
      </View>

      {/* Content column */}
      <View style={styles.contentColumn}>
        <Text style={styles.stopName} numberOfLines={1}>
          {stopName}
        </Text>
        {activity && (
          <Text style={styles.activity} numberOfLines={2}>
            {activity}
          </Text>
        )}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    minHeight: 64,
  },
  timeColumn: {
    width: 52,
    paddingTop: 2,
    alignItems: "flex-end",
    paddingRight: spacing.sm,
  },
  time: {
    fontFamily: typography.primary.semiBold,
    fontSize: 13,
    color: colors.palette.figmaBlack,
  },
  lineColumn: {
    width: 20,
    alignItems: "center",
  },
  lineTop: {
    width: 2,
    flex: 1,
    backgroundColor: colors.palette.figmaGrayLight,
    maxHeight: 8,
    marginBottom: 0,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.palette.figmaPrimaryBlack,
    borderWidth: 2,
    borderColor: colors.palette.figmaWhite,
    shadowColor: colors.palette.figmaPrimaryBlack,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
    elevation: 2,
  },
  lineBottom: {
    width: 2,
    flex: 1,
    backgroundColor: colors.palette.figmaGrayLight,
    marginTop: 0,
  },
  contentColumn: {
    flex: 1,
    paddingLeft: spacing.sm,
    paddingTop: 0,
    paddingBottom: spacing.md,
  },
  stopName: {
    fontFamily: typography.primary.semiBold,
    fontSize: 14,
    color: colors.palette.figmaBlack,
    marginBottom: 2,
  },
  activity: {
    fontFamily: typography.primary.normal,
    fontSize: 12,
    color: colors.palette.figmaGrayMedium,
    lineHeight: 18,
  },
})
