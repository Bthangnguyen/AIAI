# Phase 5 — Mobile ↔ Backend Integration Plan

> Kết nối Layer 5 (React Native/Expo) với Layer 2&3 Gateway + Layer 4 Routing Engine.

---

## 📊 Hiện trạng (AS-IS)

### Mobile (Layer 5)
- `FeatureFlags.USE_MOCK_BACKEND = true` → tất cả data là mock
- `EXPO_PUBLIC_API_URL = http://localhost:8080` → chưa trỏ đúng gateway
- `tripService.ts` đã có SSE client (`react-native-sse`) → sẵn sàng
- `useTripPipeline.ts` đã handle cả mock + real backend → sẵn sàng
- Auth mock: bất kì email/pass → login, token = timestamp
- MapTimeline hardcode Mapbox token trong code (nên move ra env)

### Backend (Layer 2&3 Gateway — port 8001)
- `POST /v1/trip/plan_trip` → JSON response (full pipeline)
- `POST /v1/trip/plan_trip_stream` → SSE streaming (L2→L3→L4 progress)
- `GET /v1/trip/health` → health check
- Rate limit: 5 req/min (slowapi)
- Không có auth middleware (open access)
- CORS chưa config cho mobile

### Backend (Layer 4 — port 8000)
- `POST /plan` → TravelItinerary JSON
- `POST /re-route` → single-day re-optimization
- `GET /health` → solver status
- Có API key middleware (`dependencies.py`)

---

## 🎯 Mục tiêu (TO-BE)

Mobile gửi prompt → Gateway SSE stream → hiển thị real-time progress → nhận itinerary → render map.

---

## 📋 Plan chi tiết

### Step 1: Backend — CORS + Environment Config
**Files cần sửa:**
- `layer2_3_gateway/app/main.py`

**Việc cần làm:**
```python
# Thêm CORS middleware cho mobile app
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dev: accept all. Prod: restrict domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Ưu tiên:** 🔴 Bắt buộc — không có CORS thì mobile không gọi được API.

---

### Step 2: Backend — SSE Response Format Alignment
**Vấn đề hiện tại:**

Gateway `plan_trip_stream` trả SSE format:
```
data: {"step": "l2_done", "tags": [...], "locked": [...]}
data: {"step": "l3_done", "pois_found": 15, "locked_count": 2}
data: <layer4 JSON chunks>
data: [DONE]
```

Mobile `useTripPipeline.ts` (real backend path) expect:
```typescript
// L2 done
if (data.step === "l2_done") → OK ✅
// L3 done
if (data.step === "l3_done") → OK ✅
// L4 result — checks data.status === "success" || data.days
if (data.status === "success" || data.days) → ⚠️ CẦN VERIFY
// Error
if (data.step === "error") → OK ✅
```

**Vấn đề:** Layer 4 `plan_stream()` trong `layer4_client.py` forwards raw JSON chunks từ Layer 4 `/plan` response. Layer 4 trả **1 JSON object** (không phải stream), nên `plan_stream()` thực ra buffer toàn bộ rồi yield 1 lần.

**Files cần sửa:**
- `layer2_3_gateway/app/services/layer4_client.py` — `plan_stream()` nên wrap L4 result:
  ```python
  # Thay vì forward raw chunks, gọi plan() rồi wrap:
  result = await self.plan(pois=pois, contract=contract)
  yield f"data: {json.dumps(result)}\n\n"
  yield "data: [DONE]\n\n"
  ```

  Hoặc giữ stream nhưng đảm bảo final chunk có `status` field.

**Ưu tiên:** 🔴 Bắt buộc — mobile cần parse đúng L4 result.

---

### Step 3: Mobile — Environment & Feature Flags
**Files cần sửa:**
- `mobile layer/AITravelOptimizer/.env`
- `mobile layer/AITravelOptimizer/app/config/features.ts`

**Việc cần làm:**

```env
# .env — Trỏ về Gateway (Layer 2&3)
EXPO_PUBLIC_API_URL=http://<LAN_IP>:8001
EXPO_PUBLIC_MAPBOX_TOKEN=pk.eyJ1...  (giữ nguyên)
```

```typescript
// features.ts — Bật real backend
export const FeatureFlags = {
  USE_MOCK_BACKEND: false,     // ← CHUYỂN false
  ENABLE_PUSH_NOTIFICATIONS: true,
  ENABLE_SHARE: false,
  ENABLE_REROUTE: false,       // Bật sau khi test xong
} as const
```

**Lưu ý:** Trên Android emulator, `localhost` = emulator chứ không phải host machine. Cần dùng:
- Android Emulator: `10.0.2.2:8001`
- iOS Simulator: `localhost:8001` OK
- Physical device: dùng LAN IP (e.g. `192.168.x.x:8001`)

**Ưu tiên:** 🔴 Bắt buộc.

---

### Step 4: Mobile — tripService.ts URL Fix
**Vấn đề:** `tripService.ts` dùng `EXPO_PUBLIC_API_URL` nhưng endpoint path là `/v1/trip/plan_trip_stream` — khớp với Gateway rồi. ✅

**Check:**
```typescript
// tripService.ts line 5
const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8080"
// → Sẽ đọc từ .env → http://<IP>:8001 ✅

