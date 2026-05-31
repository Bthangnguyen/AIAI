import React from "react"
import { View, ViewStyle } from "react-native"

import { Icon, IconTypes } from "@/components/Icon"
import { colors } from "@/theme/colors"

export type AppIconName = "home" | "route" | "history" | "profile" | "back" | "bell" | "lock" | "pin" | "check"

const ICON_MAP: Record<AppIconName, IconTypes> = {
  home: "components",
  route: "pin",
  history: "podcast",
  profile: "settings",
  back: "back",
  bell: "bell",
  lock: "lock",
  pin: "pin",
  check: "check",
}

interface AppIconProps {
  name: AppIconName
  size?: number
  color?: string
  containerStyle?: ViewStyle
}

export function AppIcon({
  name,
  size = 22,
  color = colors.palette.appInk,
  containerStyle,
}: AppIconProps) {
  return (
    <View style={containerStyle}>
      <Icon icon={ICON_MAP[name]} size={size} color={color} />
    </View>
  )
}
