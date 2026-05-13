/**
 * DayTabBar — Day 1 / Day 2 / Day 3 horizontal tab scroller.
 * Active tab: bold black text + bottom indicator line.
 * Matches Figma "Itinerary page" / "Weather query page".
 */
import React, { useRef } from "react"
import {
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ViewStyle,
  Animated,
} from "react-native"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

interface DayTab {
  dayIndex: number
  date?: string // "July 14"
  label?: string // "Day 1" (auto-generated if not provided)
}

interface DayTabBarProps {
  days: DayTab[]
  activeDay: number
  onDayChange: (dayIndex: number) => void
  style?: ViewStyle
  testID?: string
}

export const DayTabBar: React.FC<DayTabBarProps> = ({
  days,
  activeDay,
  onDayChange,
  style,
  testID,
}) => {
  return (
    <View style={[styles.wrapper, style]} testID={testID}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {days.map((day) => {
          const isActive = day.dayIndex === activeDay
          const label = day.label ?? `Day ${day.dayIndex}`
          return (
            <TouchableOpacity
              key={day.dayIndex}
              style={styles.tab}
              onPress={() => onDayChange(day.dayIndex)}
              activeOpacity={0.7}
              testID={`day-tab-${day.dayIndex}`}
            >
              <Text
                style={[
                  styles.tabLabel,
                  isActive ? styles.tabLabelActive : styles.tabLabelInactive,
                ]}
              >
                {label}
              </Text>
              {day.date && (
                <Text style={styles.tabDate}>{day.date}</Text>
              )}
              {/* Active indicator line */}
              {isActive && <View style={styles.indicator} />}
            </TouchableOpacity>
          )
        })}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  wrapper: {
    backgroundColor: colors.palette.figmaWhite,
    borderBottomWidth: 1,
    borderBottomColor: colors.palette.figmaGrayLight,
  },
  scrollContent: {
    paddingHorizontal: spacing.lg,
  },
  tab: {
    marginRight: spacing.xl,
    paddingVertical: spacing.sm,
    alignItems: "center",
    position: "relative",
  },
  tabLabel: {
    fontFamily: typography.primary.semiBold,
    fontSize: 14,
  },
  tabLabelActive: {
    color: colors.palette.figmaPrimaryBlack,
  },
  tabLabelInactive: {
    color: colors.palette.figmaGrayMedium,
    fontFamily: typography.primary.normal,
  },
  tabDate: {
    fontFamily: typography.primary.normal,
    fontSize: 11,
    color: colors.palette.figmaGrayMedium,
    marginTop: 2,
  },
  indicator: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: colors.palette.figmaPrimaryBlack,
    borderRadius: 1,
  },
})
