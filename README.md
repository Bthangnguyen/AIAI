# 🗺️ AI Travel Optimizer — Routing Engine (Hệ Thống Tối Ưu Lộ Trình Du Lịch)

> Hệ thống tối ưu hóa lịch trình du lịch đa ngày thông minh sử dụng thuật toán OR-Tools (CVRPTW), LLM Intent Extraction, PostGIS Spatial Search, và hệ thống kiểm chuẩn chất lượng trải nghiệm du lịch Việt Nam độc quyền.

---

## 📐 Kiến trúc hệ thống (System Architecture)

Hệ thống được thiết kế theo mô hình **Multi-Layered Architecture (5 Layers)** nhằm đảm bảo tính độc lập, dễ mở rộng và cô lập luồng dữ liệu (DB I/O Isolation) tối đa.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               Mobile App (Layer 5)                                     │
│                     React Native / Expo — Giao diện di động                            │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │ HTTP POST /plan_trip hoặc Streaming SSE
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        Layer 2 & 3 — Gateway (Orchestrator - Port 8001)                │
│  ┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────────┐  │
│  │ L2: LLM Intent       │    │ L3: Spatial PostGIS  │    │ Layer 2/3 Extras:        │  │
│  │ Extractor            │───>│ & pgvector Embed     │───>│ - Utility Scorer         │  │
│  │ (Instructor Pydantic)│    │ (Force + Hybrid Fill)│    │ - Narrative (Vietnamese) │  │
│  └──────────────────────┘    └──────────────────────┘    └──────────────────────────┘  │
│  FastAPI · Async Engine · OpenAI Embeddings · slowapi Rate Limiting                     │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │ HTTP POST /plan hoặc /plan-multi
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                    Layer 4 — Core Routing Engine (OR-Tools - Port 8000)                │
│  ┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────────┐  │
│  │ CVRP Solver (OR-Tools)│    │ Constraints & Dim:   │    │ Post-Solve Pipeline:     │  │
│  │ - Drop Penalty weight│───>│ - Fatigue Capacity   │───>│ - Itinerary Validator    │  │
│  │ - locked_pois skip   │    │ - Outdoor heat 12-14h│    │ - RestBreakInserter      │  │
│  └──────────────────────┘    └──────────────────────┘    └──────────────────────────┘  │
│  FastAPI · SQLite Distance Cache · JIT Re-route · Diversity Scorer · Multi-Planner     │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │ HTTP OSRM
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         OSRM Backend (Self-hosted Routing Server - Port 5001)           │
│                 Pre-built OSM map data: Thừa Thiên Huế (hue.osrm)                      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Cấu trúc thư mục chi tiết & Ghi chú phân hệ (Directory Structure & WBS)

Dưới đây là sơ đồ cấu trúc mã nguồn được phân bổ cụ thể cho nhóm **8 người** (4 App, 2 Web, 2 POIs):

