# Phase 3: Real-World Testing & UI Polish — Implementation Plan

## Mục tiêu
Đưa AIAI Travel Optimizer đạt chuẩn phát hành sản phẩm bằng cách: mở rộng kịch bản kiểm thử 100 prompt, xây dựng module phân tích lỗi tự động, nâng cấp toàn bộ UI transitions lên chuẩn high-end, xử lý triệt để edge cases, và bổ sung các lớp hạ tầng vận hành (CI/CD, Observability, Security, Documentation).

## User Review Required

> [!IMPORTANT]
> **Scope rất lớn**: Phase 3 này bao gồm ~15 file cần tạo/sửa. Tôi đề xuất chia thành **4 Sprint nhỏ** để dễ review và kiểm soát chất lượng. Mỗi Sprint sẽ tự hoàn chỉnh và có thể verify độc lập.

> [!WARNING]
> **Test 100 prompt thật**: Script `run_pipeline_test.py` hiện tại hardcode path đến `D:\Workspaces\AI travel optimizer\...` (máy develop khác). Tôi sẽ tạo bản refactor dùng relative path + offline CSV data đã có sẵn trong repo. Tuy nhiên, việc chạy thật 100 prompt qua LLM API sẽ tốn quota API (Gemini/OpenAI). Bạn có muốn chạy toàn bộ hay chỉ chạy batch 10 case đại diện trước?

> [!IMPORTANT]
> **CI/CD với GitHub Actions**: Repo hiện tại cần có remote GitHub repo. Bạn đã push code lên GitHub chưa? Nếu chưa, tôi sẽ tạo sẵn file workflow `.github/workflows/ci.yml` để bạn kích hoạt sau khi push.

## Open Questions

1. **Sentry DSN**: Bạn đã có tài khoản Sentry chưa? Nếu chưa, tôi sẽ tạo sẵn code integration và bạn chỉ cần điền DSN sau.
2. **Firebase Realtime check**: Phase 1 đã tích hợp Firebase Auth. RLS trên Supabase/PostgreSQL hiện đang ở trạng thái nào? Đã có policies hay chưa?
3. **react-native-reanimated version**: Codebase đang dùng `react-native-reanimated` (đã import trong LoadingScreen). Tôi sẽ sử dụng thêm `Layout Animations` và `Shared Transitions` API — cần xác nhận version >= 3.x.

---

## Proposed Changes

### Sprint 3A: Test Runner Expansion & Analysis Module

Mở rộng `run_pipeline_test.py` cho 100 prompt và tạo module phân tích log tự động.

---

#### [MODIFY] [run_pipeline_test.py](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/run_pipeline_test.py)
- Refactor path thành relative (dùng `__file__` base dir)
- Thêm toàn bộ 100 test case definitions từ `testing.md` (T001–T100)
- Thêm `try/except` bắt `SolverException` để ghi `error_code` vào kết quả
- Xuất kết quả dạng JSONL tổng hợp ra `testing/results_summary.jsonl`
- Thêm auto-scoring module cho các tiêu chí (6 dimensions × 0–5)

#### [NEW] [test_analysis.py](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/testing/test_analysis.py)
Module phân tích log kết quả tự động:
- Đọc `results_summary.jsonl` → Thống kê tỷ lệ lỗi theo `ErrorCode`
- Xác định bottlenecks: nhóm nào (A–J) có failure rate cao nhất
- Phân tích root cause: LLM extraction sai vs. Solver infeasible vs. Budget conflict
- Xuất báo cáo markdown: `testing/analysis_report.md`
- Bar chart ASCII cho tỷ lệ pass/fail theo nhóm

#### [NEW] [testing/all_100_testcases.json](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/testing/all_100_testcases.json)
File JSON chứa toàn bộ 100 test case với format chuẩn:
```json
{
  "id": "T001",
  "prompt": "Tôi muốn đi Huế 1 ngày...",
  "expected_desc": "num_days=1, budget, locked Đại Nội...",
  "group": "A",
  "checks": ["..."]
}
```

