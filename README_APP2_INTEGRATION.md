# BÁO CÁO PHÂN TÍCH & TÍCH HỢP HỆ THỐNG (APP 2)
## Đề tài: API & State Sync Integration (Tích hợp API SSE & Đồng bộ trạng thái di động)

* **Nhánh phát triển:** `feature/app2-state-sync`
* **Repository:** [Bthangnguyen/AIAI](https://github.com/Bthangnguyen/AIAI.git)
* **Người thực hiện:** Quynhdepchai / Antigravity

---

## 1. Các Thay Đổi Đã Thực Hiện (App 2 Scope)

Để hoàn thành nhiệm vụ tích hợp kết nối API thời gian thực và đồng bộ trạng thái ngoại tuyến, chúng tôi đã triển khai các cấu trúc sau:

### A. Mobile Frontend (React Native)
1. **Đồng bộ luồng dữ liệu SSE 9 Stages (Strategy Option A):**
   * Cho phép màn hình `LoadingScreen` kết nối trực tiếp với hook `useTripPipeline` để theo dõi tiến độ xử lý thời gian thực từ Backend qua Server-Sent Events (SSE).
   * Khi nhận được sự kiện hoàn tất (`narrative_completed`), ứng dụng sẽ tự động điều hướng trực tiếp sang màn hình hiển thị bản đồ `MapTimelineScreen` với dữ liệu thực tế được tối ưu hóa.
2. **Khôi phục lịch trình nháp ngoại tuyến (Offline Draft):**
   * Tự động lưu trữ lịch trình nháp vào Zustand store (được đồng bộ xuống bộ nhớ flash vật lý MMKV) ngay khi tạo lịch trình thành công.
   * Cập nhật màn hình **TripSummaryPlaceholder** (Tab Lộ Trình Của Tôi): Nếu chưa có lịch trình, hiển thị màn hình trống tím hoàng gia. Nếu phát hiện có bản nháp chưa hoàn thành, hiển thị một **Glassmorphism Card** tóm tắt (số ngày, địa điểm, quãng đường, chi phí dự kiến) kèm hai nút tương thích: *"Tiếp tục hành trình"* hoặc *"Xóa nháp & Lên lịch mới"*.
3. **Sửa lỗi biên dịch TypeScript:**
   * Sửa lỗi chính tả thuộc tính CSS `backgroundcolor` thành `backgroundColor` tại file `MapTimelineScreen.tsx` để ứng dụng biên dịch thành công 100% không lỗi.

### B. Backend Gateway & Core Solver
1. **Khắc phục giới hạn LLM:**
   * Giới hạn `max_tokens=4000` cho các cuộc gọi API OpenAI / OpenRouter trong `llm_extractor.py` để khắc phục lỗi hết hạn mức credit (Error code 402 - requesting 65535 tokens) khi gọi mô hình Gemini 2.5 Flash.
2. **Khởi động hạ tầng kiểm thử E2E:**
   * Khởi chạy hệ thống cơ sở dữ liệu PostgreSQL (`travel-db`) và dịch vụ bản đồ OSRM (`v5.27.0` cho khu vực Huế) trên Docker.
   * Khởi động Core Solver (FastAPI + OR-Tools) trên cổng `8000`.
   * Kiểm thử thành công luồng SSE thông qua file chạy thử `test_stream.py`.

---

## 2. Kết Quả Kiểm Thử E2E Pipeline (Backend & Solver)

Kết quả chạy thực tế của luồng SSE khi giao tiếp giữa các Layer 2, 3 và 4:
```text
YIELD: data: {"stage": "intent_extraction_started"}
YIELD: data: {"stage": "intent_extraction_completed", "contract": ...}
YIELD: data: {"stage": "poi_search_started"}
YIELD: data: {"stage": "poi_search_completed", "pois_found": 50, "locked_count": 0}
YIELD: data: {"stage": "optimization_started"}
YIELD: data: {"stage": "optimization_completed"}
YIELD: data: {"stage": "validation_completed", "validation_notes": ["[info] Ngày 0: 210min liên tục không nghỉ"]}
YIELD: data: {"stage": "narrative_completed", "result": {"status": "success", "num_days": 1, ...}}
YIELD: data: [DONE]
```

---

## 3. Báo Cáo Các Lỗi Giao Diện Đang Gặp Phải (App 1 UI/UX - Cần Sửa)

Dưới đây là các lỗi giao diện thuộc phạm vi thiết kế của App 1 (do Developer Sang phụ trách UI/UX) cần được chỉnh sửa để tối ưu hóa trải nghiệm trên thiết bị thật:

### Lỗi 3.1: Thanh Navigation dưới cùng (Tab Bar) bị đè và lệch giao diện trên Android
* **Hiện tượng:** Trên các thiết bị Android sử dụng phím điều hướng ảo (như Realme C65), các nút bấm "Trang chủ", "Lộ trình", "Lịch sử" bị đẩy xuống quá sát viền dưới và bị phím hệ thống đè lên một phần, gây khó khăn cho việc bấm và bị cắt mất chữ.
* **Nguyên nhân:** File giao diện mới của Sang sử dụng các thẻ `<View>` và `<KeyboardAvoidingView>` chuẩn thay thế cho component `<Screen>` của Ignite. Do đó, thanh Tab Bar dưới cùng chưa tính toán bù trừ khoảng trống an toàn dưới cùng (`safeAreaInsets.bottom`).
* **Đề xuất sửa đổi:** Sử dụng hook `useSafeAreaInsets` từ thư viện `react-native-safe-area-context` để lấy giá trị `insets.bottom` và cộng trực tiếp vào `paddingBottom` hoặc `height` của Custom Tab Bar tại `MainTabNavigator.tsx`.

### Lỗi 3.2: Lỗi mã hóa ký tự (Encoding) hiển thị chữ tiếng Việt rác tại MapTimelineScreen
* **Hiện tượng:** Toàn bộ chữ tiếng Việt viết cứng trong màn hình bản đồ bị hiển thị sai định dạng font chữ dưới dạng ký tự rác (Ví dụ: `Thãªm Ä‘á»‹a Ä‘iá»ƒm (AI Chat)`, `LÆ°u NhÃ¡p`, `Chá»‘t Lá»‹ch TrÃ¬nh`, `Bá»  qua Ä‘iá»ƒm nÃ y`).
* **Nguyên nhân:** File `MapTimelineScreen.tsx` đã bị lưu nhầm bảng mã **ANSI / Windows-1252** thay vì **UTF-8** trong quá trình lập trình viên của App 1 chỉnh sửa hoặc chuyển giao file trên hệ điều hành Windows.
* **Đề xuất sửa đổi:** Mở file `MapTimelineScreen.tsx`, lưu lại (Save as) với mã hóa chuẩn **UTF-8** và thay thế lại các chuỗi ký tự bị hỏng về dạng tiếng Việt có dấu chuẩn.
