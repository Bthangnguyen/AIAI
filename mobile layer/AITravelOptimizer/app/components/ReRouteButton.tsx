/**
 * ReRouteButton - Royal Hue gradient FAB
 */
import React from "react"
import { Text, StyleSheet } from "react-native"
import { TouchableOpacity } from "react-native-gesture-handler"
import Animated, {
  useAnimatedStyle, useSharedValue, withRepeat, withTiming, withDelay,
} from "react-native-reanimated"
import { LinearGradient } from "expo-linear-gradient"
import { colors } from "@/theme/colors"
import { typography } from "@/theme/typography"

interface ReRouteButtonProps {
  onPress: () => void
  disabled?: boolean
  loading?: boolean
  testID?: string
}

export const ReRouteButton: React.FC<ReRouteButtonProps> = ({
  onPress, disabled = false, loading = false, testID = "reroute-fab",
}) => {
  const scale = useSharedValue(1)
  React.useEffect(() => {
    scale.value = withDelay(1000, withRepeat(withTiming(1.05, { duration: 1200 }), -1, true))
  }, [])

  const animatedStyle = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }))

  return (
    <Animated.View style={[styles.container, animatedStyle]}>
      <TouchableOpacity
        style={[styles.button, (disabled || loading) && styles.disabled]}
        onPress={onPress} disabled={disabled || loading}
        activeOpacity={0.8} testID={testID}
      >
        <LinearGradient
          colors={[colors.palette.royalPurple, colors.palette.royalPurpleLight]}
          style={styles.gradient}
          start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
        >
          <Text style={styles.icon}>{loading ? "⏳" : "🤖"}</Text>
          <Text style={styles.label}>{loading ? "Đang tính..." : "Re-route"}</Text>
        </LinearGradient>
      </TouchableOpacity>
    </Animated.View>
  )
}

const styles = StyleSheet.create({
  container: { position: "absolute", bottom: 24, right: 16, zIndex: 100 },
  button: { borderRadius: 30, overflow: "hidden", shadowColor: colors.palette.royalPurple, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.5, shadowRadius: 12, elevation: 8 },
  gradient: { flexDirection: "row", alignItems: "center", paddingHorizontal: 18, paddingVertical: 14, gap: 8 },
  disabled: { opacity: 0.5 },
  icon: { fontSize: 18 },
  label: { fontFamily: typography.primary.semiBold, fontSize: 14, color: "#FFFFFF", letterSpacing: 0.3 },
})