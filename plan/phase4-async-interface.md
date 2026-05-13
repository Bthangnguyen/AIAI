# Phase 4: Async Interface & Re-Route cho Layer 3

> Brainstorming + Plan — Cung cấp interface async hoàn chỉnh để Layer 3 (FastAPI Gateway) gọi vào Layer 4

---

## 1. Phân tích hiện trạng

### Vấn đề hiện tại
| Thành phần | Hiện trạng | Vấn đề |
|---|---|---|
| `POST /plan` | Sync (blocking) | OR-Tools solver chạy CPU-bound → block event loop FastAPI |
| `POST /solve-stream` | SSE legacy (threading) | Dùng `threading.Thread` + `queue.Queue`, không dùng `asyncio.to_thread` |
| Re-route | Không tồn tại | Chưa có endpoint cho du khách thay đổi lịch trình giữa chừng |
| `TravelPlanService.plan()` | Sync | Gọi `DistanceCacheService.build_matrix()` (I/O-bound) + `solver.solve()` (CPU-bound) đều blocking |

### Thiết kế mục tiêu
```
Layer 3 (FastAPI Gateway)
   │
   ├── POST /plan              → async, trả JSON (full itinerary)
   ├── POST /plan/stream       → async, trả SSE (log + kết quả realtime)
   ├── POST /re-route          → async, trả JSON (lịch trình cập nhật cho phần còn lại)
   └── GET  /health            → async (giữ nguyên)
```

---

## 2. Brainstorming: `/re-route` là gì?

**Tình huống:** Du khách đang ở POI_2 (lúc 14:00), còn 3 POIs chưa đi (POI_3, POI_4, POI_5).
Mapbox Live Traffic báo kẹt xe nghiêm trọng trên đường tới POI_3.
→ Layer 3 gửi **POST /re-route** tới Layer 4.

**Input của `/re-route`:**
```json
{
  "current_location": {"latitude": 16.46, "longitude": 107.59},
  "current_time_min": 840,
  "remaining_pois": ["poi_3", "poi_4", "poi_5"],
  "pois": [...],           // Full POI objects cho solver
  "hotel": {...},          // Hotel (return point)
  "day": {...},            // DayPlan (giữ nguyên end_time)
  "constraints": {...},
  "excluded_poi_ids": ["poi_3"]  // Optional: loại bỏ POI_3 vì kẹt xe
}
```

**Logic:**
1. Tạo depot ảo tại `current_location` (thay vì hotel).
2. Cập nhật `start_time_min = current_time_min`.
3. Lọc bỏ `excluded_poi_ids`.
4. Gọi lại `TravelSolverAdapter.solve_day()` chỉ cho các POIs còn lại.
5. Trả về `TravelItineraryDay` cập nhật.

**Đây chính xác là cơ chế JIT mà bạn đã mô tả** — Layer 3/App kiểm tra Mapbox Traffic, nếu cần thì gọi `/re-route` để Layer 4 tính lại.

---

## 3. Detailed Implementation Tasks

### Task 1: Async-ify `TravelPlanService.plan()` và `POST /plan`

**Files:**
- `src/services/travel_plan_service.py`
- `src/api/routes.py`

**Thay đổi:**
- Giữ nguyên `TravelPlanService.plan()` là hàm sync (OR-Tools không hỗ trợ async).
- Tại endpoint `POST /plan`, wrap bằng `asyncio.to_thread()`:
  ```python
  result = await asyncio.to_thread(
      travel_service.plan, request=request, ...
  )
  ```
- Thêm `threading.Lock` vào `TravelPlanService` để ngăn race condition khi 2 request gọi solver cùng lúc.

**Tests:**
- `test_plan_endpoint_is_async`: Gọi endpoint, verify nó không block (dùng `httpx.AsyncClient`).
- `test_plan_concurrent_returns_busy`: Gọi 2 lần liên tiếp, lần 2 phải trả lỗi `503 Busy`.

---

### Task 2: `POST /re-route` endpoint + `ReRouteRequest` model

**Files:**
- `src/models/api.py` — Thêm `ReRouteRequest`
- `src/services/travel_plan_service.py` — Thêm method `re_route()`
- `src/api/routes.py` — Thêm endpoint
- `tests/test_re_route.py` — Tests

**Model:**
```python
class ReRouteRequest(BaseModel):
    current_location: Location
    current_time_min: int
    remaining_poi_ids: List[str]
    pois: List[POI]
    hotel: Hotel
    day: DayPlan
    constraints: TravelConstraints
    excluded_poi_ids: Optional[List[str]] = None
```

