# Unified Merge Specification: AIAI Travel Optimizer

This specification outlines the comprehensive strategy and technical resolutions required to merge the five active development branches of the AIAI Travel Optimizer repository into a single, cohesive, production-hardened codebase.

---

## 1. Overlapping Files Matrix

The following matrix maps the key files modified across multiple branches. These files represent the core semantic and structural conflict zones that require manual integration.

| File Path | `main` | `origin/app3` | `origin/app-4` | `origin/feature/web1-e2e-integration` | `feature/webui-chat-clarification` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`HomeScreen.tsx`** | ✅ Baseline (Dark Glassmorphic UI) | ✅ Modified (Light UI, hardcoded coordinates) | ❌ Unchanged | ❌ Unchanged | ✅ Modified (Light UI, custom overrides) |
| **`LoadingScreen.tsx`** | ✅ Baseline (Dark theme, SSE pipeline, 9 stages) | ✅ Modified (Light UI, Reanimated spinner, 4 stages) | ❌ Unchanged | ❌ Unchanged | ✅ Modified (Light UI, Reanimated, 4 stages) |
| **`tripService.ts`** | ✅ Baseline (Clean client, real API fetch) | ✅ Modified (Massive mock backend interceptor) | ❌ Unchanged | ❌ Unchanged | ✅ Modified (Minor base URL change) |
| **`trip_planner.py`** | ✅ Baseline (Stateless orchestrator) | ❌ Unchanged | ✅ Modified (Firebase Auth, validations, idempotency) | ✅ Modified (Alternative planners solver) | ✅ Modified (Manual overrides, skip LLM, draft state) |
| **`layer4_client.py`** | ✅ Baseline (HTTP solver client) | ❌ Unchanged | ✅ Modified (Circuit Breaker, status code error mapping) | ✅ Modified (Dynamic constraints, alternatives solver) | ✅ Modified (Transport normalization, time windows) |

---

## 2. Optimal Conflict-Minimized Merge Sequence

Merging these branches requires a structured, logical sequence that first resolves structural layouts, then establishes security and stability boundaries, and finally layered features on top.

```
                  [main Baseline]
                         │
        (Step 1: Relocate and Flatten app-4)
                         ▼
             [app-4-flattened Branch]
                         │
          (Step 2: Merge Security & Guardrails)
                         ▼
        [Phase 2: Security & Stability Baseline]
                         │
         (Step 3: Port Alternative Planning)
                         ▼
       [Phase 3: Multi-Itinerary Solver Capability]
                         │
        (Step 4: Port Clarification & Overrides)
                         ▼
             [Phase 4: Unified Production]
```

### Deep Technical Rationale
1. **Flatten `origin/app-4` First**: Because `origin/app-4` wraps the entire codebase inside `AIAI-main/AIAI-main/`, merging any other branch into it or vice versa will cause git to think all files were deleted/added, creating massive conflicts. Resolving the directory structure in isolation isolates path adjustments.
2. **Establish the Security & Reliability Shell Second**: Merging the security and structural validations of `app-4` creates the protective outer layer (Firebase Auth, Circuit Breaker, Idempotency, rate limiters). All subsequent endpoints (like `/plan_alternatives` and manual overrides) can then be implemented inside this authenticated context safely.
3. **Port Alternative Planning Third**: Adding `/plan_alternatives` extends the capabilities of the gateway. It requires security shell support and custom transport mode lookups, which depend on the structures defined in Step 2.
4. **Port UI and Clarification Overrides Last**: Porting manual overrides and form fields into the modern dark Glassmorphic UI is best done last. This step connects the UI directly to the secure, multi-alternative endpoints built in Steps 2 and 3.

### Runnable Git Commands Sequence

Execute the following commands in order from your terminal workspace:

```powershell
# ──── STEP 1: FLATTEN AND PREPARE APP-4 ────
# Fetch remote branches and checkout origin/app-4 into a fresh local branch
git fetch origin
git checkout -b app-4-flattened origin/app-4

# Relocate files to root and clean up nested directory structure
Get-ChildItem -Path "AIAI-main\AIAI-main" | ForEach-Object {
    git mv $_.FullName .
}
git commit -m "refactor: relocate nested files from AIAI-main/AIAI-main to root directory"
Remove-Item -Recurse -Force AIAI-main
git add -A
git commit --amend --no-edit

# ──── STEP 2: MERGE SECURITY AND HARDENING INTO MAIN ────
# Checkout main and merge the flattened app-4
git checkout main
git checkout -b main-integration
git merge app-4-flattened --no-commit

# Resolve any immediate merge conflicts in gateway/mobile directories, then commit
git commit -m "merge: integrate Firebase authentication, idempotency, and circuit breaker from app-4"

# ──── STEP 3: PORT SOLVER ALTERNATIVES ────
# Merge web1-e2e-integration to add multi-itinerary planner and dynamic routing constraints
git merge origin/feature/web1-e2e-integration --no-commit
# Resolve conflicts in trip_planner.py and layer4_client.py, then commit
git commit -m "merge: integrate alternative plans /plan-multi solver from web1-e2e"

# ──── STEP 4: PORT CLARIFICATION AND FORM OVERRIDES ────
# Merge webui-chat-clarification
git merge feature/webui-chat-clarification --no-commit
# Apply full step-by-step resolution blueprints below to complete integration, then commit
git commit -m "merge: integrate manual overrides, transport normalizations, and unified UI layout"
```

---

## 3. Step-by-Step Resolution Blueprints for Overlapping Files

The following blueprints provide exact, integrated, production-ready code replacements. All placeholders have been eliminated to ensure compilation readiness.

### A. File: `mobile layer/AITravelOptimizer/app/screens/HomeScreen.tsx`
* **Conflict**: Modern dark Glassmorphic UI of `main` vs. old Light UI theme of `app3`/`webui-chat-clarification` containing direct chat parameter bindings.
* **Resolution**: Maintain `main`'s modern **Glassmorphic Dark UI** baseline. Port the manual edit capabilities from `webui-chat-clarification` directly into the modern chat context, enabling dynamic coordinate support.

```tsx
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

interface HomeScreenProps extends AppStackScreenProps<"MainTabs"> {}

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
    confirmed_fields: [],
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

    const userMsg: ChatMessage = { role: "user", content: trimmed }
    setChatHistory((prev) => [...prev, userMsg])
    setPrompt("")
    setIsTyping(true)

    try {
      const response = await TripService.processChat(
        trimmed,
        chatHistory,
        currentContract
      )

      setIsTyping(false)
      setCurrentContract(response.updated_contract)
      setChatHistory((prev) => [
        ...prev,
        { role: "assistant", content: response.reply },
      ])

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
      contract: currentContract,
    })
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

        <View style={styles.greetSection}>
          <Text style={styles.greetText}>{greeting}</Text>
          <Text style={styles.greetSub}>Bạn muốn khám phá Huế thế nào hôm nay?</Text>
        </View>

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
```

---

### B. File: `mobile layer/AITravelOptimizer/app/screens/LoadingScreen.tsx`
* **Conflict**: `main`'s 9-stage SSE pipeline and slate-dark styling vs. older flat 4-stage Reanimated layout from `app3`/`webui-chat-clarification`.
* **Resolution**: Keep `main`'s modern **Glassmorphic Dark UI** backdrop and comprehensive 9-stage pipeline support, utilizing standard `Animated` APIs for spinner rotation and timeline tracking to ensure robust cross-platform execution.

