/**
 * WeatherBadge - Dark Royal Hue Design
 */
import React from "react"
import { View, Text, StyleSheet, ViewStyle } from "react-native"
import { colors } from "@/theme/colors"
import { typography } from "@/theme/typography"

interface WeatherBadgeProps {
  icon: string
  temperature: number
  size?: "sm" | "md" | "lg"
  style?: ViewStyle
  testID?: string
}

export const WeatherBadge: React.FC<WeatherBadgeProps> = ({
  icon, temperature, size = "md", style, testID,
}) => {
  const diameter = size === "sm" ? 44 : size === "md" ? 52 : 64
  const iconSize = size === "sm" ? 18 : size === "md" ? 22 : 28
  const tempSize = size === "sm" ? 10 : size === "md" ? 11 : 13
  const isHot = temperature >= 34

  return (
    <View style={[styles.wrapper, style]} testID={testID}>
      <View style={[
        styles.circle,
        { width: diameter, height: diameter, borderRadius: diameter / 2 },
        isHot && styles.circleHot,
      ]}>
        <Text style={{ fontSize: iconSize }}>{icon}</Text>
      </View>
      <Text style={[styles.temp, { fontSize: tempSize }, isHot && styles.tempHot]}>
        {`${temperature}°`}
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  wrapper: { alignItems: "center", gap: 4 },
  circle: {
    backgroundColor: "rgba(255,255,255,0.08)",
    justifyContent: "center", alignItems: "center",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.15)",
    shadowColor: "#000", shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2, shadowRadius: 6, elevation: 3,
  },
  circleHot: {
    backgroundColor: colors.palette.sunsetOrange + "25",
    borderColor: colors.palette.sunsetOrange + "60",
  },
  temp: { fontFamily: typography.primary.semiBold, color: "rgba(255,255,255,0.7)" },
  tempHot: { color: colors.palette.sunsetOrange },
})