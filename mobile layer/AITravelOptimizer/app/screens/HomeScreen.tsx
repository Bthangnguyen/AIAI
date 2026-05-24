/**
 * HomeScreen - AI Co-Pilot Chat Center
 * Design: Glassmorphism dark + Royal Hue + Floating Chips
 */
import React, { FC, useState, useRef, useEffect } from "react"
import {
  View,
  StyleSheet,
  Pressable,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Animated,
  Dimensions,
  KeyboardAvoidingView,
  Platform,
  StatusBar,
} from "react-native"
import { Text } from "@/components/Text"
import type { AppStackScreenProps } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"

const { width } = Dimensions.get("window")

interface ChatMessage {
  sender: "user" | "ai"
  text: string
}

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

export const HomeScreen: FC<HomeScreenProps> = ({ navigation }) => {
  const [prompt, setPrompt] = useState("")
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const [micActive, setMicActive] = useState(false)
  const scrollRef = useRef<ScrollView>(null)
  const micScale = useRef(new Animated.Value(1)).current
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

  const handleSend = () => {
    const trimmed = prompt.trim()
    if (!trimmed) return
    setChatHistory((prev) => [...prev, { sender: "user", text: trimmed }])
    setPrompt("")
    setIsTyping(true)

    setTimeout(() => {
      const aiText = AI_SUGGESTIONS[Math.floor(Math.random() * AI_SUGGESTIONS.length)]
      setIsTyping(false)
      setChatHistory((prev) => [...prev, { sender: "ai", text: aiText }])
      setTimeout(() => {
        navigation.navigate("Loading", {
          prompt: trimmed,
          hotelName: "Pilgrimage Village",
          hotelLat: 16.4637,
          hotelLon: 107.5909,
          numDays: 3,
        })
      }, 1200)
    }, 1500)
  }

  const currentHour = new Date().getHours()
  const greeting =
    currentHour < 11 ? "Chào buổi sáng! ☀️" :
    currentHour < 14 ? "Giờ trưa, nghỉ ngơi tí 🌡️" :
    currentHour < 18 ? "Chiều mát rồi! 🌤️" : "Tối thơ mộng! 🌙"

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <LinearGradient
        colors={[colors.palette.deepSlate, "#111827", "#1a0a2e"]}
        style={StyleSheet.absoluteFillObject}
      />
      <View style={[styles.decorOrb, { top: -80, right: -80 }]} />
      <View style={[styles.decorOrb2, { bottom: 200, left: -60 }]} />

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={0}
      >
        {/* HEADER */}
        <View style={[styles.header, { paddingTop: insets.top + 8 }]}>
          <View style={styles.logoRow}>
            <View style={styles.logoIconWrap}>
              <Text style={styles.logoIconText}>📍</Text>
            </View>
            <Text style={styles.logoText}>TripFlow</Text>
          </View>
          <TouchableOpacity style={styles.notifBtn}>
            <Text style={styles.notifIcon}>🔔</Text>
          </TouchableOpacity>
        </View>

        {/* Greeting */}
        <View style={styles.greetSection}>
          <Text style={styles.greetText}>{greeting}</Text>
          <Text style={styles.greetSub}>Bạn muốn khám phá Huế thế nào hôm nay?</Text>
        </View>

        {/* Contextual Chips */}
        {chatHistory.length === 0 && (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.chipsScroll}
            style={styles.chipsContainer}
          >
            {CONTEXTUAL_CHIPS.map((chip, i) => (
              <TouchableOpacity key={i} style={styles.chip} onPress={() => setPrompt(chip)}>
                <LinearGradient
                  colors={["rgba(255,255,255,0.1)", "rgba(255,255,255,0.05)"]}
                  style={styles.chipGradient}
                >
                  <Text style={styles.chipText}>{chip}</Text>
                </LinearGradient>
              </TouchableOpacity>
            ))}
          </ScrollView>
        )}

        {/* Chat area */}
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
                <Text style={styles.aiAvatarText}>🤖</Text>
              </View>
              <Text style={styles.emptyStateTitle}>Xin chào! Tôi là TripFlow AI</Text>
              <Text style={styles.emptyStateSubtitle}>
                Hãy nói với tôi chuyến đi bạn mơ ước. Tôi sẽ tối ưu lộ trình theo sức bền, thời tiết và sở thích!
              </Text>
            </View>
          )}
          {chatHistory.map((msg, idx) => (
            <View key={idx} style={[styles.messageRow, msg.sender === "user" ? styles.messageRowUser : styles.messageRowAi]}>
              {msg.sender === "ai" && (
                <View style={styles.aiAvatarSmall}><Text style={{ fontSize: 16 }}>🤖</Text></View>
              )}
              <View style={msg.sender === "user" ? styles.userBubble : styles.aiBubble}>
                {msg.sender === "user" ? (
                  <LinearGradient
                    colors={[colors.palette.royalPurple, colors.palette.royalPurpleLight]}
                    style={styles.userBubbleGradient}
                    start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
                  >
                    <Text style={styles.userBubbleText}>{msg.text}</Text>
                  </LinearGradient>
                ) : (
                  <View style={styles.aiBubbleInner}>
                    <Text style={styles.aiBubbleText}>{msg.text}</Text>
                  </View>
                )}
              </View>
            </View>
          ))}
          {isTyping && (
            <View style={[styles.messageRow, styles.messageRowAi]}>
              <View style={styles.aiAvatarSmall}><Text style={{ fontSize: 16 }}>🤖</Text></View>
              <View style={styles.aiBubble}>
                <View style={styles.aiBubbleInner}>
                  <View style={styles.typingDots}>
                    <View style={[styles.typingDot, { opacity: 0.4 }]} />
                    <View style={[styles.typingDot, { opacity: 0.7 }]} />
                    <View style={[styles.typingDot, { opacity: 1 }]} />
                  </View>
                </View>
              </View>
            </View>
          )}
        </ScrollView>

        {/* Input glass card */}
        <View style={[styles.inputCard, { paddingBottom: insets.bottom + 12 }]}>
          <View style={styles.inputCardInner}>
            <TextInput
              value={prompt}
              onChangeText={setPrompt}
              placeholder="Nhập lịch trình bạn mơ ước..."
              placeholderTextColor="rgba(255,255,255,0.35)"
              style={styles.textInput}
              multiline
              maxLength={500}
            />
            <View style={styles.inputActions}>
              <Animated.View style={{ transform: [{ scale: micScale }] }}>
                <TouchableOpacity
                  style={[styles.micBtn, micActive && styles.micBtnActive]}
                  onPressIn={() => setMicActive(true)}
                  onPressOut={() => setMicActive(false)}
                >
                  <Text style={styles.micIcon}>🎤</Text>
                </TouchableOpacity>
              </Animated.View>
              <TouchableOpacity
                style={[styles.sendBtn, !prompt.trim() && styles.sendBtnDisabled]}
                onPress={handleSend}
                disabled={!prompt.trim()}
              >
                <LinearGradient
                  colors={prompt.trim() ? [colors.palette.royalPurple, colors.palette.royalPurpleLight] : ["rgba(255,255,255,0.08)", "rgba(255,255,255,0.04)"]}
                  style={styles.sendBtnGradient}
                >
                  <Text style={styles.sendBtnText}>→</Text>
                </LinearGradient>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </KeyboardAvoidingView>
    </View>
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
})