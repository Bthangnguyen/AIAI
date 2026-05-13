/**
 * SocialLoginButton — Figma "Login registration page" social auth buttons.
 * Icon + text, full-width, 36px border radius.
 */
import React from "react"
import { TouchableOpacity, Text, View, StyleSheet, ViewStyle } from "react-native"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

type SocialProvider = "google" | "facebook" | "apple"

interface SocialLoginButtonProps {
  provider: SocialProvider
  onPress: () => void
  style?: ViewStyle
  testID?: string
}

const PROVIDER_CONFIG: Record<
  SocialProvider,
  { label: string; icon: string; bg: string; textColor: string; borderColor?: string }
> = {
  google: {
    label: "Continue with Google",
    icon: "G",
    bg: "#FFFFFF",
    textColor: "#3C4043",
    borderColor: "#E7E7E7",
  },
  facebook: {
    label: "Continue with Facebook",
    icon: "f",
    bg: "#1877F2",
    textColor: "#FFFFFF",
  },
  apple: {
    label: "Continue with Apple",
    icon: "",
    bg: "#000000",
    textColor: "#FFFFFF",
  },
}

export const SocialLoginButton: React.FC<SocialLoginButtonProps> = ({
  provider,
  onPress,
  style,
  testID,
}) => {
  const config = PROVIDER_CONFIG[provider]

  return (
    <TouchableOpacity
      style={[
        styles.button,
        {
          backgroundColor: config.bg,
          borderColor: config.borderColor ?? config.bg,
          borderWidth: config.borderColor ? 1 : 0,
        },
        style,
      ]}
      onPress={onPress}
      activeOpacity={0.82}
      testID={testID}
    >
      {/* Icon */}
      <View style={styles.iconWrapper}>
        <Text
          style={[
            styles.icon,
            {
              color: config.textColor,
              fontFamily: provider === "apple" ? undefined : typography.primary.bold,
            },
          ]}
        >
          {config.icon}
        </Text>
      </View>
      {/* Label */}
      <Text style={[styles.label, { color: config.textColor }]}>{config.label}</Text>
    </TouchableOpacity>
  )
}

const styles = StyleSheet.create({
  button: {
    height: 54,
    borderRadius: 36,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.lg,
  },
  iconWrapper: {
    width: 24,
    alignItems: "center",
    marginRight: spacing.sm,
  },
  icon: {
    fontSize: 18,
    lineHeight: 22,
  },
  label: {
    fontFamily: typography.primary.semiBold,
    fontSize: 15,
    letterSpacing: 0.2,
  },
})
