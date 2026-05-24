/**
 * ExploreScreen - Dark Royal Hue redesign
 * Discovery feed: search + category filters + popular destination cards
 */
import React, { useState } from "react"
import {
  View, ScrollView, StyleSheet, StatusBar,
  TouchableOpacity, Dimensions, Image,
} from "react-native"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { useNavigation } from "@react-navigation/native"
import type { NativeStackNavigationProp } from "@react-navigation/native-stack"
import { Text } from "@/components/Text"
import { SearchBar } from "@/components/SearchBar"
import { LocationCard } from "@/components/LocationCard"
import { CategoryChip } from "@/components/CategoryChip"
import { POPULAR_LOCATIONS, PopularLocation } from "@/constants/mockPopularLocations"
import { MOCK_USER } from "@/constants/mockUser"
import { AppStackParamList } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

const { width } = Dimensions.get("window")
type Nav = NativeStackNavigationProp<AppStackParamList>

const CATEGORIES = ["Tất cả", "Di tích", "Biển", "Núi", "Phố cổ", "Thiên nhiên"]

const FEATURED_COLLECTIONS = [
  {
    id: "hue-imperial",
    title: "🏯 Cố Đô Huế",
    subtitle: "12 điểm UNESCO",
    photoUrl: "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?auto=format&fit=crop&q=80&w=800",
    gradient: [colors.palette.royalPurple + "CC", "rgba(11,15,25,0.9)"],
  },
  {
    id: "hue-cuisine",
    title: "🍜 Ẩm Thực Cung Đình",
    subtitle: "20+ món đặc sản",
    photoUrl: "https://images.unsplash.com/photo-1555921015-5532091f6026?auto=format&fit=crop&q=80&w=800",
    gradient: [colors.palette.sunsetOrange + "BB", "rgba(11,15,25,0.9)"],
  },
  {
    id: "hue-sunset",
    title: "🌅 Phá Tam Giang",
    subtitle: "Hoàng hôn đẹp nhất VN",
    photoUrl: "https://images.unsplash.com/photo-1592806088932-05058af0ad8d?auto=format&fit=crop&q=80&w=800",
    gradient: [colors.palette.imperialGold + "BB", "rgba(11,15,25,0.9)"],
  },
]

