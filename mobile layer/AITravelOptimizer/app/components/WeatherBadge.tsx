/**
 * WeatherBadge — Circular weather icon + temperature.
 * Matches Figma "Itinerary page" weather circles.
 */
import React from "react"
import { View, Text, StyleSheet, ViewStyle } from "react-native"
import { colors } from "@/theme/colors"
import { typography } from "@/theme/typography"

interface WeatherBadgeProps {
  icon: string // emoji e.g. "☀️"
  temperature: number // Celsius
  size?: "sm" | "md" | "lg"
  style?: ViewStyle
  testID?: string
}

export const WeatherBadge: React.FC<WeatherBadgeProps> = ({
  icon,
  temperature,
  size = "md",
  style,
  testID,
}) => {
  const diameter = size === "sm" ? 44 : size === "md" ? 52 : 64
  const iconSize = size === "sm" ? 18 : size === "md" ? 22 : 28
  const tempSize = size === "sm" ? 10 : size === "md" ? 11 : 13

  return (
    <View style={[styles.wrapper, style]} testID={testID}>
      <View
        style={[
          styles.circle,
          { width: diameter, height: diameter, borderRadius: diameter / 2 },
        ]}
      >
        <Text style={{ fontSize: iconSize }}>{icon}</Text>
      </View>
      <Text style={[styles.temp, { fontSize: tempSize }]}>{`${temperature}°`}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  wrapper: {
    alignItems: "center",
    gap: 4,
  },
  circle: {
    backgroundColor: colors.palette.figmaWhite,
    justifyContent: "center",
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 6,
    elevation: 3,
  },
  temp: {
    fontFamily: typography.primary.semiBold,
    color: colors.palette.figmaBlack,
  },
})
