# Đặc Tả Thiết Kế: Luồng Câu Hỏi Follow-Up LLM Extractor & Chốt Chặn An Toàn Logic

* **Ngày tạo:** 25/05/2026
* **Trạng thái:** Đã phê duyệt (Phương án 2 - Royal CTA)
* **Tác giả:** Antigravity (AI Pair Programmer)

---

## 1. Tổng Quan (Goal Description)

Tính năng này nâng cấp màn hình **HomeScreen.tsx (AI Co-Pilot Chat Center)** từ trạng thái giả lập (Fake AI) sang **luồng đàm thoại tương tác thực tế** kết nối trực tiếp với API `/v1/trip/chat_process` của Gateway. 

Mục tiêu chính là giúp AI Co-Pilot hỏi các câu hỏi follow-up để thu thập đầy đủ thông tin bắt buộc (Điểm đến, Số ngày, Ngân sách tối đa, Sở thích, Địa điểm bắt buộc) trước khi kích hoạt bộ giải thuật tối ưu hóa lộ trình. Luồng này cũng đi kèm các cơ chế phòng vệ chống lỗi logic và lỗi người dùng cực đoan tại lớp trích xuất thông tin.

---

## 2. Luồng Tương Tác & Giao Diện (UX/UI Flow)

Hệ thống hoạt động theo mô hình **State Machine dạng đàm thoại**:

1. **Khởi đầu (Initial Chat):** Người dùng nhập một yêu cầu tối giản (ví dụ: *"Tôi muốn đi du lịch Huế"*).
2. **Vòng lặp Làm rõ (Clarification Loop):** AI trích xuất thông tin, lưu trữ vào Hợp đồng (`LLMDataContract`), phát hiện các trường còn thiếu (ví dụ: số ngày, ngân sách) và gửi phản hồi hỏi làm rõ duy nhất một thông tin còn thiếu đầu tiên bằng tiếng Việt tự nhiên (`status = "clarifying"`).
3. **Sửa đổi linh hoạt (Interactive Corrections):** Người dùng có thể đàm thoại để thay đổi ý định giữa chừng (ví dụ: đổi từ 3 ngày thành 4 ngày, đổi khách sạn, thêm chùa Thiên Mụ, ăn chay). Hợp đồng được Gateway gộp và cập nhật động.
4. **Trạng thái Sẵn sàng (Ready Transition):** Khi hợp đồng đã tích lũy đầy đủ thông tin bắt buộc (`status = "ready"`), AI gửi câu xác nhận và giao diện Mobile sẽ kích hoạt hiển thị **Nút bấm Glassmorphic Royal CTA: "🤖 Tạo Lộ Trình Tối Ưu Ngay ✨"** trượt lên nổi bật phía trên thanh Input.
5. **Kích hoạt Solver:** Khi người dùng nhấn nút CTA, Mobile sẽ đóng gói hợp đồng thành một câu lệnh hợp nhất (**Unified Prompt**) và chuyển tiếp sang màn hình `LoadingScreen` để tiến hành SSE stream giải lộ trình tức thì.

---

## 3. Kiến Trúc Kỹ Thuật (Technical Architecture)

### 3.1. Cập Nhật Kiểu Dữ Liệu (`app/types/api.ts`)

Bổ sung các interface định nghĩa tin nhắn hội thoại và cấu trúc request/response của API đàm thoại:

```typescript
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatProcessRequest {
  message: string;
  history: ChatMessage[];
  current_contract: LLMDataContract;
}

export interface ChatProcessResponse {
  status: 'ready' | 'clarifying';
  reply: string;
  updated_contract: LLMDataContract;
}
```

### 3.2. Cập Nhật API Service (`app/services/api/tripService.ts`)

Bổ sung phương thức `processChat` để tương tác trực tiếp với Gateway:

```typescript
  /**
   * Đàm thoại làm rõ hợp đồng du lịch (Clarification Chat Turn).
   * Gửi tin nhắn mới nhất + lịch sử chat + hợp đồng hiện tại lên Gateway.
   */
  async processChat(
    message: string,
    history: ChatMessage[],
    currentContract: LLMDataContract
  ): Promise<ChatProcessResponse> {
    try {
      const res = await fetch(`${API_BASE_URL}/v1/trip/chat_process`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "ngrok-skip-browser-warning": "1",
        },
        body: JSON.stringify({
          message,
          history,
          current_contract: currentContract,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned code ${res.status}`);
      }

      const data: ChatProcessResponse = await res.json();
      return data;
    } catch (e: any) {
      console.error("Lỗi đàm thoại chat_process:", e);
      // Fallback an toàn phòng khi mất kết nối mạng để không làm sập UI
      return {
        status: "clarifying",
        reply: "Dạ mạng nhà em đang gặp chút trục trặc nhỏ. Anh/chị có thể nói rõ hơn số ngày đi và ngân sách mong muốn không ạ?",
        updated_contract: currentContract,
      };
    }
  },
