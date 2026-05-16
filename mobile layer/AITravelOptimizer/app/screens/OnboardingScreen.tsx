/**
 * OnboardingScreen — Figma "Start page 1/2/3" clone.
 * 3 full-screen slides with hero image, Poppins headings, dot indicators,
 * "Continue" CTA + "Nordic Vacation Sponsor" badge.
 */
import { useState, useRef } from "react"
import {
  View,
  Text,
  Dimensions,
  FlatList,
  NativeSyntheticEvent,
  NativeScrollEvent,
  StyleSheet,
  TouchableOpacity,
  Image,
  StatusBar,
  SafeAreaView,
  ScrollView,
} from "react-native"
import { NativeStackScreenProps } from "@react-navigation/native-stack"

import { CTAButton } from "@/components/CTAButton"
import { AppStackParamList } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

const { width, height } = Dimensions.get("window")

interface OnboardingSlide {
  id: string
  title: string
  subtitle: string
  imageUri: string
  accentColor: string
}

const SLIDES: OnboardingSlide[] = [
  {
    id: "1",
    title: "Make your own\nprivate travel plan",
    subtitle:
      "AI-powered itineraries crafted just for you — optimized routes, hidden gems, and real-time re-routing.",
    imageUri:
      "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&q=80&w=900",
    accentColor: "#68D6CA",
  },
  {
    id: "2",
    title: "Discover high-end\ntravel experiences",
    subtitle:
      "Curated POIs from local experts. From Imperial Citadels to hidden cafés — explore every corner.",
    imageUri:
      "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?auto=format&fit=crop&q=80&w=900",
    accentColor: "#2E60F4",
  },
  {
    id: "3",
    title: "Smart routes,\nperfect timing",
    subtitle:
      "Our OR-Tools solver finds the optimal path. No wasted time, maximum adventure in every day.",
    imageUri:
      "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&q=80&w=900",
    accentColor: "#FF6B35",
  },
]

type OnboardingScreenProps = NativeStackScreenProps<AppStackParamList, "Onboarding">

export const OnboardingScreen = ({ navigation }: OnboardingScreenProps) => {
  const [activeIndex, setActiveIndex] = useState(0)
  const flatListRef = useRef<FlatList>(null)

  const onScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const idx = Math.round(e.nativeEvent.contentOffset.x / width)
    setActiveIndex(idx)
  }

  const handleNext = () => {
    if (activeIndex < SLIDES.length - 1) {
      flatListRef.current?.scrollToIndex({ index: activeIndex + 1, animated: true })
    } else {
      navigation.navigate("Login")
    }
  }

  const handleSkip = () => navigation.navigate("Login")

  const renderItem = ({ item }: { item: OnboardingSlide }) => (
    <View style={styles.slide}>
      {/* Hero Image */}
      <Image source={{ uri: item.imageUri }} style={styles.heroImage} resizeMode="cover" />
      {/* Gradient overlay */}
      <View style={styles.imageOverlay} />

      {/* Content card */}
      <ScrollView
        contentContainerStyle={styles.contentCard}
        showsVerticalScrollIndicator={false}
        bounces={false}
      >
        {/* Sponsor badge */}
        <View style={styles.sponsorBadge}>
          <Text style={styles.sponsorText}>✈ AI Travel Optimizer</Text>
        </View>

        {/* Title */}
        <Text style={styles.title}>{item.title}</Text>

        {/* Subtitle */}
        <Text style={styles.subtitle}>{item.subtitle}</Text>

        {/* Accent line */}
        <View style={[styles.accentLine, { backgroundColor: item.accentColor }]} />
      </ScrollView>
    </View>
  )

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />

      {/* Skip button */}
      <TouchableOpacity style={styles.skipBtn} onPress={handleSkip}>
        <Text style={styles.skipText}>Skip</Text>
      </TouchableOpacity>

      <FlatList
        ref={flatListRef}
        data={SLIDES}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onScroll={onScroll}
        scrollEventThrottle={16}
      />

      {/* Bottom Controls */}
      <View style={styles.bottomBar}>
        {/* Dot indicators */}
        <View style={styles.dots}>
          {SLIDES.map((_, i) => (
            <View
              key={i}
              style={[
                styles.dot,
                activeIndex === i ? styles.dotActive : styles.dotInactive,
              ]}
            />
          ))}
        </View>

        {/* CTA Button */}
        <CTAButton
          label={activeIndex === SLIDES.length - 1 ? "Get Started 🚀" : "Continue →"}
          onPress={handleNext}
          style={styles.cta}
          testID="onboarding-cta"
        />

        {/* Login link */}
        <TouchableOpacity onPress={handleSkip} style={styles.loginLink}>
          <Text style={styles.loginLinkText}>
            Already have an account?{" "}
            <Text style={styles.loginLinkBold}>Sign in</Text>
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.palette.figmaBlack,
  },
  skipBtn: {
    position: "absolute",
    top: 52,
    right: spacing.lg,
    zIndex: 10,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xxs,
    backgroundColor: "rgba(255,255,255,0.15)",
    borderRadius: 20,
  },
  skipText: {
    fontFamily: typography.primary.medium,
    fontSize: 14,
    color: colors.palette.figmaWhite,
  },
  slide: {
    width,
    height,
    position: "relative",
  },
  heroImage: {
    width: "100%",
    height: "65%",
  },
  imageOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    height: "65%",
    backgroundColor: "rgba(0,0,0,0.25)",
  },
  contentCard: {
    flexGrow: 1,
    backgroundColor: colors.palette.figmaWhite,
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    marginTop: -30,
    paddingTop: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.lg,
  },
  sponsorBadge: {
    alignSelf: "flex-start",
    backgroundColor: colors.palette.figmaOffWhite,
    borderRadius: 20,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xxs,
    marginBottom: spacing.md,
  },
  sponsorText: {
    fontFamily: typography.primary.medium,
    fontSize: 12,
    color: colors.palette.figmaGrayMedium,
  },
  title: {
    fontFamily: typography.primary.bold,
    fontSize: 28,
    lineHeight: 38,
    color: colors.palette.figmaBlack,
    marginBottom: spacing.sm,
  },
  subtitle: {
    fontFamily: typography.primary.normal,
    fontSize: 15,
    lineHeight: 24,
    color: colors.palette.figmaGrayMedium,
    marginBottom: spacing.lg,
  },
  accentLine: {
    width: 48,
    height: 4,
    borderRadius: 2,
  },
  bottomBar: {
    backgroundColor: colors.palette.figmaWhite,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xl,
    paddingTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.palette.figmaGrayLight,
  },
  dots: {
    flexDirection: "row",
    justifyContent: "center",
    marginBottom: spacing.md,
    gap: spacing.xs,
  },
  dot: {
    height: 8,
    borderRadius: 4,
  },
  dotActive: {
    width: 28,
    backgroundColor: colors.palette.figmaPrimaryBlack,
  },
  dotInactive: {
    width: 8,
    backgroundColor: colors.palette.figmaGrayLight,
  },
  cta: {
    marginBottom: spacing.md,
  },
  loginLink: {
    alignItems: "center",
    paddingVertical: spacing.xxs,
  },
  loginLinkText: {
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: colors.palette.figmaGrayMedium,
  },
  loginLinkBold: {
    fontFamily: typography.primary.semiBold,
    color: colors.palette.figmaBlack,
  },
})
