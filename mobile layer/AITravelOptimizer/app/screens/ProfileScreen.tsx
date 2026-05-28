/**
 * ProfileScreen - Dark Royal Hue Design
 * User profile with stats, achievement badges & settings
 */
import React, { useState } from "react"
import {
  View, StyleSheet, ScrollView, TouchableOpacity, StatusBar, Image, Dimensions, Platform,
} from "react-native"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { useNavigation } from "@react-navigation/native"
import type { NativeStackNavigationProp } from "@react-navigation/native-stack"
import { Text } from "@/components/Text"
import { MOCK_USER } from "@/constants/mockUser"
import { AppStackParamList } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { useAuth } from "@/context/AuthContext"

const { width } = Dimensions.get("window")
type Nav = NativeStackNavigationProp<AppStackParamList>

const ACHIEVEMENTS = [
  { icon: "🏯", label: "Kiến trúc cổ", count: 12, color: colors.palette.royalPurple },
  { icon: "🍜", label: "Ẩm thực", count: 28, color: colors.palette.sunsetOrange },
  { icon: "🌅", label: "Hoàng hôn", count: 7, color: colors.palette.imperialGold },
  { icon: "🛵", label: "Phượt thủ", count: 5, color: colors.palette.jadeGreen },
]

const MENU_ITEMS = [
  { icon: "🗺️", label: "Lộ trình đã lưu", count: "14", action: "MapTimeline" },
  { icon: "⭐", label: "Địa điểm yêu thích", count: "32", action: null },
  { icon: "🔔", label: "Thông báo", count: "3 mới", action: null },
  { icon: "⚙️", label: "Cài đặt", count: null, action: "Settings" },
  { icon: "🌐", label: "Ngôn ngữ", count: "Tiếng Việt", action: null },
  { icon: "💬", label: "Phản hồi & Góp ý", count: null, action: null },
  { icon: "📋", label: "Điều khoản & Chính sách", count: null, action: null },
]

