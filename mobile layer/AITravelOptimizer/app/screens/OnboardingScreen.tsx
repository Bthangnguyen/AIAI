/**
 * OnboardingScreen - TripFlow Welcome & Health Survey
 * Design: Glassmorphism + Modern Royal Hue Palette
 * Screens: Welcome slides + 3-question health survey
 */
import { useState, useRef, useEffect } from "react"
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
  Animated,
} from "react-native"
import { NativeStackScreenProps } from "@react-navigation/native-stack"
import { LinearGradient } from "expo-linear-gradient"
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
  icon: string
}

const SLIDES: OnboardingSlide[] = [
  {
    id: "1",
    title: "Khám Phá Huế\nTheo Cách Của Bạn",
    subtitle: "Trợ lý AI tối ưu lộ trình theo sức bền, tránh nắng nóng và tự động điều tuyến khi bạn đang trên đường.",
    imageUri: "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?auto=format&fit=crop&q=80&w=900",
    accentColor: colors.palette.imperialGold,
    icon: "🏯",
  },
  {
    id: "2",
    title: "Lộ Trình Thông Minh\nTối Ưu Thực Tế",
    subtitle: "Hệ thống tự động chèn điểm nghỉ, cảnh báo nắng gắt và gợi ý cơm hến, chè Huế đúng lúc.",
    imageUri: "https://images.unsplash.com/photo-1528360983277-13d401cdc186?auto=format&fit=crop&q=80&w=900",
    accentColor: colors.palette.jadeGreen,
    icon: "🗺️",
  },
  {
    id: "3",
    title: "Thuyết Minh AI\nGiọng Huế Ấm Áp",
    subtitle: "Nghe câu chuyện thâm cung bí sử về Triều Nguyễn khi đặt chân đến từng di tích lịch sử.",
    imageUri: "https://images.unsplash.com/photo-1563492065599-3520f775eeed?auto=format&fit=crop&q=80&w=900",
    accentColor: colors.palette.royalPurple,
    icon: "🎧",
  },
]

const SURVEY_QUESTIONS = [
  {
    id: "stamina",
    question: "Sức bền của bạn hôm nay?",
    icon: "⚡",
    options: [
      { label: "Thoải mái", value: "high", emoji: "💪", color: colors.palette.jadeGreen },
      { label: "Vừa sức", value: "medium", emoji: "😊", color: colors.palette.imperialGold },
      { label: "Thử thách", value: "low", emoji: "🐢", color: colors.palette.sunsetOrange },
    ],
  },
  {
    id: "companion",
    question: "Bạn đi cùng ai?",
    icon: "👥",
    options: [
      { label: "Một mình", value: "solo", emoji: "🧭", color: colors.palette.royalPurple },
      { label: "Cặp đôi", value: "couple", emoji: "💑", color: colors.palette.sunsetOrange },
      { label: "Gia đình", value: "family", emoji: "👨‍👩‍👧", color: colors.palette.jadeGreen },
    ],
  },
  {
    id: "heatPreference",
    question: "Muốn tránh nắng 12h-14h?",
    icon: "☀️",
    options: [
      { label: "Có, sợ nắng lắm!", value: "avoid", emoji: "🌂", color: colors.palette.jadeGreen },
      { label: "Bình thường", value: "normal", emoji: "😎", color: colors.palette.imperialGold },
    ],
  },
]

type Props = NativeStackScreenProps<AppStackParamList, "Onboarding">

type SurveyAnswers = {
  stamina?: string
  companion?: string
  heatPreference?: string
}

