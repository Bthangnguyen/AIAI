import { View, TextStyle, ViewStyle } from "react-native"

import { Text } from "../components/Text"
import { colors } from "../theme/colors"
import { spacing } from "../theme/spacing"
import { typography } from "../theme/typography"

export interface ItineraryCardProps {
  timeString: string
  title: string
  emoji: string
  visitDurationMin: number
  entranceFee: number
  travelTimeMin: number
}

export const ItineraryCard = ({
  timeString,
  title,
  emoji,
  visitDurationMin,
  entranceFee,
  travelTimeMin,
}: ItineraryCardProps) => (
  <>
    <View style={$cardHeader}>
      <Text text={emoji} style={$cardEmoji} />
      <View style={$cardTextWrap}>
        <Text text={title} style={$cardTitle} numberOfLines={1} />
        <Text text={timeString} style={$cardSubtitle} />
      </View>
    </View>
    <View style={$cardTags}>
      <View style={$tag}>
        <Text text={`⏱ ${visitDurationMin}m`} style={$tagText} />
      </View>
      {entranceFee > 0 && (
        <View style={$tag}>
          <Text text={`💰 ${(entranceFee / 1000).toFixed(0)}k`} style={$tagText} />
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

const $cardHeader: ViewStyle = {
  flexDirection: "row",
  alignItems: "center",
  marginBottom: spacing.xs,
}

const $cardEmoji: TextStyle = {
  fontSize: 28,
  marginRight: spacing.sm,
}

const $cardTextWrap: ViewStyle = {
  flex: 1,
}

const $cardTitle: TextStyle = {
  fontSize: 16,
  fontFamily: typography.primary.semiBold,
  color: colors.text,
}

const $cardSubtitle: TextStyle = {
  fontSize: 14,
  fontFamily: typography.primary.normal,
  color: colors.palette.figmaGrayMedium,
  marginTop: 2,
}

const $cardTags: ViewStyle = {
  flexDirection: "row",
  flexWrap: "wrap",
  gap: 6,
  marginTop: spacing.xs,
}

const $tag: ViewStyle = {
  backgroundColor: colors.palette.figmaSurface,
  borderRadius: 8,
  paddingHorizontal: 10,
  paddingVertical: 4,
}

const $tagText: TextStyle = {
  fontSize: 12,
  fontFamily: typography.primary.medium,
  color: colors.palette.figmaGrayDark,
}
