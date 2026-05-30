/**
 * LocationCard - Dark Glassmorphism with gradient overlay
 */
import React from "react"
import { View, Text, Image, StyleSheet, TouchableOpacity, ViewStyle, Dimensions } from "react-native"
import { LinearGradient } from "expo-linear-gradient"
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
  wide?: boolean
  testID?: string
}

export const LocationCard: React.FC<LocationCardProps> = ({
  name, subtitle, photoUrl, priceFrom, rating, locationCount,
  onPress, style, wide = false, testID,
}) => (
  <TouchableOpacity
    style={[styles.card, wide && styles.cardWide, style]}
    onPress={onPress} activeOpacity={0.88} testID={testID}
  >
    <Image source={{ uri: photoUrl }} style={[styles.image, wide && styles.imageWide]} resizeMode="cover" />
    <LinearGradient
      colors={["transparent", "rgba(11,15,25,0.75)", "rgba(11,15,25,0.95)"]}
      style={styles.gradientOverlay}
    />
    <View style={styles.overlay}>
      <Text style={styles.name} numberOfLines={1}>{name}</Text>
      {subtitle && <Text style={styles.subtitle} numberOfLines={1}>{subtitle}</Text>}
      <View style={styles.footer}>
        {priceFrom !== undefined && (
          <Text style={styles.price}>{`từ ${priceFrom.toLocaleString("vi-VN")}₫`}</Text>
        )}
        {/* rating !== undefined && (
          <RatingStars rating={rating} size="sm" showScore style={styles.rating} />
        ) */}
      </View>
      {locationCount !== undefined && (
        <Text style={styles.locationCount}>{`${locationCount} điểm tham quan`}</Text>
      )}
    </View>
  </TouchableOpacity>
)

const styles = StyleSheet.create({
  card: {
    width: CARD_WIDTH, borderRadius: 16, overflow: "hidden",
    backgroundColor: "rgba(255,255,255,0.05)",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
    shadowColor: "#000", shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2, shadowRadius: 8, elevation: 4,
  },
  cardWide: { width: "100%" },
  image: { width: "100%", height: 140 },
  imageWide: { height: 180 },
  gradientOverlay: {
    position: "absolute", bottom: 0, left: 0, right: 0, height: "70%",
  },
  overlay: { position: "absolute", bottom: 0, left: 0, right: 0, padding: spacing.sm },
  name: { fontFamily: typography.primary.semiBold, fontSize: 14, color: "#FFFFFF", marginBottom: 2 },
  subtitle: { fontFamily: typography.primary.normal, fontSize: 11, color: "rgba(255,255,255,0.6)", marginBottom: spacing.xxs },
  footer: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 2 },
  price: { fontFamily: typography.primary.semiBold, fontSize: 11, color: colors.palette.imperialGold },
  rating: { flexShrink: 1 },
  locationCount: { fontFamily: typography.primary.normal, fontSize: 10, color: "rgba(255,255,255,0.45)", marginTop: 2 },
})