export const ExploreScreen: React.FC = () => {
  const navigation = useNavigation<Nav>()
  const insets = useSafeAreaInsets()
  const [searchQuery, setSearchQuery] = useState("")
  const [activeCategory, setActiveCategory] = useState("Tất cả")

  const filteredLocations = activeCategory === "Tất cả"
    ? POPULAR_LOCATIONS
    : POPULAR_LOCATIONS.filter((loc) => loc.category.toLowerCase() === activeCategory.toLowerCase())

  const handleLocationPress = (loc: PopularLocation) => {
    navigation.navigate("POIDetail", {
      poiId: loc.id, poiName: loc.name, photoUrl: loc.photoUrl,
      rating: loc.rating, reviewCount: loc.locationCount * 145,
      description: loc.tagline, entranceFee: 0,
      openTime: "08:00", closeTime: "18:00",
      lat: 16.46, lon: 107.59,
    })
  }

  const currentHour = new Date().getHours()
  const greeting = currentHour < 11 ? "Buổi sáng" : currentHour < 14 ? "Buổi trưa" : currentHour < 18 ? "Buổi chiều" : "Buổi tối"

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <LinearGradient
        colors={[colors.palette.deepSlate, "#111827", "#0d0e1a"]}
        style={StyleSheet.absoluteFillObject}
      />
      <View style={styles.orb} />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={[styles.scrollContent, { paddingBottom: insets.bottom + 100 }]}
      >
        {/* HEADER */}
        <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
          <View>
            <Text style={styles.greeting}>{greeting} tốt lành! 👋</Text>
            <Text style={styles.userName}>{MOCK_USER.firstName}, bạn muốn đi đâu?</Text>
          </View>
          <TouchableOpacity
            style={styles.avatarBtn}
            onPress={() => navigation.navigate("MainTabs", { screen: "Profile" })}
          >
            <Image
              source={{ uri: MOCK_USER.avatarUrl }}
              style={styles.avatar}
            />
          </TouchableOpacity>
        </View>

        {/* SEARCH */}
        <View style={styles.searchWrap}>
          <SearchBar
            value={searchQuery}
            onChangeText={setSearchQuery}
            placeholder="Tìm địa điểm, lăng tẩm, ẩm thực..."
          />
          <TouchableOpacity style={styles.filterBtn}>
            <Text style={styles.filterBtnText}>🎛️</Text>
          </TouchableOpacity>
        </View>

        {/* FEATURED COLLECTIONS */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>🔥 Bộ sưu tập nổi bật</Text>
        </View>
        <ScrollView
          horizontal showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.featuredScroll}
        >
          {FEATURED_COLLECTIONS.map((col) => (
            <TouchableOpacity key={col.id} style={styles.featuredCard}>
              <Image source={{ uri: col.photoUrl }} style={styles.featuredImage} resizeMode="cover" />
              <LinearGradient
                colors={col.gradient as [string, string]}
                style={styles.featuredGradient}
                start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
              />
              <View style={styles.featuredText}>
                <Text style={styles.featuredTitle}>{col.title}</Text>
                <Text style={styles.featuredSub}>{col.subtitle}</Text>
              </View>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* QUICK PLAN CTA */}
        <TouchableOpacity
          style={styles.quickPlanCard}
          onPress={() => navigation.navigate("ItineraryForm")}
        >
          <LinearGradient
            colors={[colors.palette.royalPurple + "40", colors.palette.royalPurple + "15"]}
            style={styles.quickPlanGradient}
            start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
          >
            <View style={styles.quickPlanLeft}>
              <Text style={styles.quickPlanTitle}>🤖 Lập lịch với AI</Text>
              <Text style={styles.quickPlanSub}>Tối ưu theo sức bền & thời tiết thực tế</Text>
            </View>
            <View style={styles.quickPlanArrow}>
              <Text style={styles.quickPlanArrowText}>→</Text>
            </View>
          </LinearGradient>
        </TouchableOpacity>

        {/* CATEGORY CHIPS */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>📍 Khám phá theo chủ đề</Text>
        </View>
        <ScrollView
          horizontal showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.chipsScroll}
        >
          {CATEGORIES.map((cat) => (
            <CategoryChip
              key={cat}
              label={cat}
              active={activeCategory === cat}
              onPress={() => setActiveCategory(cat)}
            />
          ))}
        </ScrollView>

        {/* LOCATION GRID */}
        <View style={styles.gridSection}>
          {filteredLocations.length === 0 ? (
            <View style={styles.emptyGrid}>
              <Text style={styles.emptyText}>😕 Không tìm thấy địa điểm phù hợp</Text>
            </View>
          ) : (
            <View style={styles.grid}>
              {filteredLocations.map((loc) => (
                <LocationCard
                  key={loc.id}
                  name={loc.name}
                  subtitle={loc.tagline}
                  photoUrl={loc.photoUrl}
                  rating={loc.rating}
                  locationCount={loc.locationCount}
                  onPress={() => handleLocationPress(loc)}
                  testID={`location-card-${loc.id}`}
                />
              ))}
            </View>
          )}
        </View>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  orb: {
    position: "absolute", top: -100, right: -80,
    width: 300, height: 300, borderRadius: 150,
    backgroundColor: colors.palette.royalPurple + "20",
  },
  scrollContent: { paddingHorizontal: spacing.lg },
  header: {
    flexDirection: "row", alignItems: "flex-start",
    justifyContent: "space-between", paddingBottom: spacing.lg,
  },
  greeting: { fontFamily: typography.primary.normal, fontSize: 14, color: "rgba(255,255,255,0.5)", marginBottom: 2 },
  userName: { fontFamily: typography.primary.bold, fontSize: 22, color: "#FFFFFF" },
  avatarBtn: { marginTop: 4 },
  avatar: { width: 44, height: 44, borderRadius: 14, borderWidth: 2, borderColor: colors.palette.royalPurple },
  searchWrap: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.lg },
  filterBtn: {
    width: 50, height: 50, borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.08)",
    justifyContent: "center", alignItems: "center",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
    flexShrink: 0,
  },
  filterBtnText: { fontSize: 20 },
  sectionHeader: { marginBottom: spacing.sm },
  sectionTitle: { fontFamily: typography.primary.semiBold, fontSize: 16, color: "#FFFFFF" },
  featuredScroll: { flexDirection: "row", gap: spacing.md, marginBottom: spacing.lg, paddingRight: spacing.lg },
  featuredCard: {
    width: 200, height: 130, borderRadius: 16, overflow: "hidden",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
  },
  featuredImage: { width: "100%", height: "100%", position: "absolute" },
  featuredGradient: { position: "absolute", inset: 0 } as any,
  featuredText: { position: "absolute", bottom: 0, left: 0, right: 0, padding: spacing.sm },
  featuredTitle: { fontFamily: typography.primary.bold, fontSize: 15, color: "#FFFFFF" },
  featuredSub: { fontFamily: typography.primary.normal, fontSize: 11, color: "rgba(255,255,255,0.7)", marginTop: 2 },
  quickPlanCard: {
    borderRadius: 16, overflow: "hidden",
    borderWidth: 1, borderColor: colors.palette.royalPurple + "50",
    marginBottom: spacing.lg,
  },
  quickPlanGradient: {
    flexDirection: "row", alignItems: "center",
    padding: spacing.md, gap: spacing.md,
  },
  quickPlanLeft: { flex: 1 },
  quickPlanTitle: { fontFamily: typography.primary.semiBold, fontSize: 15, color: "#FFFFFF" },
  quickPlanSub: { fontFamily: typography.primary.normal, fontSize: 12, color: "rgba(255,255,255,0.5)", marginTop: 2 },
  quickPlanArrow: {
    width: 36, height: 36, borderRadius: 10,
    backgroundColor: colors.palette.royalPurple + "50",
    justifyContent: "center", alignItems: "center",
  },
  quickPlanArrowText: { fontSize: 20, color: "#FFFFFF" },
  chipsScroll: { flexDirection: "row", gap: 8, marginBottom: spacing.lg },
  gridSection: {},
  grid: {
    flexDirection: "row", flexWrap: "wrap",
    gap: spacing.md, justifyContent: "space-between",
  },
  emptyGrid: { alignItems: "center", paddingVertical: 40 },
  emptyText: { fontFamily: typography.primary.normal, fontSize: 14, color: "rgba(255,255,255,0.4)" },
})