```
Routing Engine/
├── fleet-route-optimizer-cvrptw/          # 🧠 LAYER 4: CORE SOLVER (Python FastAPI)
│   ├── src/
│   │   ├── api/
│   │   │   ├── routes.py                  # Endpoints chính: /plan, /plan-multi, /re-route
│   │   │   └── dependencies.py            # Middleware xác thực API key
│   │   ├── core/
│   │   │   └── solvers/
│   │   │       ├── base.py                # Định nghĩa abstract BaseSolver
│   │   │       ├── factory.py             # Khởi tạo Solver theo cấu hình
│   │   │       ├── ortools_solver.py      # Lớp bao OR-Tools solver
│   │   │       └── ortools_impl.py        # 💥 [QUAN TRỌNG] Cài đặt CVRPTW, Fatigue, Tránh nắng nóng trưa
│   │   ├── models/
│   │   │   ├── domain.py                  # Domain models: POI, Hotel, Itinerary, Constraints
│   │   │   └── api.py                     # API Schemas nhận vào và trả ra
│   │   ├── services/
│   │   │   ├── travel_plan_service.py     # Điều phối chính: Gọi solver + check budget + validator
│   │   │   ├── travel_solver.py           # Chuyển đổi dữ liệu domain -> OR-Tools problem
│   │   │   ├── poi_allocator.py           # Stage 1: Phân bổ POI về từng ngày (Heuristic)
│   │   │   ├── distance_cache.py          # SQLite Cache tránh gọi OSRM lặp lại
│   │   │   ├── itinerary_validator.py     # 🔍 [MỚI] Bộ kiểm tra 4 quy tắc vàng chất lượng tour
│   │   │   ├── rest_inserter.py           # ☕ [MỚI] Tự động chèn stop nghỉ ngơi (__rest_break__)
│   │   │   ├── diversity_scorer.py        # 📊 [MỚI] Tính độ đa dạng thể loại và gợi ý tráo đổi điểm
│   │   │   └── multi_planner.py           # ⚡ [MỚI] Bộ sinh 3 phương án (Cân bằng, Tiết kiệm, Chill)
│   │   ├── config/                        # Cấu hình biến môi trường và log
│   │   └── app.py                         # FastAPI App entrypoint
│   └── tests/                             # Bộ kiểm thử gồm 90+ testcases tự động
│
├── layer2_3_gateway/                      # 🔍 LAYER 2 & 3: LLM & SPATIAL GATEWAY
│   ├── app/
│   │   ├── api/
│   │   │   └── trip_planner.py            # API Gateway: /plan_trip, /plan_trip_stream (SSE)
│   │   ├── models/
│   │   │   └── poi.py                     # PointOfInterest DB Model (PostGIS geography + pgvector)
│   │   ├── schemas/
│   │   │   └── trip.py                    # Định nghĩa LLMDataContract và POIResponse
│   │   ├── services/
│   │   │   ├── llm_extractor.py           # Layer 2: Instructor + OpenAI phân tích prompt thành JSON
│   │   │   ├── spatial_filter.py          # Layer 3: Truy vấn PostGIS ST_DWithin + pgvector Cosine
│   │   │   ├── embedding_service.py       # Tạo vector nhúng 1536 chiều từ tags địa điểm
│   │   │   ├── layer4_client.py           # Client giao tiếp HTTP qua Layer 4 Solver
│   │   │   ├── utility_scorer.py          # 🎯 [MỚI] Chấm điểm POI dựa trên 8 chiều hữu ích
│   │   │   └── narrative_generator.py     # ✍️ [MỚI] Tạo thuyết minh lộ trình tiếng Việt tự động
│   │   ├── database.py                    # Kết nối database không đồng bộ AsyncSession
│   │   └── main.py                        # Điểm khởi chạy Gateway Uvicorn
│   ├── ingestion/
│   │   └── ingest_pois.py                 # Tool import danh sách POI từ CSV vào PostgreSQL
│   └── run_gateway.py                     # Entrypoint chạy gateway với SelectorEventLoop cho Windows
│
├── mobile layer/                          # 📱 LAYER 5: MOBILE APP (React Native Expo)
│   └── AITravelOptimizer/                 # Khởi tạo bằng Ignite template + TypeScript
│       ├── app/                           # Màn hình điều hướng Expo Router
│       ├── assets/                        # Hình ảnh, font chữ
│       └── package.json                   # Các thư viện di động
│
└── fleet-route-optimizer-cvrptw/webui/    # 🌐 WEBSITE WORKSPACE (Next.js)
    ├── src/
    │   ├── app/
    │   │   └── page.tsx                   # Trang chủ điều phối Chat Workspace, Leaflet Map, Playback
    │   ├── components/                    # Các components UI: ChatPanel, RouteComparison, Map...
    │   └── lib/
    │       └── api.ts                     # Tích hợp API gọi Gateway
```

---

## 🛠️ Chi tiết nâng cấp nổi bật (Scheduling Layer v2 Upgrades)

Hệ thống đã được nâng cấp mạnh mẽ từ việc lập lịch dựa trên khoảng cách thuần túy lên tối ưu hóa **Trải nghiệm du khách và Sự hài lòng (Quality & Satisfaction)**:

### 1. Chỉ số Hữu ích (POI Utility-based Optimization)
* **Ý tưởng:** Gateway tính điểm `utility_score` (từ 0.0 đến 1.0) cho mỗi địa điểm dựa trên 8 chiều: Mức độ khớp sở thích (28%), Chất lượng reviews (18%), Đặc sản bản địa (14%), Trải nghiệm độc đáo (10%), Ngân sách (10%), Sự thoải mái (10%), Khoảng cách (6%), Độ đa dạng đóng góp (4%).
* **Áp dụng:** Điểm số này được chuyển thành trọng số bỏ điểm phạt (Drop Penalty disjunction) trong OR-Tools theo công thức: `int(100_000 + utility * 900_000)`. Điểm có độ hữu ích cao sẽ cực kỳ khó bị bộ giải thuật bỏ qua.

### 2. Tránh nắng nóng & Trực quan hóa Fatigue (Sức bền)
* **Tránh nắng trưa:** Tự động phát hiện các địa điểm ngoài trời (`is_outdoor = True`) và sử dụng bộ lọc OR-Tools `RemoveInterval` loại trừ khung giờ nắng gắt **12:00 - 14:00**.
* **Ràng buộc Fatigue:** Định nghĩa một chiều tích lũy Fatigue tăng dần theo độ nặng tham quan (nhẹ=1, vừa=2, nặng=3). Giới hạn sức bền tối đa mỗi ngày dựa theo phong cách chuyến đi (Chill: 10, Balanced: 15, Intense: 20) giúp du khách không bị kiệt sức.

### 3. Bộ kiểm chuẩn chất lượng (Itinerary Validator Framework)
Post-solve kiểm tra tự động lộ trình qua 4 quy tắc vàng:
1.  **Thiếu bữa trưa (`meal_missing`):** Cảnh báo nếu lịch trình đi liên tục qua khung giờ 11:30 - 13:30 mà không ghé quán ăn/nhà hàng.
2.  **Quá tải liên tục (`consecutive_heavy`):** Cảnh báo nếu xếp > 2 địa điểm mệt nặng liên tiếp.
3.  **Nắng nóng cực độ (`outdoor_heat`):** Nhắc nhở nếu ghé điểm ngoài trời lúc 12:00 - 14:00.
4.  **Thiếu nghỉ chân (`rest_needed`):** Tự động phát hiện hoạt động > 180 phút liên tục không nghỉ.

### 4. Tự động chèn điểm nghỉ chân (`RestBreakInserter`)
* Khi du khách đi bộ tham quan liên tục quá 180 phút mà không có điểm dừng ẩm thực/spa, hệ thống sẽ tự động chèn một điểm dừng ảo gọi là **`__rest_break__`** (Nghỉ ngơi nhẹ 20 phút) để đảm bảo sức khỏe.

### 5. Thuyết minh tiếng Việt tự động (Narrative Generator)
* Không dựa vào LLM chậm chạp khi trả kết quả đồng bộ. Hệ thống sử dụng mẫu template ngữ cảnh tiếng Việt động để viết tiêu đề ngày, mô tả chi tiết và lý do tối ưu hóa lộ trình dựa trên thể loại địa điểm (ví dụ: *"Ngày hội ngộ ẩm thực miền Hương Ngự"*, *"Hành trình khám phá nét cổ kính lăng tẩm"*).

### 6. Đa dạng hóa phương án (Multi-Plan / `POST /plan-multi`)
* Cho phép sinh cùng lúc 3 phương án: **Cân bằng (Balanced)**, **Tiết kiệm (Budget)**, và **Thoải mái (Chill)**.
* Sử dụng bộ lọc chống lặp: Địa điểm đã dùng ở phương án 1 sẽ bị giảm **25% điểm hữu ích (utility)** ở phương án sau, đảm bảo 3 lộ trình có độ khác biệt về địa điểm (Jaccard Variance) lớn hơn 75%.

---

## 🚀 Hướng dẫn khởi động nhanh toàn bộ hệ thống (Quick Start)

Để chạy thử nghiệm toàn bộ hệ thống local, thực hiện theo thứ tự sau:

### Bước 1: Khởi động Database & OSRM Server
1. Cài đặt và bật Docker Desktop.
2. Chạy PostgreSQL với PostGIS & pgvector:
   ```bash
   cd layer2_3_gateway
   docker-compose up -d
   ```
3. Chạy OSRM server cho Huế tại cổng 5001:
   ```bash
   docker run -t -i -p 5001:5000 -v ./Hue_OSRM_Data:/data ghcr.io/project-osrm/osrm-backend:latest osrm-routed --algorithm ch /data/hue.osrm
   ```