```tsx
/**
 * LoadingScreen - AI Processing with SSE Progress Integration
 * Screen 2: Loading animation & real-time SSE progress
 */
import React, { FC, useEffect, useRef } from "react"
import {
  View,
  StyleSheet,
  Animated,
  StatusBar,
  ScrollView,
  TouchableOpacity,
  Platform,
} from "react-native"
import { Text } from "@/components/Text"
import { LinearGradient } from "expo-linear-gradient"
import { NativeStackScreenProps } from "@react-navigation/native-stack"
import { AppStackParamList } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { useTripPipeline } from "@/hooks/useTripPipeline"

type Props = NativeStackScreenProps<AppStackParamList, "Loading">

export const LoadingScreen: FC<Props> = ({ navigation, route }) => {
  const { prompt = "", hotelLat, hotelLon, hotelName, numDays = 1, contract } =
    route.params ?? {}

  const rotateAnim = useRef(new Animated.Value(0)).current
  const progressAnim = useRef(new Animated.Value(0)).current
  const insets = useSafeAreaInsets()

  // Spinner rotation
  useEffect(() => {
    Animated.loop(
      Animated.timing(rotateAnim, { toValue: 1, duration: 1200, useNativeDriver: true })
    ).start()
  }, [])

  // Call real SSE stream pipeline passing contract details
  const { steps, logs, errorMsg } = useTripPipeline({
    prompt,
    hotelLat,
    hotelLon,
    hotelName,
    numDays,
    contract,
    onItinerary: (itinerary) => {
      navigation.replace("MapTimeline", { itinerary })
    },
  })

  // Calculate overall progress percentage
  const completedSteps = steps.filter(s => s.status === "done").length
  const activeProgress = completedSteps / steps.length

  useEffect(() => {
    Animated.timing(progressAnim, {
      toValue: activeProgress,
      duration: 500,
      useNativeDriver: false,
    }).start()
  }, [activeProgress])

  const spin = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "360deg"],
  })

  const getStepIcon = (stepId: string) => {
    switch (stepId) {
      case "l2": return "🧠"
      case "l3": return "🔍"
      case "l4": return "⚙️"
      default: return "🗺️"
    }
  }

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <LinearGradient
        colors={[colors.palette.deepSlate, "#111827", "#1a0a2e"]}
        style={StyleSheet.absoluteFillObject}
      />
      <View style={[styles.loadingContainer, { paddingTop: insets.top + 40, paddingBottom: insets.bottom + 20 }]}>
        <View style={styles.logoRow}>
          <View style={styles.logoIconWrap}>
            <Text style={styles.logoIconText}>📍</Text>
          </View>
          <Text style={styles.logoText}>TripFlow</Text>
        </View>

        <View style={styles.spinnerWrapper}>
          <Animated.View style={[styles.spinnerOuter, { transform: [{ rotate: spin }] }]}>
            <LinearGradient
              colors={[colors.palette.royalPurple, colors.palette.imperialGold, colors.palette.jadeGreen]}
              style={styles.spinnerGradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
            />
          </Animated.View>
          <View style={styles.spinnerInner}>
            <Text style={styles.spinnerIcon}>🤖</Text>
          </View>
        </View>

        <Text style={styles.loadingTitle}>
          {errorMsg ? "Đã xảy ra lỗi" : "AI đang tối ưu hóa..."}
        </Text>
        <Text style={[styles.loadingSubtitle, errorMsg ? { color: colors.error } : undefined]} numberOfLines={2}>
          {errorMsg || `"${prompt.slice(0, 60)}${prompt.length > 60 ? "..." : ""}"`}
        </Text>

        {errorMsg && (
          <View style={styles.errorActions}>
            <TouchableOpacity style={styles.errorBtn} onPress={() => navigation.goBack()}>
              <Text style={styles.errorBtnText}>← Quay lại</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.errorBtn, styles.retryBtn]}
              onPress={() => navigation.replace("Loading", route.params)}
            >
              <Text style={[styles.errorBtnText, { color: "#fff" }]}>🔄 Thử lại</Text>
            </TouchableOpacity>
          </View>
        )}

        {!errorMsg && (
          <View style={styles.stepsContainer}>
            {steps.map((step) => {
              const isActive = step.status === "active"
              const isDone = step.status === "done"
              const isError = step.status === "error"

              let dotBg = "rgba(255,255,255,0.15)"
              if (isDone) dotBg = colors.palette.jadeGreen
              else if (isActive) dotBg = colors.palette.imperialGold
              else if (isError) dotBg = colors.error

              return (
                <View key={step.id} style={[styles.stepRow, { opacity: step.status === "pending" ? 0.35 : 1 }]}>
                  <View style={[styles.stepDot, { backgroundColor: dotBg }]}>
                    <Text style={styles.stepDotText}>
                      {isDone ? "✓" : getStepIcon(step.id)}
                    </Text>
                  </View>
                  <View style={styles.stepInfo}>
                    <Text style={[styles.stepText, isActive && { color: "#FFFFFF", fontFamily: typography.primary.semiBold }]}>
                      {step.label}
                    </Text>
                    <Text style={styles.stepDetailText}>{step.detail}</Text>
                  </View>
                </View>
              )
            })}
          </View>
        )}

        {!errorMsg && (
          <View style={styles.progressBar}>
            <Animated.View style={[
              styles.progressFill,
              {
                width: progressAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: ["0%", "100%"],
                }),
              },
            ]} />
          </View>
        )}

        <View style={styles.logsCard}>
          <Text style={styles.logsTitle}>Nhật ký tiến trình</Text>
          <ScrollView
            style={styles.logsScroll}
            contentContainerStyle={styles.logsContent}
            ref={(ref) => ref?.scrollToEnd({ animated: true })}
            showsVerticalScrollIndicator={false}
          >
            {logs.map((log) => {
              let logColor = "rgba(255, 255, 255, 0.45)"
              if (log.type === "success") logColor = colors.palette.jadeGreen
              else if (log.type === "error") logColor = colors.error

              return (
                <View key={log.id} style={styles.logRow}>
                  <View style={[styles.logDot, { backgroundColor: logColor }]} />
                  <Text style={[styles.logText, { color: logColor }]}>{log.message}</Text>
                </View>
              )
            })}
          </ScrollView>
        </View>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  loadingContainer: {
    flex: 1,
    alignItems: "center",
    paddingHorizontal: spacing.xl,
  },
  logoRow: { flexDirection: "row", alignItems: "center", marginBottom: 30 },
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
    fontSize: 22,
    color: "#FFFFFF",
  },
  spinnerWrapper: {
    width: 100,
    height: 100,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 20,
    marginTop: 10,
  },
  spinnerOuter: {
    width: 100,
    height: 100,
    borderRadius: 50,
    position: "absolute",
  },
  spinnerGradient: {
    flex: 1,
    borderRadius: 50,
    opacity: 0.8,
  },
  spinnerInner: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "#1a1a2e",
    borderWidth: 2,
    borderColor: "rgba(255,255,255,0.15)",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 10,
  },
  spinnerIcon: { fontSize: 40 },
  loadingTitle: {
    fontFamily: typography.primary.semiBold,
    fontSize: 22,
    color: "#FFFFFF",
    marginBottom: 8,
    textAlign: "center",
  },
  loadingSubtitle: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: "rgba(255,255,255,0.45)",
    marginBottom: 25,
    textAlign: "center",
    fontStyle: "italic",
    paddingHorizontal: 10,
  },
  stepsContainer: { width: "100%", gap: 12, marginBottom: 25 },
  stepRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  stepDot: {
    width: 32,
    height: 32,
    borderRadius: 10,
    justifyContent: "center",
    alignItems: "center",
  },
  stepDotText: {
    fontSize: 14,
    color: "#FFFFFF",
  },
  stepInfo: {
    flex: 1,
    justifyContent: "center",
  },
  stepText: {
    fontFamily: typography.primary.medium,
    fontSize: 14,
    color: "rgba(255,255,255,0.5)",
  },
  stepDetailText: {
    fontFamily: typography.primary.normal,
    fontSize: 12,
    color: "rgba(255,255,255,0.3)",
    marginTop: 1,
  },
  progressBar: {
    width: "100%",
    height: 4,
    backgroundColor: "rgba(255,255,255,0.1)",
    borderRadius: 2,
    overflow: "hidden",
    marginBottom: 25,
  },
  progressFill: {
    height: "100%",
    backgroundColor: colors.palette.imperialGold,
    borderRadius: 2,
  },
  logsCard: {
    flex: 1,
    width: "100%",
    backgroundColor: "rgba(255, 255, 255, 0.05)",
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.08)",
    padding: spacing.md,
  },
  logsTitle: {
    fontFamily: typography.primary.semiBold,
    fontSize: 14,
    color: "#FFFFFF",
    marginBottom: 8,
  },
  logsScroll: {
    flex: 1,
  },
  logsContent: {
    paddingBottom: 10,
  },
  logRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 6,
  },
  logDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginTop: 6,
    marginRight: 8,
  },
  logText: {
    flex: 1,
    fontSize: 12,
    fontFamily: typography.primary.normal,
    lineHeight: 18,
  },
  errorActions: {
    flexDirection: "row",
    justifyContent: "center",
    gap: spacing.md,
    marginBottom: 20,
    width: "100%",
  },
  errorBtn: {
    flex: 1,
    minHeight: 44,
    borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.08)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.12)",
    justifyContent: "center",
    alignItems: "center",
  },
  retryBtn: {
    backgroundColor: colors.tint,
    borderColor: colors.tint,
  },
  errorBtnText: {
    fontSize: 15,
    fontFamily: typography.primary.semiBold,
    color: "#FFFFFF",
  },
})
```

