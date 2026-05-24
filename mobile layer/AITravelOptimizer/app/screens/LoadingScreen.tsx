import { FC, useCallback, useEffect, useRef, useState } from "react"
import { View, ViewStyle, TextStyle, FlatList, Dimensions, Pressable, ScrollView } from "react-native"
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  FadeInDown,
  Easing,
} from "react-native-reanimated"

import { Screen } from "@/components/Screen"
import { Text } from "@/components/Text"
import type { AppStackScreenProps } from "@/navigators/navigationTypes"
import type { TravelItinerary } from "@/navigators/navigationTypes"
import { useTripPipeline } from "@/hooks/useTripPipeline"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

// ─── Pipeline Step Definitions (re-exported from hook) ──────────────────────
type StepStatus = "pending" | "active" | "done" | "error"

interface PipelineStep {
  id: string
  label: string
  detail: string
  status: StepStatus
}

interface LogEntry {
  id: number
  message: string
  type: "info" | "success" | "error"
  timestamp: number
}

// ─── Component ──────────────────────────────────────────────────
interface LoadingScreenProps extends AppStackScreenProps<"Loading"> {}

export const LoadingScreen: FC<LoadingScreenProps> = ({ route, navigation }) => {
  const { prompt = "", hotelLat = 0, hotelLon = 0, hotelName = "", numDays = 1 } =
    route.params ?? {}

  // ─── Spinner + pulse animations (kept as-is) ─────────
  const rotation = useSharedValue(0)
  useEffect(() => {
    rotation.value = withRepeat(
      withTiming(360, { duration: 1500, easing: Easing.linear }),
      -1,
      false,
    )
  }, [])

  const spinnerStyle = useAnimatedStyle(() => ({
    transform: [{ rotate: `${rotation.value}deg` }],
  }))

  const pulse = useSharedValue(1)
  useEffect(() => {
    pulse.value = withRepeat(withTiming(1.15, { duration: 800 }), -1, true)
  }, [])

  const pulseStyle = useAnimatedStyle(() => ({
    transform: [{ scale: pulse.value }],
  }))

  // ─── Wire trip pipeline (mock or real backend) ────────
  const { steps, logs, errorMsg } = useTripPipeline({
    prompt,
    hotelLat,
    hotelLon,
    hotelName,
    numDays,
    onItinerary: (itinerary) => navigation.replace("MapTimeline", { itinerary }),
  })


  // ─── Render helpers ───────────────────────
  const renderStep = (step: PipelineStep, index: number) => {
    const isLast = index === steps.length - 1
    const dotColor =
      step.status === "done"
        ? colors.tint
        : step.status === "active"
          ? colors.tint
          : step.status === "error"
            ? colors.error
            : colors.palette.figmaInactive

    const textColor =
      step.status === "done" || step.status === "active"
        ? colors.text
        : colors.palette.figmaGrayMedium

    return (
      <View key={step.id} style={$stepRow}>
        {/* Timeline: node + line */}
        <View style={$timelineCol}>
          {step.status === "active" ? (
            <Animated.View style={pulseStyle}>
              <View style={[$stepDot, { backgroundColor: dotColor }]}>
                {step.status === "active" && <View style={$stepDotInner} />}
              </View>
            </Animated.View>
          ) : (
            <View style={[$stepDot, { backgroundColor: dotColor }]}>
              {step.status === "done" && <Text text="✓" style={$checkmark} />}
            </View>
          )}
          {!isLast && (
            <View
              style={[
                $stepLine,
                {
                  backgroundColor:
                    step.status === "done" ? colors.tint : colors.palette.figmaGrayLight,
                },
              ]}
            />
          )}
        </View>

        {/* Content */}
        <View style={$stepContent}>
          <Text text={step.label} style={[$stepLabel, { color: textColor }]} />
          <Text text={step.detail} style={$stepDetail} />
        </View>
      </View>
    )
  }

  const renderLogItem = ({ item }: { item: LogEntry }) => {
    const logColor =
      item.type === "success"
        ? colors.tint
        : item.type === "error"
          ? colors.error
          : colors.palette.figmaGrayDark

    return (
      <Animated.View entering={FadeInDown.duration(300)} style={$logRow}>
        <View style={[$logDot, { backgroundColor: logColor }]} />
        <Text text={item.message} style={[$logText, { color: logColor }]} numberOfLines={2} />
      </Animated.View>
    )
  }

  // ─── Main Render ──────────────────────────
  return (
    <Screen style={$root} preset="fixed" contentContainerStyle={{ flex: 1 }}>
      <ScrollView style={{ flex: 1 }} contentContainerStyle={$container}>
        {/* Header */}
        <View style={$header}>
          <Animated.View style={[$spinnerWrap, spinnerStyle]}>
            <View style={$spinner} />
          </Animated.View>

          <Text text="Planning Your Trip" style={$heading} />
          <Text
            text={errorMsg || "AI is optimizing your perfect route..."}
            style={[$subtitle, errorMsg ? { color: colors.error } : undefined]}
          />
        </View>

        {/* Error Actions */}
        {errorMsg && (
          <View style={$errorActions}>
            <Pressable style={$errorBtn} onPress={() => navigation.goBack()}>
              <Text text="← Go Back" style={$errorBtnText} />
            </Pressable>
            <Pressable
              style={[$errorBtn, $retryBtn]}
              onPress={() => navigation.replace("Loading", route.params)}
            >
              <Text text="🔄 Retry" style={[$errorBtnText, { color: "#fff" }]} />
            </Pressable>
          </View>
        )}

        {/* Pipeline Steps */}
        <View style={$stepsCard}>{steps.map(renderStep)}</View>

        {/* Live Log Stream */}
        <View style={$logCard}>
          <Text text="Live Progress" style={$logTitle} />
          <FlatList
            data={logs}
            keyExtractor={(item) => item.id.toString()}
            renderItem={renderLogItem}
            contentContainerStyle={$logList}
            showsVerticalScrollIndicator={false}
            inverted={false}
            scrollEnabled={false}
          />
        </View>
      </ScrollView>
    </Screen>
  )
}

