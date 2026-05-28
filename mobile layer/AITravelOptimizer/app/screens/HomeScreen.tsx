import React, { FC, useRef, useState, useEffect } from "react"
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StatusBar,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
  Animated,
  Easing,
} from "react-native"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"

import { AppIcon } from "@/components/AppIcon"
import { Text } from "@/components/Text"
import type { AppStackScreenProps } from "@/navigators/navigationTypes"
import { TripService } from "@/services/api/tripService"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { ChatMessage, LLMDataContract } from "@/types/api"

const CONTEXTUAL_CHIPS = [
  "Đại Nội Huế 1 ngày",
  "Tour xe máy lăng tẩm",
  "Chiều hoàng hôn Phá Tam Giang",
  "Cơm hến và bún bò sáng",
  "Vườn An Hiên thư thái",
  "Trà cung đình chiều tà",
]

interface HomeScreenProps extends AppStackScreenProps<"MainTabs"> {}

export const HomeScreen: FC<HomeScreenProps> = ({ navigation }) => {
  const insets = useSafeAreaInsets()
  const scrollRef = useRef<ScrollView>(null)
  const [prompt, setPrompt] = useState("")
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const [isReady, setIsReady] = useState(false)
  const [currentContract, setCurrentContract] = useState<LLMDataContract>({
    destination: undefined,
    budget_max: undefined,
    radius_km: 10,
    num_days: 1,
    tags: [],
    locked_pois: [],
    hotel_name: "Pilgrimage Village",
    hotel_lat: 16.4637,
    hotel_lon: 107.5909,
    confirmed_fields: [],
  })

  // ─── Gemini Aura Animations ──────────────────────────────────────────────────
  const orb1Scale = useRef(new Animated.Value(1)).current
  const orb1TransX = useRef(new Animated.Value(0)).current
  const orb1TransY = useRef(new Animated.Value(0)).current

  const orb2Scale = useRef(new Animated.Value(1)).current
  const orb2TransX = useRef(new Animated.Value(0)).current
  const orb2TransY = useRef(new Animated.Value(0)).current

  const sparkleRotate = useRef(new Animated.Value(0)).current
  const shimmerOpacity = useRef(new Animated.Value(0.4)).current
  const inputFocusAnim = useRef(new Animated.Value(0)).current

  useEffect(() => {
    // 1. Orb 1 Animation Loop
    Animated.loop(
      Animated.parallel([
        Animated.sequence([
          Animated.timing(orb1Scale, { toValue: 1.25, duration: 6000, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
          Animated.timing(orb1Scale, { toValue: 1, duration: 6000, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        ]),
        Animated.sequence([
          Animated.timing(orb1TransX, { toValue: 35, duration: 6000, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
          Animated.timing(orb1TransX, { toValue: 0, duration: 6000, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        ]),
        Animated.sequence([
          Animated.timing(orb1TransY, { toValue: -25, duration: 6000, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
          Animated.timing(orb1TransY, { toValue: 0, duration: 6000, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        ]),
      ])
    ).start()

    // 2. Orb 2 Animation Loop
    Animated.loop(
      Animated.parallel([
        Animated.sequence([
          Animated.timing(orb2Scale, { toValue: 1.2, duration: 8000, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
          Animated.timing(orb2Scale, { toValue: 1, duration: 8000, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        ]),
        Animated.sequence([
          Animated.timing(orb2TransX, { toValue: -30, duration: 8000, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
          Animated.timing(orb2TransX, { toValue: 0, duration: 8000, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        ]),
        Animated.sequence([
          Animated.timing(orb2TransY, { toValue: 40, duration: 8000, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
          Animated.timing(orb2TransY, { toValue: 0, duration: 8000, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        ]),
      ])
    ).start()

    // 3. Sparkle Rotation Loop
    Animated.loop(
      Animated.timing(sparkleRotate, {
        toValue: 1,
        duration: 4000,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    ).start()

    // 4. Shimmer opacity loop for loader
    Animated.loop(
      Animated.sequence([
        Animated.timing(shimmerOpacity, { toValue: 1, duration: 900, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(shimmerOpacity, { toValue: 0.4, duration: 900, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      ])
    ).start()
  }, [])

  const spinSparkle = sparkleRotate.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "360deg"],
  })

  // ─── API handlers ────────────────────────────────────────────────────────────
  const handleSend = async () => {
    const trimmed = prompt.trim()
    if (!trimmed) return

    const userMsg: ChatMessage = { role: "user", content: trimmed }
    const history = [...chatHistory, userMsg]
    setChatHistory(history)
    setPrompt("")
    setIsTyping(true)

    try {
      const response = await TripService.processChat(trimmed, chatHistory, currentContract)
      setCurrentContract(response.updated_contract)
      setChatHistory((prev) => [...prev, { role: "assistant", content: response.reply }])
      setIsReady(response.status === "ready")
    } catch (err: any) {
      Alert.alert("Lỗi kết nối", err?.message || "Không thể gửi yêu cầu lúc này.")
    } finally {
      setIsTyping(false)
    }
  }

  const handleLaunchRouteSolver = () => {
    const parts: string[] = []
    parts.push(`Lập kế hoạch du lịch tại ${currentContract.destination || "Huế"}`)
    parts.push(`trong ${currentContract.num_days || 1} ngày`)
    parts.push(
      currentContract.budget_max
        ? `với ngân sách tối đa ${currentContract.budget_max.toLocaleString()} VND.`
        : "với ngân sách thoải mái.",
    )
    if (currentContract.locked_pois?.length) {
      parts.push(`Địa điểm bắt buộc ghé thăm: ${currentContract.locked_pois.join(", ")}.`)
    }
    if (currentContract.tags?.length) {
      parts.push(`Sở thích: ${currentContract.tags.join(", ")}.`)
    }

    navigation.navigate("Loading", {
      prompt: parts.join(" "),
      hotelName: currentContract.hotel_name || "Pilgrimage Village",
      hotelLat: currentContract.hotel_lat || 16.4637,
      hotelLon: currentContract.hotel_lon || 107.5909,
      numDays: currentContract.num_days || 1,
      contract: currentContract,
    })
  }

  return (
    <View style={styles.root}>
      <StatusBar barStyle="dark-content" backgroundColor="transparent" translucent />
      
      {/* ─── Pulsing Aura Background Orbs (Gemini style) ──────────────────────── */}
      <Animated.View
        style={[
          styles.orb1,
          {
            transform: [
              { scale: orb1Scale },
              { translateX: orb1TransX },
              { translateY: orb1TransY },
            ],
          },
        ]}
      />
      <Animated.View
        style={[
          styles.orb2,
          {
            transform: [
              { scale: orb2Scale },
              { translateX: orb2TransX },
              { translateY: orb2TransY },
            ],
          },
        ]}
      />

      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === "ios" ? "padding" : "height"}>
        <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
          <View style={styles.logoRow}>
            <View style={styles.logoIconWrap}>
              <Animated.Text style={[styles.logoIconText, { transform: [{ rotate: spinSparkle }] }]}>✨</Animated.Text>
            </View>
            <View>
              <Text style={styles.logoText}>TripFlow</Text>
              <Text style={styles.logoSub}>AI travel optimizer</Text>
            </View>
          </View>
          <TouchableOpacity style={styles.iconButton}>
            <AppIcon name="bell" size={19} color={colors.palette.appOrangeDark} />
          </TouchableOpacity>
        </View>

        <View style={styles.hero}>
          <Text style={styles.greetText}>Lên lịch trình Huế thật gọn</Text>
          <Text style={styles.greetSub}>
            Nói mục tiêu chuyến đi, TripFlow sẽ tự động hỏi thêm khi thiếu dữ liệu và tối ưu tuyến đường cho bạn.
          </Text>
        </View>

        {chatHistory.length === 0 && (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.chipsScroll}
            style={styles.chipsContainer}
          >
            {CONTEXTUAL_CHIPS.map((chip) => (
              <TouchableOpacity key={chip} style={styles.chip} onPress={() => setPrompt(chip)}>
                <Text style={styles.chipText}>{chip}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        )}

        <ScrollView
          ref={scrollRef}
          style={styles.chatScroll}
          contentContainerStyle={styles.chatContent}
          showsVerticalScrollIndicator={false}
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
        >
          {chatHistory.length === 0 && (
            <View style={styles.emptyState}>
              <View style={styles.aiAvatar}>
                <Animated.View style={[styles.sparkleRing, { transform: [{ rotate: spinSparkle }] }]}>
                  <Text style={styles.aiSparkle}>✨</Text>
                </Animated.View>
                <AppIcon name="route" size={32} color={colors.palette.appOrangeDark} />
              </View>
              <Text style={styles.emptyStateTitle}>Bạn muốn đi theo kiểu nào?</Text>
              <Text style={styles.emptyStateSubtitle}>
                Ví dụ: “Tôi có 2 ngày ở Huế, thích di tích, ăn địa phương, đi nhẹ nhàng và tránh nắng buổi trưa.”
              </Text>
            </View>
          )}

          {chatHistory.map((msg, idx) => (
            <View key={`${msg.role}-${idx}`} style={[styles.messageRow, msg.role === "user" && styles.messageRowUser]}>
              {msg.role === "assistant" && (
                <View style={styles.aiAvatarSmall}>
                  <AppIcon name="route" size={16} color={colors.palette.appOrangeDark} />
                </View>
              )}
              <View style={msg.role === "user" ? styles.userBubble : styles.aiBubble}>
                <Text style={msg.role === "user" ? styles.userBubbleText : styles.aiBubbleText}>{msg.content}</Text>
              </View>
            </View>
          ))}

          {isTyping && (
            <View style={styles.messageRow}>
              <View style={styles.aiAvatarSmall}>
                <AppIcon name="route" size={16} color={colors.palette.appOrangeDark} />
              </View>
              <Animated.View style={[styles.aiBubble, styles.aiBubbleLoading, { opacity: shimmerOpacity }]}>
                <Text style={[styles.aiBubbleText, { fontStyle: "italic", color: colors.palette.appOrangeDark }]}>
                  TripFlow đang phân tích yêu cầu ✨
                </Text>
              </Animated.View>
            </View>
          )}
        </ScrollView>

        {isReady && (
          <TouchableOpacity style={styles.ctaButton} onPress={handleLaunchRouteSolver}>
            <LinearGradient
              colors={[colors.palette.appOrange, colors.palette.appOrangeDark]}
              style={styles.ctaGradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
            >
              <Text style={styles.ctaButtonText}>Tạo lộ trình tối ưu</Text>
            </LinearGradient>
          </TouchableOpacity>
        )}

        <View style={styles.inputCard}>
          <Animated.View style={[styles.inputCardInner, { borderColor: inputFocusAnim.interpolate({ inputRange: [0, 1], outputRange: [colors.palette.appLine, colors.palette.appOrange] }) }]}>
            <TextInput
              value={prompt}
              onChangeText={setPrompt}
              placeholder="Nhập lịch trình bạn mong muốn..."
              placeholderTextColor={colors.palette.appMuted}
              style={styles.textInput}
              multiline
              maxLength={500}
              onFocus={() => Animated.timing(inputFocusAnim, { toValue: 1, duration: 200, useNativeDriver: false }).start()}
              onBlur={() => Animated.timing(inputFocusAnim, { toValue: 0, duration: 200, useNativeDriver: false }).start()}
            />
            <TouchableOpacity
              style={[styles.sendBtn, !prompt.trim() && styles.sendBtnDisabled]}
              onPress={handleSend}
              disabled={!prompt.trim()}
            >
              <Text style={styles.sendBtnText}>→</Text>
            </TouchableOpacity>
          </Animated.View>
        </View>
      </KeyboardAvoidingView>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.palette.appCream, overflow: "hidden" },
  flex: { flex: 1 },
  orb1: {
    position: "absolute",
    top: -150,
    right: -150,
    width: 600,
    height: 600,
    borderRadius: 300,
    backgroundColor: "#E3D5FF", // Soft premium pastel lavender
    opacity: 0.08,
    zIndex: -1,
  },
  orb2: {
    position: "absolute",
    bottom: -150,
    left: -150,
    width: 700,
    height: 700,
    borderRadius: 350,
    backgroundColor: "#D5FFF6", // Soft premium pastel mint
    opacity: 0.06,
    zIndex: -1,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingBottom: 12,
  },
  logoRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  logoIconWrap: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: "rgba(255, 255, 255, 0.65)",
    borderWidth: 1.5,
    borderColor: "rgba(255, 255, 255, 0.9)",
    justifyContent: "center",
    alignItems: "center",
    ...Platform.select({
      web: {
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
      } as any
    }),
    shadowColor: "#1F2937",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.02,
    shadowRadius: 8,
    elevation: 2,
  },
  logoIconText: { fontSize: 20, color: colors.palette.appOrangeDark },
  logoText: { fontFamily: typography.primary.bold, fontSize: 20, color: colors.palette.appInk },
  logoSub: { fontFamily: typography.primary.medium, fontSize: 11, color: colors.palette.appMuted },
  iconButton: {
    width: 42,
    height: 42,
    borderRadius: 14,
    backgroundColor: "rgba(255, 255, 255, 0.7)",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.6)",
    shadowColor: "#1F2937",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.02,
    shadowRadius: 8,
    elevation: 1,
  },
  hero: { paddingHorizontal: spacing.lg, paddingTop: spacing.sm, paddingBottom: spacing.md },
  greetText: {
    fontFamily: typography.primary.bold,
    fontSize: 28,
    color: colors.palette.appInk,
    lineHeight: 36,
  },
  greetSub: {
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: colors.palette.appMuted,
    lineHeight: 22,
    marginTop: 8,
  },
  chipsContainer: { maxHeight: 52 },
  chipsScroll: { paddingHorizontal: spacing.lg, paddingBottom: 8, gap: 8, flexDirection: "row" },
  chip: {
    borderRadius: 999,
    backgroundColor: "rgba(255, 255, 255, 0.58)",
    borderWidth: 1.5,
    borderColor: "rgba(255, 255, 255, 0.9)",
    paddingHorizontal: 14,
    paddingVertical: 9,
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
    elevation: 1,
  },
  chipText: { fontFamily: typography.primary.medium, fontSize: 13, color: colors.palette.appOrangeDark },
  chatScroll: { flex: 1 },
  chatContent: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: spacing.lg, flexGrow: 1 },
  emptyState: { flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: spacing.md, gap: spacing.md },
  aiAvatar: {
    width: 82,
    height: 82,
    borderRadius: 26,
    backgroundColor: colors.palette.appOrangeSoft,
    borderWidth: 1,
    borderColor: "rgba(249, 115, 22, 0.2)",
    justifyContent: "center",
    alignItems: "center",
    position: "relative",
  },
  sparkleRing: {
    position: "absolute",
    top: -12,
    right: -12,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: "#FFFFFF",
    alignItems: "center",
    justifyContent: "center",
    elevation: 3,
    shadowColor: colors.palette.appOrangeDark,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
  },
  aiSparkle: { fontSize: 14 },
  emptyStateTitle: {
    fontFamily: typography.primary.bold,
    fontSize: 20,
    color: colors.palette.appInk,
    textAlign: "center",
  },
  emptyStateSubtitle: {
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: colors.palette.appMuted,
    textAlign: "center",
    lineHeight: 22,
  },
  messageRow: { flexDirection: "row", marginBottom: 12, alignItems: "flex-end" },
  messageRowUser: { justifyContent: "flex-end" },
  aiAvatarSmall: {
    width: 32,
    height: 32,
    borderRadius: 12,
    backgroundColor: colors.palette.appOrangeSoft,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 8,
  },
  userBubble: {
    maxWidth: "82%",
    borderRadius: 18,
    backgroundColor: colors.palette.appOrange,
    paddingHorizontal: 14,
    paddingVertical: 10,
    elevation: 2,
    shadowColor: colors.palette.appOrangeDark,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
  },
  userBubbleText: { fontFamily: typography.primary.normal, fontSize: 14, color: "#FFFFFF", lineHeight: 21 },
  aiBubble: {
    maxWidth: "82%",
    backgroundColor: "rgba(255, 255, 255, 0.58)",
    borderRadius: 18,
    borderWidth: 1.5,
    borderColor: "rgba(255, 255, 255, 0.9)",
    paddingHorizontal: 14,
    paddingVertical: 10,
    ...Platform.select({
      web: {
        backdropFilter: "blur(25px)",
        WebkitBackdropFilter: "blur(25px)",
      } as any
    }),
    shadowColor: "#1F2937",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.04,
    shadowRadius: 14,
    elevation: 2,
  },
  aiBubbleLoading: {
    borderColor: "rgba(249, 115, 22, 0.2)",
    backgroundColor: "rgba(255, 243, 232, 0.5)",
  },
  aiBubbleText: { fontFamily: typography.primary.normal, fontSize: 14, color: colors.palette.appInk, lineHeight: 21 },
  ctaButton: {
    marginHorizontal: spacing.lg,
    marginBottom: spacing.sm,
    borderRadius: 16,
    overflow: "hidden",
  },
  ctaGradient: { paddingVertical: 15, alignItems: "center", justifyContent: "center" },
  ctaButtonText: { fontFamily: typography.primary.bold, fontSize: 15, color: "#FFFFFF" },
  inputCard: {
    paddingHorizontal: spacing.md,
    paddingTop: 8,
    paddingBottom: Platform.OS === "ios" ? spacing.xl : spacing.md,
    borderTopWidth: 1,
    borderTopColor: "rgba(249, 115, 22, 0.12)",
    backgroundColor: "rgba(255, 255, 255, 0.85)",
  },
  inputCardInner: {
    backgroundColor: "rgba(255, 255, 255, 0.6)",
    borderRadius: 18,
    borderWidth: 1.5,
    borderColor: "rgba(255, 255, 255, 0.9)",
    flexDirection: "row",
    alignItems: "flex-end",
    paddingHorizontal: 14,
    paddingVertical: 10,
    gap: 8,
    ...Platform.select({
      web: {
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
      } as any
    }),
    shadowColor: "#1F2937",
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.04,
    shadowRadius: 16,
    elevation: 3,
  },
  textInput: {
    flex: 1,
    fontFamily: typography.primary.normal,
    fontSize: 15,
    color: colors.palette.appInk,
    minHeight: 40,
    maxHeight: 100,
    paddingTop: 0,
    paddingBottom: 0,
  },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: 13,
    backgroundColor: colors.palette.appOrange,
    justifyContent: "center",
    alignItems: "center",
  },
  sendBtnDisabled: { backgroundColor: colors.palette.appOrangePale },
  sendBtnText: { fontSize: 20, color: "#FFFFFF", fontFamily: typography.primary.bold },
})
