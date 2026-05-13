/**
 * CategoryChip — Figma "Schedule page" filter pills.
 * Active: black bg + white text. Inactive: white bg + gray text + border.
 * Border radius: 34px (Figma exact).
 */
import React from "react"
import { TouchableOpacity, Text, StyleSheet, ViewStyle } from "react-native"
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

export const CategoryChip: React.FC<CategoryChipProps> = ({
  label,
  active = false,
  onPress,
  style,
  testID,
}) => {
  return (
    <TouchableOpacity
      style={[styles.chip, active ? styles.chipActive : styles.chipInactive, style]}
      onPress={onPress}
      activeOpacity={0.75}
      testID={testID}
    >
      <Text style={[styles.label, active ? styles.labelActive : styles.labelInactive]}>
        {label}
      </Text>
    </TouchableOpacity>
  )
}

const styles = StyleSheet.create({
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xxs + 2,
    borderRadius: 34,
    justifyContent: "center",
    alignItems: "center",
  },
  chipActive: {
    backgroundColor: colors.palette.figmaPrimaryBlack,
  },
  chipInactive: {
    backgroundColor: colors.palette.figmaWhite,
    borderWidth: 1,
    borderColor: colors.palette.figmaGrayLight,
  },
  label: {
    fontFamily: typography.primary.medium,
    fontSize: 13,
    letterSpacing: 0.2,
  },
  labelActive: {
    color: colors.palette.figmaWhite,
  },
  labelInactive: {
    color: colors.palette.figmaGrayMedium,
  },
})
