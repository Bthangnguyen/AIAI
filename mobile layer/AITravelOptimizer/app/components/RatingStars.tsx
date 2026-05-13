/**
 * RatingStars — 5-star rating with score and review count.
 * Matches Figma "Attraction details page" / "Attraction introduction page".
 */
import React from "react"
import { View, Text, StyleSheet, ViewStyle } from "react-native"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

interface RatingStarsProps {
  rating: number // 0-5
  reviewCount?: number
  showScore?: boolean
  size?: "sm" | "md" | "lg"
  style?: ViewStyle
  testID?: string
}

export const RatingStars: React.FC<RatingStarsProps> = ({
  rating,
  reviewCount,
  showScore = true,
  size = "md",
  style,
  testID,
}) => {
  const starSize = size === "sm" ? 12 : size === "md" ? 16 : 20
  const clampedRating = Math.min(5, Math.max(0, rating))

  return (
    <View style={[styles.container, style]} testID={testID}>
      {/* Stars */}
      <View style={styles.starsRow}>
        {[1, 2, 3, 4, 5].map((star) => {
          const filled = clampedRating >= star
          const half = !filled && clampedRating >= star - 0.5
          return (
            <Text
              key={star}
              style={[
                styles.star,
                { fontSize: starSize },
                filled ? styles.starFilled : half ? styles.starHalf : styles.starEmpty,
              ]}
            >
              {filled ? "★" : half ? "⯨" : "☆"}
            </Text>
          )
        })}
      </View>

      {/* Score */}
      {showScore && (
        <Text style={[styles.score, size === "sm" && styles.scoreSm]}>
          {clampedRating.toFixed(1)}
        </Text>
      )}

      {/* Review count */}
      {reviewCount !== undefined && (
        <Text style={[styles.reviewCount, size === "sm" && styles.reviewCountSm]}>
          {`(${reviewCount.toLocaleString()} reviews)`}
        </Text>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xxs,
  },
  starsRow: {
    flexDirection: "row",
    gap: 1,
  },
  star: {
    lineHeight: 20,
  },
  starFilled: {
    color: colors.palette.figmaStarYellow,
  },
  starHalf: {
    color: colors.palette.figmaStarYellow,
  },
  starEmpty: {
    color: colors.palette.figmaGrayLight,
  },
  score: {
    fontFamily: typography.primary.semiBold,
    fontSize: 14,
    color: colors.palette.figmaBlack,
    marginLeft: 2,
  },
  scoreSm: {
    fontSize: 12,
  },
  reviewCount: {
    fontFamily: typography.primary.normal,
    fontSize: 12,
    color: colors.palette.figmaGrayMedium,
  },
  reviewCountSm: {
    fontSize: 11,
  },
})
