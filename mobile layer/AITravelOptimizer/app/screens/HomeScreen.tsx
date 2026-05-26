import React, { FC, useState } from "react"
import { View, ViewStyle, TextStyle, ImageBackground, StyleSheet, Pressable, ScrollView } from "react-native"
import { Screen } from "@/components/Screen"
import { Text } from "@/components/Text"
import { TextField } from "@/components/TextField"
import type { AppStackScreenProps } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { LLMDataContract, ChatMessage } from "@/types/api"
import { TripService } from "@/services/api/tripService"

const { width } = Dimensions.get("window")

const CONTEXTUAL_CHIPS = [
  "🏯 Đại Nội Huế 1 ngày",
  "🛵 Tour xe máy lăng tẩm",
  "🌅 Chiều hoàng hôn Phá Tam Giang",
  "🍜 Cơm hến + bún bò sáng",
  "🎋 Vườn An Hiên thư thái",
  "☕ Trà cung đình chiều tà",
]

const AI_SUGGESTIONS = [
  "Tôi sẽ lập lịch ngay! Cho tôi biết bạn có bao nhiêu ngày và ngân sách khoảng bao nhiêu nhé? 🗺️",
  "Tuyệt vời! Đang phân tích tuyến đường tối ưu theo sức bền và thời tiết của bạn... ⚡",
  "Đã tìm thấy lộ trình phù hợp! 3 phương án đang được chuẩn bị - Balanced, Chill và Budget. 🎯",
]

interface HomeScreenProps extends AppStackScreenProps<"MainTabs"> {}

const BACKGROUND_URL = "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?q=80&w=2021&auto=format&fit=crop"