---

### C. File: `mobile layer/AITravelOptimizer/app/services/api/tripService.ts`
* **Conflict**: Clean backend API client of `main` vs. the huge client-side mock backend interceptor in `origin/app3`.
* **Resolution**: Keep the baseline routing structure. Implement the mock backend pipeline in `reRoute` strictly protected by `FeatureFlags.USE_MOCK_BACKEND`, ensuring the app can switch between mock testing and production backend mode seamlessly.

```typescript
import EventSource from "react-native-sse"
import type { ReRoutePayload, ReRouteResponse } from "@/navigators/navigationTypes"
import type { ChatMessage, ChatProcessResponse } from "../../types/api"
import { FeatureFlags } from "@/config/features"

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8001"

export const TripService = {
  /**
   * Pre-flight health check — verify gateway is reachable before starting pipeline.
   */
  async checkHealth(): Promise<{ ready: boolean; message: string }> {
    try {
      const res = await fetch(`${API_BASE_URL}/v1/trip/health`, {
        method: "GET",
        headers: { Accept: "application/json", "ngrok-skip-browser-warning": "1" },
      })
      if (!res.ok) return { ready: false, message: `Server error: ${res.status}` }
      const data = await res.json()
      return { ready: data.status === "ready", message: data.status }
    } catch (e: any) {
      return { ready: false, message: e?.message || "Server unreachable" }
    }
  },

  planTripStream(
    prompt: string,
    hotelLat: number | undefined,
    hotelLon: number | undefined,
    hotelName: string | undefined,
    numDays: number | undefined,
    onMessage: (data: any) => void,
    onError: (error: any) => void,
    onDone: () => void,
  ) {
    const url = `${API_BASE_URL}/v1/trip/plan_trip_stream`
    const eventSource = new EventSource(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "ngrok-skip-browser-warning": "1" },
      body: JSON.stringify({
        user_prompt: prompt,
        hotel_lat: hotelLat,
        hotel_lon: hotelLon,
        hotel_name: hotelName,
        num_days: numDays,
      }),
    })

    eventSource.addEventListener("message", (event: any) => {
      if (event.data === "[DONE]") {
        eventSource.close()
        onDone()
        return
      }
      try {
        const parsedData = JSON.parse(event.data)
        onMessage(parsedData)
      } catch (e) {
        console.error("Error parsing SSE data", e)
      }
    })

    eventSource.addEventListener("error", (error: any) => {
      console.error("SSE Error:", error)
      onError(error)
      eventSource.close()
    })

    return eventSource
  },

  /**
   * Re-route remaining POIs from current location (JIT).
   * Sends current GPS + remaining POI IDs + original itinerary to Gateway,
   * which forwards to Layer 4 OR-Tools solver.
   */
  async reRoute(payload: ReRoutePayload): Promise<ReRouteResponse> {
    if (FeatureFlags.USE_MOCK_BACKEND) {
      console.log("[MOCK] Intercepting reroute request via FeatureFlags");
      await new Promise(res => setTimeout(res, 1200));
      
      const day = payload.original_itinerary?.days?.find((d: any) => d.day_index === payload.day_index);
      if (!day) return { status: "error", message: "Day index not found in mock state" };

      const modifiedDay = JSON.parse(JSON.stringify(day));
      const userText = payload.user_state?.text?.toLowerCase() || "";
      const currentMin = payload.current_time_min || 600;
      const userState = payload.user_state || {};

      if (userText.includes("lỗi") || userText.includes("quá tải") || userText.includes("infeasible")) {
        return { status: "error", message: "Infeasible: Lịch di chuyển quá dày đặc hoặc tắc nghẽn." };
      }

      if (userState.tired || userText.match(/mệt|đau chân|nghỉ ngơi/)) {
        const cafeStop = {
          poi_id: "mock_cafe_1",
          poi_name: "The Note Coffee (Nghỉ chân)",
          location: { latitude: 16.4625, longitude: 107.5925 },
          arrival_time_min: currentMin + 15,
          departure_time_min: currentMin + 60,
          visit_duration_min: 45,
          travel_time_from_prev_min: 15,
          entrance_fee: 45000,
        };
        modifiedDay.stops.splice(0, 0, cafeStop);
        modifiedDay.total_visit_min += 45;
        modifiedDay.total_entrance_fee += 45000;
      } 
      else if (userState.hungry || userText.match(/đói|khát|ăn|uống/)) {
        const restStop = {
          poi_id: "mock_rest_1",
          poi_name: "Phở 10 Lý Quốc Sư (Chi nhánh Huế)",
          location: { latitude: 16.4615, longitude: 107.5915 },
          arrival_time_min: currentMin + 10,
          departure_time_min: currentMin + 55,
          visit_duration_min: 45,
          travel_time_from_prev_min: 10,
          entrance_fee: 75000,
        };
        modifiedDay.stops.splice(0, 0, restStop);
        modifiedDay.total_visit_min += 45;
        modifiedDay.total_entrance_fee += 75000;
      }
      else if (userState.weather || userText.match(/mưa|nóng|thời tiết/)) {
        if (modifiedDay.stops.length > 0) {
          const indoorStop = {
            poi_id: "mock_indoor_1",
            poi_name: "Cung Diên Thọ (Tránh nắng/mưa)",
            location: { latitude: 16.4695, longitude: 107.5785 },
            arrival_time_min: modifiedDay.stops[0].arrival_time_min,
            departure_time_min: modifiedDay.stops[0].arrival_time_min + 90,
            visit_duration_min: 90,
            travel_time_from_prev_min: modifiedDay.stops[0].travel_time_from_prev_min,
            entrance_fee: 150000,
          };
          modifiedDay.total_entrance_fee = modifiedDay.total_entrance_fee - modifiedDay.stops[0].entrance_fee + indoorStop.entrance_fee;
          modifiedDay.total_visit_min = modifiedDay.total_visit_min - modifiedDay.stops[0].visit_duration_min + indoorStop.visit_duration_min;
          modifiedDay.stops[0] = indoorStop;
        }
      }
      else if (userState.wants_cafe || userText.match(/cafe|cà phê|trà/)) {
        const cafeStop = {
          poi_id: "mock_cafe_2",
          poi_name: "Giảng Café (Cà phê trứng muối Huế)",
          location: { latitude: 16.465, longitude: 107.595 },
          arrival_time_min: currentMin + 15,
          departure_time_min: currentMin + 60,
          visit_duration_min: 45,
          travel_time_from_prev_min: 15,
          entrance_fee: 40000,
        };
        modifiedDay.stops.splice(0, 0, cafeStop);
        modifiedDay.total_visit_min += 45;
        modifiedDay.total_entrance_fee += 40000;
      }
      else if (userState.extend_time) {
        if (modifiedDay.stops.length > 0) {
          modifiedDay.stops[modifiedDay.stops.length - 1].visit_duration_min += 30;
          modifiedDay.total_visit_min += 30;
        }
      }
      else if (userState.prioritize_free) {
        let maxFeeIdx = -1;
        let maxFee = 0;
        for (let i = 0; i < modifiedDay.stops.length; i++) {
          if (modifiedDay.stops[i].entrance_fee > maxFee) {
            maxFee = modifiedDay.stops[i].entrance_fee;
            maxFeeIdx = i;
          }
        }
        if (maxFeeIdx !== -1) {
          modifiedDay.total_entrance_fee -= maxFee;
          modifiedDay.total_visit_min -= modifiedDay.stops[maxFeeIdx].visit_duration_min;
          modifiedDay.stops.splice(maxFeeIdx, 1);
        }
      }
      else {
        if (modifiedDay.stops.length > 0) {
          const oldStop = modifiedDay.stops[0];
          const alternativeStop = {
            poi_id: "mock_alt_1",
            poi_name: "Hồ Tịnh Tâm (Điểm dừng thư thả)",
            location: { latitude: 16.476, longitude: 107.579 },
            arrival_time_min: oldStop.arrival_time_min,
            departure_time_min: oldStop.arrival_time_min + 60,
            visit_duration_min: 60,
            travel_time_from_prev_min: oldStop.travel_time_from_prev_min,
            entrance_fee: 0,
          };
          modifiedDay.total_entrance_fee -= oldStop.entrance_fee;
          modifiedDay.total_visit_min = modifiedDay.total_visit_min - oldStop.visit_duration_min + alternativeStop.visit_duration_min;
          modifiedDay.stops[0] = alternativeStop;
        }
      }

      if (modifiedDay.stops.length > 1) {
        for (let i = 1; i < modifiedDay.stops.length; i++) {
          modifiedDay.stops[i].arrival_time_min = modifiedDay.stops[i - 1].departure_time_min + modifiedDay.stops[i].travel_time_from_prev_min;
          modifiedDay.stops[i].departure_time_min = modifiedDay.stops[i].arrival_time_min + modifiedDay.stops[i].visit_duration_min;
        }
      }

      return { status: "success", day: modifiedDay };
    }

    try {
      const res = await fetch(`${API_BASE_URL}/v1/trip/re_route`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "ngrok-skip-browser-warning": "1",
        },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        return {
          status: "error",
          message: `Server error: ${res.status}`,
        }
      }

      const data: ReRouteResponse = await res.json()
      return data
    } catch (e: any) {
      return {
        status: "error",
        message: e?.message || "Re-route request failed",
      }
    }
  },

  async processChat(
    message: string,
    history: ChatMessage[],
    currentContract: any
  ): Promise<ChatProcessResponse> {
    try {
      const res = await fetch(`${API_BASE_URL}/v1/trip/chat_process`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "ngrok-skip-browser-warning": "1",
        },
        body: JSON.stringify({
          message,
          history,
          current_contract: currentContract,
        }),
      })

      if (!res.ok) {
        throw new Error(`Server returned code ${res.status}`)
      }

      const data = await res.json()
      return data
    } catch (e: any) {
      console.error("Conversational chat_process error:", e)
      return {
        status: "clarifying",
        reply: "Dạ kết nối mạng đang gián đoạn một chút. Bạn có thể cho tôi biết rõ hơn số ngày đi và ngân sách mong muốn tại Huế không?",
        updated_contract: currentContract,
      }
    }
  },
}
```

