# Kế hoạch dọn dẹp ổ C: Trực quan & Tự động (C-Drive Visual & Automated Cleanup Plan)

Tài liệu này trình bày chi tiết kế hoạch dọn dẹp ổ C an toàn, hiệu quả dành riêng cho môi trường chạy hệ điều hành Windows, đặc biệt tối ưu cho người dùng là lập trình viên (Developer).

---

## 1. Tổng quan & Mục tiêu

*   **Mục tiêu**: Giải phóng tối đa dung lượng ổ C (đặc biệt là tệp tin lớn không dùng tới và cache lập trình viên) mà vẫn đảm bảo hệ thống Windows hoạt động ổn định 100%.
*   **Phương pháp**: Kết hợp phân tích trực quan qua công cụ WizTree + Tự động hóa bằng PowerShell Script + Hướng dẫn thủ công cho các thành phần nhạy cảm.

---

## 2. Phần 1: Phân tích & Xử lý File lớn bằng WizTree

WizTree là công cụ phân tích dung lượng ổ cứng nhanh nhất thế giới cho Windows bằng cách đọc trực tiếp Master File Table (MFT) của hệ thống tệp NTFS.

### Quy trình thực hiện:
1.  **Tải xuống**: Tải bản WizTree Portable từ trang chủ: [Diskanalyzer](https://diskanalyzer.com/download) (chọn bản ZIP để không cần cài đặt).
2.  **Khởi chạy**: Giải nén và chạy tệp `WizTree64.exe` với quyền **Run as administrator** (để quét được các thư mục ẩn/hệ thống).
3.  **Quét ổ đĩa**: Chọn ổ `C:` và nhấn **Scan**.
4.  **Nhận diện & Xử lý**:
    *   **Thư mục Downloads (`C:\Users\<Tên_User>\Downloads`)**: Nơi chứa nhiều file bộ cài `.exe`, `.msi`, `.zip`, `.iso` cũ.
    *   **Thư mục Videos / Documents / Desktop**: Chứa tệp cá nhân lớn.
    *   **Các thư mục game cũ (Steam, Epic, Riot...)**: Có thể đã bị gỡ cài đặt nhưng vẫn để lại các thư mục dữ liệu game khỏng lồ trong `%LocalAppData%` hoặc `%ProgramFiles%`.
    *   **Lưu ý an toàn**: Chỉ trực tiếp xóa các tệp cá nhân trong thư mục người dùng (`C:\Users`). **Không** xóa bất kỳ tệp nào trong các thư mục `C:\Windows` hoặc `C:\Program Files` nếu chưa hiểu rõ chức năng của chúng.

---

## 3. Phần 2: Script tự động dọn rác hệ thống & Developer Cache

Một script PowerShell an toàn (`clean_c_drive.ps1`) sẽ được phát triển để tự động hóa việc dọn dẹp các thư mục rác hệ thống và dọn cache của các công cụ lập trình.

### Các thư mục và tác vụ dọn dẹp:

#### A. Bộ nhớ đệm và File tạm của Windows (System Junk)
*   **User Temp (`%TEMP%`)**: Thư mục chứa các tệp tạm của ứng dụng đang chạy. Xóa các tệp không bị khóa.
*   **System Temp (`C:\Windows\Temp`)**: Thư mục lưu trữ tệp tạm của các dịch vụ hệ thống Windows.
*   **Windows Update Cache (`C:\Windows\SoftwareDistribution\Download`)**: Nơi lưu trữ các tệp tải về của Windows Update. Sau khi cập nhật xong, các tệp này hoàn toàn có thể xóa an toàn để giải phóng từ 2GB - 10GB.
*   **Log files & Error Dumps**: Xóa các tệp `.log` hệ thống cũ và tệp `.dmp` sinh ra khi máy bị lỗi màn hình xanh hoặc crash ứng dụng.
*   **Prefetch (`C:\Windows\Prefetch`)**: Dữ liệu tải trước của các ứng dụng giúp khởi động nhanh hơn, nhưng tích tụ lâu ngày sẽ gây đầy ổ đĩa.

#### B. Cache lập trình viên (Developer Cache)
Lập trình viên thường bị đầy ổ C do cache của các trình quản lý gói. Script sẽ tự động dọn dẹp:
*   **npm cache**: Dọn cache của Node.js qua lệnh `npm cache clean --force` và xóa `%AppData%\npm-cache`.
*   **pip cache**: Dọn cache của Python qua lệnh `pip cache purge` và xóa `%LocalAppData%\pip\Cache`.
*   **NuGet cache**: Dọn cache thư viện .NET qua lệnh `dotnet nuget locals all --clear` và xóa `%UserProfile%\.nuget\packages`.
*   **Gradle cache**: Xóa thư mục bộ đệm `.gradle\caches` trong thư mục User (nếu có).
*   **Rust Cargo cache**: Xóa các thư mục registry của Cargo `%UserProfile%\.cargo\registry\cache` (nếu có).

*Lưu ý: Đối với Docker, script sẽ cung cấp hướng dẫn chạy lệnh `docker system prune -a --volumes` trực quan để người dùng xác nhận trước khi xóa các container/images/volumes không dùng tới.*

---

## 4. Phần 3: Các bước dọn dẹp thủ công bổ sung an toàn

Có những thư mục rất lớn nhưng cần người dùng tự tay xác nhận thông qua giao diện Windows Settings để đảm bảo an toàn tuyệt đối:

### A. Xóa thư mục Windows.old (Bản sao lưu Windows cũ)
*   Thư mục này xuất hiện sau khi Windows thực hiện cập nhật lớn (feature update). Nó chứa toàn bộ hệ điều hành cũ để roll-back nếu cần, chiếm từ 10GB đến 30GB.
*   **Cách xóa an toàn**:
    1. Vào **Settings** (Win + I) -> **System** -> **Storage** (Lưu trữ).
    2. Chọn **Temporary files**.
    3. Tích chọn **Previous Windows installation(s)** (Bản cài đặt Windows trước đó).
    4. Nhấn **Remove files**.

### B. Kiểm tra và Gỡ cài đặt ứng dụng không dùng tới
1.  Vào **Settings** -> **Apps** -> **Installed apps**.
2.  Lọc danh sách theo **Size: Large to small** (Dung lượng: Từ lớn đến bé).
3.  Tìm các ứng dụng hoặc game cũ không còn dùng tới và chọn **Uninstall**.

### C. Dọn sạch Recycle Bin (Thùng rác)
*   Thùng rác mặc định trên ổ C có thể chiếm tới 5-10% tổng dung lượng ổ đĩa. Hãy nhấn chuột phải vào biểu tượng **Recycle Bin** ngoài Desktop và chọn **Empty Recycle Bin**.

---

## 5. Kế hoạch xác minh & Đảm bảo an toàn

1.  **Xác minh trước khi chạy**:
    *   Script PowerShell sẽ hiển thị dung lượng ổ C hiện tại trước khi bắt đầu dọn dẹp.
    *   Tất cả lệnh xóa thư mục quan trọng đều có xử lý lỗi `Try-Catch` để không gây gián đoạn hệ thống nếu file đang bị hệ điều hành khóa (in-use).
2.  **Xác minh sau khi chạy**:
    *   Script hiển thị dung lượng ổ C sau khi dọn dẹp và tính toán tổng số GB đã giải phóng được.
    *   Kiểm tra tính ổn định của Windows bằng cách mở thử một vài ứng dụng cơ bản.