---

### Sprint 3B: UI/UX Polish — Skeleton Loading & Shared Transitions

Nâng cấp trải nghiệm chuyển cảnh và loading states.

---

#### [NEW] [SkeletonCard.tsx](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/mobile%20layer/AITravelOptimizer/app/components/SkeletonCard.tsx)
Component skeleton loading thay thế spinner:
- Shimmer/pulse animation dùng `react-native-reanimated`
- Mô phỏng cấu trúc ItineraryCard (avatar tròn + 2 dòng text + badge)
- Gradient overlay nhấp nháy từ trái sang phải
- Dùng trong LoadingScreen khi `step l4 active`

#### [NEW] [SkeletonList.tsx](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/mobile%20layer/AITravelOptimizer/app/components/SkeletonList.tsx)
Render 3–5 SkeletonCard xếp chồng với stagger delay:
- FadeIn stagger 100ms giữa các card
- Tự fade out khi dữ liệu itinerary load xong

#### [MODIFY] [LoadingScreen.tsx](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/mobile%20layer/AITravelOptimizer/app/screens/LoadingScreen.tsx)
- Thay spinner tròn bằng animated travel icon (máy bay/bản đồ) + pulse
- Thêm `<SkeletonList>` hiển thị bên dưới pipeline steps khi `l4` đang active
- Thêm elapsed time counter ("Đang tối ưu... 15s") để user biết app "sống"
- Thêm SSE progress percentage (nếu backend gửi `progress: 0.6`)
- Sử dụng `Animated.Layout` cho transition mượt khi steps thay đổi status

#### [MODIFY] [AppNavigator.tsx](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/mobile%20layer/AITravelOptimizer/app/navigators/AppNavigator.tsx)
- Thêm `animation: "fade"` cho transition Loading → MapTimeline
- Cấu hình `customAnimation` dùng reanimated cho smooth cross-fade thay vì push mặc định
- Thêm `gestureEnabled: false` cho LoadingScreen (không cho swipe back khi đang processing)

#### [MODIFY] [MapTimelineScreen.tsx](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/mobile%20layer/AITravelOptimizer/app/screens/MapTimelineScreen.tsx)
- Thêm `FadeInDown` entry animation cho Bottom Sheet content
- Micro-animation cho lock/unlock POI: scale bounce + haptic feedback (`expo-haptics`)
- Thêm empty state khi user xóa hết stops: illustration SVG + nút "Thêm địa điểm"
- Cải thiện delete animation: slide-out + undo snackbar mượt hơn

---

### Sprint 3C: Edge Cases & Error Handling Hardening

Xử lý triệt để các "góc chết" UX.

---

#### [MODIFY] [ItineraryFormScreen.tsx](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/mobile%20layer/AITravelOptimizer/app/screens/ItineraryFormScreen.tsx)
- Thay `Alert.alert()` bằng inline validation message (đỏ nhẹ dưới input field)
- Disable nút "Next" khi prompt trống (dim + không nhấn được)
- Thêm character counter cho query input (xx/500)
- Thêm subtle shake animation khi user nhấn Next với input invalid

#### [MODIFY] [ErrorRecoveryCard.tsx](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/mobile%20layer/AITravelOptimizer/app/components/ErrorRecoveryCard.tsx)
- Thêm entry animation `FadeInUp + scale` khi card xuất hiện
- Thêm gradient accent strip ở top card (theo severity: warning=orange, error=red)
- Thêm error code `TIMEOUT_GATEWAY` và `DATA_MISSING` mapping
- Cải thiện copy tiếng Việt cho từng lỗi: actionable + empathetic

#### [NEW] [HotelFallbackBanner.tsx](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/mobile%20layer/AITravelOptimizer/app/components/HotelFallbackBanner.tsx)
Banner cảnh báo khi hệ thống dùng khách sạn mặc định:
- Hiển thị ở đầu MapTimelineScreen nếu `itinerary.hotel_fallback === true`
- Thiết kế nhất quán với NetworkBanner (cùng border-radius, slide-in animation)
- Màu info (xanh dương nhạt) thay vì error
- Nút "Chọn khách sạn khác" → navigate về ItineraryForm