// URL = http://<IP>:8001/v1/trip/plan_trip_stream ✅
```

Chỉ cần đảm bảo `.env` đúng → **không cần sửa code** ở đây.

**Ưu tiên:** ✅ Đã OK.

---

### Step 5: Mobile — SSE Event Handling Hardening
**Files cần sửa:**
- `mobile layer/AITravelOptimizer/app/hooks/useTripPipeline.ts`

**Việc cần làm:**

```typescript
// Real backend handler — thêm defensive parsing
(data: any) => {
  // L2
  if (data.step === "l2_done") { ... } // OK

  // L3
  else if (data.step === "l3_done") { ... } // OK

  // L4 result — STRENGTHEN check
  else if (data.step === "l4_result" || data.status === "success" || data.days) {
    updateStep("l4", "done")
    // L4 result có thể nested trong layer4_result (từ plan_trip JSON endpoint)
    // hoặc flat (từ plan_trip_stream forward)
    const itinerary = data.layer4_result || data
    itineraryRef.current = itinerary as TravelItinerary

    // Push notification
    Notifications.scheduleNotificationAsync({
      content: {
        title: "Hành trình đã sẵn sàng! ✈️",
        body: "AI đã tạo xong lịch trình tối ưu của bạn.",
        sound: true,
      },
      trigger: null,
    })
    addLog(`✓ Route optimized — ${itinerary.total_pois_visited} POIs`, "success")
  }

  // Error
  else if (data.step === "error") { ... } // OK

  // Status/progress messages
  else if (data.step === "status" || data.message) {
    addLog(data.message || "Processing…", "info")
  }
}
```

**Thêm timeout + retry:**
```typescript
// Thêm connection timeout
useEffect(() => {
  const TIMEOUT_MS = 120_000 // 2 phút max
  const timer = setTimeout(() => {
    if (!itineraryRef.current) {
      setErrorMsg("Request timed out. Please try again.")
      addLog("Connection timed out", "error")
    }
  }, TIMEOUT_MS)

  // ... existing SSE setup ...

  return () => { clearTimeout(timer); es.close() }
}, [])
```

**Ưu tiên:** 🟡 Quan trọng — tránh crash khi data format khác expect.

---

### Step 6: Mobile — Network Error UX
**Files cần sửa:**
- `mobile layer/AITravelOptimizer/app/screens/LoadingScreen.tsx`

**Việc cần làm:**
- Thêm "Retry" button khi `errorMsg` !== null
- Thêm "Back" button để quay lại ItineraryForm

```tsx
{errorMsg && (
  <View style={$errorActions}>
    <Pressable onPress={() => navigation.goBack()}>
      <Text text="← Back" style={$retryText} />
    </Pressable>
    <Pressable onPress={() => {
      // Reset state và re-trigger pipeline
      setErrorMsg(null)
      setSteps(INITIAL_STEPS)
      setLogs([])
      // Re-run effect — cần refactor thành callable function
    }}>
      <Text text="🔄 Retry" style={$retryText} />
    </Pressable>
  </View>
)}
```

**Ưu tiên:** 🟡 UX quan trọng cho real backend (network failures).

---

### Step 7: Backend — API Health Check Endpoint cho Mobile
**Files cần sửa:**
- `layer2_3_gateway/app/api/trip_planner.py` (đã có `/health` ✅)

**Mobile nên check health trước khi gọi pipeline:**
```typescript
// Thêm vào tripService.ts
async checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/trip/health`, { timeout: 5000 })
    const data = await res.json()
    return data.status === "ready"
  } catch {
    return false
  }
}
```

**Ưu tiên:** 🟢 Nice-to-have — hiển thị "Server offline" sớm.

---

### Step 8: Mobile — Re-route Integration (sau khi Step 1-6 xong)
**Files cần sửa:**
- `mobile layer/AITravelOptimizer/app/config/features.ts` → `ENABLE_REROUTE: true`
- `mobile layer/AITravelOptimizer/app/services/api/tripService.ts` → fix `reRoute()` endpoint
- `mobile layer/AITravelOptimizer/app/screens/MapTimelineScreen.tsx` → thêm "Re-route" button

**Hiện tại `reRoute()` gọi `/v1/trip/re_route`** nhưng Gateway chưa có endpoint này.

**Cần thêm vào Gateway:**
```python
# layer2_3_gateway/app/api/trip_planner.py
@router.post("/re_route")
async def re_route(request: Request, body: ReRouteRequest):
    """Forward re-route to Layer 4."""
    result = await layer4_client.re_route(body)
    return result
```