// ─── Styles ─────────────────────────────────────────────────────

const $root: ViewStyle = {
  flex: 1,
  backgroundColor: colors.background,
}

const $container: ViewStyle = {
  flexGrow: 1,
  paddingHorizontal: spacing.lg,
  paddingTop: 60,
  paddingBottom: 40,
}

const $header: ViewStyle = {
  alignItems: "center",
  marginBottom: spacing.xl,
}

const $spinnerWrap: ViewStyle = {
  width: 64,
  height: 64,
  marginBottom: spacing.lg,
  justifyContent: "center",
  alignItems: "center",
}

const $spinner: ViewStyle = {
  width: 56,
  height: 56,
  borderRadius: 28,
  borderWidth: 4,
  borderColor: colors.palette.figmaGrayLight,
  borderTopColor: colors.tint,
}

const $heading: TextStyle = {
  fontSize: 28,
  fontFamily: typography.primary.semiBold,
  color: colors.text,
  marginBottom: spacing.xs,
  textAlign: "center",
}

const $subtitle: TextStyle = {
  fontSize: 16,
  fontFamily: typography.primary.normal,
  color: colors.palette.figmaPlaceholder,
  textAlign: "center",
}

// ─── Pipeline Steps ──────────
const $stepsCard: ViewStyle = {
  backgroundColor: colors.palette.figmaSurface,
  borderRadius: 24,
  padding: spacing.lg,
  marginBottom: spacing.lg,
  // Figma shadow: effect_OMBK8U
  shadowColor: "#000",
  shadowOffset: { width: 0, height: 4 },
  shadowOpacity: 0.05,
  shadowRadius: 4,
  elevation: 2,
}

const $stepRow: ViewStyle = {
  flexDirection: "row",
  minHeight: 56,
}

const $timelineCol: ViewStyle = {
  width: 32,
  alignItems: "center",
}

const $stepDot: ViewStyle = {
  width: 26,
  height: 26,
  borderRadius: 13,
  justifyContent: "center",
  alignItems: "center",
}

const $stepDotInner: ViewStyle = {
  width: 10,
  height: 10,
  borderRadius: 5,
  backgroundColor: "#fff",
}

const $checkmark: TextStyle = {
  color: "#fff",
  fontSize: 14,
  fontFamily: typography.primary.semiBold,
}

const $stepLine: ViewStyle = {
  width: 2,
  flex: 1,
  marginVertical: 4,
}

const $stepContent: ViewStyle = {
  flex: 1,
  marginLeft: spacing.sm,
  paddingBottom: spacing.md,
}

const $stepLabel: TextStyle = {
  fontSize: 16,
  fontFamily: typography.primary.semiBold,
  marginBottom: 2,
}

const $stepDetail: TextStyle = {
  fontSize: 14,
  fontFamily: typography.primary.normal,
  color: colors.palette.figmaGrayMedium,
}

// ─── Log Stream ──────────────
const $logCard: ViewStyle = {
  flex: 1,
  backgroundColor: colors.palette.figmaSurface,
  borderRadius: 24,
  padding: spacing.lg,
  shadowColor: "#000",
  shadowOffset: { width: 0, height: 4 },
  shadowOpacity: 0.05,
  shadowRadius: 4,
  elevation: 2,
}

const $logTitle: TextStyle = {
  fontSize: 16,
  fontFamily: typography.primary.semiBold,
  color: colors.text,
  marginBottom: spacing.md,
}

const $logList: ViewStyle = {
  paddingBottom: spacing.md,
}

const $logRow: ViewStyle = {
  flexDirection: "row",
  alignItems: "flex-start",
  marginBottom: spacing.sm,
}

const $logDot: ViewStyle = {
  width: 6,
  height: 6,
  borderRadius: 3,
  marginTop: 7,
  marginRight: spacing.sm,
}

const $logText: TextStyle = {
  flex: 1,
  fontSize: 14,
  fontFamily: typography.primary.normal,
  lineHeight: 20,
}

// ─── Error Actions ───────────
const $errorActions: ViewStyle = {
  flexDirection: "row",
  justifyContent: "center",
  gap: spacing.md,
  marginBottom: spacing.lg,
}

const $errorBtn: ViewStyle = {
  flex: 1,
  minHeight: 48,
  paddingVertical: 12,
  paddingHorizontal: 24,
  borderRadius: 16,
  backgroundColor: colors.palette.figmaOffWhite,
  borderWidth: 1,
  borderColor: colors.palette.figmaGrayLight,
  justifyContent: "center",
  alignItems: "center",
}

const $retryBtn: ViewStyle = {
  backgroundColor: colors.tint,
  borderColor: colors.tint,
}

const $errorBtnText: TextStyle = {
  fontSize: 16,
  fontFamily: typography.primary.semiBold,
  color: colors.text,
}