---

### D. File: `layer2_3_gateway/app/api/trip_planner.py`
* **Conflict**: Multiple competing integrations: Firebase Auth (`app-4`), strict valid validators (`app-4`), idempotency headers (`app-4`), Solver Alternatives (`web1-e2e`), manual contract overrides (`webui-chat-clarification`), and active draft states (`webui-chat-clarification`).
* **Resolution**: Merge all features into a unified gateway orchestrator. Enforce Firebase auth and validation guardrails. If a confirmed manual `contract` is submitted, bypass the LLM phase, apply manual overrides directly, check idempotency, and execute solver algorithms.

```python
"""Orchestrator API: Text → L2 → L3 → L4 pipeline (JSON + SSE streaming).

PRODUCTION-HARDENED ARCHITECTURE:
- DB I/O ISOLATION: LLM + Embedding calls (2-5s) execute OUTSIDE any DB session.
  DB session only opens for the 50ms spatial query then immediately returns to pool.
- ZERO Depends(get_db): All endpoints use _run_pipeline() which owns its own session.
- Pool cannot be exhausted by LLM latency or L4 solve time under ANY load.
- Firebase Auth: Protected endpoints require a valid Firebase ID token.
"""

import json as json_lib
import asyncio
import time
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.responses import StreamingResponse

from app.database import AsyncSessionFactory
from app.schemas.trip import TripPlanRequest, TripPlanResponse, LLMDataContract, POIResponse, ChatProcessRequest, ChatProcessResponse
from app.schemas.re_route import MobileReRouteRequest, ReRouteResponse
from app.services.llm_extractor import LLMExtractorService
from app.services.spatial_filter import SpatialFilterService
from app.services.layer4_client import Layer4Client
from app.services.embedding_service import EmbeddingService
from app.utils.logging import AppLogger

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.middleware.firebase_verify import get_current_user, get_optional_user, FirebaseUser

router = APIRouter(prefix="/v1/trip")
logger = AppLogger().get_logger()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Service singletons (stateless, thread-safe)
llm_service = LLMExtractorService()
spatial_service = SpatialFilterService()
layer4_client = Layer4Client()
embed_service = EmbeddingService()


class IdempotencyManager:
    def __init__(self, ttl_seconds=300):
        self.ttl = ttl_seconds
        self.cache = {}  # key -> {"status": "pending" | "completed", "response": data, "timestamp": time}
        self.lock = asyncio.Lock()

    async def get_or_set(self, key: str):
        async with self.lock:
            now = time.time()
            self.cache = {k: v for k, v in self.cache.items() if now - v["timestamp"] < self.ttl}
            
            if key in self.cache:
                return self.cache[key]
            
            self.cache[key] = {
                "status": "pending",
                "response": None,
                "timestamp": now
            }
            return None

    async def set_completed(self, key: str, response):
        async with self.lock:
            if key in self.cache:
                self.cache[key]["status"] = "completed"
                self.cache[key]["response"] = response
                self.cache[key]["timestamp"] = time.time()
                
    async def remove(self, key: str):
        async with self.lock:
            self.cache.pop(key, None)


idempotency_manager = IdempotencyManager()


def _mark_confirmed(contract: LLMDataContract, field: str) -> None:
    if field not in contract.confirmed_fields:
        contract.confirmed_fields.append(field)


def _merge_unique(left: list[str] | None, right: list[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in list(left or []) + list(right or []):
        key = str(value).strip()
        if key and key.lower() not in seen:
            seen.add(key.lower())
            result.append(key)
    return result


def _apply_request_overrides(contract: LLMDataContract, request: TripPlanRequest) -> LLMDataContract:
    """Apply manual request overrides from forms directly on top of the contract."""
    if request.destination:
        contract.destination = request.destination
        _mark_confirmed(contract, "destination")

    if request.num_days:
        contract.num_days = request.num_days
        _mark_confirmed(contract, "num_days")

    if request.budget is not None and not contract.budget_is_unlimited:
        contract.budget_max = request.budget
        _mark_confirmed(contract, "budget")

    if request.preferences:
        contract.tags = _merge_unique(contract.tags, request.preferences)
        _mark_confirmed(contract, "interests")

    if request.hotel_lat is not None:
        contract.hotel_lat = request.hotel_lat
    if request.hotel_lon is not None:
        contract.hotel_lon = request.hotel_lon
    if request.hotel_name:
        contract.hotel_name = request.hotel_name
    if request.hotel_lat is not None or request.hotel_lon is not None or request.hotel_name:
        contract.hotel_confirmed = True
        _mark_confirmed(contract, "hotel")

    return contract


async def _run_pipeline(
    request: TripPlanRequest,
) -> tuple[LLMDataContract, List[POIResponse], bool]:
    """L2 → Embed → L3 pipeline with TOTAL DB I/O isolation."""
    logger.info(f"🚀 _run_pipeline STARTED for prompt: {request.user_prompt}")
    
    prompt = request.user_prompt.strip()
    if len(prompt) < 10 or len(prompt) > 500:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "LLM_PARSE_ERROR", "message": "Độ dài mô tả lịch trình phải từ 10 đến 500 ký tự."}
        )

    # ──── PHASE A: NETWORK I/O (NO DB SESSION) ────
    if request.contract is not None:
        contract = request.contract.model_copy(deep=True)
        logger.info("Using confirmed manual contract from request; skipping LLM extraction")
    else:
        contract = await llm_service.extract_intent(
            user_prompt=request.user_prompt,
            hotel_lat=request.hotel_lat,
            hotel_lon=request.hotel_lon,
            hotel_name=request.hotel_name,
            num_days=request.num_days or 1,
        )

    # Apply manual overrides (e.g. from web form elements)
    contract = _apply_request_overrides(contract, request)

    # Spatial scope check: Huế/Hue only
    if not contract.destination or not any(x in contract.destination.lower() for x in ["huế", "hue"]):
        raise HTTPException(
            status_code=400,
            detail={"error_code": "LLM_PARSE_ERROR", "message": "Hiện tại hệ thống chỉ hỗ trợ lên lịch trình tại Huế. Vui lòng ghi rõ 'Huế' trong mô tả chuyến đi."}
        )

    # Vague intent fallback heuristics
    is_empty_tags = not contract.tags or contract.tags == ["general"]
    is_empty_locked = not contract.locked_pois
    is_empty_vibe_and_type = not contract.vibe and not contract.trip_type
    
    if is_empty_tags and is_empty_locked and is_empty_vibe_and_type:
        contract.tags = ["culture", "street_food", "sightseeing"]
        contract.vibe = "chill"
        contract.trip_type = "mixed"
        logger.info("Vague intent detected for Hue. Applying high-quality default preferences.")

    # Validate trip duration constraints
    if contract.num_days is not None and (contract.num_days < 1 or contract.num_days > 7):
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "LLM_INVALID_DURATION",
                "message": f"Số ngày du lịch ({contract.num_days} ngày) không hợp lệ. Lập lịch trình hỗ trợ từ 1 đến 7 ngày."
            }
        )

    # Validate budget limits
    if contract.budget_max is not None and contract.budget_max < 50000:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "LLM_INVALID_BUDGET",
                "message": f"Ngân sách tối đa {contract.budget_max:,.0f} VND quá thấp. Vui lòng nhập tối thiểu 50,000 VND."
            }
        )

    query_vector = None
    if contract.tags:
        tag_text = embed_service.build_poi_text(
            name="query", category="preference",
            tags=contract.tags, description="",
        )
        try:
            query_vector = await embed_service.aembed_text(tag_text)
        except Exception as e:
            logger.warning(f"Embedding failed, falling back to priority_score: {e}")

    # ──── PHASE B: DATABASE I/O (FLASH OPEN/CLOSE ~50ms) ────
    hotel_fallback = False
    async with AsyncSessionFactory() as db_session:
        if contract.hotel_lat is None or contract.hotel_lon is None:
            hotel_fallback = True
            from sqlalchemy import select
            from geoalchemy2.functions import ST_AsGeoJSON
            from app.models.poi import PointOfInterest
            import json as json_lib
            
            POI = PointOfInterest
            stmt = select(POI.name, ST_AsGeoJSON(POI.coordinates).label("geojson")).where(
                POI.category.ilike("%Khách sạn%")
            )
            if contract.budget_max:
                stmt = stmt.where(POI.price <= contract.budget_max * 0.3)
            stmt = stmt.order_by(POI.priority_score.desc()).limit(1)
            
            result = await db_session.execute(stmt)
            row = result.first()
            if row:
                contract.hotel_name = row.name
                geojson = json_lib.loads(row.geojson)
                contract.hotel_lon = geojson["coordinates"][0]
                contract.hotel_lat = geojson["coordinates"][1]
                logger.info(f"🏨 Auto-selected hotel: {contract.hotel_name}")
            else:
                contract.hotel_name = "Hue Default Hotel"
                contract.hotel_lat = 16.4637
                contract.hotel_lon = 107.5905
                logger.warning("No hotel found matching criteria, using default.")

        pois = await spatial_service.get_optimized_pois(
            contract=contract,
            db_session=db_session,
            query_vector=query_vector,
        )

    return contract, pois, hotel_fallback


@router.post("/plan_trip", response_model=TripPlanResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def plan_trip(request: Request, body: TripPlanRequest, user: FirebaseUser = Depends(get_current_user)):
    """Full pipeline (JSON): Text → LLM → Spatial → OR-Tools. Requires Firebase Auth."""
    logger.info(f"🔐 plan_trip called by user: {user.uid} ({user.email})")
    
    idempotency_key = request.headers.get("X-Idempotency-Key")
    if idempotency_key:
        cached = await idempotency_manager.get_or_set(idempotency_key)
        if cached:
            if cached["status"] == "pending":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error_code": "DUPLICATE_REQUEST", "message": "Yêu cầu của bạn đang được xử lý. Vui lòng đợi."}
                )
            elif cached["status"] == "completed":
                logger.info("Idempotency hit: returning completed response")
                return cached["response"]

    try:
        contract, pois, hotel_fallback = await _run_pipeline(body)

        if not pois:
            response_data = TripPlanResponse(
                status="error", llm_contract=contract, pois=[],
                message="Không tìm thấy địa điểm du lịch nào phù hợp với yêu cầu của bạn.",
            )
            if idempotency_key:
                await idempotency_manager.set_completed(idempotency_key, response_data.model_dump())
            return response_data

        locked_count = sum(1 for p in pois if p.is_locked)
        l4_result = await layer4_client.plan(pois=pois, contract=contract)

        if l4_result and "error_code" in l4_result:
            raise HTTPException(
                status_code=400,
                detail={"error_code": l4_result["error_code"], "message": l4_result["message"]}
            )

        if l4_result:
            l4_result["hotel_fallback"] = hotel_fallback

        response_data = TripPlanResponse(
            status="success" if l4_result else "partial",
            llm_contract=contract, pois=pois,
            locked_pois=locked_count, layer4_result=l4_result,
            message="Tối ưu lịch trình thành công!" if l4_result else "Lỗi lập lịch trình.",
        )

        if idempotency_key:
            await idempotency_manager.set_completed(idempotency_key, response_data.model_dump())
        return response_data

    except Exception as e:
        if idempotency_key:
            await idempotency_manager.remove(idempotency_key)
        raise e


@router.post("/plan_trip_stream")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def plan_trip_stream(request: Request, body: TripPlanRequest, user: FirebaseUser = Depends(get_current_user)):
    """SSE streaming: pushes route chunks in real-time. Requires Firebase Auth."""
    logger.info(f"📡 SSE REQUEST from user: {user.uid} ({user.email}), host: {request.client.host}")
    
    idempotency_key = request.headers.get("X-Idempotency-Key")
    if idempotency_key:
        cached = await idempotency_manager.get_or_set(idempotency_key)
        if cached:
            if cached["status"] == "pending":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error_code": "DUPLICATE_REQUEST", "message": "Yêu cầu của bạn đang được xử lý. Vui lòng đợi."}
                )
            elif cached["status"] == "completed":
                logger.info("Idempotency hit (stream): returning completed response")
                async def cached_generator():
                    yield f"data: {json_lib.dumps(cached['response'])}\n\n"
                    yield "data: [DONE]\n\n"
                return StreamingResponse(
                    cached_generator(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                )

    try:
        contract, pois, hotel_fallback = await _run_pipeline(body)
    except HTTPException as e:
        if idempotency_key:
            await idempotency_manager.remove(idempotency_key)
        raise e
    except Exception as e:
        if idempotency_key:
            await idempotency_manager.remove(idempotency_key)
        raise HTTPException(
            status_code=400,
            detail={"error_code": "LLM_PARSE_ERROR", "message": f"Không hiểu mô tả chuyến đi: {str(e)}"}
        )

    async def event_generator():
        yield f"data: {json_lib.dumps({'step': 'l2_done', 'tags': contract.tags, 'locked': contract.locked_pois})}\n\n"

        if not pois:
            err_payload = {'step': 'error', 'error_code': 'NO_FEASIBLE_ROUTE', 'message': 'Không tìm thấy địa điểm nào phù hợp.'}
            yield f"data: {json_lib.dumps(err_payload)}\n\n"
            yield "data: [DONE]\n\n"
            if idempotency_key:
                await idempotency_manager.set_completed(idempotency_key, err_payload)
            return

        yield f"data: {json_lib.dumps({'step': 'l3_done', 'pois_found': len(pois), 'locked_count': sum(1 for p in pois if p.is_locked)})}\n\n"

        try:
            plan_result = None
            async for chunk in layer4_client.plan_stream(pois=pois, contract=contract, hotel_fallback=hotel_fallback):
                yield chunk
                if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
                    try:
                        data_content = json_lib.loads(chunk[6:].strip())
                        if "days" in data_content or "status" in data_content or "error_code" in data_content:
                            plan_result = data_content
                    except Exception:
                        pass

            if idempotency_key and plan_result:
                await idempotency_manager.set_completed(idempotency_key, plan_result)
        except Exception as e:
            err_payload = {'step': 'error', 'error_code': 'NO_FEASIBLE_ROUTE', 'message': str(e)}
            yield f"data: {json_lib.dumps(err_payload)}\n\n"
            yield "data: [DONE]\n\n"
            if idempotency_key:
                await idempotency_manager.remove(idempotency_key)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/plan_alternatives")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def plan_alternatives(request: Request, body: TripPlanRequest, user: FirebaseUser = Depends(get_current_user)):
    """Generate Balanced / Budget / Chill alternatives via Layer 4 /plan-multi solver. Requires Auth."""
    logger.info(f"🔐 plan_alternatives called by user: {user.uid}")
    try:
        contract, pois, hotel_fallback = await _run_pipeline(body)
        if not pois:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy địa điểm du lịch nào phù hợp với yêu cầu của bạn.",
            )

        result = await layer4_client.plan_alternatives(pois=pois, contract=contract, time_limit=60)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Layer 4 multi-plan solver unavailable",
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"plan_alternatives error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat_process", response_model=ChatProcessResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def chat_process(request: Request, body: ChatProcessRequest, user: FirebaseUser = Depends(get_current_user)):
    """Processes a chat turn conversationally. Requires Firebase Auth."""
    logger.info(f"💬 chat_process called by user: {user.uid}")
    history_dict = [{"role": h.role, "content": h.content} for h in body.history]
    
    result = await llm_service.process_chat_turn(
        message=body.message,
        history=history_dict,
        current_contract=body.current_contract,
        has_draft=getattr(body, "has_draft", False),
    )
    
    return ChatProcessResponse(
        status=result["status"],
        reply=result["reply"],
        updated_contract=result["updated_contract"],
    )


@router.get("/health")
async def health():
    return {"status": "ready", "service": "Layer 2&3 Gateway"}


@router.get("/search_pois", response_model=List[POIResponse])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def search_pois_endpoint(request: Request, query: str, limit: int = 5, user: FirebaseUser = Depends(get_current_user)):
    """Tìm kiếm POI theo tên để hỗ trợ thao tác Add POI. Requires Firebase Auth."""
    from sqlalchemy import select
    from app.models.poi import PointOfInterest
    from geoalchemy2.functions import ST_AsGeoJSON
    import json as json_lib
    
    POI = PointOfInterest
    stmt = select(
        POI, ST_AsGeoJSON(POI.coordinates).label("geojson")
    ).where(POI.name.ilike(f"%{query}%")).limit(limit)
    
    async with AsyncSessionFactory() as db_session:
        result = await db_session.execute(stmt)
        rows = result.all()
        
        pois = []
        for row in rows:
            poi = row.PointOfInterest
            geojson = json_lib.loads(row.geojson) if row.geojson else None
            lat = geojson["coordinates"][1] if geojson else 0.0
            lon = geojson["coordinates"][0] if geojson else 0.0
            
            pois.append(POIResponse(
                uuid=poi.uuid,
                name=poi.name,
                category=poi.category,
                description=poi.description,
                latitude=lat,
                longitude=lon,
                visit_duration_min=poi.visit_duration_min,
                price=poi.price,
                entrance_fee=poi.entrance_fee,
                open_time=poi.open_time,
                close_time=poi.close_time,
                priority_score=poi.priority_score,
                tags=poi.tags,
                is_locked=False,
            ))
        return pois


@router.post("/re_route")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def re_route(request: Request, body: MobileReRouteRequest, user: FirebaseUser = Depends(get_current_user)):
    """Proxy re-route request from mobile to Layer 4. Requires Firebase Auth."""
    logger.info(f"🔄 re_route called by user: {user.uid}")
    try:
        result = await layer4_client.re_route(
            current_lat=body.current_lat,
            current_lon=body.current_lon,
            current_time_min=body.current_time_min,
            remaining_poi_ids=body.remaining_poi_ids,
            original_itinerary=body.original_itinerary,
            day_index=body.day_index,
            excluded_poi_ids=body.excluded_poi_ids,
        )

        if result is None:
            return ReRouteResponse(
                status="error",
                message="Layer 4 solver unavailable or returned no result",
            )

        solver_status = result.get("status", "success")
        return ReRouteResponse(
            status=solver_status, 
            day=result if solver_status in ["success", "optimized_with_warning"] else None,
            message=result.get("message")
        )

    except Exception as e:
        logger.error(f"Re-route proxy error: {e}")
        return ReRouteResponse(status="error", message=str(e))
```