export const HomeScreen: FC<HomeScreenProps> = ({ navigation }) => {
  const [prompt, setPrompt] = useState("")
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])
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
  })
  const [isTyping, setIsTyping] = useState(false)
  const [isReady, setIsReady] = useState(false)
  const [micActive, setMicActive] = useState(false)
  const scrollRef = useRef<ScrollView>(null)
  const micScale = useRef(new Animated.Value(1)).current
  const ctaAnim = useRef(new Animated.Value(0)).current
  const insets = useSafeAreaInsets()

  useEffect(() => {
    if (micActive) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(micScale, { toValue: 1.2, duration: 600, useNativeDriver: true }),
          Animated.timing(micScale, { toValue: 1, duration: 600, useNativeDriver: true }),
        ])
      ).start()
    } else {
      micScale.setValue(1)
    }
  }, [micActive])

  useEffect(() => {
    Animated.spring(ctaAnim, {
      toValue: isReady ? 1 : 0,
      tension: 50,
      friction: 8,
      useNativeDriver: true,
    }).start()
  }, [isReady])

  const handleSend = async () => {
    const trimmed = prompt.trim()
    if (!trimmed) return

    // 1. Ghi nhận tin nhắn người dùng nhập vào khung chat
    const userMsg: ChatMessage = { role: "user", content: trimmed }
    setChatHistory((prev) => [...prev, userMsg])
    setPrompt("")
    setIsTyping(true)

    try {
      // 2. Gửi yêu cầu đàm thoại làm rõ hợp đồng du lịch lên Gateway
      const response = await TripService.processChat(
        trimmed,
        chatHistory,
        currentContract
      )

      setIsTyping(false)
      
      // 3. Cập nhật hợp đồng đã gộp trên Backend và thêm bong bóng trả lời của AI
      setCurrentContract(response.updated_contract)
      setChatHistory((prev) => [
        ...prev,
        { role: "assistant", content: response.reply },
      ])

      // 4. Nếu đàm thoại đạt trạng thái sẵn sàng (status === "ready"), tạm thời lưu lại state isReady (Task 3 sẽ dùng hiển thị nút bấm)
      if (response.status === "ready") {
        setIsReady(true)
      } else {
        setIsReady(false)
      }
    } catch (err) {
      setIsTyping(false)
      console.error("Chat API error:", err)
    }
  }

  const handleLaunchRouteSolver = () => {
    const parts: string[] = []
    parts.push(`Lập kế hoạch du lịch tại ${currentContract.destination || "Huế"}`)
    parts.push(`trong ${currentContract.num_days} ngày`)
    if (currentContract.budget_max) {
      parts.push(`với ngân sách tối đa là ${currentContract.budget_max.toLocaleString()} VND.`)
    } else {
      parts.push(`với ngân sách thoải mái.`)
    }
    if (currentContract.locked_pois && currentContract.locked_pois.length > 0) {
      parts.push(`Địa điểm bắt buộc ghé thăm: ${currentContract.locked_pois.join(", ")}.`)
    }
    if (currentContract.tags && currentContract.tags.length > 0) {
      parts.push(`Sở thích: ${currentContract.tags.join(", ")}.`)
    }

    const unifiedPrompt = parts.join(" ")

    navigation.navigate("Loading", {
      prompt: unifiedPrompt,
      hotelName: currentContract.hotel_name || "Pilgrimage Village",
      hotelLat: currentContract.hotel_lat || 16.4637,
      hotelLon: currentContract.hotel_lon || 107.5909,
      numDays: currentContract.num_days || 1,
    })
  }

  const handleChip = (chipText: string) => {
    setPrompt(chipText)
  }

  return (
    <Screen style={$root} preset="fixed" contentContainerStyle={{ flex: 1 }}>
      <ImageBackground source={{ uri: BACKGROUND_URL }} style={$background} blurRadius={8}>
        <View style={$overlay} />
        
        {/* Header */}
        <View style={$header}>
          <Text text="Bạn muốn đi đâu?" style={$titleHighlight} />
        </View>

        {/* Chat Area */}
        <ScrollView style={$chatArea} contentContainerStyle={{ paddingBottom: 20 }}>
          {chatHistory.length === 0 && (
            <View style={$welcomeContainer}>
              <Text text="Hãy trò chuyện để lên kế hoạch!" style={$heroSub} />
            </View>
          )}
          {chatHistory.map((msg, idx) => (
            <View key={idx} style={[styles.messageRow, msg.role === "user" ? styles.messageRowUser : styles.messageRowAi]}>
              {msg.role === "assistant" && (
                <View style={styles.aiAvatarSmall}><Text style={{ fontSize: 16 }}>🤖</Text></View>
              )}
              <View style={msg.role === "user" ? styles.userBubble : styles.aiBubble}>
                {msg.role === "user" ? (
                  <LinearGradient
                    colors={[colors.palette.royalPurple, colors.palette.royalPurpleLight]}
                    style={styles.userBubbleGradient}
                    start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
                  >
                    <Text style={styles.userBubbleText}>{msg.content}</Text>
                  </LinearGradient>
                ) : (
                  <View style={styles.aiBubbleInner}>
                    <Text style={styles.aiBubbleText}>{msg.content}</Text>
                  </View>
                )}
              </View>
            </View>
          ))}
        </ScrollView>

        {/* Nút bấm Royal CTA xuất hiện mượt mà khi isReady === true */}
        {isReady && (
          <Animated.View
            style={[
              styles.ctaWrapper,
              {
                opacity: ctaAnim,
                transform: [
                  {
                    translateY: ctaAnim.interpolate({
                      inputRange: [0, 1],
                      outputRange: [20, 0],
                    }),
                  },
                ],
              },
            ]}
          >
            <TouchableOpacity style={styles.ctaButton} onPress={handleLaunchRouteSolver}>
              <LinearGradient
                colors={[colors.palette.royalPurple, colors.palette.royalPurpleLight]}
                style={styles.ctaGradient}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
              >
                <Text style={styles.ctaButtonText}>🤖 Tạo Lộ Trình Tối Ưu Ngay ✨</Text>
              </LinearGradient>
            </TouchableOpacity>
          </Animated.View>
        )}

        {/* Input glass card */}
        <View style={[styles.inputCard, { paddingBottom: insets.bottom + 12 }]}>
          <View style={styles.inputCardInner}>
            <TextInput
              value={prompt}
              onChangeText={setPrompt}
              containerStyle={$inputContainer}
              style={$promptInput}
              placeholder="Nhập lịch trình bạn muốn..."
              placeholderTextColor={colors.palette.figmaPlaceholder}
              multiline
            />
            <Pressable onPress={handleSend} style={$sendButton}>
              <Text text="Gửi" style={$buttonText} />
            </Pressable>
          </View>
        </View>
      </ImageBackground>
    </Screen>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  decorOrb: {
    position: "absolute",
    width: 250,
    height: 250,
    borderRadius: 125,
    backgroundColor: colors.palette.royalPurple + "40",
  },
  decorOrb2: {
    position: "absolute",
    width: 200,
    height: 200,
    borderRadius: 100,
    backgroundColor: colors.palette.imperialGold + "20",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingBottom: 12,
  },
  logoRow: { flexDirection: "row", alignItems: "center" },
  logoIconWrap: {
    width: 34, height: 34, borderRadius: 10,
    backgroundColor: colors.palette.sunsetOrange,
    justifyContent: "center", alignItems: "center", marginRight: 8,
  },
  logoIconText: { fontSize: 16 },
  logoText: { fontFamily: typography.primary.bold, fontSize: 20, color: "#FFFFFF", letterSpacing: 0.3 },
  notifBtn: {
    width: 38, height: 38, borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.08)",
    justifyContent: "center", alignItems: "center",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
  },
  notifIcon: { fontSize: 18 },
  greetSection: { paddingHorizontal: spacing.lg, paddingBottom: spacing.md },
  greetText: { fontFamily: typography.primary.semiBold, fontSize: 24, color: "#FFFFFF", marginBottom: 4 },
  greetSub: { fontFamily: typography.primary.normal, fontSize: 14, color: "rgba(255,255,255,0.5)" },
  chipsContainer: { maxHeight: 60 },
  chipsScroll: { paddingHorizontal: spacing.lg, paddingBottom: 8, gap: 8, flexDirection: "row" },
  chip: { borderRadius: 20, overflow: "hidden", borderWidth: 1, borderColor: "rgba(255,255,255,0.15)" },
  chipGradient: { paddingHorizontal: 14, paddingVertical: 8 },
  chipText: { fontFamily: typography.primary.medium, fontSize: 13, color: "rgba(255,255,255,0.85)" },
  chatScroll: { flex: 1 },
  chatContent: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: spacing.lg, flexGrow: 1 },
  emptyState: { flex: 1, alignItems: "center", justifyContent: "center", paddingTop: 40, paddingHorizontal: 20 },
  aiAvatar: {
    width: 72, height: 72, borderRadius: 24,
    backgroundColor: "rgba(108,42,123,0.3)",
    borderWidth: 2, borderColor: "rgba(108,42,123,0.5)",
    justifyContent: "center", alignItems: "center", marginBottom: 16,
  },
  aiAvatarText: { fontSize: 36 },
  emptyStateTitle: { fontFamily: typography.primary.semiBold, fontSize: 18, color: "#FFFFFF", textAlign: "center", marginBottom: 10 },
  emptyStateSubtitle: { fontFamily: typography.primary.normal, fontSize: 14, color: "rgba(255,255,255,0.5)", textAlign: "center", lineHeight: 22 },
  messageRow: { flexDirection: "row", marginBottom: 12, alignItems: "flex-end" },
  messageRowUser: { justifyContent: "flex-end" },
  messageRowAi: { justifyContent: "flex-start" },
  aiAvatarSmall: {
    width: 32, height: 32, borderRadius: 10,
    backgroundColor: "rgba(108,42,123,0.3)",
    justifyContent: "center", alignItems: "center", marginRight: 8,
  },
  userBubble: { maxWidth: "80%", borderRadius: 16, overflow: "hidden" },
  userBubbleGradient: { paddingHorizontal: 14, paddingVertical: 10 },
  userBubbleText: { fontFamily: typography.primary.normal, fontSize: 14, color: "#FFFFFF", lineHeight: 20 },
  aiBubble: { maxWidth: "80%" },
  aiBubbleInner: {
    backgroundColor: "rgba(255,255,255,0.08)",
    borderRadius: 16, borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
    paddingHorizontal: 14, paddingVertical: 10,
  },
  aiBubbleText: { fontFamily: typography.primary.normal, fontSize: 14, color: "rgba(255,255,255,0.85)", lineHeight: 20 },
  typingDots: { flexDirection: "row", gap: 4, padding: 4 },
  typingDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.palette.imperialGold },
  inputCard: { paddingHorizontal: spacing.md, paddingTop: 8, borderTopWidth: 1, borderTopColor: "rgba(255,255,255,0.06)" },
  inputCardInner: {
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 20, borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
    flexDirection: "row", alignItems: "flex-end",
    paddingHorizontal: 16, paddingVertical: 10, gap: 8,
  },
  textInput: {
    flex: 1, fontFamily: typography.primary.normal, fontSize: 15, color: "#FFFFFF",
    minHeight: 40, maxHeight: 100, paddingTop: 0, paddingBottom: 0,
  },
  inputActions: { flexDirection: "row", alignItems: "center", gap: 8 },
  micBtn: {
    width: 40, height: 40, borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.08)",
    justifyContent: "center", alignItems: "center",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.15)",
  },
  micBtnActive: { backgroundColor: colors.palette.sunsetOrange + "40", borderColor: colors.palette.sunsetOrange },
  micIcon: { fontSize: 18 },
  sendBtn: { borderRadius: 12, overflow: "hidden" },
  sendBtnDisabled: { opacity: 0.5 },
  sendBtnGradient: { width: 40, height: 40, justifyContent: "center", alignItems: "center" },
  sendBtnText: { fontSize: 20, color: "#FFFFFF", fontFamily: typography.primary.bold },
  ctaWrapper: {
    paddingHorizontal: spacing.lg,
    paddingTop: 8,
    paddingBottom: 4,
    width: "100%",
  },
  ctaButton: {
    borderRadius: 16,
    overflow: "hidden",
    shadowColor: colors.palette.royalPurple,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  ctaGradient: {
    paddingVertical: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  ctaButtonText: {
    fontFamily: typography.primary.bold,
    fontSize: 15,
    color: "#FFFFFF",
    letterSpacing: 0.5,
  },
})