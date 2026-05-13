/**
 * LocationCard — Figma "Front page" destination cards.
 * Image + title + subtitle + price + rating + locations count.
 * Border radius: 15px.
 */
import React from "react"
import {
  View,
  Text,
  Image,
  StyleSheet,
  TouchableOpacity,
  ViewStyle,
  Dimensions,
} from "react-native"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { RatingStars } from "./RatingStars"

const { width: SCREEN_WIDTH } = Dimensions.get("window")
const CARD_WIDTH = (SCREEN_WIDTH - spacing.lg * 2 - spacing.md) / 2

interface LocationCardProps {
  name: string
  subtitle?: string
  photoUrl: string
  priceFrom?: number
  rating?: number
  locationCount?: number
  onPress: () => void
  style?: ViewStyle
  wide?: boolean // Full-width variant
  testID?: string
}

export const LocationCard: React.FC<LocationCardProps> = ({
  name,
  subtitle,
  photoUrl,
  priceFrom,
  rating,
  locationCount,
  onPress,
  style,
  wide = false,
  testID,
}) => {
  return (
    <TouchableOpacity
      style={[styles.card, wide && styles.cardWide, style]}
      onPress={onPress}
      activeOpacity={0.88}
      testID={testID}
    >
      {/* Photo */}
      <Image
        source={{ uri: photoUrl }}
        style={[styles.image, wide && styles.imageWide]}
        resizeMode="cover"
      />

      {/* Overlay content */}
      <View style={styles.overlay}>
        <Text style={styles.name} numberOfLines={1}>
          {name}
        </Text>
        {subtitle && (
          <Text style={styles.subtitle} numberOfLines={1}>
            {subtitle}
          </Text>
        )}
        <View style={styles.footer}>
          {priceFrom !== undefined && (
            <Text style={styles.price}>{`from $${priceFrom}`}</Text>
          )}
          {rating !== undefined && (
            <RatingStars rating={rating} size="sm" showScore={true} style={styles.rating} />
          )}
        </View>
        {locationCount !== undefined && (
          <Text style={styles.locationCount}>{`${locationCount} locations`}</Text>
        )}
      </View>
    </TouchableOpacity>
  )
}

const styles = StyleSheet.create({
  card: {
    width: CARD_WIDTH,
    borderRadius: 15,
    overflow: "hidden",
    backgroundColor: colors.palette.figmaSurface,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  cardWide: {
    width: "100%",
  },
  image: {
    width: "100%",
    height: 140,
  },
  imageWide: {
    height: 180,
  },
  overlay: {
    padding: spacing.sm,
  },
  name: {
    fontFamily: typography.primary.semiBold,
    fontSize: 14,
    color: colors.palette.figmaBlack,
    marginBottom: 2,
  },
  subtitle: {
    fontFamily: typography.primary.normal,
    fontSize: 12,
    color: colors.palette.figmaGrayMedium,
    marginBottom: spacing.xxs,
  },
  footer: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 2,
  },
  price: {
    fontFamily: typography.primary.semiBold,
    fontSize: 12,
    color: colors.palette.figmaWhite,
  },
  rating: {
    flexShrink: 1,
  },
  locationCount: {
    fontFamily: typography.primary.normal,
    fontSize: 11,
    color: colors.palette.figmaWhite,
    marginTop: 2,
  },
})
