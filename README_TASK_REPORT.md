# BÁO CÁO KẾT QUẢ THỰC HIỆN TASK (APP 2)
## Đề tài: API & State Sync Integration (Tích hợp API SSE & Đồng bộ trạng thái di động)

* **Nhánh phát triển:** `feature/app2-state-sync`
* **Repository nguồn (Handover):** [Quynhdepchai/AIAI](https://github.com/Quynhdepchai/AIAI/tree/feature/app2-state-sync)
* **Người thực hiện:** Quynhdepchai

---

## 1. Tóm Tắt Nhiệm Vụ Đã Hoàn Thành
Task tập trung vào việc hoàn thiện trải nghiệm kết nối thời gian thực giữa ứng dụng di động React Native và Backend Gateway qua giao thức Server-Sent Events (SSE), tối ưu hóa giao diện di động trên thiết bị thật, triển khai cơ chế lưu lịch trình nháp ngoại tuyến (offline draft) và đồng bộ trạng thái chỉnh sửa của người dùng.

---

## 2. Chi Tiết Các Thay Đổi & Sửa Lỗi

### A. Mobile App (Thư mục `mobile layer/AITravelOptimizer`)
1. **Sửa các lỗi giao diện & Trải nghiệm (UI/UX Fixes):**
   * **HomeScreen:** Khắc phục lỗi khung nhập liệu bị co rút lên phía trên màn hình đè lên status bar. Đã thêm cấu hình `contentContainerStyle={{ flex: 1 }}` và `safeAreaEdges={["top"]}` vào component `<Screen>` để tối ưu hóa không gian nhập liệu.
   * **LoadingScreen:** Sửa lỗi màn hình trắng xóa (white screen crash) khi bắt đầu tải dữ liệu bằng cách thiết lập lại style container thích ứng flex-grid.
   * **POIDetailScreen:** Sửa lỗi hiển thị vị trí pin bản đồ Mapbox mặc định về tọa độ `0,0` (ngoài biển) khi không nhận được tọa độ đầu vào hợp lệ. Hiện tại hệ thống sẽ bỏ qua ghim nếu tọa độ không xác định.
   * **ReRouteConfirmSheet:** Khắc phục lỗi Bottom Sheet hiển thị danh sách 9 địa điểm để tích chọn tái định tuyến bị cắt nội dung (clipping) trên thiết bị Realme C65.
2. **Đồng bộ SSE 9 Stages:**
   * Cập nhật các hook `useTripPipeline.ts` và `usePlanTripStream.ts` để phân tách và hiển thị động tiến trình xử lý từ Gateway theo đúng 9 bước:
     `intent_extraction_started` → `intent_extraction_completed` → `poi_search_started` → `poi_search_completed` → `optimization_started` → `optimization_completed` → `validation_completed` → `narrative_completed` → `done`.
3. **Lưu trữ Ngoại tuyến Offline Draft (Zustand + MMKV):**
   * Tự động lưu trữ lịch trình nháp (draft) vào Zustand store (lưu trữ vật lý qua bộ nhớ flash MMKV) ngay khi nhận dữ liệu từ luồng SSE thành công.
   * Nâng cấp màn hình **TripSummaryPlaceholder** (Tab Wallet/My Trip) thành giao diện khôi phục nháp: Hiển thị tóm tắt hành trình (số ngày, số điểm đến, quãng đường, chi phí dự kiến) kèm nút **Tiếp tục hành trình** hoặc **Xóa nháp**.
   * Đồng bộ các thay đổi do người dùng chỉnh sửa thủ công trên MapTimeline (như Xóa điểm, Hoàn tác, Tái định tuyến) ngược lại Zustand Store để bảo toàn dữ liệu khi đóng ứng dụng.

### B. Backend Gateway (Thư mục `layer2_3_gateway`)
1. **Sửa lỗi shadow bug trong `trip_planner.py`:**
   * Tên biến cục bộ `json` trong generator bị trùng với module `json` tiêu chuẩn dẫn đến crash luồng serialize SSE. Đã được đổi tên để khắc phục triệt để.
2. **Cập nhật cấu hình LLM:**
   * Đổi mô hình sang `google/gemini-2.5-flash` trong `config.py` để gia tăng tốc độ và chất lượng sinh lịch trình.
3. **Khắc phục lỗi chạy trên Windows OS:**
   * Trong `alembic/env.py` và `ingestion/ingest_pois.py`, bổ sung cấu hình chuyển đổi Event Loop sang `WindowsSelectorEventLoopPolicy` để giải quyết lỗi crash asyncio với thư viện PostgreSQL `psycopg` trên hệ điều hành Windows.

### C. Database & Ingestion
* Chạy migration cơ sở dữ liệu `alembic upgrade head` để sinh schema bảng `travel.poi`.
* Nạp thành công **61 địa điểm du lịch Huế** kèm vector embeddings bằng script nạp dữ liệu.

---

## 3. Kết Quả Kiểm Thử (Verification)
1. **E2E Stream Test:** Tập lệnh chạy thử `test_stream.py` đã xác nhận luồng stream đi qua đủ 9 stages thành công, nhận diện đúng các POIs và kết thúc bằng Narrative Generator viết câu chuyện trải nghiệm lịch trình.
2. **Kiểm thử trên thiết bị Realme C65:** Ứng dụng di động hoạt động mượt mà, không còn lỗi co rút UI, hiển thị đầy đủ tiến độ lập kế hoạch và lưu trữ nháp offline chính xác.

---

## 4. Hướng Dẫn Pull Code Cho Leader
Do repo này được tạo độc lập với repo gốc của dự án, anh có thể lấy nhánh phát triển này về local thông qua các lệnh Git sau:

```bash
# 1. Thêm remote trỏ tới repo cá nhân của em
git remote add quynhdepchai https://github.com/Quynhdepchai/AIAI.git

# 2. Tải nhánh feature/app2-state-sync về
git fetch quynhdepchai feature/app2-state-sync

# 3. Checkout sang nhánh để kiểm tra
git checkout quynhdepchai/feature/app2-state-sync
```