### Bước 2: Khởi động Core Solver (Port 8000)
```bash
cd fleet-route-optimizer-cvrptw
pip install -r requirements.txt
python -m src.app
```
*Server Solver sẽ khởi chạy tại cổng `http://localhost:8000`.*

### Bước 3: Khởi động API Gateway (Port 8001)
```bash
cd layer2_3_gateway
pip install -r requirements.txt
# Chạy thông qua script tối ưu hóa event loop trên Windows
python run_gateway.py
```
*Gateway sẽ khởi chạy tại cổng `http://localhost:8001`.*

### Bước 4: Khởi động Web Workspace (Port 3000)
```bash
cd fleet-route-optimizer-cvrptw/webui
npm install
npm run dev
```
*Mở trình duyệt truy cập `http://localhost:3000` để bắt đầu trải nghiệm.*

---

## ⚡ Phân hệ kiểm thử tự động & Nâng cấp Trải nghiệm (Phase 3 Upgrades)

Trong giai đoạn **Phase 3 (Real-World Testing & UI Polish)**, hệ thống đã được gia cố toàn diện để đạt tiêu chuẩn phát hành thương mại:

### 1. Kịch bản kiểm thử 100 Prompt & Phân tích tự động
- **100 Prompts Suite**: Định nghĩa 100 test case thực tế tại `testing/all_100_testcases.json`, bao phủ đầy đủ các nhóm hành vi từ đi tour Huế ngắn ngày, budget cực thấp, cho tới ghim quá nhiều điểm tham quan (Locked POIs), đi nhóm đông người, lỗi mất kết nối mạng.
- **Batch Test Runner (`run_pipeline_test.py`)**: Script kiểm thử tự động gửi batch các prompt song song qua Gateway SSE stream, tự động bắt lỗi và tính điểm chất lượng (chất lượng lăng tẩm, thời gian di chuyển, bữa trưa, Fatigue, v.v.).
- **Auto logs analysis (`testing/test_analysis.py`)**: Đọc file kết quả `results_summary.jsonl`, tự động tính toán tỷ lệ Pass/Fail theo nhóm prompt và xuất ra báo cáo markdown `testing/analysis_report.md` trực quan bằng biểu đồ ASCII.

### 2. Skeletons & Transitions chuẩn High-End (Mobile Layer)
- **Shimmer Placeholder (`SkeletonCard`)**: Thay thế Loading Spinner truyền thống bằng hiệu ứng mờ nhấp nháy chuyển động staggered mượt mà, mô phỏng đúng cấu trúc các thẻ địa điểm thực tế.
- **Stagger Anim (`SkeletonList`)**: Các card xuất hiện xen kẽ với delay 100ms nhẹ nhàng dùng `react-native-reanimated`.
- **Gesture Lock & Elapsed Time**: Loading Screen tự khóa thao tác vuốt ngược về (`gestureEnabled: false`) và có bộ đếm thời gian thực ("Đang tối ưu... 15s") tăng tính tương tác trực quan.

### 3. Edge Cases & Khả năng Tự Phục Hồi (Error Resilience)
- **Khách sạn mặc định (Hotel Fallback)**: Khi người dùng không cung cấp tọa độ hoặc budget bị giới hạn quá thấp khiến không thể thuê khách sạn mong muốn, hệ thống sẽ tự động chuyển về **Default Central Hotel (Huế)**, gửi cờ `hotel_fallback: true` về client để hiển thị `HotelFallbackBanner` thông minh hướng dẫn người dùng chỉnh sửa.
- **Ràng buộc Ghim Cá nhân (POI Locking)**: Du khách có thể nhấn khóa/mở khóa từng địa điểm trực tiếp trên timeline di động. Nút khóa có hiệu ứng **Scale Bounce (Spring zoom 1.3 -> 1.0) kết hợp haptic feedback** cực kỳ sinh động và tương tác cao.
- **Empty State**: Thiết kế màn hình minh họa khi người dùng xóa sạch stop, hướng dẫn nhấn nút thêm điểm từ AI Chat mượt mà.

---

## 📄 Bản quyền (License)
Dự án được bảo hộ dưới giấy phép MIT License. Bản quyền thuộc về **AIAI Travel Team** (2026).
