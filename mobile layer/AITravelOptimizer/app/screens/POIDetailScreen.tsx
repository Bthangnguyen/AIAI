/**
 * POIDetailScreen - Authentic Narrative Guide (Screen 6)
 * Design: Parallax hero + Audio Guide player + Royal Hue glassmorphism
 */
import React, { useState, useRef, useEffect } from "react"
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Animated,
  Dimensions,
  StatusBar,
  Platform,
  Linking,
  Image,
} from "react-native"
import { Text } from "@/components/Text"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { NativeStackScreenProps } from "@react-navigation/native-stack"
import { useNavigation, useRoute } from "@react-navigation/native"
import { NativeStackNavigationProp } from "@react-navigation/native-stack"
import { AppStackParamList } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get("window")
const HERO_HEIGHT = SCREEN_HEIGHT * 0.48

const TABS = ["Câu chuyện", "Thông tin", "Giá vé", "Khách sạn"] as const
type TabKey = typeof TABS[number]

const AUDIO_NARRATIVE = `Lăng Tự Đức — hay còn gọi là Khiêm Lăng — là lăng mộ tráng lệ nhất trong số các lăng vua triều Nguyễn. Được xây dựng từ năm 1864 đến 1867, công trình này không chỉ là nơi an nghỉ của vua Tự Đức mà còn là cả một khu cung điện sống động khi người còn tại vị.

Vua Tự Đức, tên thật là Nguyễn Phúc Hồng Nhậm, là vị hoàng đế có học thức uyên bác và đa cảm nhất triều Nguyễn. Ông là thi nhân, nhạc sĩ, và cũng là người cô đơn nhất ngai vàng — không có người kế thừa trực tiếp.

Khu lăng rộng 475 mẫu với hồ Lưu Khiêm nước biếc, đình Xung Khiêm ngao du thơ văn, và khu vườn thơ mộng phản chiếu tâm hồn nhạy cảm của vị hoàng đế đặc biệt này...`

const WAVEFORM_BARS = Array.from({ length: 40 }, () => Math.random() * 0.6 + 0.2)

type Nav = NativeStackNavigationProp<AppStackParamList>
type Props = NativeStackScreenProps<AppStackParamList, "POIDetail">

