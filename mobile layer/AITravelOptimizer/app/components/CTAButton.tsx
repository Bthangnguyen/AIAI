/**
 * CTAButton - Royal Hue Gradient Upgrade
 * Variants: primary (purple gradient), outline, ghost
 */
import React from "react"
import {
  TouchableOpacity, StyleSheet, ViewStyle, TextStyle, ActivityIndicator, View,
} from "react-native"
import { LinearGradient } from "expo-linear-gradient"
import { Text } from "@/components/Text"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

type CTAVariant = "primary" | "outline" | "ghost" | "danger"

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
  label, onPress, variant = "primary",
  disabled = false, loading = false,
  style, labelStyle, testID,
}) => {
  const isDisabled = disabled || loading

  if (variant === "primary") {
    return (
      <TouchableOpacity
        style={[styles.base, isDisabled && styles.disabled, style]}
        onPress={onPress} disabled={isDisabled}
        activeOpacity={0.85} testID={testID}
      >
        <LinearGradient
          colors={isDisabled
            ? ["rgba(255,255,255,0.08)", "rgba(255,255,255,0.04)"]
            : [colors.palette.royalPurple, colors.palette.royalPurpleLight]}
          style={styles.gradientInner}
          start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
        >
          {loading
            ? <ActivityIndicator color="#FFF" size="small" />
            : <Text style={[styles.label, styles.labelPrimary, labelStyle]}>{label}</Text>
          }
        </LinearGradient>
      </TouchableOpacity>
    )
  }

  if (variant === "danger") {
    return (
      <TouchableOpacity
        style={[styles.base, styles.danger, isDisabled && styles.disabled, style]}
        onPress={onPress} disabled={isDisabled} activeOpacity={0.85} testID={testID}
      >
        {loading
          ? <ActivityIndicator color={colors.palette.sunsetOrange} size="small" />
          : <Text style={[styles.label, styles.labelDanger, labelStyle]}>{label}</Text>
        }
      </TouchableOpacity>
    )
  }

  return (
    <TouchableOpacity
      style={[
        styles.base,
        variant === "outline" && styles.outline,
        variant === "ghost" && styles.ghost,
        isDisabled && styles.disabled,
        style,
      ]}
      onPress={onPress} disabled={isDisabled}
      activeOpacity={0.82} testID={testID}
    >
      {loading
        ? <ActivityIndicator color="rgba(255,255,255,0.6)" size="small" />
        : <Text style={[styles.label, styles.labelOutline, labelStyle]}>{label}</Text>
      }
    </TouchableOpacity>
  )
}

const styles = StyleSheet.create({
  base: {
    height: 54, borderRadius: 16,
    justifyContent: "center", alignItems: "center",
    paddingHorizontal: spacing.xl, overflow: "hidden",
  },
  gradientInner: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: "center", alignItems: "center",
  },
  outline: {
    backgroundColor: "rgba(255,255,255,0.06)",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.2)",
  },
  ghost: { backgroundColor: "transparent" },
  danger: {
    backgroundColor: colors.palette.sunsetOrange + "20",
    borderWidth: 1, borderColor: colors.palette.sunsetOrange + "50",
  },
  disabled: { opacity: 0.45 },
  label: {
    fontFamily: typography.primary.semiBold,
    fontSize: 16, letterSpacing: 0.3,
  },
  labelPrimary: { color: "#FFFFFF" },
  labelOutline: { color: "rgba(255,255,255,0.8)" },
  labelDanger: { color: colors.palette.sunsetOrange },
})