/**
 * DayTabBar - Dark Royal Hue Design
 * Active tab: Imperial Gold indicator + white text
 */
import React from "react"
import { ScrollView, View, Text, TouchableOpacity, StyleSheet, ViewStyle } from "react-native"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

interface DayTab {
  dayIndex: number
  date?: string
  label?: string
}

interface DayTabBarProps {
  days: DayTab[]
  activeDay: number
  onDayChange: (dayIndex: number) => void
  style?: ViewStyle
  testID?: string
}

export const DayTabBar: React.FC<DayTabBarProps> = ({ days, activeDay, onDayChange, style, testID }) => (
  <View style={[styles.wrapper, style]} testID={testID}>
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
      {days.map((day) => {
        const isActive = day.dayIndex === activeDay
        const label = day.label ?? `Ngày ${day.dayIndex}`
        return (
          <TouchableOpacity
            key={day.dayIndex}
            style={[styles.tab, isActive && styles.tabActive]}
            onPress={() => onDayChange(day.dayIndex)}
            activeOpacity={0.7}
            testID={`day-tab-${day.dayIndex}`}
          >
            <Text style={[styles.tabLabel, isActive && styles.tabLabelActive]}>{label}</Text>
            {day.date && <Text style={[styles.tabDate, isActive && styles.tabDateActive]}>{day.date}</Text>}
            {isActive && <View style={styles.indicator} />}
          </TouchableOpacity>
        )
      })}
    </ScrollView>
  </View>
)

const styles = StyleSheet.create({
  wrapper: {
    backgroundColor: "rgba(255,255,255,0.04)",
    borderBottomWidth: 1,
    borderBottomColor: "rgba(255,255,255,0.08)",
  },
  scrollContent: { paddingHorizontal: spacing.lg },
  tab: {
    marginRight: spacing.xl, paddingVertical: spacing.sm,
    alignItems: "center", position: "relative",
  },
  tabActive: {},
  tabLabel: {
    fontFamily: typography.primary.normal, fontSize: 14,
    color: "rgba(255,255,255,0.4)",
  },
  tabLabelActive: {
    fontFamily: typography.primary.semiBold, color: "#FFFFFF",
  },
  tabDate: {
    fontFamily: typography.primary.normal, fontSize: 11,
    color: "rgba(255,255,255,0.3)", marginTop: 2,
  },
  tabDateActive: { color: "rgba(255,255,255,0.65)" },
  indicator: {
    position: "absolute", bottom: 0, left: 0, right: 0,
    height: 2, backgroundColor: colors.palette.imperialGold, borderRadius: 1,
  },
})