```

### 3.3. Tái Cấu Trúc `HomeScreen.tsx`

Tái lập trình màn hình HomeScreen để kết nối với API thực tế thay thế mock-up:
* Quản lý State: `chatHistory` (khởi tạo rỗng), `currentContract` (chứa mặc định hotel Pilgrimage Village), `isReady` (mặc định `false`), và `isTyping` (hiển thị 3 chấm động).
* Bổ sung nút Glassmorphic Royal CTA trượt lên mềm mại bằng `Animated.View` (hiệu ứng `translateY` và `opacity`) khi `isReady` chuyển thành `true`.
* Hàm `handleLaunchRouteSolver` đúc kết `currentContract` thành chuỗi Prompt hợp nhất có cấu trúc cao để truyền cho `LoadingScreen`.

---

## 4. Chốt Chặn An Toàn Logic (Failsafes & Error Handling)

Để giải quyết triệt để 6 nhóm lỗi logic/người dùng đã phân tích trong báo cáo, chúng ta sẽ áp dụng các giải pháp chốt chặn sau:

1. **Chuẩn Hóa Ngân Sách (Budget Normalization):**
   * *Nơi thực hiện:* Backend Gateway & Mobile.
   * *Cơ chế:* Sử dụng Regex quét tin nhắn phía Client trước khi gửi hoặc phía Gateway trong `_apply_backend_failsafes` để chuẩn hóa các cụm từ viết tắt như `1tr5`, `1.5tr` thành `1500000` VND; `800k` thành `800000` VND; tiếng lóng `1 củ` thành `1000000` VND.
2. **Mâu Thuẫn Ràng Buộc Vé (Admission Cost Failsafe):**
   * *Nơi thực hiện:* Gateway `/chat_process`.
   * *Cơ chế:* Khi nhận `updated_contract.locked_pois`, truy vấn nhanh giá vé cơ bản của các POI này. Nếu `Sum(Giá vé POI bắt buộc) > budget_max`, tự động chuyển trạng thái về `clarifying` kèm theo câu trả lời đề xuất tăng ngân sách hoặc tự động bỏ qua kiểm tra ngân sách.
3. **Giới Hạn Ngưỡng Trên Lập Lịch (Scheduling Upper Bound):**
   * *Nơi thực hiện:* Mobile `ItineraryFormScreen` và Gateway.
   * *Cơ chế:* Khóa cứng số ngày tối đa lập lịch trên biểu mẫu là `7 ngày`. Tại lớp Extractor, nếu phát hiện `num_days > 7`, ép giá trị về `7` và phản hồi lịch sự để bảo vệ giải thuật toán OR-Tools khỏi quá tải.
4. **Lọc Rác Địa Danh Chung (Generic Word Blacklisting):**
   * *Nơi thực hiện:* Gateway `_apply_backend_failsafes`.
   * *Cơ chế:* Ngoài danh sách đen các thành phố lớn (`Huế`, `Đà Nẵng`...), bổ sung thêm các danh từ chung chung vào blacklist của `locked_pois` để tránh việc tìm kiếm pgvector khớp bừa bãi: `"khách sạn"`, `"chùa"`, `"lăng"`, `"lăng tẩm"`, `"quán ăn"`, `"quán cafe"`.
5. **Bảo Vệ Trạng Thái Local (State Preservation):**
   * *Nơi thực hiện:* Mobile HomeScreen.
   * *Cơ chế:* Khi nhận kết quả từ `/chat_process`, thực hiện gộp (merge) giá trị cẩn thận thay vì ghi đè mù quáng. Đảm bảo các thuộc tính cục bộ như tọa độ khách sạn, tên khách sạn của thiết bị không bao giờ bị ghi đè bởi giá trị `null` từ phản hồi của LLM.

---

## 5. Kế Hoạch Xác Minh (Verification Plan)

### 5.1. Kiểm Thử Tự Động (Automated Testing)
1. **Kiểm thử API Endpoint:** Viết các ca kiểm thử tích hợp trong file `sseContract.test.ts` hoặc tương đương để gọi trực tiếp `/chat_process` từ Mobile client, giả lập đàm thoại 3 lượt (Thiếu thông tin -> Cập nhật hợp đồng -> Đầy đủ chuyển sang Ready).
2. **Kiểm thử TypeScript:** Chạy lệnh `npm run tsc` trên Mobile layer để đảm bảo các Interface mới không gây ra bất kỳ lỗi ép kiểu hay import sai lệch nào.

### 5.2. Xác Minh Thủ Công (Manual Verification)
1. **Trải nghiệm đàm thoại thực tế:**
   * Mở ứng dụng, vào tab Co-Pilot. Nhập *"Tôi muốn đi Huế"*. Xác minh AI hỏi lại về số ngày.
   * Nhập *"Đi 3 ngày nha"*. Xác minh AI hỏi tiếp về ngân sách tối đa.
   * Nhập *"Ngân sách tầm 2 triệu"*. Xác minh AI phản hồi sẵn sàng và nút bấm **"🤖 Tạo Lộ Trình Tối Ưu Ngay ✨"** xuất hiện lung linh.
2. **Sửa sai giữa chừng:**
   * Trong lúc đàm thoại, gõ câu lệnh thay đổi: *"À đổi lại đi trong 2 ngày thôi nhé"*. Xác minh `currentContract.num_days` cập nhật về `2`.
3. **Kích hoạt Solver:**
   * Nhấn nút Royal CTA, kiểm tra quá trình chuyển hướng sang màn hình `LoadingScreen`, theo dõi toàn bộ log SSE chạy mượt mà và chuyển tiếp hoàn hảo tới màn hình bản đồ hành trình `MapTimeline` với đúng các tham số đã đàm thoại.