export const ProfileScreen: React.FC = () => {
  const navigation = useNavigation<Nav>()
  const insets = useSafeAreaInsets()
  const { logout } = useAuth()
  const [avatarError, setAvatarError] = useState(false)

  return (
    <View style={styles.root}>
      <StatusBar barStyle="dark-content" backgroundColor="transparent" translucent />
      <LinearGradient
        colors={[colors.palette.appCream, "#FFFFFF"]}
        style={StyleSheet.absoluteFillObject}
      />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={[styles.scroll, { paddingBottom: insets.bottom + 100 }]}
      >
        {/* HERO SECTION */}
        <LinearGradient
          colors={["rgba(249, 115, 22, 0.08)", "transparent"]}
          style={[styles.heroSection, { paddingTop: insets.top + 20 }]}
        >
          {/* Settings shortcut */}
          <View style={styles.heroActions}>
            <Text style={styles.heroTitle}>Tài Khoản</Text>
            <TouchableOpacity
              style={styles.settingsBtn}
              onPress={() => navigation.navigate("Settings")}
              testID="settings-btn"
            >
              <Text style={styles.settingsBtnIcon}>⚙️</Text>
            </TouchableOpacity>
          </View>

          {/* Avatar + info */}
          <View style={styles.profileBlock}>
            <View style={styles.avatarWrap}>
              {!avatarError ? (
                <Image
                  source={{ uri: MOCK_USER.avatarUrl }}
                  style={styles.avatar}
                  onError={() => setAvatarError(true)}
                />
              ) : (
                <View style={[styles.avatar, styles.avatarFallback]}>
                  <Text style={styles.avatarInitial}>{MOCK_USER.firstName?.[0] ?? "U"}</Text>
                </View>
              )}
              <View style={styles.onlineDot} />
            </View>
            <Text style={styles.name}>{MOCK_USER.name}</Text>
            <Text style={styles.email}>{MOCK_USER.email}</Text>
            <View style={styles.locationRow}>
              <Text style={styles.locationText}>📍 {MOCK_USER.location}</Text>
              <View style={styles.locationDot} />
              <Text style={styles.joinedText}>Tham gia {MOCK_USER.joinedDate.split("-")[0]}</Text>
            </View>
            {MOCK_USER.bio && <Text style={styles.bio}>{MOCK_USER.bio}</Text>}
          </View>
        </LinearGradient>

        {/* STATS */}
        <View style={styles.statsRow}>
          {[
            { value: MOCK_USER.tripCount, label: "Chuyến đi", color: colors.palette.appOrangeDark },
            { value: MOCK_USER.reviewCount, label: "Đánh giá", color: colors.palette.imperialGold },
            { value: MOCK_USER.savedCount, label: "Đã lưu", color: colors.palette.jadeGreen },
          ].map((stat, i) => (
            <View key={i} style={styles.statCard}>
              <LinearGradient
                colors={[stat.color + "08", "rgba(255,255,255,0.7)"]}
                style={styles.statCardGradient}
              >
                <Text style={[styles.statValue, { color: stat.color }]}>{stat.value}</Text>
                <Text style={styles.statLabel}>{stat.label}</Text>
              </LinearGradient>
            </View>
          ))}
        </View>

        {/* ACHIEVEMENTS */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>🏆 Thành tích</Text>
          <View style={styles.achievementsGrid}>
            {ACHIEVEMENTS.map((ach, i) => (
              <View key={i} style={styles.achievementCard}>
                <LinearGradient
                  colors={[ach.color + "10", "rgba(255,255,255,0.7)"]}
                  style={styles.achievementGradient}
                >
                  <Text style={styles.achievementIcon}>{ach.icon}</Text>
                  <Text style={[styles.achievementCount, { color: ach.color }]}>{ach.count}</Text>
                  <Text style={styles.achievementLabel}>{ach.label}</Text>
                </LinearGradient>
              </View>
            ))}
          </View>
        </View>

        {/* MENU ITEMS */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>⚡ Chức năng</Text>
          <View style={styles.menuContainer}>
            {MENU_ITEMS.map((item, i) => (
              <TouchableOpacity
                key={i}
                style={[styles.menuItem, i === MENU_ITEMS.length - 1 && styles.menuItemLast]}
                onPress={() => {
                  if (item.action === "Settings") navigation.navigate("Settings")
                }}
              >
                <View style={styles.menuItemLeft}>
                  <View style={styles.menuIconWrap}>
                    <Text style={styles.menuIcon}>{item.icon}</Text>
                  </View>
                  <Text style={styles.menuLabel}>{item.label}</Text>
                </View>
                <View style={styles.menuItemRight}>
                  {item.count && (
                    <View style={styles.menuCountBadge}>
                      <Text style={styles.menuCountText}>{item.count}</Text>
                    </View>
                  )}
                  <Text style={styles.menuArrow}>›</Text>
                </View>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* LOGOUT */}
        <TouchableOpacity style={styles.logoutBtn} onPress={logout}>
          <View style={styles.logoutBtnInner}>
            <Text style={styles.logoutIcon}>🚪</Text>
            <Text style={styles.logoutText}>Đăng xuất</Text>
          </View>
        </TouchableOpacity>

        {/* App version */}
        <Text style={styles.appVersion}>TripFlow v1.0.0 · Made with ❤️ in Vietnam</Text>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.palette.appCream },
  scroll: {},
  heroSection: { paddingHorizontal: spacing.lg, paddingBottom: spacing.xl },
  heroActions: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.xl },
  heroTitle: { fontFamily: typography.primary.bold, fontSize: 24, color: colors.palette.appInk },
  settingsBtn: {
    width: 44, height: 44, borderRadius: 14,
    backgroundColor: "rgba(255, 255, 255, 0.65)",
    justifyContent: "center", alignItems: "center",
    borderWidth: 1.5, borderColor: "rgba(255, 255, 255, 0.9)",
    ...Platform.select({
      web: {
        backdropFilter: "blur(15px)",
        WebkitBackdropFilter: "blur(15px)",
      } as any
    }),
  },
  settingsBtnIcon: { fontSize: 20 },
  profileBlock: { alignItems: "center" },
  avatarWrap: { position: "relative", marginBottom: spacing.md },
  avatar: { width: 100, height: 100, borderRadius: 30, borderWidth: 3, borderColor: colors.palette.appOrange },
  avatarFallback: { backgroundColor: colors.palette.appOrange + "40", justifyContent: "center", alignItems: "center" },
  avatarInitial: { fontFamily: typography.primary.bold, fontSize: 36, color: colors.palette.appOrangeDark },
  onlineDot: {
    position: "absolute", bottom: 4, right: 4,
    width: 16, height: 16, borderRadius: 8,
    backgroundColor: colors.palette.jadeGreen,
    borderWidth: 2, borderColor: "#FFFFFF",
  },
  name: { fontFamily: typography.primary.bold, fontSize: 22, color: colors.palette.appInk, marginBottom: 4 },
  email: { fontFamily: typography.primary.normal, fontSize: 14, color: colors.palette.appMuted, marginBottom: 8 },
  locationRow: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 8 },
  locationText: { fontFamily: typography.primary.normal, fontSize: 13, color: colors.palette.appMuted },
  locationDot: { width: 3, height: 3, borderRadius: 1.5, backgroundColor: "rgba(31, 41, 55, 0.25)" },
  joinedText: { fontFamily: typography.primary.normal, fontSize: 13, color: "rgba(31, 41, 55, 0.5)" },
  bio: { fontFamily: typography.primary.normal, fontSize: 14, color: colors.palette.appInk, textAlign: "center", lineHeight: 22, marginTop: 4 },
  statsRow: { flexDirection: "row", paddingHorizontal: spacing.lg, gap: spacing.sm, marginTop: spacing.md, marginBottom: spacing.md },
  statCard: {
    flex: 1,
    borderRadius: 16,
    overflow: "hidden",
    borderWidth: 1.5,
    borderColor: "rgba(255, 255, 255, 0.9)",
  },
  statCardGradient: { padding: spacing.md, alignItems: "center" },
  statValue: { fontFamily: typography.primary.bold, fontSize: 24, marginBottom: 2 },
  statLabel: { fontFamily: typography.primary.normal, fontSize: 11, color: colors.palette.appMuted },
  section: { paddingHorizontal: spacing.lg, marginBottom: spacing.lg },
  sectionTitle: { fontFamily: typography.primary.semiBold, fontSize: 16, color: colors.palette.appInk, marginBottom: spacing.md },
  achievementsGrid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  achievementCard: {
    width: (width - spacing.lg * 2 - spacing.sm) / 2,
    borderRadius: 16, overflow: "hidden",
    borderWidth: 1.5, borderColor: "rgba(255, 255, 255, 0.9)",
  },
  achievementGradient: { padding: spacing.md, alignItems: "center", gap: 6 },
  achievementIcon: { fontSize: 32 },
  achievementCount: { fontFamily: typography.primary.bold, fontSize: 20 },
  achievementLabel: { fontFamily: typography.primary.normal, fontSize: 12, color: colors.palette.appMuted },
  menuContainer: {
    backgroundColor: "rgba(255, 255, 255, 0.58)",
    borderRadius: 16, borderWidth: 1.5, borderColor: "rgba(255, 255, 255, 0.9)",
    overflow: "hidden",
    ...Platform.select({
      web: {
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
      } as any
    }),
    shadowColor: "#1F2937",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.03,
    shadowRadius: 10,
    elevation: 2,
  },
  menuItem: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    padding: spacing.md,
    borderBottomWidth: 1, borderBottomColor: "rgba(249, 115, 22, 0.08)",
  },
  menuItemLast: { borderBottomWidth: 0 },
  menuItemLeft: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  menuIconWrap: {
    width: 36, height: 36, borderRadius: 10,
    backgroundColor: "rgba(249, 115, 22, 0.06)",
    justifyContent: "center", alignItems: "center",
  },
  menuIcon: { fontSize: 18 },
  menuLabel: { fontFamily: typography.primary.medium, fontSize: 15, color: colors.palette.appInk },
  menuItemRight: { flexDirection: "row", alignItems: "center", gap: 8 },
  menuCountBadge: {
    backgroundColor: "rgba(249, 115, 22, 0.08)",
    borderRadius: 10, paddingHorizontal: 8, paddingVertical: 2,
    borderWidth: 1, borderColor: "rgba(249, 115, 22, 0.15)",
  },
  menuCountText: { fontFamily: typography.primary.semiBold, fontSize: 11, color: colors.palette.appOrangeDark },
  menuArrow: { fontSize: 20, color: "rgba(31, 41, 55, 0.3)", fontFamily: typography.primary.normal },
  logoutBtn: { marginHorizontal: spacing.lg, marginBottom: spacing.md },
  logoutBtnInner: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: spacing.sm, paddingVertical: 14,
    backgroundColor: "rgba(255, 107, 107, 0.08)",
    borderRadius: 16, borderWidth: 1, borderColor: "rgba(255, 107, 107, 0.2)",
  },
  logoutIcon: { fontSize: 20 },
  logoutText: { fontFamily: typography.primary.semiBold, fontSize: 15, color: colors.palette.sunsetOrange },
  appVersion: { fontFamily: typography.primary.normal, fontSize: 12, color: "rgba(31, 41, 55, 0.3)", textAlign: "center", paddingBottom: spacing.md },
})