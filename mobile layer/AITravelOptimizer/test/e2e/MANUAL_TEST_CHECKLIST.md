# Tầng 4: E2E Manual Test Checklist — Android

> Chạy trên **Android Emulator (API 33+)** hoặc device thật.
> Đánh dấu ✅ khi pass, ❌ khi fail + ghi chú.

---

## Chuẩn bị

- [ ] Docker Desktop đang chạy
- [ ] OSRM container running (`docker ps | grep osrm`)
- [ ] Layer 4 running trên port 8000 (`curl http://localhost:8000/health`)
- [ ] Gateway running trên port 8001 (`curl http://localhost:8001/v1/trip/health`)
- [ ] `.env` đã set `EXPO_PUBLIC_API_URL=http://10.0.2.2:8001` (Android emulator)
- [ ] `.env` đã set `EXPO_PUBLIC_MAPBOX_TOKEN=pk.eyJ1...`
- [ ] `FeatureFlags.USE_MOCK_BACKEND = false`
- [ ] `npx expo start` running

---

## B4.1: Smoke Test (Mock Backend)

> Tạm set `USE_MOCK_BACKEND = true` để test UI flow trước.

- [ ] App khởi động không crash
- [ ] Onboarding 3-step swipe hoạt động
- [ ] Login → nhập email/pass → vào MainTabs
- [ ] ExploreScreen: greeting hiển thị, category chips, location cards
- [ ] "Plan a Trip" → ItineraryFormScreen
- [ ] Calendar: chọn range ngày
- [ ] **HotelPicker**: preset chips hiển thị, tap chọn hotel khác
- [ ] **HotelPicker**: tap "Other..." → search input xuất hiện
- [ ] Nhập prompt → "Next step" → LoadingScreen
- [ ] LoadingScreen: L2→L3→L4 steps hiển thị đúng thứ tự
- [ ] Push notification fires "Hành trình đã sẵn sàng!"
- [ ] MapTimeline: map render với markers + polyline
- [ ] BottomSheet: swipe lên/xuống, itinerary cards hiển thị
- [ ] Tap card → camera fly to POI
- [ ] Tap marker → BottomSheet snap to 50%

---

## B4.2: Smoke Test (Real Backend)

> Set `USE_MOCK_BACKEND = false`

- [ ] Health check: "✓ Server connected" log xuất hiện
- [ ] Full pipeline: prompt → L2 tags → L3 POIs → L4 itinerary
- [ ] MapTimeline hiển thị **real POIs** (không phải mock data)
- [ ] POI markers đúng tọa độ Huế (không phải Hà Nội/TPHCM)
- [ ] Route polyline render trên map
- [ ] Summary bar: Places count + Duration + Distance chính xác
- [ ] BottomSheet itinerary cards khớp với markers trên map

---

## B4.3: Error Scenarios

- [ ] Gateway down → "Server unreachable" hiển thị
- [ ] "← Go Back" button → quay lại ItineraryForm
- [ ] "🔄 Retry" button → re-trigger pipeline
- [ ] Empty prompt → Alert "Please describe your trip"
- [ ] Timeout 2 phút → "Request timed out" message
- [ ] 0 POIs found → error event hiển thị đúng

---

## B4.4: Hotel Selection (Phase A fix)

- [ ] Default hotel = "Hue Heritage Hotel"
- [ ] Tap "Saigon Morin Hotel" chip → selected hotel thay đổi
- [ ] Tap "Other..." → search input xuất hiện
- [ ] Gõ "khach san" → Mapbox suggestions xuất hiện
- [ ] Tap suggestion → hotel name + coordinates cập nhật
- [ ] "Next step" → Loading params có đúng hotel đã chọn

---

## B4.5: MapTimeline Bug #1 Fix

- [ ] Real backend: MapTimeline hiển thị itinerary thật (không phải "Đại Nội Huế" mock)
- [ ] Hotel name trong itinerary khớp với hotel đã chọn
- [ ] POI count trên summary bar khớp với actual stops

---

## Ghi chú test
| Tester | Ngày | Device | Kết quả |
|--------|------|--------|---------|
| | | | |
