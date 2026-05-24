# AIAI Travel Optimizer - Mobile API Integration Spec

Tài liệu này mô tả chi tiết các endpoint, payload và cấu trúc dữ liệu mà **Mobile Frontend (React Native)** đang mong đợi. Backend Engineer cần xây dựng hoặc điều chỉnh API Gateway (Layer 2 & 3) khớp đúng với các cấu trúc này để ứng dụng hoạt động hoàn hảo khi tắt Mock Mode.

---

## 1. Kiểm tra trạng thái (Health Check)
Ứng dụng sẽ gọi API này trước khi bắt đầu tạo lịch trình để đảm bảo server đang hoạt động.

*   **Endpoint:** `GET /v1/trip/health`
*   **Response (JSON):**
    ```json
    {
      "status": "ready"
    }
    ```

---

## 2. Tạo lịch trình AI (Server-Sent Events - SSE Stream)
Đây là API quan trọng nhất. Mobile gọi endpoint này để tạo lịch trình và mong đợi backend trả về luồng sự kiện (event stream) theo từng bước để làm hiệu ứng loading.

*   **Endpoint:** `POST /v1/trip/plan_trip_stream`
*   **Headers:** `Content-Type: application/json`, `Accept: text/event-stream`
*   **Payload (JSON):**
    ```json
    {
      "user_prompt": "string (Ví dụ: Cho tôi 2 ngày du lịch lịch sử ở Huế)",
      "hotel_lat": 16.4637,
      "hotel_lon": 107.5909,
      "hotel_name": "Tên khách sạn",
      "num_days": 2
    }
    ```

### Các sự kiện (Events) mong đợi trong luồng SSE:
Backend cần gửi data dưới định dạng chuỗi JSON `data: { ... }\n\n` theo chuẩn SSE.

**A. Cập nhật trạng thái thông thường (Status updates)**
```json
{ "step": "status", "message": "Đang phân tích ý định..." }
```

**B. Hoàn thành bước L2 (NLP Intent)**
```json
{
  "step": "l2_done",
  "tags": ["historic", "cafe", "budget"],
  "locked": ["poi_123"] // Danh sách ID các địa điểm bắt buộc phải đi
}
```

**C. Hoàn thành bước L3 (Spatial Search)**
```json
{
  "step": "l3_done",
  "pois_found": 25,
  "locked_count": 1
}
```

**D. Kết quả cuối cùng (L4 OR-Tools)**
Gửi cấu trúc toàn bộ lịch trình. Đây là object `TravelItinerary` mà app sẽ dùng để render màn hình bản đồ.
```json
{
  "status": "success",
  "num_days": 2,
  "total_pois_visited": 4,
  "total_pois_dropped": 0,
  "total_entrance_fee": 100000,
  "total_travel_min": 60,
  "total_distance_km": 15.5,
  "budget_used": 100000,
  "days": [
    {
      "day_index": 0,
      "date": "2026-05-10",
      "hotel_name": "Tên khách sạn",
      "hotel_location": { "latitude": 16.4637, "longitude": 107.5909 },
      "total_travel_min": 30,
      "total_visit_min": 120,
      "total_distance_km": 5.5,
      "total_entrance_fee": 50000,
      "num_pois": 2,
      "stops": [
        {
          "poi_id": "poi_1",
          "poi_name": "Đại Nội Huế",
          "location": { "latitude": 16.468, "longitude": 107.577 },
          "arrival_time_min": 540,      // (Ví dụ 9:00 AM)
          "departure_time_min": 600,    // (Ví dụ 10:00 AM)
          "visit_duration_min": 60,     // 60 phút
          "travel_time_from_prev_min": 15,
          "entrance_fee": 50000
        }
      ]
    }
  ]
}
```

**E. Kết thúc Stream**
Chuỗi kết thúc chuẩn để báo cho Mobile ngắt kết nối:
```text
data: [DONE]\n\n
```

**F. Nếu có lỗi (Error)**
```json
{ "step": "error", "message": "Chi tiết lý do lỗi để hiển thị cho user" }
```

---

## 3. Reroute / Điều tuyến JIT (Just-In-Time)
Khi user bấm bỏ qua (skip) một điểm hoặc bấm "Tính toán lại", Mobile sẽ gửi toạ độ hiện tại và danh sách các POI còn lại để backend chạy lại Solver L4 cho **ngày hiện tại**.

*   **Endpoint:** `POST /v1/trip/re_route`
*   **Headers:** `Content-Type: application/json`
*   **Payload (JSON):**
    ```json
    {
      "current_lat": 16.46,
      "current_lon": 107.58,
      "current_time_min": 620,  // Thời gian lúc bấm nút (số phút từ 00:00)
      "remaining_poi_ids": ["poi_4", "poi_5"],
      "excluded_poi_ids": ["poi_3"], // (Tuỳ chọn) ID của POI vừa bị user bấm "Skip"
      "day_index": 0, // Chỉ mục của ngày đang đi
      "original_itinerary": { ... } // Toàn bộ object TravelItinerary gốc
    }
    ```

*   **Response (JSON):**
    Trả về cấu trúc **một ngày** (`TravelItineraryDay`) đã được tối ưu lại. Mobile sẽ tự động thay thế ngày này vào lịch trình cũ.
    ```json
    {
      "status": "success",
      "day": {
        "day_index": 0,
        "date": "2026-05-10",
        "hotel_name": "Tên khách sạn",
        "hotel_location": { "latitude": 16.4637, "longitude": 107.5909 },
        "total_travel_min": 25,
        "total_visit_min": 60,
        "total_distance_km": 4.5,
        "total_entrance_fee": 0,
        "num_pois": 2,
        "stops": [
          // Danh sách các điểm đã được sắp xếp lại
        ]
      }
    }
    ```

---

## Ghi chú cho Backend Engineer
1. Các biến `*_time_min` (ví dụ: `arrival_time_min`) được tính bằng **tổng số phút từ 00:00 sáng**. (VD: `540` = 09:00 AM, `720` = 12:00 PM).
2. App đã có sẵn các cấu trúc mapping icon (Emoji). Backend chỉ cần gửi đúng `poi_name` chứa các keyword cơ bản hoặc frontend tự xử lý.
3. Không bắt buộc phải có `budget_total` hay `dropped_pois`, nhưng nếu có sẽ được frontend hiển thị ở màn hình thống kê (Trip Summary) sau này.
