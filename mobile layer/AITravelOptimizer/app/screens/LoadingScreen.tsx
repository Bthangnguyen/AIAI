/**
 * LoadingScreen - AI Processing with SSE Progress Integration
 * Screen 2: Loading animation & real-time SSE progress
 */
import React, { FC, useEffect, useRef } from "react"
import {
  View,
  StyleSheet,
  Animated,
  StatusBar,
  ScrollView,
  TouchableOpacity,
  Platform,
} from "react-native"
import { Text } from "@/components/Text"
import { LinearGradient } from "expo-linear-gradient"
import { NativeStackScreenProps } from "@react-navigation/native-stack"
import { AppStackParamList } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { useTripPipeline } from "@/hooks/useTripPipeline"

type Props = NativeStackScreenProps<AppStackParamList, "Loading">

export const LoadingScreen: FC<Props> = ({ navigation, route }) => {
  const { prompt = "", hotelLat, hotelLon, hotelName, numDays = 1, contract } =
    route.params ?? {}

  const rotateAnim = useRef(new Animated.Value(0)).current
  const progressAnim = useRef(new Animated.Value(0)).current
  const insets = useSafeAreaInsets()

  // Spinner rotation
  useEffect(() => {
    Animated.loop(
      Animated.timing(rotateAnim, { toValue: 1, duration: 1200, useNativeDriver: true })
    ).start()
  }, [])

  // Call real SSE stream pipeline passing contract details
  const { steps, logs, errorMsg } = useTripPipeline({
    prompt,
    hotelLat,
    hotelLon,
    hotelName,
    numDays,
    contract,
    onItinerary: (itinerary) => {
      navigation.replace("MapTimeline", { itinerary })
    },
  })

  // Calculate overall progress percentage
  const completedSteps = steps.filter(s => s.status === "done").length
  const activeProgress = completedSteps / steps.length

  useEffect(() => {
    Animated.timing(progressAnim, {
      toValue: activeProgress,
      duration: 500,
      useNativeDriver: false,
    }).start()
  }, [activeProgress])

  const spin = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "360deg"],
  })

  const getStepIcon = (stepId: string) => {
    switch (stepId) {
      case "l2": return "🧠"
      case "l3": return "🔍"
      case "l4": return "⚙️"
      default: return "🗺️"
    }
  }

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <LinearGradient
        colors={[colors.palette.deepSlate, "#111827", "#1a0a2e"]}
        style={StyleSheet.absoluteFillObject}
      />
      <View style={[styles.loadingContainer, { paddingTop: insets.top + 40, paddingBottom: insets.bottom + 20 }]}>
        <View style={styles.logoRow}>
          <View style={styles.logoIconWrap}>
            <Text style={styles.logoIconText}>📍</Text>
          </View>
          <Text style={styles.logoText}>TripFlow</Text>
        </View>

        <View style={styles.spinnerWrapper}>
          <Animated.View style={[styles.spinnerOuter, { transform: [{ rotate: spin }] }]}>
            <LinearGradient
              colors={[colors.palette.royalPurple, colors.palette.imperialGold, colors.palette.jadeGreen]}
              style={styles.spinnerGradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
            />
          </Animated.View>
          <View style={styles.spinnerInner}>
            <Text style={styles.spinnerIcon}>🤖</Text>
          </View>
        </View>

        <Text style={styles.loadingTitle}>
          {errorMsg ? "Đã xảy ra lỗi" : "AI đang tối ưu hóa..."}
        </Text>
        <Text style={[styles.loadingSubtitle, errorMsg ? { color: colors.error } : undefined]} numberOfLines={2}>
          {errorMsg || `"${prompt.slice(0, 60)}${prompt.length > 60 ? "..." : ""}"`}
        </Text>

        {errorMsg && (
          <View style={styles.errorActions}>
            <TouchableOpacity style={styles.errorBtn} onPress={() => navigation.goBack()}>
              <Text style={styles.errorBtnText}>← Quay lại</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.errorBtn, styles.retryBtn]}
              onPress={() => navigation.replace("Loading", route.params)}
            >
              <Text style={[styles.errorBtnText, { color: "#fff" }]}>🔄 Thử lại</Text>
            </TouchableOpacity>
          </View>
        )}

        {!errorMsg && (
          <View style={styles.stepsContainer}>
            {steps.map((step) => {
              const isActive = step.status === "active"
              const isDone = step.status === "done"
              const isError = step.status === "error"

              let dotBg = "rgba(255,255,255,0.15)"
              if (isDone) dotBg = colors.palette.jadeGreen
              else if (isActive) dotBg = colors.palette.imperialGold
              else if (isError) dotBg = colors.error

              return (
                <View key={step.id} style={[styles.stepRow, { opacity: step.status === "pending" ? 0.35 : 1 }]}>
                  <View style={[styles.stepDot, { backgroundColor: dotBg }]}>
                    <Text style={styles.stepDotText}>
                      {isDone ? "✓" : getStepIcon(step.id)}
                    </Text>
                  </View>
                  <View style={styles.stepInfo}>
                    <Text style={[styles.stepText, isActive && { color: "#FFFFFF", fontFamily: typography.primary.semiBold }]}>
                      {step.label}
                    </Text>
                    <Text style={styles.stepDetailText}>{step.detail}</Text>
                  </View>
                </View>
              )
            })}
          </View>
        )}

        {!errorMsg && (
          <View style={styles.progressBar}>
            <Animated.View style={[
              styles.progressFill,
              {
                width: progressAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: ["0%", "100%"],
                }),
              },
            ]} />
          </View>
        )}

        <View style={styles.logsCard}>
          <Text style={styles.logsTitle}>Nhật ký tiến trình</Text>
          <ScrollView
            style={styles.logsScroll}
            contentContainerStyle={styles.logsContent}
            ref={(ref) => ref?.scrollToEnd({ animated: true })}
            showsVerticalScrollIndicator={false}
          >
            {logs.map((log) => {
              let logColor = "rgba(255, 255, 255, 0.45)"
              if (log.type === "success") logColor = colors.palette.jadeGreen
              else if (log.type === "error") logColor = colors.error

              return (
                <View key={log.id} style={styles.logRow}>
                  <View style={[styles.logDot, { backgroundColor: logColor }]} />
                  <Text style={[styles.logText, { color: logColor }]}>{log.message}</Text>
                </View>
              )
            })}
          </ScrollView>
        </View>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  loadingContainer: {
    flex: 1,
    alignItems: "center",
    paddingHorizontal: spacing.xl,
  },
  logoRow: { flexDirection: "row", alignItems: "center", marginBottom: 30 },
  logoIconWrap: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: colors.palette.sunsetOrange,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 8,
  },
  logoIconText: { fontSize: 18 },
  logoText: {
    fontFamily: typography.primary.bold,
    fontSize: 22,
    color: "#FFFFFF",
  },
  spinnerWrapper: {
    width: 100,
    height: 100,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 20,
    marginTop: 10,
  },
  spinnerOuter: {
    width: 100,
    height: 100,
    borderRadius: 50,
    position: "absolute",
  },
  spinnerGradient: {
    flex: 1,
    borderRadius: 50,
    opacity: 0.8,
  },
  spinnerInner: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "#1a1a2e",
    borderWidth: 2,
    borderColor: "rgba(255,255,255,0.15)",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 10,
  },
  spinnerIcon: { fontSize: 40 },
  loadingTitle: {
    fontFamily: typography.primary.semiBold,
    fontSize: 22,
    color: "#FFFFFF",
    marginBottom: 8,
    textAlign: "center",
  },
  loadingSubtitle: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: "rgba(255,255,255,0.45)",
    marginBottom: 25,
    textAlign: "center",
    fontStyle: "italic",
    paddingHorizontal: 10,
  },
  stepsContainer: { width: "100%", gap: 12, marginBottom: 25 },
  stepRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  stepDot: {
    width: 32,
    height: 32,
    borderRadius: 10,
    justifyContent: "center",
    alignItems: "center",
  },
  stepDotText: {
    fontSize: 14,
    color: "#FFFFFF",
  },
  stepInfo: {
    flex: 1,
    justifyContent: "center",
  },
  stepText: {
    fontFamily: typography.primary.medium,
    fontSize: 14,
    color: "rgba(255,255,255,0.5)",
  },
  stepDetailText: {
    fontFamily: typography.primary.normal,
    fontSize: 12,
    color: "rgba(255,255,255,0.3)",
    marginTop: 1,
  },
  progressBar: {
    width: "100%",
    height: 4,
    backgroundColor: "rgba(255,255,255,0.1)",
    borderRadius: 2,
    overflow: "hidden",
    marginBottom: 25,
  },
  progressFill: {
    height: "100%",
    backgroundColor: colors.palette.imperialGold,
    borderRadius: 2,
  },
  logsCard: {
    flex: 1,
    width: "100%",
    backgroundColor: "rgba(255, 255, 255, 0.05)",
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.08)",
    padding: spacing.md,
  },
  logsTitle: {
    fontFamily: typography.primary.semiBold,
    fontSize: 14,
    color: "#FFFFFF",
    marginBottom: 8,
  },
  logsScroll: {
    flex: 1,
  },
  logsContent: {
    paddingBottom: 10,
  },
  logRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 6,
  },
  logDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginTop: 6,
    marginRight: 8,
  },
  logText: {
    flex: 1,
    fontSize: 12,
    fontFamily: typography.primary.normal,
    lineHeight: 18,
  },
  errorActions: {
    flexDirection: "row",
    justifyContent: "center",
    gap: spacing.md,
    marginBottom: 20,
    width: "100%",
  },
  errorBtn: {
    flex: 1,
    minHeight: 44,
    borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.08)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.12)",
    justifyContent: "center",
    alignItems: "center",
  },
  retryBtn: {
    backgroundColor: colors.tint,
    borderColor: colors.tint,
  },
  errorBtnText: {
    fontSize: 15,
    fontFamily: typography.primary.semiBold,
    color: "#FFFFFF",
  },
})
