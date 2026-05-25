# Implementation Plan — Sprint 2: Error Resilience & Network (Phase 2)

Chúng ta triển khai Phase 2 nhằm tối ưu hóa khả năng chịu lỗi, khả năng phục hồi mạng và cải thiện trải nghiệm người dùng bằng cách xử lý lỗi có cấu trúc từ Solver qua Gateway đến Mobile App.

---

## User Review Required

> [!IMPORTANT]
> **1. Circuit Breaker tại Gateway**
> Nếu Solver thất bại liên tiếp 5 lần, Gateway sẽ kích hoạt Circuit Breaker trong 30 giây, trả về lỗi ngay lập tức mà không gửi tiếp yêu cầu lên Solver.
> 
> **2. Cơ chế Idempotency chống Spam**
> Nhận `X-Idempotency-Key` từ header của yêu cầu gửi lên Gateway, lưu vết kết quả xử lý trong bộ nhớ để tránh xử lý trùng lặp khi người dùng click liên tục.
> 
> **3. Validate Prompt**
> Enforce validation prompt từ 10 đến 500 ký tự tại cả Mobile và Gateway.

---

## Proposed Changes

### Component 1: Solver (Layer 4)

Định nghĩa mã lỗi có cấu trúc và cập nhật service để ném ra các mã lỗi này.

#### [NEW] [errors.py](file:///d:/tư duy tính toán/vibe code/group_work/AIAI-main/AIAI-main/fleet-route-optimizer-cvrptw/src/models/errors.py)
- Định nghĩa `ErrorCode` Enum: `NO_FEASIBLE_ROUTE`, `BUDGET_EXCEEDED`, `TOO_MANY_LOCKED`, `OSRM_UNREACHABLE`, `LLM_EXTRACTION_FAILED`, `LLM_PARSE_ERROR`.
- Tạo custom `SolverException(Exception)` nhận `error_code` và `message`.

#### [MODIFY] [travel_plan_service.py](file:///d:/tư duy tính toán/vibe code/group_work/AIAI-main/AIAI-main/fleet-route-optimizer-cvrptw/src/services/travel_plan_service.py)
- Import `ErrorCode` và `SolverException`.
- Pre-flight validate locked POIs: Nếu số điểm ghim nhiều hơn tổng số lượng địa điểm của các ngày hoặc tổng thời lượng ghim lớn hơn tổng quỹ thời gian hoạt động, trả về `TOO_MANY_LOCKED`.
- Cập nhật `_validate_budget`: Nếu sau khi đã thử giảm bớt địa điểm không khóa mà vẫn vượt ngân sách, ném `SolverException(ErrorCode.BUDGET_EXCEEDED)`.
- Cập nhật `build_matrix`: Nếu OSRM sập/không truy cập được:
  - Nếu có dữ liệu cache đầy đủ, tiếp tục xử lý.
  - Nếu không có cache và OSRM sập, thay vì chạy Haversine ngầm mà không báo gì, chúng ta có thể trả về cảnh báo "Best-effort" bằng cách chèn note `"BEST_EFFORT_HAVERSINE"` vào `validation_notes`. Nếu sập hoàn toàn không thể khởi tạo hành trình, ném `OSRM_UNREACHABLE`.

#### [MODIFY] [routes.py](file:///d:/tư duy tính toán/vibe code/group_work/AIAI-main/AIAI-main/fleet-route-optimizer-cvrptw/src/api/routes.py)
- Bắt `SolverException` trong endpoint `/plan` và `/re-route` để trả về status 400 hoặc 422 kèm payload chứa `error_code` và `message` rõ ràng.

---

### Component 2: Gateway (Layer 2/3)

Cấu hình Circuit Breaker, Idempotency, validate đầu vào và propagate lỗi có cấu trúc qua SSE.

#### [MODIFY] [config.py](file:///d:/tư duy tính toán/vibe code/group_work/AIAI-main/AIAI-main/layer2_3_gateway/app/config.py)
- Thêm cấu hình: `SOLVER_TIMEOUT = 120.0`.

#### [MODIFY] [layer4_client.py](file:///d:/tư duy tính toán/vibe code/group_work/AIAI-main/AIAI-main/layer2_3_gateway/app/services/layer4_client.py)
- Tích hợp lớp `CircuitBreaker` theo dõi số lỗi liên tiếp của Solver. Nếu đạt 5 lỗi liên tiếp, chuyển trạng thái sang `OPEN` trong 30s.
- Nếu Circuit Breaker đang `OPEN`, chặn cuộc gọi Solver ngay lập tức và ném lỗi `CIRCUIT_BREAKER_OPEN`.
- Phân biệt lỗi Solver (`NO_FEASIBLE_ROUTE`, v.v.) và lỗi `TIMEOUT` (httpx.TimeoutException). Trả về payload chứa `error_code` tương ứng.

