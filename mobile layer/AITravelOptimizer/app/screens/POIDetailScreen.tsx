/**
 * POIDetailScreen — Figma "Attraction details page".
 * Full-width hero image + white card + tabs + CTA.
 */
import React, { useState } from "react"
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  Image,
  TouchableOpacity,
  StatusBar,
  Dimensions,
  Platform,
  Linking,
} from "react-native"
import { useNavigation, useRoute } from "@react-navigation/native"
import type { NativeStackNavigationProp, NativeStackScreenProps } from "@react-navigation/native-stack"

import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { RatingStars } from "@/components/RatingStars"
import { CTAButton } from "@/components/CTAButton"
import { AppStackParamList } from "@/navigators/navigationTypes"

type Nav = NativeStackNavigationProp<AppStackParamList>
type Props = NativeStackScreenProps<AppStackParamList, "POIDetail">

const { width: SCREEN_WIDTH } = Dimensions.get("window")
const HERO_HEIGHT = SCREEN_WIDTH * 0.65

const TABS = ["About", "Pricing", "Flights", "Hotels"] as const
type TabKey = typeof TABS[number]

export const POIDetailScreen: React.FC<Props> = () => {
  const navigation = useNavigation<Nav>()
  const route = useRoute<Props["route"]>()
  const {
    poiName, photoUrl, rating, reviewCount, description,
    entranceFee, openTime, closeTime, lat, lon,
  } = route.params

  const [activeTab, setActiveTab] = useState<TabKey>("About")

  const formatFee = (fee: number) =>
    fee === 0 ? "Free" : `${fee.toLocaleString()} VND`

  const openNativeMap = () => {
    const url = Platform.select({
      ios: `maps:0,0?q=${poiName}@${lat},${lon}`,
      android: `geo:0,0?q=${lat},${lon}(${poiName})`,
      web: `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`,
    })
    if (url) {
      Linking.openURL(url).catch(() => {
        // Fallback if no map app installed
        Linking.openURL(`https://www.google.com/maps/search/?api=1&query=${lat},${lon}`)
      })
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
        {/* ─── Hero Image ── */}
        <View style={styles.heroContainer}>
          <Image source={{ uri: photoUrl }} style={styles.heroImage} resizeMode="cover" />
          {/* Overlay gradient simulation */}
          <View style={styles.heroOverlay} />
          {/* Back button */}
          <TouchableOpacity
            style={styles.backBtn}
            onPress={() => navigation.goBack()}
            testID="back-btn"
          >
            <Text style={styles.backArrow}>←</Text>
          </TouchableOpacity>
          {/* Heart */}
          <TouchableOpacity style={styles.heartBtn}>
            <Text style={styles.heart}>🤍</Text>
          </TouchableOpacity>
        </View>

        {/* ─── White Card ── */}
        <View style={styles.card}>
          <Text style={styles.poiName}>{poiName}</Text>

          <RatingStars
            rating={rating}
            reviewCount={reviewCount}
            size="md"
            style={styles.rating}
          />

          {/* Info row */}
          <View style={styles.infoRow}>
            <View style={styles.infoItem}>
              <Text style={styles.infoIcon}>🎫</Text>
              <Text style={styles.infoText}>{formatFee(entranceFee)}</Text>
            </View>
            <View style={styles.infoItem}>
              <Text style={styles.infoIcon}>🕐</Text>
              <Text style={styles.infoText}>{openTime} – {closeTime}</Text>
            </View>
          </View>

          {/* Tab bar */}
          <View style={styles.tabBar}>
            {TABS.map((tab) => (
              <TouchableOpacity
                key={tab}
                style={[styles.tab, activeTab === tab && styles.tabActive]}
                onPress={() => setActiveTab(tab)}
              >
                <Text style={[styles.tabText, activeTab === tab && styles.tabTextActive]}>
                  {tab}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Tab content */}
          <View style={styles.tabContent}>
            {activeTab === "About" && (
              <Text style={styles.descText}>{description}</Text>
            )}
            {activeTab === "Pricing" && (
              <View>
                <Text style={styles.descText}>
                  Entrance fee: {formatFee(entranceFee)}
                </Text>
                <Text style={[styles.descText, { marginTop: spacing.sm }]}>
                  Audio guide: 50,000 VND
                </Text>
                <Text style={[styles.descText, { marginTop: spacing.sm }]}>
                  Photography permit: Free
                </Text>
              </View>
            )}
            {activeTab === "Flights" && (
              <Text style={styles.descText}>
                Nearest airport: Phú Bài International Airport (HUI)
                {"\n"}~15 minutes from city center.
              </Text>
            )}
            {activeTab === "Hotels" && (
              <Text style={styles.descText}>
                Recommended: Hue Heritage Hotel ★★★★
                {"\n"}La Résidence Hotel & Spa ★★★★★
                {"\n"}Pilgrimage Village Boutique Resort ★★★★
              </Text>
            )}
          </View>

          {/* CTAs */}
          <View style={styles.ctaRow}>
            <CTAButton
              label="Plan trip"
              onPress={() => navigation.navigate("ItineraryForm")}
              style={styles.ctaBtnPrimary}
              testID="plan-trip-btn"
            />
            <CTAButton
              label="Map"
              onPress={openNativeMap}
              variant="outline"
              style={styles.ctaBtnSecondary}
            />
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.palette.figmaWhite },
  container: { flex: 1 },
  heroContainer: {
    width: SCREEN_WIDTH,
    height: HERO_HEIGHT,
  },
  heroImage: {
    width: "100%",
    height: "100%",
  },
  heroOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.18)",
  },
  backBtn: {
    position: "absolute",
    top: 50,
    left: spacing.lg,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.9)",
    justifyContent: "center",
    alignItems: "center",
  },
  backArrow: { fontSize: 20, color: colors.palette.figmaBlack },
  heartBtn: {
    position: "absolute",
    top: 50,
    right: spacing.lg,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.9)",
    justifyContent: "center",
    alignItems: "center",
  },
  heart: { fontSize: 20 },
  card: {
    backgroundColor: colors.palette.figmaWhite,
    borderTopLeftRadius: 29,
    borderTopRightRadius: 29,
    marginTop: -29,
    padding: spacing.lg,
    minHeight: 500,
  },
  poiName: {
    fontFamily: typography.primary.bold,
    fontSize: 22,
    color: colors.palette.figmaBlack,
    marginBottom: spacing.xs,
  },
  rating: { marginBottom: spacing.md },
  infoRow: {
    flexDirection: "row",
    gap: spacing.lg,
    marginBottom: spacing.md,
    padding: spacing.md,
    backgroundColor: colors.palette.figmaOffWhite,
    borderRadius: 15,
  },
  infoItem: { flexDirection: "row", alignItems: "center", gap: spacing.xxs },
  infoIcon: { fontSize: 16 },
  infoText: {
    fontFamily: typography.primary.medium,
    fontSize: 13,
    color: colors.palette.figmaGrayDark,
  },
  tabBar: {
    flexDirection: "row",
    borderBottomWidth: 1,
    borderBottomColor: colors.palette.figmaGrayLight,
    marginBottom: spacing.md,
  },
  tab: {
    flex: 1,
    paddingVertical: spacing.sm,
    alignItems: "center",
  },
  tabActive: {
    borderBottomWidth: 2,
    borderBottomColor: colors.palette.figmaPrimaryBlack,
  },
  tabText: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: colors.palette.figmaGrayMedium,
  },
  tabTextActive: {
    fontFamily: typography.primary.semiBold,
    color: colors.palette.figmaBlack,
  },
  tabContent: { marginBottom: spacing.xl },
  descText: {
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: colors.palette.figmaGrayDark,
    lineHeight: 22,
  },
  ctaRow: {
    flexDirection: "row",
    gap: spacing.sm,
  },
  ctaBtnPrimary: { flex: 2 },
  ctaBtnSecondary: { flex: 1 },
})
