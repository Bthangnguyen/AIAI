/**
 * CTAButton — Primary action button (Figma: 36px radius, full-width black).
 * Variants: primary (black), outline (white + border), gradient.
 */
import React from "react"
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ViewStyle,
  TextStyle,
  ActivityIndicator,
} from "react-native"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

type CTAVariant = "primary" | "outline" | "ghost"

interface CTAButtonProps {
  label: string
  onPress: () => void
  variant?: CTAVariant
  disabled?: boolean
  loading?: boolean
  style?: ViewStyle
  labelStyle?: TextStyle
  testID?: string
}

export const CTAButton: React.FC<CTAButtonProps> = ({
  label,
  onPress,
  variant = "primary",
  disabled = false,
  loading = false,
  style,
  labelStyle,
  testID,
}) => {
  const isPrimary = variant === "primary"
  const isOutline = variant === "outline"

  return (
    <TouchableOpacity
      style={[
        styles.base,
        isPrimary && styles.primary,
        isOutline && styles.outline,
        variant === "ghost" && styles.ghost,
        (disabled || loading) && styles.disabled,
        style,
      ]}
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.82}
      testID={testID}
    >
      {loading ? (
        <ActivityIndicator color={isPrimary ? "#fff" : colors.palette.figmaPrimaryBlack} size="small" />
      ) : (
        <Text
          style={[
            styles.label,
            isPrimary && styles.labelPrimary,
            isOutline && styles.labelOutline,
            labelStyle,
          ]}
        >
          {label}
        </Text>
      )}
    </TouchableOpacity>
  )
}

const styles = StyleSheet.create({
  base: {
    height: 54,
    borderRadius: 36,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: spacing.xl,
  },
  primary: {
    backgroundColor: colors.palette.figmaPrimaryBlack,
  },
  outline: {
    backgroundColor: colors.palette.figmaWhite,
    borderWidth: 1.5,
    borderColor: colors.palette.figmaGrayLight,
  },
  ghost: {
    backgroundColor: "transparent",
  },
  disabled: {
    opacity: 0.45,
  },
  label: {
    fontFamily: typography.primary.semiBold,
    fontSize: 16,
    letterSpacing: 0.3,
  },
  labelPrimary: {
    color: colors.palette.figmaWhite,
  },
  labelOutline: {
    color: colors.palette.figmaGrayDark,
  },
})
