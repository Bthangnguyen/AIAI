/**
 * ProfileScreen — User profile with stats and settings access.
 */
import React from "react"
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  TouchableOpacity,
} from "react-native"
import { useNavigation } from "@react-navigation/native"
import type { NativeStackNavigationProp } from "@react-navigation/native-stack"

import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { AvatarBadge } from "@/components/AvatarBadge"
import { CTAButton } from "@/components/CTAButton"
import { MOCK_USER } from "@/constants/mockUser"
import { AppStackParamList } from "@/navigators/navigationTypes"

type Nav = NativeStackNavigationProp<AppStackParamList>

export const ProfileScreen: React.FC = () => {
  const navigation = useNavigation<Nav>()

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.palette.figmaWhite} />
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* ─── Header ── */}
        <View style={styles.header}>
          <Text style={styles.title}>Profile</Text>
          <TouchableOpacity
            onPress={() => navigation.navigate("Settings")}
            testID="settings-btn"
          >
            <Text style={styles.settingsIcon}>⚙️</Text>
          </TouchableOpacity>
        </View>

        {/* ─── Avatar + Name ── */}
        <View style={styles.profileBlock}>
          <AvatarBadge uri={MOCK_USER.avatarUrl} size={88} showOnline style={styles.avatar} />
          <Text style={styles.name}>{MOCK_USER.name}</Text>
          <Text style={styles.email}>{MOCK_USER.email}</Text>
          <Text style={styles.location}>📍 {MOCK_USER.location}</Text>
          {MOCK_USER.bio ? <Text style={styles.bio}>{MOCK_USER.bio}</Text> : null}
        </View>

        {/* ─── Stats Row ── */}
        <View style={styles.statsRow}>
          {[
            { value: MOCK_USER.tripCount, label: "Trips" },
            { value: MOCK_USER.reviewCount, label: "Reviews" },
            { value: MOCK_USER.savedCount, label: "Saved" },
          ].map((stat) => (
            <View key={stat.label} style={styles.statItem}>
              <Text style={styles.statValue}>{stat.value}</Text>
              <Text style={styles.statLabel}>{stat.label}</Text>
            </View>
          ))}
        </View>

        {/* ─── Plan New Trip ── */}
        <CTAButton
          label="✈️  Plan a New Trip"
          onPress={() => navigation.navigate("ItineraryForm")}
          style={styles.ctaButton}
        />

        {/* ─── Menu Items ── */}
        <View style={styles.menuSection}>
          {[
            { icon: "🗺️", label: "My Trips", onPress: () => {} },
            { icon: "❤️", label: "Saved Places", onPress: () => {} },
            { icon: "🔔", label: "Notifications", onPress: () => {} },
            { icon: "⚙️", label: "Settings", onPress: () => navigation.navigate("Settings") },
            { icon: "📤", label: "Share App", onPress: () => {} },
          ].map((item) => (
            <TouchableOpacity
              key={item.label}
              style={styles.menuItem}
              onPress={item.onPress}
              activeOpacity={0.7}
            >
              <Text style={styles.menuIcon}>{item.icon}</Text>
              <Text style={styles.menuLabel}>{item.label}</Text>
              <Text style={styles.menuArrow}>›</Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.palette.figmaWhite,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
  },
  title: {
    fontFamily: typography.primary.bold,
    fontSize: 24,
    color: colors.palette.figmaBlack,
  },
  settingsIcon: {
    fontSize: 22,
  },
  profileBlock: {
    alignItems: "center",
    paddingVertical: spacing.lg,
    paddingHorizontal: spacing.lg,
  },
  avatar: {
    marginBottom: spacing.md,
  },
  name: {
    fontFamily: typography.primary.bold,
    fontSize: 22,
    color: colors.palette.figmaBlack,
    marginBottom: 4,
  },
  email: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: colors.palette.figmaGrayMedium,
    marginBottom: 4,
  },
  location: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: colors.palette.figmaGrayMedium,
    marginBottom: spacing.xs,
  },
  bio: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: colors.palette.figmaGrayDark,
    textAlign: "center",
    lineHeight: 20,
  },
  statsRow: {
    flexDirection: "row",
    justifyContent: "space-around",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.palette.figmaGrayLight,
    marginHorizontal: spacing.lg,
    borderRadius: 15,
    backgroundColor: colors.palette.figmaOffWhite,
    marginBottom: spacing.lg,
  },
  statItem: {
    alignItems: "center",
  },
  statValue: {
    fontFamily: typography.primary.bold,
    fontSize: 20,
    color: colors.palette.figmaBlack,
  },
  statLabel: {
    fontFamily: typography.primary.normal,
    fontSize: 12,
    color: colors.palette.figmaGrayMedium,
    marginTop: 2,
  },
  ctaButton: {
    marginHorizontal: spacing.lg,
    marginBottom: spacing.lg,
  },
  menuSection: {
    marginHorizontal: spacing.lg,
    borderRadius: 15,
    backgroundColor: colors.palette.figmaOffWhite,
    overflow: "hidden",
  },
  menuItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.palette.figmaGrayLight,
  },
  menuIcon: {
    fontSize: 20,
    marginRight: spacing.md,
  },
  menuLabel: {
    flex: 1,
    fontFamily: typography.primary.medium,
    fontSize: 15,
    color: colors.palette.figmaGrayDark,
  },
  menuArrow: {
    fontFamily: typography.primary.normal,
    fontSize: 20,
    color: colors.palette.figmaGrayMedium,
  },
})
