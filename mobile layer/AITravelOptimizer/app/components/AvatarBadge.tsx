/**
 * AvatarBadge — Circular avatar with optional online indicator dot.
 * Matches Figma avatar circles (profile, greeting header).
 */
import React from "react"
import { View, Image, StyleSheet, ViewStyle } from "react-native"
import { colors } from "@/theme/colors"

interface AvatarBadgeProps {
  uri?: string
  size?: number
  showOnline?: boolean
  style?: ViewStyle
  testID?: string
}

export const AvatarBadge: React.FC<AvatarBadgeProps> = ({
  uri,
  size = 44,
  showOnline = false,
  style,
  testID,
}) => {
  const dotSize = Math.round(size * 0.27)

  return (
    <View style={[{ width: size, height: size }, style]} testID={testID}>
      <Image
        source={
          uri
            ? { uri }
            : require("../../assets/images/logo.png")
        }
        style={[
          styles.avatar,
          { width: size, height: size, borderRadius: size / 2 },
        ]}
        resizeMode="cover"
      />
      {showOnline && (
        <View
          style={[
            styles.onlineDot,
            {
              width: dotSize,
              height: dotSize,
              borderRadius: dotSize / 2,
              bottom: 1,
              right: 1,
            },
          ]}
        />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  avatar: {
    backgroundColor: colors.palette.figmaGrayLight,
  },
  onlineDot: {
    position: "absolute",
    backgroundColor: colors.palette.figmaSuccess,
    borderWidth: 2,
    borderColor: colors.palette.figmaWhite,
  },
})
