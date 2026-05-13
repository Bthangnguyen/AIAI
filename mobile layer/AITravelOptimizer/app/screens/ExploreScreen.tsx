/**
 * ExploreScreen — Figma "Front page" (Home tab).
 * Greeting header + search + category chips + popular locations grid.
 */
import React, { useState } from "react"
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  TouchableOpacity,
  FlatList,
  Dimensions,
} from "react-native"
import { useNavigation } from "@react-navigation/native"
import type { NativeStackNavigationProp } from "@react-navigation/native-stack"

import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { SearchBar } from "@/components/SearchBar"
import { LocationCard } from "@/components/LocationCard"
import { CategoryChip } from "@/components/CategoryChip"
import { AvatarBadge } from "@/components/AvatarBadge"
import { CTAButton } from "@/components/CTAButton"
import { POPULAR_LOCATIONS, PopularLocation } from "@/constants/mockPopularLocations"
import { MOCK_USER } from "@/constants/mockUser"
import { AppStackParamList } from "@/navigators/navigationTypes"

type Nav = NativeStackNavigationProp<AppStackParamList>

const CATEGORIES = ["All", "Island", "Beach", "Mountain", "City", "Heritage"]
const { width: SCREEN_WIDTH } = Dimensions.get("window")

export const ExploreScreen: React.FC = () => {
  const navigation = useNavigation<Nav>()
  const [searchQuery, setSearchQuery] = useState("")
  const [activeCategory, setActiveCategory] = useState("All")

  const filteredLocations =
    activeCategory === "All"
      ? POPULAR_LOCATIONS
      : POPULAR_LOCATIONS.filter(
          (loc) => loc.category.toLowerCase() === activeCategory.toLowerCase(),
        )

  const handleLocationPress = (loc: PopularLocation) => {
    // Navigate to POIDetail with representative data
    navigation.navigate("POIDetail", {
      poiId: loc.id,
      poiName: loc.name,
      photoUrl: loc.photoUrl,
      rating: loc.rating,
      reviewCount: loc.locationCount * 145, // mock review count
      description: loc.tagline,
      entranceFee: 0,
      openTime: "08:00",
      closeTime: "18:00",
      lat: 16.46,
      lon: 107.59,
    })
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.palette.figmaWhite} />
      <ScrollView
        style={styles.container}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {/* ─── Header ────────────────────────────────────────────── */}
        <View style={styles.header}>
          <View style={styles.greetingBlock}>
            <Text style={styles.greeting}>Hello,</Text>
            <Text style={styles.userName}>{MOCK_USER.firstName} 👋</Text>
            <Text style={styles.subtitle}>Where do you want to go?</Text>
          </View>
          <TouchableOpacity
            onPress={() => navigation.navigate("Settings")}
            testID="header-avatar"
          >
            <AvatarBadge uri={MOCK_USER.avatarUrl} size={48} showOnline />
          </TouchableOpacity>
        </View>

        {/* ─── Search Bar ────────────────────────────────────────── */}
        <SearchBar
          value={searchQuery}
          onChangeText={setSearchQuery}
          placeholder="Search destinations..."
          style={styles.searchBar}
          testID="explore-search"
        />

        {/* ─── Plan Trip CTA ─────────────────────────────────────── */}
        <CTAButton
          label="✈️  Plan a Trip"
          onPress={() => navigation.navigate("ItineraryForm")}
          style={styles.planButton}
          testID="plan-trip-cta"
        />

        {/* ─── Category Chips ────────────────────────────────────── */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Explore</Text>
        </View>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.chipsRow}
        >
          {CATEGORIES.map((cat) => (
            <CategoryChip
              key={cat}
              label={cat}
              active={activeCategory === cat}
              onPress={() => setActiveCategory(cat)}
              style={styles.chip}
            />
          ))}
        </ScrollView>

        {/* ─── Popular Locations ─────────────────────────────────── */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Popular Locations</Text>
          <TouchableOpacity>
            <Text style={styles.seeAll}>See all</Text>
          </TouchableOpacity>
        </View>

        {/* Grid — 2 columns */}
        <View style={styles.grid}>
          {filteredLocations.map((loc, index) => (
            <LocationCard
              key={loc.id}
              name={loc.name}
              subtitle={loc.tagline}
              photoUrl={loc.photoUrl}
              priceFrom={loc.priceFrom}
              rating={loc.rating}
              locationCount={loc.locationCount}
              onPress={() => handleLocationPress(loc)}
              style={index % 2 === 0 ? styles.cardLeft : styles.cardRight}
              testID={`location-card-${loc.id}`}
            />
          ))}
        </View>

        {/* Padding bottom for tab bar */}
        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  )
}

const CARD_SIZE = (SCREEN_WIDTH - spacing.lg * 2 - spacing.sm) / 2

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.palette.figmaWhite,
  },
  container: {
    flex: 1,
  },
  scrollContent: {
    paddingTop: spacing.sm,
  },
  header: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
  },
  greetingBlock: {
    flex: 1,
  },
  greeting: {
    fontFamily: typography.primary.normal,
    fontSize: 16,
    color: colors.palette.figmaGrayMedium,
  },
  userName: {
    fontFamily: typography.primary.bold,
    fontSize: 24,
    color: colors.palette.figmaBlack,
    marginTop: 2,
  },
  subtitle: {
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: colors.palette.figmaGrayMedium,
    marginTop: 2,
  },
  searchBar: {
    marginHorizontal: spacing.lg,
    marginBottom: spacing.md,
  },
  planButton: {
    marginHorizontal: spacing.lg,
    marginBottom: spacing.lg,
  },
  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: spacing.lg,
    marginBottom: spacing.sm,
  },
  sectionTitle: {
    fontFamily: typography.primary.semiBold,
    fontSize: 18,
    color: colors.palette.figmaBlack,
  },
  seeAll: {
    fontFamily: typography.primary.medium,
    fontSize: 13,
    color: colors.palette.figmaBlue,
  },
  chipsRow: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
    gap: spacing.xs,
  },
  chip: {
    marginRight: spacing.xs,
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    paddingHorizontal: spacing.lg,
    gap: spacing.sm,
  },
  cardLeft: {
    width: CARD_SIZE,
  },
  cardRight: {
    width: CARD_SIZE,
  },
})
