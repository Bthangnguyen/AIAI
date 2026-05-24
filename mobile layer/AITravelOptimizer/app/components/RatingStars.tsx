/**
 * RatingStars - Dark Design
 */
import React from "react"
import { View, Text, StyleSheet, ViewStyle } from "react-native"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

interface RatingStarsProps {
  rating: number
  reviewCount?: number
  showScore?: boolean
  size?: "sm" | "md" | "lg"
  style?: ViewStyle
  testID?: string
}

export const RatingStars: React.FC<RatingStarsProps> = ({
  rating, reviewCount, showScore = true, size = "md", style, testID,
}) => {
  const starSize = size === "sm" ? 12 : size === "md" ? 16 : 20
  const clampedRating = Math.min(5, Math.max(0, rating))

  return (
    <View style={[styles.container, style]} testID={testID}>
      <View style={styles.starsRow}>
        {[1, 2, 3, 4, 5].map((star) => {
          const filled = clampedRating >= star
          const half = !filled && clampedRating >= star - 0.5
          return (
            <Text key={star} style={[styles.star, { fontSize: starSize },
              filled ? styles.starFilled : half ? styles.starHalf : styles.starEmpty]}>
              {filled ? "★" : half ? "⭐" : "☆"}
            </Text>
          )
        })}
      </View>
      {showScore && (
        <Text style={[styles.score, size === "sm" && styles.scoreSm]}>{clampedRating.toFixed(1)}</Text>
      )}
      {reviewCount !== undefined && (
        <Text style={[styles.reviewCount, size === "sm" && styles.reviewCountSm]}>
          ({reviewCount.toLocaleString()})
        </Text>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flexDirection: "row", alignItems: "center", gap: spacing.xxs },
  starsRow: { flexDirection: "row", gap: 1 },
  star: { lineHeight: 20 },
  starFilled: { color: colors.palette.imperialGold },
  starHalf: { color: colors.palette.imperialGold },
  starEmpty: { color: "rgba(255,255,255,0.15)" },
  score: { fontFamily: typography.primary.semiBold, fontSize: 14, color: "#FFFFFF", marginLeft: 2 },
  scoreSm: { fontSize: 12 },
  reviewCount: { fontFamily: typography.primary.normal, fontSize: 12, color: "rgba(255,255,255,0.4)" },
  reviewCountSm: { fontSize: 11 },
})