# Phase 3 (V2): Robust OSRM Integration & Matrix Caching

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Integrate `Hue_OSRM_Data` via Docker, rebuild `DistanceCacheService` to utilize OSRM's `/table` API for $O(1)$ matrix fetching, adapt SQLite schema to support multi-modal (`mode`), and modify OR-Tools solver to accept real OSRM durations instead of the Haversine/Speed heuristic.

**Architectural Updates:**
- Mảng Dữ Liệu Tĩnh: Chuyển hoàn toàn từ tính toán Haversine sang truy xuất `DistanceCacheService`.
- Tối ưu API: Gọi `/table/v1` để lấy ma trận N*N trong 1 call duy nhất, thay vì gọi `/route/v1` N^2 lần.
- Multi-modal: Lưu trữ cache theo `mode` (`taxi`, `bus`, `walking`). Walking dùng Heuristic Fallback (km / 5km/h).
- OR-Tools Core: Cập nhật `ortools_impl.py` để ưu tiên sử dụng `duration_matrix` nếu có.

---

## 📋 Comprehensive Test Cases Specification

Chúng ta sẽ đảm bảo chất lượng thông qua TDD với các test cases sau:

### 1. `test_distance_cache.py` (New file)
- `test_schema_migration`: DB khởi tạo thành công với bảng `distances_v2` chứa cột `mode`.
- `test_osrm_table_parsing`: Giả lập HTTP Response từ `/table/v1`, kiểm tra cache lưu đúng N*N cặp.
- `test_cache_hit_prevents_api_call`: Gọi 2 lần cùng ma trận, lần 2 không phát sinh HTTP call.
- `test_walking_mode_heuristic`: Khi gọi `WALKING`, hệ thống tự tính `duration_min = distance_km / (5km/h)` mà không gọi OSRM.
- `test_osrm_fallback_to_haversine`: Giả lập OSRM server chết (Timeout), service tự động fallback về tính Haversine.

### 2. `test_ortools_impl.py` (Update)
- `test_solver_uses_duration_matrix`: Truyền `duration_matrix` vào `ProblemData`, kiểm tra OR-Tools KHÔNG dùng công thức `distance/speed` nữa.
- `test_service_time_integration`: `service_time` (chính là visit_duration của POI) phải được cộng dồn ĐÚNG vào `duration_matrix` tại các node (trừ Depot).

### 3. `test_travel_plan_service.py` (Update)
- `test_service_prefetches_matrix`: Kiểm tra Orchestrator gọi hàm `build_matrix` trước khi chạy Stage 1 và Stage 2.

---

## 🛠 Detailed Implementation Steps

### Task 1: OSRM Docker Setup
- Mở `docker-compose.yml`, thêm service:
  ```yaml
  osrm-hue:
    image: ghcr.io/project-osrm/osrm-backend:v5.24.0
    container_name: routing_osrm_hue
    restart: always
    ports:
      - "5000:5000"
    volumes:
      - ../Hue_OSRM_Data:/data:ro
    command: "osrm-routed --algorithm ch --max-table-size 100 /data/hue.osrm"
  ```
- Cập nhật `src/config/settings.py` để chứa `OSRM_BASE_URL` (mặc định `http://localhost:5000`).

### Task 2: Rebuild DistanceCacheService
- **Schema:** Đổi tên table cũ, tạo bảng mới:
  `locations (hash, lat, lon)`
  `distances (from_hash, to_hash, mode, distance_km, duration_min)`
- **API `build_matrix(locations: List[Location], mode: TransportMode) -> Dict`:**
  - Lọc ra các điểm chưa có trong cache.
  - Định dạng URL: `/table/v1/driving/lon1,lat1;lon2,lat2...?annotations=distance,duration`
  - Ghi toàn bộ kết quả vào SQLite.
  - Trả về Dictionary mapping `((lat1,lon1), (lat2,lon2)) -> (dist, dur)`.
- **Heuristic:** Nếu `mode == WALKING`, lấy cache của `TAXI`, chia distance cho 5km/h = 83 mét/phút. Nếu OSRM lỗi, dùng Haversine.

### Task 3: Core Solver Matrix Update
- Mở `src/core/solvers/ortools_impl.py`.
- Sửa đổi hàm `_create_time_callback`:
  - Nếu `problem_data.get('duration_matrix')` tồn tại: dùng giá trị này + `service_time`.
  - Nếu không: dùng logic cũ `distance / speed + service_time`.

### Task 4: Travel Plan Service Integration
- Mở `src/services/travel_plan_service.py`.
- Khởi tạo `self.distance_cache = DistanceCacheService()`.
- Trong hàm `plan()`:
  - Gộp tất cả tọa độ (Hotels + POIs) thành một danh sách unique.
  - Gọi `matrix = self.distance_cache.build_matrix(all_locations, TransportMode.TAXI)`.
- Cập nhật `POIAllocator._score()`: Truyền `matrix` vào để lấy `geo_score` thực tế thay vì Haversine.
- Cập nhật `TravelSolverAdapter.build_problem_data()`: Bốc `dist_km` và `dur_min` từ `matrix` ra thành 2 mảng `distance_matrix` (2D) và `duration_matrix` (2D), nhúng vào `ProblemData` trả về cho Solver.

### Task 5: End-to-End TDD Execution
- Chạy TDD Red-Green cho `test_distance_cache.py`.
- Chạy TDD Red-Green cho `test_ortools_impl.py`.
- Đảm bảo toàn bộ 28 tests cũ + tests mới đều Pass.
- Chạy thử Server với Docker OSRM đang bật để kiểm nghiệm tính thực tế.

---
**Review & Approval:** Vui lòng xác nhận bản plan chi tiết với độ phủ Test này đã đạt yêu cầu để tôi bắt đầu dùng subagent thực thi Phase 3!
