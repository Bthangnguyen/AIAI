# LLM Extractor Follow-up Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay thế chat AI giả lập hiện tại trên HomeScreen bằng luồng đàm thoại tương tác thực tế kết nối với API `/chat_process` của Gateway, hiển thị nút Royal CTA để khởi chạy bộ giải tối ưu hóa khi đã sẵn sàng.

**Architecture:** Sử dụng kiến trúc State Machine hội thoại. Mobile quản lý `currentContract` (LLMDataContract) và `chatHistory` cục bộ, gửi chúng cùng tin nhắn mới nhất lên `/v1/trip/chat_process`. Khi Gateway phản hồi `status === "ready"`, nút bấm Glassmorphic Royal CTA được hiển thị. Khi bấm nút, hợp đồng được đúc kết thành Unified Prompt và truyền tiếp sang `LoadingScreen`.

**Tech Stack:** React Native, Expo, TypeScript, Jest, Fetch API, Animated API

---

### Task 1: API Service & Types Integration

**Files:**
- Modify: `app/types/api.ts`
- Modify: `app/services/api/tripService.ts`
- Modify: `test/services/tripService.test.ts`

- [ ] **Step 1: Write the failing test**

Thêm test case mô tả hành vi của `TripService.processChat` vào `test/services/tripService.test.ts`.

```typescript
  describe("processChat", () => {
    it("calls /chat_process with message, history, contract and returns updated data", async () => {
      const mockResponse = {
        status: "clarifying",
        reply: "Dạ mình muốn đi Huế mấy ngày ạ?",
        updated_contract: { destination: "Huế", num_days: 1, tags: [] },
      }

      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      }) as any

      const history = [{ role: "user", content: "Hi" }]
      const contract = { destination: "Huế", num_days: 1, tags: [] }

      const result = await TripService.processChat("Tôi muốn đi Huế", history as any, contract)

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/v1/trip/chat_process"),
        expect.objectContaining({
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "ngrok-skip-browser-warning": "1",
          },
          body: JSON.stringify({
            message: "Tôi muốn đi Huế",
            history,
            current_contract: contract,
          }),
        })
      )
      expect(result).toEqual(mockResponse)
    })
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- test/services/tripService.test.ts`
Expected: FAIL với lỗi `TripService.processChat is not a function` hoặc biên dịch TypeScript thất bại do thiếu định nghĩa hàm và kiểu dữ liệu.

- [ ] **Step 3: Write minimal implementation**

1. Thêm định nghĩa interface vào `app/types/api.ts` ở cuối file:
```typescript
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatProcessResponse {
  status: 'ready' | 'clarifying';
  reply: string;
  updated_contract: LLMDataContract;
}
```

2. Bổ sung hàm `processChat` vào `TripService` trong file `app/services/api/tripService.ts`:
```typescript
  async processChat(
    message: string,
    history: any[],
    currentContract: any
  ): Promise<any> {
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
      console.error("Lỗi đàm thoại chat_process:", e)
      return {
        status: "clarifying",
        reply: "Dạ mạng nhà em đang gặp chút trục trặc nhỏ. Anh/chị có thể nói rõ hơn số ngày đi và ngân sách mong muốn không ạ?",
        updated_contract: currentContract,
      }
    }
  },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test -- test/services/tripService.test.ts`
Expected: PASS cả 7 test cases.

- [ ] **Step 5: Commit**

```bash
git add app/types/api.ts app/services/api/tripService.ts test/services/tripService.test.ts
git commit -m "feat: add processChat API method and types with unit test coverage"
```

---

### Task 2: HomeScreen UI & Dynamic Chat Integration

**Files:**
- Modify: `app/screens/HomeScreen.tsx`

- [ ] **Step 1: Replace Fake chat logic with processChat integration**

1. Khai báo imports các kiểu dữ liệu và service thực tế:
```typescript
// Replace lines 20-23
import type { AppStackScreenProps } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { LLMDataContract, ChatMessage } from "@/types/api"
import { TripService } from "@/services/api/tripService"
```

2. Tái lập trình State và hàm `handleSend` trong `HomeScreen`:
```typescript
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
  const insets = useSafeAreaInsets()
```

3. Thay đổi hoàn toàn logic hàm `handleSend` để gọi API:
```typescript
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
      console.error("Chat error:", err)
    }
  }
```

4. Cập nhật ánh xạ hiển thị bong bóng chat trong JSX (render `chatHistory` dựa trên `role === "user"` thay vì `sender === "user"`):
```typescript
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
```

- [ ] **Step 2: Verify code builds cleanly**

Run: `npm run compile`
Expected: Lệnh chạy thành công và không báo lỗi TypeScript nào liên quan đến import hay kiểu dữ liệu.

- [ ] **Step 3: Commit**

```bash
git add app/screens/HomeScreen.tsx
git commit -m "feat: replace fake AI chat with real interactive processChat connection in HomeScreen"
```

---

### Task 3: Royal CTA Button & Unified Solver Launch

**Files:**
- Modify: `app/screens/HomeScreen.tsx`

- [ ] **Step 1: Implement Glassmorphic Royal CTA Button UI & Animation**

1. Khai báo thêm Animated value quản lý trượt nút bấm:
```typescript
  // Thêm vào dưới micScale ref
  const ctaAnim = useRef(new Animated.Value(0)).current
```

2. Thêm `useEffect` để chạy hiệu ứng trượt nút bấm lên/xuống khi `isReady` thay đổi:
```typescript
  useEffect(() => {
    Animated.spring(ctaAnim, {
      toValue: isReady ? 1 : 0,
      tension: 50,
      friction: 8,
      useNativeDriver: true,
    }).start()
  }, [isReady])
```

3. Thêm hàm `handleLaunchRouteSolver` tổng hợp Unified Prompt cấu trúc cao:
```typescript
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
```

4. Tích hợp giao diện Nút Royal CTA vào JSX, nằm ngay phía trên Input card:
```typescript
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
```

5. Thêm CSS Styles tương ứng vào `StyleSheet.create`:
```typescript
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
```

- [ ] **Step 2: Verify code compiles and all tests pass**

Run: `npm run compile`
Expected: SUCCESS

Run: `npm run test`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add app/screens/HomeScreen.tsx
git commit -m "feat: integrate animated Royal CTA button and navigation unified prompt handoff on HomeScreen"
```
