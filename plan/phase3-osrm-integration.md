# Phase 3: OSRM Local Integration & Distance Caching

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Integrate the pre-processed `Hue_OSRM_Data` into the Routing Engine via Docker, and wire it up to `DistanceCacheService` to provide real-world travel times and distances for the Stage 2 Travel Solver.

**Quality Check on `Hue_OSRM_Data`:**
- Kích thước base map (`hue.osm.pbf`) là ~1.69MB, hoàn toàn hợp lý cho phạm vi thành phố Huế và vùng phụ cận.
- Đã chứa đủ các file compile cho thuật toán **CH (Contraction Hierarchies)** như `.hsgr` (6.2MB), `.ebg`, `.geometry`.
- Điều này có nghĩa là chúng ta **không cần** chạy lại các bước `osrm-extract` và `osrm-contract` gây tốn RAM/CPU. Chỉ cần chạy thẳng lệnh phục vụ `osrm-routed`.

---

## Architecture & Brainstorming

### 1. Docker Integration
Chúng ta sẽ thêm một service `osrm-hue` vào `docker-compose.yml` hiện tại. Service này dùng image `ghcr.io/project-osrm/osrm-backend` và mount thư mục `Hue_OSRM_Data`.

### 2. Xử lý Multi-modal (Walking vs Taxi)
**Vấn đề:** OSRM backend chỉ chạy **1 profile duy nhất** trên mỗi bản đồ compile (hiện tại 99% là `car.lua` / driving).
**Giải pháp cho Phase 3:**
- Mặc định sử dụng OSRM Huế này cho phương tiện `TAXI` và `BUS` (dùng chung routing ô tô).
- Đối với `WALKING`: Tạm thời áp dụng công thức **Heuristic Fallback** trong `DistanceCacheService`. Ta lấy khoảng cách vật lý của OSRM (distance) chia cho vận tốc đi bộ trung bình (ví dụ 5 km/h = 83 mét/phút) để ước tính thời gian đi bộ, thay vì dựng thêm một server OSRM `foot.lua` tốn tài nguyên.

### 3. Bộ nhớ đệm (SQLite Cache)
Dự án đã có sẵn `DistanceCacheService` dùng SQLite (`distance_cache.db`). Ta sẽ tái sử dụng nó hoàn toàn để giảm số lượng API calls tới OSRM:
- Lần 1 chạy: Missing cache -> Gọi OSRM `/table/v1/driving/...` -> Lưu vào SQLite.
- Lần 2 chạy (cùng danh sách POI): Hit cache -> Không gọi OSRM.

---

## Task 1: Thêm OSRM vào Docker Compose

**Files:**
- Modify: `docker-compose.yml`
- Modify: `src/config/settings.py`

- [ ] **Step 1: Update `docker-compose.yml`**
Add the following service:
```yaml
  osrm-hue:
    image: ghcr.io/project-osrm/osrm-backend:v5.24.0
    container_name: routing_osrm_hue
    restart: always
    ports:
      - "5000:5000"
    volumes:
      - ../Hue_OSRM_Data:/data:ro  # Read-only mount
    command: "osrm-routed --algorithm ch /data/hue.osrm"
```

- [ ] **Step 2: Update `settings.py`**
Ensure `OSRM_BASE_URL` can be overridden via ENV, default to `http://localhost:5000`.

---

## Task 2: Refactor DistanceCacheService cho Travel Domain

**Files:**
- Modify: `src/services/distance_cache.py`
- Modify: `tests/test_distance_cache.py` (Create new)

- [ ] **Step 1: Write tests**
Create tests for `DistanceCacheService` simulating OSRM responses.

- [ ] **Step 2: Update `distance_cache.py`**
- Đảm bảo hàm gọi `/table/v1/driving/` xử lý đúng mảng tọa độ `lng,lat`.
- Trích xuất cả `durations` (giây -> phút) và `distances` (mét -> km).
- **Multi-modal Hack:** Thêm logic tính toán `walking_duration`: `walk_min = (distance_m / 83.33)` (tương đương 5km/h).

---

## Task 3: Tích hợp Cache vào TravelPlanService

**Files:**
- Modify: `src/services/travel_plan_service.py`

- [ ] **Step 1: Inject Distance Cache**
- Trong quá trình khởi tạo `TravelPlanService`, khởi tạo `DistanceCacheService`.
- Trước Stage 1 (Allocator), gọi OSRM để lấy toàn bộ ma trận (Hotels + POIs) và nạp vào cache.

- [ ] **Step 2: Cập nhật hàm `_score()` trong POIAllocator**
- Thay vì dùng tính toán Haversine chay, cho phép `POIAllocator` sử dụng khoảng cách thực tế từ `DistanceCacheService` (nếu có) để scoring (tùy chọn, nâng cao độ chính xác).

- [ ] **Step 3: Cập nhật TravelSolverAdapter**
- Trong `TravelSolverAdapter`, khi build `ProblemData`, truyền thêm ma trận `distance_matrix` và `duration_matrix` thực tế từ cache (thay vì để OR-Tools tự tính Haversine). OR-Tools Solver đã hỗ trợ nhận matrix qua API.

---

## Task 4: API Testing (End-to-End)

- [ ] Chạy `docker-compose up -d osrm-hue`
- [ ] Gửi request chứa 3-5 POI thực tế tại Huế (ví dụ: Đại Nội, Lăng Tự Đức, Chợ Đông Ba).
- [ ] Xác nhận lộ trình trả về sử dụng thời gian di chuyển (travel_time_from_prev_min) thực tế từ OSRM chứ không phải Haversine thẳng.