**Service logic (`re_route()`):**
1. Filter `pois` to only include `remaining_poi_ids`, remove `excluded_poi_ids`.
2. Create virtual depot from `current_location`.
3. Override `day.start_time_min = current_time_min`.
4. Fetch matrix from OSRM (cache sẽ hit cho hầu hết các cặp).
5. Call `TravelSolverAdapter.solve_day()`.
6. Return updated `TravelItineraryDay`.

**Tests:**
- `test_reroute_basic`: 3 remaining POIs, exclude 1, verify 2 POIs in result.
- `test_reroute_updates_start_time`: Verify `start_time_min` is overridden.
- `test_reroute_uses_current_location_as_depot`: Verify depot is `current_location`, not hotel.
- `test_reroute_empty_remaining`: Edge case → return empty day.

---

### Task 3: `POST /plan/stream` — SSE cho Travel Planning

**Files:**
- `src/api/routes.py` — Thêm endpoint `/plan/stream`

**Thay đổi:**
- Dùng pattern tương tự `/solve-stream` nhưng cho travel domain.
- SSE events:
  ```
  event: log        data: {"message": "Stage 1: Allocating 15 POIs to 3 days..."}
  event: log        data: {"message": "Stage 2: Solving Day 0 (5 POIs)..."}
  event: progress   data: {"day": 0, "status": "solved", "pois": 5}
  event: progress   data: {"day": 1, "status": "solving", "pois": 4}
  event: result     data: {<full TravelItinerary JSON>}
  event: error      data: {"message": "..."}
  ```
- Sử dụng `asyncio.to_thread()` + `asyncio.Queue` thay vì `threading.Thread` + `queue.Queue`.

**Tests:**
- `test_plan_stream_returns_sse`: Verify `Content-Type: text/event-stream`.
- `test_plan_stream_emits_result_event`: Verify event cuối cùng chứa `TravelItinerary`.

---

### Task 4: Thread Safety & Concurrency Guards

**Files:**
- `src/services/travel_plan_service.py`

**Thay đổi:**
- Thêm `threading.Lock` + `_is_busy` flag (giống `SolverService` hiện tại).
- Expose `is_busy()` method cho health check.
- Update `/health` để báo status của cả `solver_service` và `travel_service`.

**Tests:**
- `test_health_reports_travel_busy`: Khi travel solver đang chạy, `/health` trả `busy`.
- `test_concurrent_plan_rejected`: Gửi 2 requests cùng lúc, 1 bị reject.

---

### Task 5: Full Integration & Regression

- Chạy toàn bộ test suite (35 tests cũ + tests mới).
- Verify server khởi động thành công.
- Git commit.

---

## 4. Test Cases Specification

| File | Test | Mô tả |
|---|---|---|
| `test_re_route.py` | `test_reroute_basic` | 3 POIs còn lại, exclude 1 → 2 POIs |
| `test_re_route.py` | `test_reroute_updates_start_time` | `start_time` = `current_time_min` |
| `test_re_route.py` | `test_reroute_uses_current_location_as_depot` | Depot = vị trí hiện tại |
| `test_re_route.py` | `test_reroute_empty_remaining` | Empty list → empty day |
| `test_async_plan.py` | `test_plan_endpoint_uses_async` | Verify `asyncio.to_thread` wrap |
| `test_async_plan.py` | `test_concurrent_plan_rejected` | 2nd request → 503 |
| `test_async_plan.py` | `test_health_reports_travel_busy` | Health shows busy state |
| `test_plan_stream.py` | `test_stream_returns_sse` | `Content-Type: text/event-stream` |
| `test_plan_stream.py` | `test_stream_emits_result` | Final event = `TravelItinerary` |

---

## 5. Dependency & Risk Assessment

| Risk | Mitigation |
|---|---|
| OR-Tools là CPU-bound, `asyncio.to_thread` chỉ offload sang threadpool | Đủ tốt cho 1-2 concurrent requests. Nếu cần scale, dùng Celery worker |
| Re-route gọi OSRM cho `current_location` mới → cache miss | Matrix nhỏ (1 depot + ≤5 POIs), OSRM local phản hồi <100ms |
| SSE connection bị drop giữa chừng | Client retry với `EventSource` auto-reconnect |

---

**Xác nhận để bắt đầu thực thi Phase 4!**