export const POIDetailScreen: React.FC<Props> = () => {
  const navigation = useNavigation<Nav>()
  const route = useRoute<Props["route"]>()
  const {
    poiName,
    photoUrl,
    rating = 4.8,
    reviewCount = 2847,
    description,
    entranceFee = 150000,
    openTime = "07:00",
    closeTime = "17:30",
    lat = 16.4508,
    lon = 107.5745,
  } = route.params ?? {}

  const [activeTab, setActiveTab] = useState<TabKey>("Câu chuyện")
  const [isPlaying, setIsPlaying] = useState(false)
  const [audioProgress, setAudioProgress] = useState(0)
  const [isFavorite, setIsFavorite] = useState(false)
  const insets = useSafeAreaInsets()

  // Animations
  const scrollY = useRef(new Animated.Value(0)).current
  const discRotate = useRef(new Animated.Value(0)).current
  const progressAnim = useRef(new Animated.Value(0)).current
  const heartScale = useRef(new Animated.Value(1)).current

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>
    if (isPlaying) {
      Animated.loop(
        Animated.timing(discRotate, { toValue: 1, duration: 4000, useNativeDriver: true })
      ).start()
      timer = setInterval(() => {
        setAudioProgress((p) => {
          const next = Math.min(p + 0.5, 100)
          if (next >= 100) {
            setIsPlaying(false)
            clearInterval(timer)
          }
          return next
        })
      }, 300)
    } else {
      discRotate.stopAnimation()
    }
    return () => clearInterval(timer)
  }, [isPlaying])

  const spin = discRotate.interpolate({ inputRange: [0, 1], outputRange: ["0deg", "360deg"] })

  const heroScale = scrollY.interpolate({
    inputRange: [-100, 0],
    outputRange: [1.2, 1],
    extrapolate: "clamp",
  })

  const heroOpacity = scrollY.interpolate({
    inputRange: [0, HERO_HEIGHT * 0.5],
    outputRange: [1, 0.7],
    extrapolate: "clamp",
  })

  const handleFavorite = () => {
    Animated.sequence([
      Animated.timing(heartScale, { toValue: 1.4, duration: 150, useNativeDriver: true }),
      Animated.timing(heartScale, { toValue: 1, duration: 150, useNativeDriver: true }),
    ]).start()
    setIsFavorite(!isFavorite)
  }

  const openNativeMap = () => {
    const url = Platform.select({
      ios: `maps:0,0?q=${poiName}@${lat},${lon}`,
      android: `geo:0,0?q=${lat},${lon}(${poiName})`,
      default: `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`,
    })
    if (url) Linking.openURL(url).catch(() => {})
  }

  const formatFee = (fee: number) => fee === 0 ? "Miễn phí" : `${fee.toLocaleString("vi-VN")} ₫`

  const displayName = poiName ?? "Lăng Tự Đức"
  const displayPhoto = photoUrl ?? "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?auto=format&fit=crop&q=80&w=900"
  const displayDescription = description ?? AUDIO_NARRATIVE

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />

      {/* Back & heart buttons - floating */}
      <View style={[styles.floatingActions, { top: insets.top + 12 }]}>
        <TouchableOpacity style={styles.floatBtn} onPress={() => navigation.goBack()}>
          <Text style={styles.floatBtnText}>←</Text>
        </TouchableOpacity>
        <Animated.View style={{ transform: [{ scale: heartScale }] }}>
          <TouchableOpacity style={styles.floatBtn} onPress={handleFavorite}>
            <Text style={styles.floatBtnText}>{isFavorite ? "❤️" : "🤍"}</Text>
          </TouchableOpacity>
        </Animated.View>
      </View>

      <Animated.ScrollView
        onScroll={Animated.event([{ nativeEvent: { contentOffset: { y: scrollY } } }], {
          useNativeDriver: false,
        })}
        scrollEventThrottle={16}
        showsVerticalScrollIndicator={false}
        bounces
      >
        {/* Parallax Hero */}
        <View style={{ height: HERO_HEIGHT, overflow: "hidden" }}>
          <Animated.Image
            source={{ uri: displayPhoto }}
            style={[styles.heroImage, { transform: [{ scale: heroScale }], opacity: heroOpacity }]}
            resizeMode="cover"
          />
          <LinearGradient
            colors={["transparent", "rgba(11,15,25,0.5)", "rgba(11,15,25,1)"]}
            style={styles.heroGradient}
          />
          {/* POI name overlay on hero */}
          <View style={styles.heroTextOverlay}>
            <View style={styles.heroCategoryBadge}>
              <Text style={styles.heroCategoryText}>🏯 Di Tích Lịch Sử</Text>
            </View>
            <Text style={styles.heroTitle} numberOfLines={2}>{displayName}</Text>
            <View style={styles.heroMeta}>
              <Text style={styles.heroRating}>⭐ {rating}</Text>
              <Text style={styles.heroReviews}>({reviewCount.toLocaleString()} đánh giá)</Text>
              <View style={styles.heroDot} />
              <Text style={styles.heroTime}>{openTime} - {closeTime}</Text>
            </View>
          </View>
        </View>

        {/* Content card */}
        <View style={styles.contentCard}>
          {/* Quick info strip */}
          <View style={styles.infoStrip}>
            <View style={styles.infoStripItem}>
              <Text style={styles.infoStripIcon}>🎫</Text>
              <Text style={styles.infoStripValue}>{formatFee(entranceFee)}</Text>
              <Text style={styles.infoStripLabel}>Vé vào</Text>
            </View>
            <View style={styles.infoStripDivider} />
            <View style={styles.infoStripItem}>
              <Text style={styles.infoStripIcon}>⏱️</Text>
              <Text style={styles.infoStripValue}>2-3h</Text>
              <Text style={styles.infoStripLabel}>Thời gian</Text>
            </View>
            <View style={styles.infoStripDivider} />
            <View style={styles.infoStripItem}>
              <Text style={styles.infoStripIcon}>📍</Text>
              <Text style={styles.infoStripValue}>Kim Long</Text>
              <Text style={styles.infoStripLabel}>Khu vực</Text>
            </View>
          </View>

          {/* Tab bar */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.tabScroll}
            contentContainerStyle={styles.tabBar}
          >
            {TABS.map((tab) => (
              <TouchableOpacity
                key={tab}
                style={[styles.tab, activeTab === tab && styles.tabActive]}
                onPress={() => setActiveTab(tab)}
              >
                <Text style={[styles.tabText, activeTab === tab && styles.tabTextActive]}>{tab}</Text>
                {activeTab === tab && <View style={styles.tabIndicator} />}
              </TouchableOpacity>
            ))}
          </ScrollView>

          {/* Tab: Câu chuyện = Audio Guide */}
          {activeTab === "Câu chuyện" && (
            <View style={styles.audioSection}>
              {/* Audio Player */}
              <View style={styles.audioPlayer}>
                <LinearGradient
                  colors={[colors.palette.royalPurple + "40", colors.palette.deepSlate]}
                  style={styles.audioPlayerGradient}
                >
                  {/* Spinning disc */}
                  <Animated.View style={[styles.audioDisc, { transform: [{ rotate: spin }] }]}>
                    <LinearGradient
                      colors={[colors.palette.royalPurple, "#2a1040", colors.palette.royalPurple]}
                      style={styles.audioDiscGradient}
                    />
                    <View style={styles.audioDiscCenter} />
                  </Animated.View>

                  {/* Audio info */}
                  <View style={styles.audioInfo}>
                    <Text style={styles.audioTitle}>🎧 Thuyết minh AI</Text>
                    <Text style={styles.audioSubtitle}>Giọng Huế · Tiếng Việt</Text>
                    <Text style={styles.audioDuration}>07:23 / 15:00</Text>
                  </View>
                </LinearGradient>

                {/* Waveform + progress */}
                <View style={styles.waveformContainer}>
                  {WAVEFORM_BARS.map((h, i) => (
                    <View
                      key={i}
                      style={[
                        styles.waveformBar,
                        {
                          height: h * 32,
                          backgroundColor: i / WAVEFORM_BARS.length < audioProgress / 100
                            ? colors.palette.imperialGold
                            : "rgba(255,255,255,0.15)",
                        },
                      ]}
                    />
                  ))}
                </View>

                {/* Controls */}
                <View style={styles.audioControls}>
                  <TouchableOpacity style={styles.audioControlBtn}>
                    <Text style={styles.audioControlIcon}>⏮</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.audioPlayBtn}
                    onPress={() => setIsPlaying(!isPlaying)}
                  >
                    <LinearGradient
                      colors={[colors.palette.royalPurple, colors.palette.royalPurpleLight]}
                      style={styles.audioPlayBtnGradient}
                    >
                      <Text style={styles.audioPlayIcon}>{isPlaying ? "⏸" : "▶"}</Text>
                    </LinearGradient>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.audioControlBtn}>
                    <Text style={styles.audioControlIcon}>⏭</Text>
                  </TouchableOpacity>
                </View>
              </View>

              {/* Narrative text */}
              <View style={styles.narrativeSection}>
                <Text style={styles.narrativeSectionTitle}>📜 Câu Chuyện Lịch Sử</Text>
                <Text style={styles.narrativeText}>{displayDescription}</Text>
              </View>
            </View>
          )}

          {/* Tab: Thông tin */}
          {activeTab === "Thông tin" && (
            <View style={styles.infoSection}>
              {[
                { icon: "📍", label: "Địa chỉ", value: "Kim Long, Huế, Việt Nam" },
                { icon: "🕐", label: "Giờ mở cửa", value: `${openTime} - ${closeTime}` },
                { icon: "📞", label: "Điện thoại", value: "+84 234 3523 237" },
                { icon: "🌐", label: "Website", value: "hue-tourism.gov.vn" },
              ].map((item, i) => (
                <View key={i} style={styles.infoRow}>
                  <Text style={styles.infoRowIcon}>{item.icon}</Text>
                  <View style={styles.infoRowContent}>
                    <Text style={styles.infoRowLabel}>{item.label}</Text>
                    <Text style={styles.infoRowValue}>{item.value}</Text>
                  </View>
                </View>
              ))}
            </View>
          )}

          {/* Tab: Giá vé */}
          {activeTab === "Giá vé" && (
            <View style={styles.pricingSection}>
              {[
                { type: "Vé vào cửa chính", price: formatFee(entranceFee), note: "Người lớn" },
                { type: "Vé vào cửa chính", price: "Miễn phí", note: "Trẻ em dưới 7 tuổi" },
                { type: "Audio Guide AI", price: "50.000 ₫", note: "Thuyết minh tiếng Việt/Anh" },
                { type: "Chụp ảnh chuyên nghiệp", price: "Miễn phí", note: "Không cần giấy phép" },
              ].map((item, i) => (
                <View key={i} style={styles.pricingRow}>
                  <View>
                    <Text style={styles.pricingType}>{item.type}</Text>
                    <Text style={styles.pricingNote}>{item.note}</Text>
                  </View>
                  <Text style={styles.pricingPrice}>{item.price}</Text>
                </View>
              ))}
            </View>
          )}

          {/* Tab: Khách sạn */}
          {activeTab === "Khách sạn" && (
            <View style={styles.hotelsSection}>
              {[
                { name: "Pilgrimage Village Boutique", stars: 5, distance: "3.2km", price: "2.800.000₫/đêm" },
                { name: "La Résidence Hotel & Spa", stars: 5, distance: "5.8km", price: "3.500.000₫/đêm" },
                { name: "Hue Heritage Hotel", stars: 4, distance: "6.1km", price: "1.200.000₫/đêm" },
              ].map((hotel, i) => (
                <View key={i} style={styles.hotelCard}>
                  <View style={styles.hotelInfo}>
                    <Text style={styles.hotelName}>{hotel.name}</Text>
                    <Text style={styles.hotelStars}>{"⭐".repeat(hotel.stars)} · {hotel.distance}</Text>
                  </View>
                  <View>
                    <Text style={styles.hotelPrice}>{hotel.price}</Text>
                  </View>
                </View>
              ))}
            </View>
          )}

          {/* CTAs */}
          <View style={[styles.ctaRow, { paddingBottom: insets.bottom + 16 }]}>
            <TouchableOpacity
              style={styles.ctaPrimary}
              onPress={() => navigation.navigate("ItineraryForm")}
            >
              <LinearGradient
                colors={[colors.palette.royalPurple, colors.palette.royalPurpleLight]}
                style={styles.ctaPrimaryGradient}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
              >
                <Text style={styles.ctaPrimaryText}>📅 Lên Lịch Tham Quan</Text>
              </LinearGradient>
            </TouchableOpacity>
            <TouchableOpacity style={styles.ctaSecondary} onPress={openNativeMap}>
              <Text style={styles.ctaSecondaryText}>🗺️</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Animated.ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.palette.deepSlate },
  floatingActions: {
    position: "absolute",
    left: spacing.lg,
    right: spacing.lg,
    flexDirection: "row",
    justifyContent: "space-between",
    zIndex: 20,
  },
  floatBtn: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: "rgba(11,15,25,0.6)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.2)",
    justifyContent: "center",
    alignItems: "center",
  },
  floatBtnText: { fontSize: 20 },
  heroImage: {
    width: "100%",
    height: "100%",
    position: "absolute",
  },
  heroGradient: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    height: "80%",
  },
  heroTextOverlay: {
    position: "absolute",
    bottom: 20,
    left: spacing.lg,
    right: spacing.lg,
  },
  heroCategoryBadge: {
    alignSelf: "flex-start",
    backgroundColor: "rgba(108,42,123,0.6)",
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 4,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: "rgba(108,42,123,0.8)",
  },
  heroCategoryText: {
    fontFamily: typography.primary.semiBold,
    fontSize: 12,
    color: "#FFFFFF",
  },
  heroTitle: {
    fontFamily: typography.primary.bold,
    fontSize: 26,
    color: "#FFFFFF",
    lineHeight: 34,
    marginBottom: 8,
    letterSpacing: -0.5,
  },
  heroMeta: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    flexWrap: "wrap",
  },
  heroRating: { fontFamily: typography.primary.semiBold, fontSize: 14, color: colors.palette.imperialGold },
  heroReviews: { fontFamily: typography.primary.normal, fontSize: 13, color: "rgba(255,255,255,0.6)" },
  heroDot: { width: 4, height: 4, borderRadius: 2, backgroundColor: "rgba(255,255,255,0.4)" },
  heroTime: { fontFamily: typography.primary.normal, fontSize: 13, color: "rgba(255,255,255,0.7)" },
  contentCard: {
    backgroundColor: colors.palette.deepSlate,
    paddingTop: spacing.md,
    minHeight: SCREEN_HEIGHT * 0.6,
  },
  infoStrip: {
    flexDirection: "row",
    marginHorizontal: spacing.lg,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
    padding: spacing.md,
    justifyContent: "space-around",
    alignItems: "center",
    marginBottom: spacing.md,
  },
  infoStripItem: { alignItems: "center", gap: 4 },
  infoStripIcon: { fontSize: 20 },
  infoStripValue: {
    fontFamily: typography.primary.semiBold,
    fontSize: 14,
    color: "#FFFFFF",
  },
  infoStripLabel: {
    fontFamily: typography.primary.normal,
    fontSize: 11,
    color: "rgba(255,255,255,0.45)",
  },
  infoStripDivider: { width: 1, height: 40, backgroundColor: "rgba(255,255,255,0.1)" },
  tabScroll: { maxHeight: 50 },
  tabBar: {
    flexDirection: "row",
    paddingHorizontal: spacing.lg,
    gap: spacing.sm,
    paddingBottom: 8,
  },
  tab: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20, position: "relative" },
  tabActive: { backgroundColor: "rgba(108,42,123,0.3)" },
  tabText: {
    fontFamily: typography.primary.medium,
    fontSize: 14,
    color: "rgba(255,255,255,0.45)",
  },
  tabTextActive: { color: "#FFFFFF", fontFamily: typography.primary.semiBold },
  tabIndicator: {
    position: "absolute",
    bottom: 0,
    left: 16,
    right: 16,
    height: 2,
    backgroundColor: colors.palette.royalPurple,
    borderRadius: 1,
  },
  // Audio section
  audioSection: { paddingHorizontal: spacing.lg },
  audioPlayer: {
    backgroundColor: "rgba(255,255,255,0.04)",
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
    overflow: "hidden",
    marginBottom: spacing.lg,
  },
  audioPlayerGradient: {
    flexDirection: "row",
    alignItems: "center",
    padding: spacing.md,
    gap: spacing.md,
  },
  audioDisc: {
    width: 60,
    height: 60,
    borderRadius: 30,
    overflow: "hidden",
  },
  audioDiscGradient: { flex: 1 },
  audioDiscCenter: {
    position: "absolute",
    top: "50%",
    left: "50%",
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: colors.palette.deepSlate,
    marginTop: -8,
    marginLeft: -8,
    borderWidth: 2,
    borderColor: "rgba(255,255,255,0.3)",
  },
  audioInfo: { flex: 1 },
  audioTitle: {
    fontFamily: typography.primary.semiBold,
    fontSize: 15,
    color: "#FFFFFF",
  },
  audioSubtitle: {
    fontFamily: typography.primary.normal,
    fontSize: 12,
    color: "rgba(255,255,255,0.5)",
    marginTop: 2,
  },
  audioDuration: {
    fontFamily: typography.primary.medium,
    fontSize: 12,
    color: colors.palette.imperialGold,
    marginTop: 4,
  },
  waveformContainer: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.sm,
    gap: 2,
    height: 40,
  },
  waveformBar: {
    width: 4,
    borderRadius: 2,
    flex: 1,
  },
  audioControls: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    padding: spacing.md,
    gap: spacing.xl,
  },
  audioControlBtn: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.06)",
    justifyContent: "center",
    alignItems: "center",
  },
  audioControlIcon: { fontSize: 20, color: "rgba(255,255,255,0.7)" },
  audioPlayBtn: { borderRadius: 24, overflow: "hidden" },
  audioPlayBtnGradient: {
    width: 56,
    height: 56,
    justifyContent: "center",
    alignItems: "center",
  },
  audioPlayIcon: { fontSize: 24, color: "#FFFFFF" },
  narrativeSection: { marginBottom: spacing.xl },
  narrativeSectionTitle: {
    fontFamily: typography.primary.semiBold,
    fontSize: 16,
    color: "#FFFFFF",
    marginBottom: spacing.md,
  },
  narrativeText: {
    fontFamily: "poppinsRegular",
    fontSize: 15,
    lineHeight: 26,
    color: "rgba(255,255,255,0.75)",
    letterSpacing: 0.2,
  },
  // Info section
  infoSection: { paddingHorizontal: spacing.lg, gap: spacing.md },
  infoRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.04)",
    borderRadius: 14,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
    gap: spacing.md,
  },
  infoRowIcon: { fontSize: 22 },
  infoRowContent: { flex: 1 },
  infoRowLabel: { fontFamily: typography.primary.normal, fontSize: 12, color: "rgba(255,255,255,0.45)" },
  infoRowValue: { fontFamily: typography.primary.medium, fontSize: 14, color: "#FFFFFF", marginTop: 2 },
  // Pricing section
  pricingSection: { paddingHorizontal: spacing.lg, gap: spacing.sm },
  pricingRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.04)",
    borderRadius: 14,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  pricingType: { fontFamily: typography.primary.medium, fontSize: 14, color: "#FFFFFF" },
  pricingNote: { fontFamily: typography.primary.normal, fontSize: 12, color: "rgba(255,255,255,0.45)", marginTop: 2 },
  pricingPrice: { fontFamily: typography.primary.bold, fontSize: 14, color: colors.palette.imperialGold },
  // Hotels section
  hotelsSection: { paddingHorizontal: spacing.lg, gap: spacing.sm },
  hotelCard: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.04)",
    borderRadius: 14,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  hotelInfo: { flex: 1, marginRight: spacing.sm },
  hotelName: { fontFamily: typography.primary.semiBold, fontSize: 13, color: "#FFFFFF" },
  hotelStars: { fontFamily: typography.primary.normal, fontSize: 12, color: "rgba(255,255,255,0.5)", marginTop: 2 },
  hotelPrice: { fontFamily: typography.primary.bold, fontSize: 13, color: colors.palette.jadeGreen, textAlign: "right" },
  // CTAs
  ctaRow: {
    flexDirection: "row",
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    gap: spacing.sm,
  },
  ctaPrimary: { flex: 1, borderRadius: 16, overflow: "hidden" },
  ctaPrimaryGradient: { paddingVertical: 16, alignItems: "center" },
  ctaPrimaryText: { fontFamily: typography.primary.semiBold, fontSize: 15, color: "#FFFFFF" },
  ctaSecondary: {
    width: 56,
    height: 56,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.08)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.15)",
    justifyContent: "center",
    alignItems: "center",
  },
  ctaSecondaryText: { fontSize: 24 },
})