**Hoặc mobile gọi thẳng Layer 4** (nếu expose ra):
```typescript
// tripService.ts
async reRoute(payload: ReRoutePayload) {
  const L4_URL = process.env.EXPO_PUBLIC_L4_URL || API_BASE_URL
  const response = await fetch(`${L4_URL}/re-route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  return response.json()
}
```

**Ưu tiên:** 🟢 Phase 2 — sau khi basic flow chạy ổn.

---

## 🏗️ Thứ tự triển khai

```
PHASE A — Minimal Working Connection (Ngày 1-2)
┌──────────────────────────────────────────────────────┐
│ Step 1: CORS middleware on Gateway              [30m] │
│ Step 2: SSE response format verify/fix          [1h]  │
│ Step 3: .env + feature flags                    [10m] │
│ Step 4: Verify tripService URL                  [10m] │
│                                                       │
│ 🧪 TEST: Mobile → Gateway → L4 full pipeline         │
│    - Start OSRM Docker                                │
│    - Start Layer 4 (port 8000)                        │
│    - Start Gateway (port 8001)                        │
│    - Start Expo (npx expo start)                      │
│    - ItineraryForm → Loading → MapTimeline            │
└──────────────────────────────────────────────────────┘

PHASE B — Hardening (Ngày 3-4)
┌──────────────────────────────────────────────────────┐
│ Step 5: SSE handler hardening + timeout         [1h]  │
│ Step 6: Error UX (retry/back buttons)           [1h]  │
│ Step 7: Health check pre-flight                 [30m] │
└──────────────────────────────────────────────────────┘

PHASE C — Re-route + Polish (Ngày 5+)
┌──────────────────────────────────────────────────────┐
│ Step 8: Re-route endpoint + UI                  [2h]  │
│ Step 9: Real auth (JWT/OAuth2)                  [4h]  │
│ Step 10: Production env config                  [1h]  │
└──────────────────────────────────────────────────────┘
```

---

## 🧪 Test Checklist

### Phase A — Smoke Test
- [ ] Gateway health: `curl http://localhost:8001/v1/trip/health` → `{"status": "ready"}`
- [ ] Layer 4 health: `curl http://localhost:8000/health` → `{"status": "ready"}`
- [ ] Mobile → Gateway SSE: ItineraryForm submit → LoadingScreen shows L2→L3→L4 steps
- [ ] MapTimeline receives real itinerary (not mock data)
- [ ] POI markers render on correct coordinates
- [ ] Route polyline renders on map

### Phase B — Edge Cases
- [ ] Gateway down → Mobile shows error + retry
- [ ] Layer 4 busy (503) → Error message hiển thị đúng
- [ ] OSRM down → L4 fallback Haversine → vẫn trả itinerary
- [ ] Rate limit hit → Mobile hiển thị "Too many requests"
- [ ] Empty prompt → LLM vẫn extract hợp lệ hoặc trả error
- [ ] 0 POIs found → Error message "No POIs found"

### Phase C — Re-route
- [ ] User nhấn "Re-route" trên MapTimeline → gửi current GPS + remaining POIs
- [ ] Nhận lại optimized day plan → update MapTimeline

---

## ⚠️ Rủi ro & Giải pháp

| Rủi ro | Xác suất | Giải pháp |
|--------|:--------:|-----------|
| SSE format mismatch L4→Gateway→Mobile | Cao | Step 2: verify bằng curl trước |
| Android emulator không reach localhost | Chắc chắn | Dùng `10.0.2.2` hoặc LAN IP |
| CORS block preflight | Cao | Step 1: wildcard origin cho dev |
| Gateway rate limit 5/min quá thấp cho dev | Trung bình | Tăng lên 30/min trong dev env |
| Mapbox token expire | Thấp | Token đã set, check billing |
| LLM API key hết credit | Trung bình | Monitor usage, set billing alert |

---

## 📁 Files sẽ thay đổi (tổng hợp)

### Backend
1. `layer2_3_gateway/app/main.py` — CORS middleware
2. `layer2_3_gateway/app/services/layer4_client.py` — `plan_stream()` format fix
3. `layer2_3_gateway/app/api/trip_planner.py` — (optional) re-route proxy endpoint

### Mobile
1. `mobile layer/AITravelOptimizer/.env` — API URL
2. `mobile layer/AITravelOptimizer/app/config/features.ts` — `USE_MOCK_BACKEND: false`
3. `mobile layer/AITravelOptimizer/app/hooks/useTripPipeline.ts` — SSE hardening + timeout
4. `mobile layer/AITravelOptimizer/app/screens/LoadingScreen.tsx` — retry/back UX
5. `mobile layer/AITravelOptimizer/app/services/api/tripService.ts` — (optional) health check + re-route
