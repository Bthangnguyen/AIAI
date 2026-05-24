/**
 * TripSummaryPlaceholder - Dark Royal Hue "My Trip" tab
 * Shows active trip card or beautiful empty state
 */
import React from "react"
import { View, StyleSheet, StatusBar, TouchableOpacity } from "react-native"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { useNavigation } from "@react-navigation/native"
import type { NativeStackNavigationProp } from "@react-navigation/native-stack"
import { Text } from "@/components/Text"
import { CTAButton } from "@/components/CTAButton"
import { AppStackParamList } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

type Nav = NativeStackNavigationProp<AppStackParamList>

export const TripSummaryPlaceholder: React.FC = () => {
  const navigation = useNavigation<Nav>()
  const insets = useSafeAreaInsets()

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <LinearGradient
        colors={[colors.palette.deepSlate, "#111827", "#1a0a2e"]}
        style={StyleSheet.absoluteFillObject}
      />
      {/* Decorative orb */}
      <View style={styles.orb} />

      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <Text style={styles.headerTitle}>Lộ Trình Của Tôi</Text>
        <TouchableOpacity style={styles.filterBtn}>
          <Text style={styles.filterBtnText}>🗓️</Text>
        </TouchableOpacity>
      </View>

      {/* Empty state */}
      <View style={styles.center}>
        <View style={styles.emojiWrap}>
          <LinearGradient
            colors={[colors.palette.royalPurple + "40", "rgba(108,42,123,0.1)"]}
            style={styles.emojiGradient}
          >
            <Text style={styles.emoji}>🗺️</Text>
          </LinearGradient>
        </View>

        <Text style={styles.title}>Chưa có lộ trình nào</Text>
        <Text style={styles.subtitle}>
          Hãy để AI TripFlow lên kế hoạch chuyến đi hoàn hảo cho bạn — tối ưu theo sức bền, thời tiết và sở thích!
        </Text>

        {/* Feature chips */}
        <View style={styles.featuresRow}>
          {["🤖 AI Tối ưu", "☀️ Tránh nắng", "💪 Sức bền"].map((f, i) => (
            <View key={i} style={styles.featureChip}>
              <Text style={styles.featureChipText}>{f}</Text>
            </View>
          ))}
        </View>

        <TouchableOpacity
          style={styles.ctaBtn}
          onPress={() => navigation.navigate("ItineraryForm")}
        >
          <LinearGradient
            colors={[colors.palette.royalPurple, colors.palette.royalPurpleLight]}
            style={styles.ctaBtnGradient}
            start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
          >
            <Text style={styles.ctaBtnText}>📅 Lên Kế Hoạch Ngay</Text>
          </LinearGradient>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.secondaryCta}
          onPress={() => navigation.navigate("MainTabs", { screen: "Explore" })}
        >
          <Text style={styles.secondaryCtaText}>💬 Chat với AI Co-Pilot</Text>
        </TouchableOpacity>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  orb: {
    position: "absolute", top: 100, right: -80,
    width: 300, height: 300, borderRadius: 150,
    backgroundColor: colors.palette.royalPurple + "25",
  },
  header: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    paddingHorizontal: spacing.lg, paddingBottom: 12,
    borderBottomWidth: 1, borderBottomColor: "rgba(255,255,255,0.06)",
  },
  headerTitle: { fontFamily: typography.primary.bold, fontSize: 24, color: "#FFFFFF" },
  filterBtn: {
    width: 44, height: 44, borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.08)",
    justifyContent: "center", alignItems: "center",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
  },
  filterBtnText: { fontSize: 20 },
  center: {
    flex: 1, alignItems: "center", justifyContent: "center",
    paddingHorizontal: spacing.xl, gap: spacing.md,
  },
  emojiWrap: { borderRadius: 32, overflow: "hidden", marginBottom: spacing.sm },
  emojiGradient: {
    width: 100, height: 100, borderRadius: 32,
    justifyContent: "center", alignItems: "center",
    borderWidth: 1, borderColor: colors.palette.royalPurple + "50",
  },
  emoji: { fontSize: 48 },
  title: {
    fontFamily: typography.primary.bold, fontSize: 22, color: "#FFFFFF",
    textAlign: "center",
  },
  subtitle: {
    fontFamily: typography.primary.normal, fontSize: 14, color: "rgba(255,255,255,0.5)",
    textAlign: "center", lineHeight: 22,
  },
  featuresRow: { flexDirection: "row", gap: 8, flexWrap: "wrap", justifyContent: "center" },
  featureChip: {
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 20, paddingHorizontal: 14, paddingVertical: 6,
    borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
  },
  featureChipText: { fontFamily: typography.primary.medium, fontSize: 13, color: "rgba(255,255,255,0.7)" },
  ctaBtn: { width: "100%", borderRadius: 18, overflow: "hidden" },
  ctaBtnGradient: { paddingVertical: 18, alignItems: "center" },
  ctaBtnText: { fontFamily: typography.primary.semiBold, fontSize: 16, color: "#FFFFFF", letterSpacing: 0.3 },
  secondaryCta: {
    paddingVertical: 14, paddingHorizontal: 24,
    backgroundColor: "rgba(255,255,255,0.04)",
    borderRadius: 16, borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
    width: "100%", alignItems: "center",
  },
  secondaryCtaText: { fontFamily: typography.primary.medium, fontSize: 15, color: "rgba(255,255,255,0.6)" },
})