export const OnboardingScreen = ({ navigation }: Props) => {
  const [activeIndex, setActiveIndex] = useState(0)
  const [showSurvey, setShowSurvey] = useState(false)
  const [surveyStep, setSurveyStep] = useState(0)
  const [answers, setAnswers] = useState<SurveyAnswers>({})
  const flatListRef = useRef<FlatList>(null)
  const fadeAnim = useRef(new Animated.Value(1)).current
  const slideAnim = useRef(new Animated.Value(0)).current
  const pulseAnim = useRef(new Animated.Value(1)).current

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.05, duration: 1500, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 1500, useNativeDriver: true }),
      ])
    ).start()
  }, [])

  const animateTransition = (callback: () => void) => {
    Animated.timing(fadeAnim, { toValue: 0, duration: 200, useNativeDriver: true }).start(() => {
      callback()
      Animated.timing(fadeAnim, { toValue: 1, duration: 300, useNativeDriver: true }).start()
    })
  }

  const onScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const idx = Math.round(e.nativeEvent.contentOffset.x / width)
    setActiveIndex(idx)
  }

  const handleNext = () => {
    if (activeIndex < SLIDES.length - 1) {
      flatListRef.current?.scrollToIndex({ index: activeIndex + 1, animated: true })
    } else {
      animateTransition(() => setShowSurvey(true))
    }
  }

  const handleSurveyAnswer = (questionId: string, value: string) => {
    const newAnswers = { ...answers, [questionId]: value }
    setAnswers(newAnswers)
    if (surveyStep < SURVEY_QUESTIONS.length - 1) {
      animateTransition(() => setSurveyStep(surveyStep + 1))
    } else {
      navigation.navigate("Login")
    }
  }

  const renderSlide = ({ item }: { item: OnboardingSlide }) => (
    <View style={styles.slide}>
      <Image source={{ uri: item.imageUri }} style={styles.heroImage} resizeMode="cover" />
      <LinearGradient
        colors={["rgba(11,15,25,0)", "rgba(11,15,25,0.6)", "rgba(11,15,25,0.95)"]}
        style={styles.imageGradient}
      />
      <View style={styles.slideContent}>
        <View style={styles.iconBadge}>
          <Text style={styles.iconBadgeText}>{item.icon}</Text>
        </View>
        <Text style={styles.slideTitle}>{item.title}</Text>
        <Text style={styles.slideSubtitle}>{item.subtitle}</Text>
        <View style={[styles.accentBar, { backgroundColor: item.accentColor }]} />
      </View>
    </View>
  )

  const currentQuestion = SURVEY_QUESTIONS[surveyStep]

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />

      {/* LOGO HEADER */}
      <View style={styles.logoHeader}>
        <View style={styles.logoIconWrap}>
          <Text style={styles.logoIconText}>📍</Text>
        </View>
        <Text style={styles.logoText}>TripFlow</Text>
      </View>

      {!showSurvey ? (
        <>
          {/* Skip button */}
          <TouchableOpacity style={styles.skipBtn} onPress={() => navigation.navigate("Login")}>
            <Text style={styles.skipText}>Bỏ qua</Text>
          </TouchableOpacity>

          <FlatList
            ref={flatListRef}
            data={SLIDES}
            renderItem={renderSlide}
            keyExtractor={(item) => item.id}
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            onScroll={onScroll}
            scrollEventThrottle={16}
          />

          {/* Bottom bar */}
          <LinearGradient
            colors={["rgba(11,15,25,0)", "rgba(11,15,25,1)"]}
            style={styles.bottomGradient}
          >
            {/* Dot indicators */}
            <View style={styles.dots}>
              {SLIDES.map((_, i) => (
                <Animated.View
                  key={i}
                  style={[
                    styles.dot,
                    activeIndex === i ? styles.dotActive : styles.dotInactive,
                    activeIndex === i ? { transform: [{ scale: pulseAnim }] } : {},
                  ]}
                />
              ))}
            </View>

            {/* CTA Button */}
            <TouchableOpacity style={styles.ctaBtn} onPress={handleNext}>
              <LinearGradient
                colors={[colors.palette.royalPurple, colors.palette.royalPurpleLight]}
                style={styles.ctaBtnGradient}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
              >
                <Text style={styles.ctaBtnText}>
                  {activeIndex === SLIDES.length - 1 ? "Bắt Đầu Khám Phá ✨" : "Tiếp Theo →"}
                </Text>
              </LinearGradient>
            </TouchableOpacity>

            {/* Login link */}
            <TouchableOpacity onPress={() => navigation.navigate("Login")} style={styles.loginLink}>
              <Text style={styles.loginLinkText}>
                Đã có tài khoản?{" "}
                <Text style={styles.loginLinkBold}>Đăng nhập</Text>
              </Text>
            </TouchableOpacity>
          </LinearGradient>
        </>
      ) : (
        /* SURVEY SCREEN */
        <Animated.View style={[styles.surveyContainer, { opacity: fadeAnim }]}>
          <LinearGradient
            colors={[colors.palette.deepSlate, "#111827", "#1a0a2e"]}
            style={StyleSheet.absoluteFillObject}
          />

          {/* Progress indicator */}
          <View style={styles.surveyProgress}>
            {SURVEY_QUESTIONS.map((_, i) => (
              <View
                key={i}
                style={[
                  styles.progressDot,
                  i <= surveyStep ? styles.progressDotActive : styles.progressDotInactive,
                ]}
              />
            ))}
          </View>

          <Text style={styles.surveyIntro}>
            Câu {surveyStep + 1}/{SURVEY_QUESTIONS.length}
          </Text>

          <View style={styles.questionCard}>
            <Text style={styles.questionIcon}>{currentQuestion.icon}</Text>
            <Text style={styles.questionText}>{currentQuestion.question}</Text>
          </View>

          <View style={styles.optionsContainer}>
            {currentQuestion.options.map((opt) => (
              <TouchableOpacity
                key={opt.value}
                style={styles.optionCard}
                onPress={() => handleSurveyAnswer(currentQuestion.id, opt.value)}
              >
                <LinearGradient
                  colors={["rgba(255,255,255,0.08)", "rgba(255,255,255,0.04)"]}
                  style={styles.optionCardGradient}
                >
                  <View style={[styles.optionEmojiBubble, { backgroundColor: opt.color + "33" }]}>
                    <Text style={styles.optionEmoji}>{opt.emoji}</Text>
                  </View>
                  <Text style={styles.optionLabel}>{opt.label}</Text>
                  <View style={[styles.optionAccent, { backgroundColor: opt.color }]} />
                </LinearGradient>
              </TouchableOpacity>
            ))}
          </View>
        </Animated.View>
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.palette.deepSlate,
  },
  logoHeader: {
    position: "absolute",
    top: 52,
    left: spacing.lg,
    flexDirection: "row",
    alignItems: "center",
    zIndex: 20,
  },
  logoIconWrap: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: colors.palette.sunsetOrange,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 8,
  },
  logoIconText: { fontSize: 18 },
  logoText: {
    fontFamily: typography.primary.bold,
    fontSize: 20,
    color: "#FFFFFF",
    letterSpacing: 0.5,
  },
  skipBtn: {
    position: "absolute",
    top: 60,
    right: spacing.lg,
    zIndex: 20,
    paddingHorizontal: 16,
    paddingVertical: 6,
    backgroundColor: "rgba(255,255,255,0.12)",
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.2)",
  },
  skipText: {
    fontFamily: typography.primary.medium,
    fontSize: 13,
    color: "rgba(255,255,255,0.8)",
  },
  slide: {
    width,
    height,
    position: "relative",
  },
  heroImage: {
    width: "100%",
    height: "100%",
    position: "absolute",
  },
  imageGradient: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    height: "70%",
  },
  slideContent: {
    position: "absolute",
    bottom: 200,
    left: spacing.lg,
    right: spacing.lg,
  },
  iconBadge: {
    width: 56,
    height: 56,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.12)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.2)",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: spacing.md,
  },
  iconBadgeText: { fontSize: 28 },
  slideTitle: {
    fontFamily: typography.primary.bold,
    fontSize: 30,
    lineHeight: 42,
    color: "#FFFFFF",
    marginBottom: spacing.sm,
    letterSpacing: -0.5,
  },
  slideSubtitle: {
    fontFamily: typography.primary.normal,
    fontSize: 15,
    lineHeight: 24,
    color: "rgba(255,255,255,0.75)",
    marginBottom: spacing.md,
  },
  accentBar: {
    width: 48,
    height: 4,
    borderRadius: 2,
  },
  bottomGradient: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    paddingHorizontal: spacing.lg,
    paddingBottom: 40,
    paddingTop: 60,
  },
  dots: {
    flexDirection: "row",
    justifyContent: "center",
    marginBottom: spacing.lg,
    gap: 6,
  },
  dot: { height: 6, borderRadius: 3 },
  dotActive: {
    width: 28,
    backgroundColor: colors.palette.imperialGold,
  },
  dotInactive: {
    width: 8,
    backgroundColor: "rgba(255,255,255,0.3)",
  },
  ctaBtn: {
    borderRadius: 16,
    overflow: "hidden",
    marginBottom: spacing.md,
    shadowColor: colors.palette.royalPurple,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.5,
    shadowRadius: 16,
    elevation: 12,
  },
  ctaBtnGradient: {
    paddingVertical: 18,
    alignItems: "center",
  },
  ctaBtnText: {
    fontFamily: typography.primary.semiBold,
    fontSize: 16,
    color: "#FFFFFF",
    letterSpacing: 0.3,
  },
  loginLink: { alignItems: "center", paddingVertical: 8 },
  loginLinkText: {
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: "rgba(255,255,255,0.5)",
  },
  loginLinkBold: {
    fontFamily: typography.primary.semiBold,
    color: colors.palette.imperialGold,
  },
  // Survey styles
  surveyContainer: {
    flex: 1,
    paddingHorizontal: spacing.lg,
    paddingTop: 100,
  },
  surveyProgress: {
    flexDirection: "row",
    gap: 8,
    marginBottom: spacing.xl,
  },
  progressDot: {
    height: 4,
    flex: 1,
    borderRadius: 2,
  },
  progressDotActive: { backgroundColor: colors.palette.imperialGold },
  progressDotInactive: { backgroundColor: "rgba(255,255,255,0.15)" },
  surveyIntro: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: "rgba(255,255,255,0.5)",
    marginBottom: spacing.md,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  questionCard: {
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.12)",
    padding: spacing.xl,
    marginBottom: spacing.xl,
    alignItems: "center",
  },
  questionIcon: {
    fontSize: 40,
    marginBottom: spacing.md,
  },
  questionText: {
    fontFamily: typography.primary.semiBold,
    fontSize: 22,
    color: "#FFFFFF",
    textAlign: "center",
    lineHeight: 32,
  },
  optionsContainer: {
    gap: spacing.md,
  },
  optionCard: {
    borderRadius: 16,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.12)",
  },
  optionCardGradient: {
    flexDirection: "row",
    alignItems: "center",
    padding: spacing.md,
    gap: spacing.md,
  },
  optionEmojiBubble: {
    width: 48,
    height: 48,
    borderRadius: 14,
    justifyContent: "center",
    alignItems: "center",
  },
  optionEmoji: { fontSize: 22 },
  optionLabel: {
    fontFamily: typography.primary.semiBold,
    fontSize: 16,
    color: "#FFFFFF",
    flex: 1,
  },
  optionAccent: {
    width: 4,
    height: 32,
    borderRadius: 2,
  },
})