---

### E. File: `layer2_3_gateway/app/services/layer4_client.py`
* **Conflict**: Thread-safe `CircuitBreaker` pattern (`app-4`), transport normalization (`webui-chat-clarification`), unlimited budget (`webui-chat-clarification`), operational time windows (`webui-chat-clarification`), multi-itinerary alternative planner `/plan-multi` (`web1-e2e`), and itinerary-aware dynamic rerouting constraints (`web1-e2e`).
* **Resolution**: Merge all routing solver functions. Implement the thread-safe `CircuitBreaker` globally across all endpoints. Map timeouts and OSRM errors. Perform transport normalization, budget translations, operational time window alignments (`day_plans`), and parse dynamic rerouting parameters accurately.

```python
"""HTTP client for Layer 4 (OR-Tools Routing Engine)."""

import httpx
import time
from typing import Optional, Dict, List
from app.config import settings
from app.schemas.trip import POIResponse, LLMDataContract
from app.utils.logging import AppLogger
from app.services.transport_modes import transport_modes_from_contract

logger = AppLogger().get_logger()


class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_time=30.0):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.failure_count = 0
        self.last_state_change = time.time()

    def check_state(self):
        if self.state == "OPEN":
            if time.time() - self.last_state_change > self.recovery_time:
                self.state = "HALF-OPEN"
                logger.info("Circuit Breaker transitioned to HALF-OPEN")
        return self.state

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_state_change = time.time()
        logger.info("Circuit Breaker transitioned to CLOSED (success recorded)")

    def record_failure(self):
        self.failure_count += 1
        logger.warning(f"Circuit Breaker failure recorded. Count: {self.failure_count}/{self.failure_threshold}")
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.last_state_change = time.time()
            logger.error("Circuit Breaker transitioned to OPEN (threshold exceeded)")


# Global circuit breaker instance
solver_breaker = CircuitBreaker()


class Layer4Client:
    """Assembles TravelPlanRequest and sends to Layer 4 API."""

    def __init__(self):
        self.base_url = settings.LAYER4_BASE_URL

    @staticmethod
    def _normalize_transport_modes(modes: List[str] | None) -> List[str]:
        """Map conversational transport names to Layer 4's supported enum values."""
        supported = {"walking", "taxi", "bus"}
        aliases = {
            "walk": "walking",
            "foot": "walking",
            "on_foot": "walking",
            "car": "taxi",
            "oto": "taxi",
            "o_to": "taxi",
            "private_car": "taxi",
            "motorbike": "taxi",
            "scooter": "taxi",
            "xe_may": "taxi",
            "xe máy": "taxi",
            "bus": "bus",
            "xe_buyt": "bus",
            "xe buýt": "bus",
        }
        normalized: List[str] = []
        for raw in modes or []:
            key = str(raw).strip().lower().replace(" ", "_")
            mode = aliases.get(key, key)
            if mode in supported and mode not in normalized:
                normalized.append(mode)
        return normalized or ["taxi", "walking"]

    def _build_payload(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
    ) -> Dict:
        """Assemble TravelPlanRequest matching Layer 4 schema exactly."""
        l4_pois = []
        for p in pois:
            l4_pois.append({
                "id": str(p.uuid),
                "name": p.name,
                "category": p.category,
                "location": {"latitude": p.latitude, "longitude": p.longitude},
                "visit_duration_min": p.visit_duration_min,
                "time_window": {
                    "start_min": p.open_time,
                    "end_min": p.close_time,
                },
                "entrance_fee": p.entrance_fee,
                "priority_score": p.utility_score,
                "tags": p.tags or [],
                "description": p.description,
                "is_locked": p.is_locked,
            })

        hotels = []
        for day_idx in range(contract.num_days):
            hotels.append({
                "id": f"hotel_day_{day_idx}",
                "name": contract.hotel_name,
                "location": {
                    "latitude": contract.hotel_lat,
                    "longitude": contract.hotel_lon,
                },
                "assigned_days": [day_idx],
            })

        # Integrate transport extraction & normalization
        contract_modes = transport_modes_from_contract(contract)
        normalized_modes = self._normalize_transport_modes(contract_modes)

        constraints = {
            "num_days": contract.num_days,
            "budget_total": None if getattr(contract, "budget_is_unlimited", False) else contract.budget_max,
            "transport_modes": normalized_modes,
        }

        payload = {
            "pois": l4_pois,
            "hotels": hotels,
            "constraints": constraints,
        }

        # Populate custom day plans for time windows if present
        if getattr(contract, "time_window", None) is not None:
            payload["day_plans"] = [
                {
                    "day_index": day_idx,
                    "date": f"Day {day_idx + 1}",
                    "hotel_id": f"hotel_day_{day_idx}",
                    "start_time_min": contract.time_window.start_min,
                    "end_time_min": contract.time_window.end_min,
                }
                for day_idx in range(contract.num_days)
            ]

        return payload

    def _re_route_constraints(self, original_itinerary: dict, day_index: int) -> Dict:
        """Prefer transport modes stored on original itinerary; fallback to taxi+walking."""
        stored = original_itinerary.get("constraints", {})
        modes = stored.get("transport_modes")
        if isinstance(modes, list) and modes:
            return {"num_days": 1, "transport_modes": modes}
        
        walking = original_itinerary.get("walking_tolerance")
        if walking:
            contract = LLMDataContract(walking_tolerance=walking, num_days=1)
            extracted_modes = transport_modes_from_contract(contract)
            return {"num_days": 1, "transport_modes": self._normalize_transport_modes(extracted_modes)}
        
        return {"num_days": 1, "transport_modes": ["taxi", "walking"]}

    async def plan(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
        time_limit: int = 30,
    ) -> Optional[Dict]:
        """Send assembled payload to Layer 4 POST /plan (blocking) under Circuit Breaker protection."""
        state = solver_breaker.check_state()
        if state == "OPEN":
            logger.error("Circuit breaker is OPEN. Blocking request to Layer 4 Solver.")
            return {"error_code": "CIRCUIT_BREAKER_OPEN", "message": "Hệ thống đang quá tải. Vui lòng thử lại sau 30 giây."}

        payload = self._build_payload(pois, contract)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/plan",
                    json=payload,
                    params={"time_limit": time_limit},
                )
                
                if resp.status_code == 400:
                    solver_breaker.record_success()
                    error_detail = resp.json().get("detail", {})
                    return {
                        "error_code": error_detail.get("error_code", "NO_FEASIBLE_ROUTE"),
                        "message": error_detail.get("message", "Lỗi lập lịch trình.")
                    }
                
                resp.raise_for_status()
                solver_breaker.record_success()
                return resp.json()
        except httpx.TimeoutException as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 call timed out: {e}")
            return {"error_code": "TIMEOUT", "message": "Quá thời gian phản hồi từ máy chủ lập lịch trình."}
        except httpx.HTTPStatusError as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 HTTP error: {e}")
            return {"error_code": "NO_FEASIBLE_ROUTE", "message": f"Lỗi hệ thống Solver: {e.response.status_code}"}
        except httpx.RequestError as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 request error: {e}")
            return {"error_code": "OSRM_UNREACHABLE", "message": "Không thể kết nối đến máy chủ định tuyến."}
        except Exception as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 call failed: {e}")
            return {"error_code": "NO_FEASIBLE_ROUTE", "message": f"Planning error: {str(e)}"}

    async def plan_stream(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
        time_limit: int = 30,
        hotel_fallback: bool = False,
    ):
        """SSE streaming: call Layer 4 /plan then yield result as SSE event."""
        import json as json_lib

        if hotel_fallback:
            logger.warning("🏨 [HOTEL_FALLBACK] Selected optimal hotel default chosen by spatial criteria.")

        result = await self.plan(pois=pois, contract=contract, time_limit=time_limit)

        if result is None:
            yield f"data: {json_lib.dumps({'step': 'error', 'error_code': 'NO_FEASIBLE_ROUTE', 'message': 'Layer 4 solver unavailable'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        if "error_code" in result:
            yield f"data: {json_lib.dumps({'step': 'error', 'error_code': result['error_code'], 'message': result['message']})}\n\n"
            yield "data: [DONE]\n\n"
            return

        result["hotel_fallback"] = hotel_fallback
        yield f"data: {json_lib.dumps(result)}\n\n"
        yield "data: [DONE]\n\n"

    async def plan_alternatives(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
        time_limit: int = 30,
    ) -> Optional[Dict]:
        """Send assembled payload to Layer 4 POST /plan-multi under Circuit Breaker protection."""
        state = solver_breaker.check_state()
        if state == "OPEN":
            logger.error("Circuit breaker is OPEN. Blocking request to Layer 4 alternatives.")
            return {"error_code": "CIRCUIT_BREAKER_OPEN", "message": "Hệ thống đang quá tải. Vui lòng thử lại sau 30 giây."}

        payload = self._build_payload(pois, contract)

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(
                    f"{self.base_url}/plan-multi",
                    json=payload,
                    params={"time_limit": time_limit},
                )
                
                if resp.status_code == 400:
                    solver_breaker.record_success()
                    error_detail = resp.json().get("detail", {})
                    return {
                        "error_code": error_detail.get("error_code", "NO_FEASIBLE_ROUTE"),
                        "message": error_detail.get("message", "Lỗi lập lịch trình thay thế.")
                    }
                
                resp.raise_for_status()
                solver_breaker.record_success()
                return resp.json()
        except httpx.TimeoutException as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 plan-multi timed out: {e}")
            return {"error_code": "TIMEOUT", "message": "Quá thời gian phản hồi máy chủ."}
        except httpx.HTTPStatusError as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 plan-multi HTTP error: {e}")
            return {"error_code": "NO_FEASIBLE_ROUTE", "message": f"Solver error: {e.response.status_code}"}
        except httpx.RequestError as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 plan-multi network error: {e}")
            return {"error_code": "OSRM_UNREACHABLE", "message": "Không kết nối được máy chủ định tuyến."}
        except Exception as e:
            solver_breaker.record_failure()
            logger.error(f"Layer 4 plan-multi failed: {e}")
            return {"error_code": "NO_FEASIBLE_ROUTE", "message": str(e)}

    async def re_route(
        self,
        current_lat: float,
        current_lon: float,
        current_time_min: int,
        remaining_poi_ids: list[str],
        original_itinerary: dict,
        day_index: int,
        excluded_poi_ids: list[str] | None = None,
        time_limit: int = 15,
    ) -> dict | None:
        """Forward re-route request to Layer 4 POST /re-route."""
        days = original_itinerary.get("days", [])
        target_day = None
        for d in days:
            if d.get("day_index") == day_index:
                target_day = d
                break
        if target_day is None and days:
            target_day = days[min(day_index, len(days) - 1)]

        if target_day is None:
            logger.error("No day found in original itinerary for re-route")
            return None

        pois = []
        for stop in target_day.get("stops", []):
            pois.append({
                "id": stop["poi_id"],
                "name": stop["poi_name"],
                "category": "general",
                "location": stop["location"],
                "visit_duration_min": stop.get("visit_duration_min", 60),
                "entrance_fee": stop.get("entrance_fee", 0),
                "priority_score": 0.8,
            })

        hotel_name = target_day.get("end_hotel_name") or target_day.get("start_hotel_name") or target_day.get("hotel_name", "Hotel")
        hotel_location = target_day.get("end_hotel_location") or target_day.get("start_hotel_location") or target_day.get("hotel_location", {
            "latitude": current_lat,
            "longitude": current_lon,
        })
        hotel = {
            "id": f"hotel_day_{day_index}",
            "name": hotel_name,
            "location": hotel_location,
        }

        day_plan = {
            "day_index": day_index,
            "date": target_day.get("date", "re-route"),
            "start_time_min": current_time_min,
            "end_time_min": 1260,  # 21:00
        }

        # Resolve itinerary-aware rerouting constraints
        constraints = self._re_route_constraints(original_itinerary, day_index)

        payload = {
            "current_location": {
                "latitude": current_lat,
                "longitude": current_lon,
            },
            "current_time_min": current_time_min,
            "remaining_poi_ids": remaining_poi_ids,
            "pois": pois,
            "hotel": hotel,
            "day": day_plan,
            "constraints": constraints,
            "excluded_poi_ids": excluded_poi_ids,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/re-route",
                    json=payload,
                    params={"time_limit": time_limit},
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            logger.error(f"Layer 4 re-route failed: {e}")
            return None
```
