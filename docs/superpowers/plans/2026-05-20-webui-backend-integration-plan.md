# Khôi phục Tiếng Việt WebUI & Tích hợp Docker Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Khôi phục triệt để lỗi hiển thị font tiếng Việt (lỗi chữ) trên Next.js WebUI và khởi chạy, kiểm thử kết nối end-to-end với hệ thống Docker Backend (Gateway & OR-Tools Solver) đã được build sẵn.

**Architecture:** Sử dụng Git để khôi phục (selective revert) các file giao diện thuần túy chỉ bị lỗi chữ tiếng Việt; tiến hành sửa đổi thủ công các chuỗi văn bản UTF-8 bị hỏng hoặc double-encoded trong `page.tsx` và `api.ts` để bảo tồn logic API backend. Sử dụng Docker Compose khởi động nhanh các container, chạy health check và sử dụng Browser Engine kiểm thử trực quan luồng lập lịch trình.

**Tech Stack:** Next.js, React Leaflet, TailwindCSS, Docker Compose, PostgreSQL (PostGIS), FastAPI, OR-Tools Solver.

---

### Task 1: Khôi phục sạch Tiếng Việt từ Git (Git Selective Revert & Import Fix)

**Files:**
- Modify: `fleet-route-optimizer-cvrptw/webui/src/components/AITripChatPanel.tsx`
- Revert: Toàn bộ 22 files components/types/data chỉ bị lỗi font.

- [ ] **Step 1: Khôi phục 22 files chỉ bị lỗi font về trạng thái gốc bằng Git checkout**
  Run:
  ```powershell
  git checkout -- fleet-route-optimizer-cvrptw/webui/src/app/layout.tsx fleet-route-optimizer-cvrptw/webui/src/components/AddPlaceModal.tsx fleet-route-optimizer-cvrptw/webui/src/components/AgentStatusSteps.tsx fleet-route-optimizer-cvrptw/webui/src/components/BuildProgressSteps.tsx fleet-route-optimizer-cvrptw/webui/src/components/BuilderWorkspace.tsx fleet-route-optimizer-cvrptw/webui/src/components/ExamplePromptChips.tsx fleet-route-optimizer-cvrptw/webui/src/components/HomePage.tsx fleet-route-optimizer-cvrptw/webui/src/components/HomePromptBox.tsx fleet-route-optimizer-cvrptw/webui/src/components/ItineraryArtifact.tsx fleet-route-optimizer-cvrptw/webui/src/components/ItineraryMap.tsx fleet-route-optimizer-cvrptw/webui/src/components/ItineraryMapPanel.tsx fleet-route-optimizer-cvrptw/webui/src/components/ItineraryPreviewPanel.tsx fleet-route-optimizer-cvrptw/webui/src/components/MobilePhasePage.tsx fleet-route-optimizer-cvrptw/webui/src/components/MockAuthModal.tsx fleet-route-optimizer-cvrptw/webui/src/components/SavedTripsPage.tsx fleet-route-optimizer-cvrptw/webui/src/components/TimelineDayCard.tsx fleet-route-optimizer-cvrptw/webui/src/components/TimelinePlaceCard.tsx fleet-route-optimizer-cvrptw/webui/src/components/Toast.tsx fleet-route-optimizer-cvrptw/webui/src/components/TripControlPanel.tsx fleet-route-optimizer-cvrptw/webui/src/components/TripToolbar.tsx fleet-route-optimizer-cvrptw/webui/src/data/huePois.ts fleet-route-optimizer-cvrptw/webui/src/types/trip.ts
  ```
  Expected: Các file được đưa về trạng thái sạch của nhánh Git, chứa văn bản tiếng Việt có dấu chuẩn đẹp.

- [ ] **Step 2: Khôi phục file `AITripChatPanel.tsx` bằng git checkout**
  Run:
  ```powershell
  git checkout -- fleet-route-optimizer-cvrptw/webui/src/components/AITripChatPanel.tsx
  ```
  Expected: File được phục hồi nhưng lúc này dòng import `generateItinerary` sẽ bị sai.

- [ ] **Step 3: Chỉnh sửa lại import trong `AITripChatPanel.tsx` để tham chiếu đúng file mới**
  Sửa dòng import ở đầu file `AITripChatPanel.tsx`:
  ```typescript
  // Thay thế:
  import { draftTotals } from "@/lib/generateItinerary"
  // Thành:
  import { draftTotals } from "@/lib/mockItineraryFallback"
  ```
  Expected: Sửa thành công dòng import, không còn lỗi biên dịch Next.js do thiếu file `generateItinerary.ts`.

