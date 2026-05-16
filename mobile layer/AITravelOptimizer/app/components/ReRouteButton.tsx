/**
 * ReRouteButton — Floating Action Button for re-routing.
 *
 * Appears in bottom-right of MapTimelineScreen when ENABLE_REROUTE = true.
 * Pulses subtly to draw attention.
 */
import React from "react"
import { Text, StyleSheet } from "react-native"
import { TouchableOpacity } from "react-native-gesture-handler"
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
  withDelay,
} from "react-native-reanimated"
import { colors } from "@/theme/colors"
import { typography } from "@/theme/typography"

interface ReRouteButtonProps {
  onPress: () => void
  disabled?: boolean
  loading?: boolean
  testID?: string
}

export const ReRouteButton: React.FC<ReRouteButtonProps> = ({
  onPress,
  disabled = false,
  loading = false,
  testID = "reroute-fab",
}) => {
  // Subtle pulse animation
  const scale = useSharedValue(1)
  React.useEffect(() => {
    scale.value = withDelay(
      1000,
      withRepeat(withTiming(1.05, { duration: 1200 }), -1, true),
    )
  }, [])

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }))

  return (
    <Animated.View style={[styles.container, animatedStyle]}>
      <TouchableOpacity
        style={[styles.button, (disabled || loading) && styles.disabled]}
        onPress={onPress}
        disabled={disabled || loading}
        activeOpacity={0.8}
        testID={testID}
      >
        <Text style={styles.icon}>{loading ? "⏳" : "🔄"}</Text>
        <Text style={styles.label}>{loading ? "Đang tối ưu..." : "Re-route"}</Text>
      </TouchableOpacity>
    </Animated.View>
  )
}

const styles = StyleSheet.create({
  container: {
    position: "absolute",
    bottom: 24,
    right: 16,
    zIndex: 100,
  },
  button: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.palette.figmaPrimaryBlack,
    paddingHorizontal: 18,
    paddingVertical: 14,
    borderRadius: 30,
    // Shadow
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 6,
    gap: 8,
  },
  disabled: {
    opacity: 0.5,
  },
  icon: {
    fontSize: 18,
  },
  label: {
    fontFamily: typography.primary.semiBold,
    fontSize: 14,
    color: colors.palette.figmaWhite,
    letterSpacing: 0.3,
  },
})