#### [MODIFY] [trip_planner.py](file:///d:/tư duy tính toán/vibe code/group_work/AIAI-main/AIAI-main/layer2_3_gateway/app/api/trip_planner.py)
- Validate prompt đầu vào: Từ 10 đến 500 ký tự. Nếu không đạt, trả về `LLM_PARSE_ERROR` lập tức.
- Tích hợp cơ chế Idempotency dùng một bộ nhớ đệm (in-memory dict với TTL) lưu vết các yêu cầu đang/đã xử lý theo `X-Idempotency-Key`.
- Cập nhật `plan_trip_stream` để yield đúng cấu trúc lỗi có mã hóa cho Mobile.

---

### Component 3: Mobile (Layer 5)

Lắng nghe trạng thái mạng, hiển thị Smart Error UI và xử lý Race Conditions.

#### [NEW] [useNetworkStatus.ts](file:///d:/tư duy tính toán/vibe code/group_work/AIAI-main/AIAI-main/mobile layer/AITravelOptimizer/app/hooks/useNetworkStatus.ts)
- Dùng `@react-native-community/netinfo` để export hook `useNetworkStatus()` trả về trạng thái offline/online.

#### [NEW] [ErrorRecoveryCard.tsx](file:///d:/tư duy tính toán/vibe code/group_work/AIAI-main/AIAI-main/mobile layer/AITravelOptimizer/app/components/ErrorRecoveryCard.tsx)
- UI card thông minh hiển thị theo từng mã lỗi cụ thể:
  - `BUDGET_EXCEEDED` -> Gợi ý: "Giảm bớt địa điểm hoặc tăng ngân sách" kèm 4 tùy chọn phục hồi.
  - `TOO_MANY_LOCKED` -> Gợi ý: "Bạn đang ghim quá nhiều điểm, hãy bỏ ghim bớt".
  - `OSRM_UNREACHABLE` -> Gợi ý: "Máy chủ định tuyến OSRM đang ngoại tuyến. Hãy thử lại hoặc chuyển sang Haversine".
  - `TIMEOUT` -> Gợi ý: "Server quá tải. Vui lòng tạo bản nhẹ hơn hoặc thử lại sau".
  - `LLM_PARSE_ERROR` -> Gợi ý: "AI không hiểu được mô tả của bạn. Hãy viết rõ ràng hơn".

#### [NEW] [NetworkBanner.tsx](file:///d:/tư duy tính toán/vibe code/group_work/AIAI-main/AIAI-main/mobile layer/AITravelOptimizer/app/components/NetworkBanner.tsx)
- Banner màu cam/đỏ overlay hiển thị trên toàn ứng dụng khi mất mạng (`isConnected === false`).

#### [MODIFY] [useTripPipeline.ts](file:///d:/tư duy tính toán/vibe code/group_work/AIAI-main/AIAI-main/mobile layer/AITravelOptimizer/app/hooks/useTripPipeline.ts)
- Thực hiện **Pre-flight health check**: Kiểm tra nếu mất mạng hoặc Gateway down thì block và hiện lỗi ngay, không mở SSE stream.
- Quản lý đóng SSE cũ khi "Retry" để tránh Race Conditions.
- Auto-reconnect SSE nếu mất mạng dưới 5 giây. Nếu trên 5 giây, dừng và hiện banner lỗi.

#### [MODIFY] [LoadingScreen.tsx](file:///d:/tư duy tính toán/vibe code/group_work/AIAI-main/AIAI-main/mobile layer/AITravelOptimizer/app/screens/LoadingScreen.tsx)
- Tích hợp `ErrorRecoveryCard` khi có lỗi.
- Đổi nút Retry sang cơ chế kích hoạt lại pipeline an toàn.

#### [MODIFY] [ItineraryFormScreen.tsx](file:///d:/tư duy tính toán/vibe code/group_work/AIAI-main/AIAI-main/mobile layer/AITravelOptimizer/app/screens/ItineraryFormScreen.tsx)
- Thêm Debounce 2 giây cho nút submit.
- Validate độ dài prompt: 10 - 500 ký tự.

#### [MODIFY] [HomeScreen.tsx](file:///d:/tư duy tính toán/vibe code/group_work/AIAI-main/AIAI-main/mobile layer/AITravelOptimizer/app/screens/HomeScreen.tsx)
- Thêm Debounce 2 giây cho nút submit và validate độ dài prompt.

---

## Verification Plan

### Automated Tests
- Khởi chạy test suite kiểm tra code:
  `cd fleet-route-optimizer-cvrptw && python -m pytest tests/ -v`

### Manual Verification
1. **Chống spam**: Click liên tiếp vào nút "Next Step" -> Verify chỉ chuyển màn hình Loading 1 lần duy nhất nhờ debounce.
2. **Mất kết nối mạng**: Bật Airplane Mode -> Verify banner mất kết nối hiện lập tức. Tắt Airplane Mode < 5s -> Verify SSE kết nối lại tự động.
3. **Smart Error Card**: Nhập prompt vượt ngân sách -> Verify thẻ `ErrorRecoveryCard` hiển thị gợi ý thông minh của `BUDGET_EXCEEDED`.
4. **Circuit Breaker**: Gửi liên tiếp 5 yêu cầu lỗi cực nặng -> Gửi yêu cầu thứ 6 -> Verify lỗi được trả về ngay lập tức dạng `CIRCUIT_BREAKER_OPEN`.