- [ ] **Step 4: Commit thay đổi khôi phục font ban đầu**
  Run:
  ```bash
  git add fleet-route-optimizer-cvrptw/webui/src/
  git commit -m "style(webui): revert corrupted font files and fix AI panel import"
  ```

---

### Task 2: Sửa chuỗi Tiếng Việt trong logic API (`api.ts` và `page.tsx`)

**Files:**
- Modify: `fleet-route-optimizer-cvrptw/webui/src/lib/api.ts`
- Modify: `fleet-route-optimizer-cvrptw/webui/src/app/page.tsx`

- [ ] **Step 1: Sửa các chuỗi double-encoded trong `api.ts` thành tiếng Việt UTF-8 chuẩn**
  Mở `fleet-route-optimizer-cvrptw/webui/src/lib/api.ts` và cập nhật các dòng có chứa ký tự lỗi:
  * Dòng 30:
    ```typescript
    destination: string = "Huế",
    ```
  * Dòng 52:
    ```typescript
    throw new Error(data.message || "Không thể tạo lịch trình hợp lệ")
    ```
  * Dòng 55:
    ```typescript
    // Cập nhật cache POI
    ```
  * Dòng 71:
    ```typescript
    // Ẩn khách sạn khỏi timeline chính nếu muốn, nhưng hiện tại cứ render để xem
    ```
  * Dòng 82:
    ```typescript
    title: `Ngày ${d.day_index + 1} (${d.date})`,
    ```
  * Dòng 114:
    ```typescript
    current_time_min: 8 * 60, // Giả sử re-route từ 8h sáng nếu reorder
    ```
  Expected: Lưu lại file thành công ở mã hóa UTF-8 sạch.

- [ ] **Step 2: Sửa các chuỗi bị lỗi chữ trong `page.tsx`**
  Mở `fleet-route-optimizer-cvrptw/webui/src/app/page.tsx` và tiến hành sửa:
  * Trong hàm `handleAddPoiBackend`:
    * `setToastMessage("Không thể thêm điểm này vào lịch trình (hết thời gian).")`
    * `content: \`Đã thêm \${poi.name} và tối ưu lại (qua OR-Tools).\``
    * `setToastMessage("Đã tối ưu lại lịch trình thành công.")`
    * `setToastMessage("Lỗi re-route: " + e.message)`
  * Trong hàm `handleRemovePlaceBackend`:
    * `setToastMessage("Lỗi server khi tính lại route.")`
    * `content: \`Đã xóa một địa điểm và tối ưu lại lịch trình.\``
    * `setToastMessage("Đã cập nhật lại lịch trình.")`
    * `setToastMessage("Lỗi re-route: " + e.message)`
  * Trong hàm `handleOptimizeDay`:
    * `setToastMessage(\`Đã tối ưu lại ngày \${dayNumber}.\`)`
  * Trong hàm `handleRebuild`:
    * `setToastMessage("Đã tạo lại lịch trình.")`
    * `setToastMessage("Lỗi tạo lại: " + e.message)`
  * Trong hàm `openSavedDraft`:
    * `content: \`Đã mở lại bản nháp \${nextDraft.destination} \${nextDraft.days.length} ngày.\``
  Expected: Tất cả Toast và thông báo hiển thị bằng tiếng Việt chuẩn chỉnh, không còn bất kỳ chữ lỗi `?` hay `Ð` nào.

- [ ] **Step 3: Commit các bản vá chữ tiếng Việt trong logic API**
  Run:
  ```bash
  git add fleet-route-optimizer-cvrptw/webui/src/lib/api.ts fleet-route-optimizer-cvrptw/webui/src/app/page.tsx
  git commit -m "fix(webui): fix double-encoded and corrupted Vietnamese strings in API logic"
  ```

---

### Task 3: Khởi chạy Docker Backend & Health Check

**Files:**
- None (Cơ sở hạ tầng & chạy container).

- [ ] **Step 1: Khởi chạy ứng dụng Docker Desktop trên Windows**
  Run (PowerShell):
  ```powershell
  Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
  ```
  Expected: Docker Desktop khởi chạy thành công trên khay hệ thống Windows.

