/**
 * ItineraryCard - Dark Royal Hue Design
 * Used in MapTimelineScreen bottom sheet
 */
import React from "react"
import { View, StyleSheet } from "react-native"
import { Text } from "@/components/Text"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

export interface ItineraryCardProps {
  timeString: string
  title: string
  emoji: string
  visitDurationMin: number
  entranceFee: number
  travelTimeMin: number
  isActive?: boolean
  isCompleted?: boolean
}

export const ItineraryCard = ({
  timeString, title, emoji,
  visitDurationMin, entranceFee, travelTimeMin,
  isActive = false, isCompleted = false,
}: ItineraryCardProps) => (
  <>
    <View style={[$cardHeader, isActive && $cardHeaderActive, isCompleted && $cardHeaderCompleted]}>
      <View style={[$emojiWrap, isActive && $emojiWrapActive]}>
        <Text text={emoji} style={$cardEmoji} />
      </View>
      <View style={$cardTextWrap}>
        <Text
          text={title}
          style={[$cardTitle, isCompleted && $cardTitleCompleted]}
          numberOfLines={1}
        />
        <Text text={timeString} style={$cardSubtitle} />
      </View>
      {isActive && <View style={$activeDot} />}
      {isCompleted && <Text style={$checkMark}>✓</Text>}
    </View>
    <View style={$cardTags}>
      <View style={$tag}>
        <Text text={`⏱️ ${visitDurationMin}m`} style={$tagText} />
      </View>
      {entranceFee > 0 && (
        <View style={$tag}>
          <Text text={`🎫 ${(entranceFee / 1000).toFixed(0)}k`} style={$tagText} />
        </View>
      )}
      {travelTimeMin > 0 && (
        <View style={$tag}>
          <Text text={`🚗 ${travelTimeMin}m`} style={$tagText} />
        </View>
      )}
    </View>
  </>
)

const $cardHeader: { [key: string]: any } = {
  flexDirection: "row" as const,
  alignItems: "center" as const,
  marginBottom: spacing.xs,
  gap: spacing.sm,
}

const $cardHeaderActive: { [key: string]: any } = {}

const $cardHeaderCompleted: { [key: string]: any } = {
  opacity: 0.6,
}

const $emojiWrap: { [key: string]: any } = {
  width: 44, height: 44, borderRadius: 14,
  backgroundColor: "#f0f0f0",
  justifyContent: "center" as const, alignItems: "center" as const,
}

const $emojiWrapActive: { [key: string]: any } = {
  backgroundColor: colors.palette.imperialGold + "25",
  borderWidth: 1, borderColor: colors.palette.imperialGold + "50",
}

const $cardEmoji: { [key: string]: any } = { fontSize: 22 }

const $cardTextWrap: { [key: string]: any } = { flex: 1 }

const $cardTitle: { [key: string]: any } = {
  fontSize: 15,
  fontFamily: typography.primary.semiBold,
  color: "#1a1a1a",
}

const $cardTitleCompleted: { [key: string]: any } = {
  textDecorationLine: "line-through" as const,
  color: "#a0a0a0",
}

const $cardSubtitle: { [key: string]: any } = {
  fontSize: 13,
  fontFamily: typography.primary.normal,
  color: "#666666",
  marginTop: 2,
}

const $activeDot: { [key: string]: any } = {
  width: 10, height: 10, borderRadius: 5,
  backgroundColor: colors.palette.imperialGold,
}

const $checkMark: { [key: string]: any } = {
  fontSize: 16, color: colors.palette.jadeGreen,
  fontFamily: typography.primary.bold,
}

const $cardTags: { [key: string]: any } = {
  flexDirection: "row" as const,
  flexWrap: "wrap" as const,
  gap: 6,
}

const $tag: { [key: string]: any } = {
  backgroundColor: "#f5f5f5",
  borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3,
  borderWidth: 1, borderColor: "#eaeaea",
}

const $tagText: { [key: string]: any } = {
  fontSize: 11,
  fontFamily: typography.primary.medium,
  color: "#666666",
}