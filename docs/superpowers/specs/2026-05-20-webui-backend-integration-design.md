# Thiết kế: Khôi phục Tiếng Việt WebUI & Kiểm thử kết nối Docker Backend

Tài liệu này đặc tả thiết kế chi tiết để khôi phục lỗi hiển thị chữ tiếng Việt (lỗi font/encoding) trên WebUI Next.js và quy trình khởi chạy, kiểm thử kết nối end-to-end với hệ thống Docker Backend (Gateway & OR-Tools Solver) đã được build sẵn.

## 1. Khôi phục Tiếng Việt chuẩn cho WebUI (Selective Revert & Fix)

### 1.1 Khôi phục các file components chỉ bị lỗi chữ
Hầu hết các file giao diện trong `fleet-route-optimizer-cvrptw/webui/src/` chỉ bị lỗi hiển thị chữ tiếng Việt (biến thành `?` hoặc ký tự lạ) chứ không có thay đổi logic nghiệp vụ. Ta sẽ khôi phục chúng về trạng thái gốc bằng Git:
* `fleet-route-optimizer-cvrptw/webui/src/app/layout.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/AddPlaceModal.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/AgentStatusSteps.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/BuildProgressSteps.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/BuilderWorkspace.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/ExamplePromptChips.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/HomePage.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/HomePromptBox.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/ItineraryArtifact.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/ItineraryMap.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/ItineraryMapPanel.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/ItineraryPreviewPanel.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/MobilePhasePage.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/MockAuthModal.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/SavedTripsPage.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/TimelineDayCard.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/TimelinePlaceCard.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/Toast.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/TripControlPanel.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/components/TripToolbar.tsx`
* `fleet-route-optimizer-cvrptw/webui/src/data/huePois.ts`
* `fleet-route-optimizer-cvrptw/webui/src/types/trip.ts`

### 1.2 Chỉnh sửa các file chứa logic kết nối API mới
Với các file chứa code kết nối backend thực tế, ta sẽ sửa thủ công các chuỗi tiếng Việt bị lỗi chữ, đảm bảo giữ nguyên 100% logic code:
* **`api.ts`**: Chỉnh sửa các chuỗi thông báo lỗi tiếng Việt bị sai font trong các hàm `generateRealItinerary`, `reRouteDay`, `searchPoisBackend`.
* **`page.tsx`**: Khôi phục tiếng Việt chuẩn cho các hàm hiển thị Toast, xử lý sự kiện Thêm/Xóa/Tối ưu lại POI (`handleAddPoiBackend`, `handleRemovePlaceBackend`).
* **`AITripChatPanel.tsx`**: Khôi phục import hàm `draftTotals` từ `mockItineraryFallback.ts` và khôi phục text cho các nút lựa chọn nhanh (quick actions).

---

## 2. Khởi chạy Docker Backend & Kiểm thử kết nối

Vì Docker image đã được build sẵn, ta chỉ cần bật Docker daemon và chạy khởi động nhanh container (không cần `--build`):

### 2.1 Bật Docker Desktop trên Windows
Khởi chạy tiến trình Docker Desktop bằng PowerShell:
```powershell
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```
Đợi và kiểm tra trạng thái Docker daemon bằng `docker info` cho đến khi sẵn sàng.

### 2.2 Khởi chạy các container cụm Solver & Routing
Vào thư mục `fleet-route-optimizer-cvrptw/docker` và khởi động container:
```bash
docker compose up -d
```
* **Dịch vụ chạy:** Solver Backend (cổng 8000), OSRM routing engine (cổng 5000).

### 2.3 Khởi chạy các container cụm Gateway & Database
Vào thư mục `layer2_3_gateway` và khởi động container:
```bash
docker compose up -d
```
* **Dịch vụ chạy:** Postgres DB (cổng 5432), Gateway API (cổng 8001).

### 2.4 Kiểm thử kết nối End-to-End
* Gọi thử API kiểm tra sức khỏe (Health Check):
  * Solver: `GET http://localhost:8000/health`
  * Gateway: `GET http://localhost:8001/health`
* Thực hiện gửi yêu cầu tạo lịch trình mẫu từ WebUI Next.js đến Gateway để kiểm thử dữ liệu trả về từ OR-Tools Solver.

---

## 3. Chạy WebUI phát triển cục bộ & Xác minh giao diện
* Chạy frontend dưới chế độ dev:
  ```bash
  cd fleet-route-optimizer-cvrptw/webui
  npm run dev
  ```
* Sử dụng công cụ Browser để kiểm thử:
  * Đảm bảo font chữ tiếng Việt hiển thị đẹp đẽ, chuẩn xác 100%.
  * Thao tác tạo lịch trình, thêm/xóa POI và kiểm tra kết quả tối ưu hóa trực tuyến từ solver Docker.