- [ ] **Step 2: Đợi và kiểm tra trạng thái Docker daemon**
  Chạy lệnh kiểm thử trạng thái lặp lại mỗi 5 giây bằng cách gọi `docker info` cho đến khi daemon kết nối thành công:
  Run:
  ```powershell
  docker info
  ```
  Expected: Docker daemon phản hồi thông số đầy đủ (Exit code: 0).

- [ ] **Step 3: Khởi chạy cụm Solver và OSRM container**
  Run (PowerShell/CMD tại thư mục solver docker):
  ```powershell
  cd "d:\Workspaces\AI travel optimizer\Routing Engine\fleet-route-optimizer-cvrptw\docker"
  docker compose up -d
  ```
  Expected: Khởi động container `cvrptw-solver-backend`, `cvrptw-solver-frontend`, và `routing_osrm_hue` ở trạng thái Running mà không cần rebuild (đã build sẵn).

- [ ] **Step 4: Khởi chạy cụm Gateway và Postgres DB container**
  Run (PowerShell/CMD tại thư mục gateway):
  ```powershell
  cd "d:\Workspaces\AI travel optimizer\Routing Engine\layer2_3_gateway"
  docker compose up -d
  ```
  Expected: Khởi động container `travel-db` và `travel-gateway` thành công.

- [ ] **Step 5: Thực hiện Alembic database migration cho Gateway**
  Run:
  ```powershell
  docker compose exec app alembic upgrade head
  ```
  Expected: Chạy thành công các file migrations nâng cấp cấu trúc db PostGIS, phản hồi thành công từ alembic.

- [ ] **Step 6: Kiểm tra sức khỏe (Health Check) các dịch vụ cổng 8000 và 8001**
  Run:
  ```powershell
  curl http://localhost:8000/health
  curl http://localhost:8001/health
  ```
  Expected: Cả 2 endpoint đều trả về trạng thái `{"status": "ready"}` hoặc `{"status": "healthy"}`.

---

### Task 4: Khởi chạy WebUI Local & Kiểm thử trực quan

**Files:**
- None (Kiểm thử chức năng qua trình duyệt và log Next.js).

- [ ] **Step 1: Khởi động server phát triển Next.js cục bộ**
  Run (PowerShell tại thư mục `fleet-route-optimizer-cvrptw/webui`):
  ```powershell
  cd "d:\Workspaces\AI travel optimizer\Routing Engine\fleet-route-optimizer-cvrptw\webui"
  npm run dev
  ```
  Expected: Khởi chạy thành công máy chủ phát triển trên cổng `http://localhost:3000`.

- [ ] **Step 2: Mở trình duyệt truy cập ứng dụng và kiểm tra lỗi chữ**
  Mở trình duyệt truy cập `http://localhost:3000` thông qua công cụ browser.
  Xác thực: Quét nội dung trang chủ để xác nhận toàn bộ tiếng Việt hiển thị đẹp đẽ, chuẩn chỉnh, không còn bất cứ lỗi chữ nào. Chụp lại ảnh màn hình.

- [ ] **Step 3: Kiểm thử luồng lên lịch trình Huế 3 ngày kết nối API thực tế**
  * Nhập prompt: *"Huế 3 ngày, ngân sách 1 triệu, muốn đi Đại Nội, lăng Khải Định, lăng Minh Mạng và uống cafe muối"*
  * Bấm nút Gửi/Tạo lịch trình.
  * Quan sát console/network tab để kiểm chứng cuộc gọi `POST http://localhost:8001/v1/trip/plan_trip` hoạt động trơn tru.
  * Xác thực: UI hiển thị đầy đủ timeline 3 ngày và vẽ đường đi trên bản đồ OSM kết nối các POI chính xác.

- [ ] **Step 4: Kiểm thử luồng Re-route (Thêm/Xóa địa điểm)**
  * Bấm nút xóa (thùng rác) một POI bất kỳ trên timeline hoặc sử dụng chat panel gõ *"Xóa cafe muối"*.
  * Kiểm chứng cuộc gọi `POST http://localhost:8001/v1/trip/re_route` hoạt động thành công và OR-Tools cập nhật lại lộ trình tối ưu trên bản đồ Next.js.
  * Chụp lại ảnh màn hình kết quả tối ưu thành công.
