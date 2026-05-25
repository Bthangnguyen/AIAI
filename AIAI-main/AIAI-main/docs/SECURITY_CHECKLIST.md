# AIAI Travel Optimizer — Báo cáo Kiểm duyệt Bảo mật & Hướng dẫn RLS

Tài liệu này cung cấp danh sách rà soát bảo mật toàn diện (Security Audit) và tài liệu đặc tả cấu hình **Row Level Security (RLS)** trên PostgreSQL/Supabase nhằm đảm bảo dữ liệu chuyến đi của mỗi người dùng được bảo vệ an toàn tuyệt đối.

---

## 1. Rà Soát Bảo Mật (Security Checklist)

### 🔑 Quản Lý API Key & Secrets
- [x] **Không Lưu Trữ Cứng API Key**: Tất cả API key (Google Gemini, OpenAI, Mapbox, Firebase Admin) được quản lý qua biến môi trường (`.env`, `travel.env`).
- [x] **Harden `.gitignore`**: Đã chặn hoàn toàn việc commit các file cấu hình nhạy cảm (`google-services.json`, `GoogleService-Info.plist`, keystores, `.env`, `firebase-admin-key.json`).
- [x] **Firebase Admin SDK Key**: Khoá private key của Firebase Admin SDK trên Gateway được lưu trữ an toàn trong biến môi trường `FIREBASE_CREDENTIALS` hoặc file local được gitignore.

### 🌐 Mạng & Kết Nối (HTTPS/CORS)
- [ ] **HTTPS Enforced**: Cấu hình tất cả các API endpoint chạy dưới giao thức HTTPS ở môi trường Production.
- [ ] **CORS Origins Restricted**: Trên Gateway (FastAPI), cấu hình CORS `allow_origins` chỉ cho phép domain chính thức của Mobile Web / Dashboard, tránh sử dụng `["*"]` ở môi trường Production.
- [ ] **SSE Connection Security**: SSE endpoints (`/v1/trip/plan_trip_stream`) yêu cầu Bearer token hợp lệ qua URL param hoặc Authorization header để tránh lạm dụng băng thông LLM.

---

## 2. Hướng Dẫn Cấu Hình Row Level Security (RLS)

Để bảo vệ dữ liệu người dùng tại tầng Database (PostgreSQL / Supabase), hệ thống **BẮT BUỘC** phải bật Row Level Security (RLS) cho tất cả các bảng lưu trữ thông tin nhạy cảm của người dùng (ví dụ: `trips`, `user_profiles`).

### 📐 Thực Thể Cơ Sở Dữ Liệu
Mỗi bảng liên quan đến thông tin người dùng đều phải có cột định danh người dùng: `user_id` kiểu `UUID` hoặc `VARCHAR` (khớp với Firebase Auth UID).

### 🛠️ Các Câu Lệnh SQL Thiết Lập RLS

Dưới đây là kịch bản SQL chuẩn để kích hoạt RLS và thiết lập các Policies trên bảng `trips`:

```sql
-- 1. Kích hoạt Row Level Security trên bảng trips
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;

-- 2. Tạo Policy: Cho phép người dùng đọc chuyến đi của chính họ
CREATE POLICY "Users can view their own trips" 
ON trips
FOR SELECT
USING (auth.uid() = user_id);

-- 3. Tạo Policy: Cho phép người dùng tạo chuyến đi mới cho chính họ
CREATE POLICY "Users can insert their own trips" 
ON trips
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- 4. Tạo Policy: Cho phép người dùng cập nhật chuyến đi của chính họ
CREATE POLICY "Users can update their own trips" 
ON trips
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- 5. Tạo Policy: Cho phép người dùng xóa chuyến đi của chính họ
CREATE POLICY "Users can delete their own trips" 
ON trips
FOR DELETE
USING (auth.uid() = user_id);
```

### 🔒 Đồng Bộ Xác Thực Giữa Firebase Auth và PostgreSQL

Nếu sử dụng Supabase, Supabase hỗ trợ JWT verification gốc. Khi Gateway xác thực Firebase JWT ID Token thành công:
1. Trích xuất `uid` từ Firebase Token.
2. Thiết lập Session variables trước khi thực hiện truy vấn:
```sql
-- Thiết lập user_id trong transaction session
SET LOCAL request.jwt.claim.sub = 'firebase_user_uid_here';
```
3. Hoặc đơn giản là Gateway lọc và thực thi câu lệnh SQL kèm theo điều kiện `WHERE user_id = :uid` sau khi đã verify token thành công từ Middleware xác thực Firebase (`firebase_verify.py`).

---

## 3. Chính Sách Định Kỳ Thay Thế Khoá (Key Rotation Policy)

1. **Mapbox Public Token**: Định kỳ 3 tháng tạo mới token trên Mapbox Dashboard và thay đổi giá trị `EXPO_PUBLIC_MAPBOX_TOKEN` trong biến môi trường của ứng dụng di động.
2. **Firebase Admin Key**: Tạo mới Firebase Service Account Key định kỳ 6 tháng và xoá bỏ Key cũ trên Google Cloud Console.
3. **LLM API Keys**: Giới hạn quota sử dụng hàng ngày và hàng tháng trên console của OpenAI / Google AI Studio để tránh các đòn tấn công DDoS làm cạn kiệt tài chính.
