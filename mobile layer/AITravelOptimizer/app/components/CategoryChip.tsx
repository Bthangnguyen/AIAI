/**
 * CategoryChip - Dark Royal Hue Design
 */
import React from "react"
import { TouchableOpacity, Text, StyleSheet, ViewStyle } from "react-native"
import { LinearGradient } from "expo-linear-gradient"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

interface CategoryChipProps {
  label: string
  active?: boolean
  onPress: () => void
  style?: ViewStyle
  testID?: string
}

export const CategoryChip: React.FC<CategoryChipProps> = ({ label, active = false, onPress, style, testID }) => (
  <TouchableOpacity
    style={[styles.chip, active ? styles.chipActive : styles.chipInactive, style]}
    onPress={onPress} activeOpacity={0.75} testID={testID}
  >
    <Text style={[styles.label, active ? styles.labelActive : styles.labelInactive]}>{label}</Text>
  </TouchableOpacity>
)

const styles = StyleSheet.create({
  chip: {
    paddingHorizontal: spacing.md, paddingVertical: spacing.xxs + 4,
    borderRadius: 34, justifyContent: "center", alignItems: "center",
  },
  chipActive: {
    backgroundColor: colors.palette.royalPurple,
    shadowColor: colors.palette.royalPurple,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4, shadowRadius: 8, elevation: 4,
  },
  chipInactive: {
    backgroundColor: "rgba(255,255,255,0.07)",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
  },
  label: { fontFamily: typography.primary.medium, fontSize: 13, letterSpacing: 0.2 },
  labelActive: { color: "#FFFFFF" },
  labelInactive: { color: "rgba(255,255,255,0.5)" },
})