#### [MODIFY] [useTripPipeline.ts](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/mobile%20layer/AITravelOptimizer/app/hooks/useTripPipeline.ts)
- Thêm `elapsedTime` counter (setInterval mỗi 1s) expose ra LoadingScreen
- Thêm `hotel_fallback` flag vào itinerary response khi gateway trả về warning
- Parse SSE chunk `hotel_warning` từ gateway → set flag

#### [MODIFY] [trip_planner.py](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/layer2_3_gateway/app/api/trip_planner.py)
- Trong `_run_pipeline()`: khi dùng default hotel (line 152), emit SSE event `hotel_warning` kèm tên hotel mặc định
- Thêm structured logging cho mỗi pipeline step (duration_ms, step_name)

---

### Sprint 3D: Infrastructure — CI/CD, Observability, Security, Documentation

Bổ sung các lớp hạ tầng vận hành production-grade.

---

#### [NEW] [.github/workflows/ci.yml](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/.github/workflows/ci.yml)
GitHub Actions CI pipeline:
- **Job 1 — Solver Tests**: `pytest fleet-route-optimizer-cvrptw/tests/ -v`
- **Job 2 — Gateway Lint**: `flake8 layer2_3_gateway/` + `mypy --ignore-missing-imports`
- **Job 3 — Mobile TypeScript**: `npx tsc --noEmit` trong thư mục mobile
- Trigger: push to `main`, pull_request
- Cache pip + npm dependencies

#### [NEW] [sentry.ts](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/mobile%20layer/AITravelOptimizer/app/services/sentry.ts)
Sentry integration wrapper:
- `initSentry(dsn)` — gọi trong `app.tsx`
- `captureError(error, context)` — gọi trong useTripPipeline khi lỗi
- `setUserContext(uid, email)` — gọi sau Firebase auth
- Guard `__DEV__` mode (chỉ report production)

#### [NEW] [SECURITY_CHECKLIST.md](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/docs/SECURITY_CHECKLIST.md)
Tài liệu rà soát bảo mật:
- `.gitignore` audit: xác nhận `.env`, `travel.env`, `google-services.json` đã được ignore ✅
- Firebase Admin SDK key management
- API key rotation policy
- RLS status trên PostgreSQL (checklist template)
- CORS configuration review

#### [MODIFY] [README.md](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/README.md)
Bổ sung sections:
- **Architecture Diagram**: Mermaid diagram cho L2→L3→L4 pipeline
- **Quick Start**: Hướng dẫn setup local dev environment
- **API Documentation**: Endpoints summary cho Gateway
- **Testing**: Hướng dẫn chạy 100 prompt test suite
- **Deployment**: Checklist deploy production

#### [MODIFY] [.gitignore](file:///d:/tư%20duy%20tính%20toán/vibe%20code/group_work/AIAI-main/AIAI-main/.gitignore)
Bổ sung:
- `google-services.json`, `GoogleService-Info.plist`
- `*.keystore`, `*.jks`
- `sentry.properties`
- `firebase-admin-key.json`

---

## Verification Plan

### Automated Tests
- `pytest fleet-route-optimizer-cvrptw/tests/ -v` — Solver unit tests pass
- `npx tsc --noEmit` trong mobile — 0 TypeScript errors
- Chạy `test_analysis.py` trên sample JSONL → verify markdown report output

### Manual Verification
- Review LoadingScreen: skeleton shimmer animation mượt, không giật
- Review MapTimeline: lock/unlock POI có haptic + scale bounce
- Review ItineraryForm: inline validation thay Alert, character counter hoạt động
- Review ErrorRecoveryCard: gradient strip + actionable Vietnamese copy
- Review HotelFallbackBanner: nhất quán style với NetworkBanner
- Review CI workflow: GitHub Actions YAML valid syntax
- Review SECURITY_CHECKLIST.md: tất cả sensitive files đã ignored
