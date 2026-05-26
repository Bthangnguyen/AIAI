# Hướng dẫn dọn dẹp ổ C thủ công bằng WizTree & Windows Settings

Tài liệu này hướng dẫn chi tiết cách dọn dẹp các tệp tin có dung lượng lớn và cấu hình tối ưu hóa sâu ổ C bằng công cụ trực quan và các tính năng tích hợp sẵn của Windows.

---

## 1. Tìm và xóa tệp tin lớn bằng WizTree (Trực quan)

WizTree là công cụ quét ổ cứng siêu nhanh giúp bro tìm ra chính xác thư mục hay file nào đang chiếm dụng nhiều dung lượng nhất.

*   **Tải xuống**: Tải bản WizTree Portable (file ZIP không cần cài đặt) tại trang chủ: [Diskanalyzer](https://diskanalyzer.com/download).
*   **Giải nén & Khởi chạy**:
    1. Giải nén file `.zip` vừa tải về.
    2. Nhấn chuột phải vào tệp `WizTree64.exe` (hoặc `WizTree.exe` nếu máy chạy Windows 32-bit) -> Chọn **Run as administrator** (Chạy với quyền Quản trị viên).
*   **Quét ổ đĩa**:
    1. Ở góc trên bên trái, chọn ổ đĩa **C:**.
    2. Nhấn nút **Scan** (Quá trình quét chỉ mất từ 1 - 3 giây).
*   **Cách đọc sơ đồ trực quan (Treemap)**:
    - Ở bên dưới giao diện sẽ hiển thị sơ đồ khối màu sắc. Mỗi khối đại diện cho một tệp tin. Khối có kích thước **càng lớn** tức là tệp đó chiếm **càng nhiều dung lượng**.
    - Di chuột vào khối lớn để xem đường dẫn chi tiết của tệp.
*   **Hướng dẫn xóa an toàn**:
    - Nhấp đúp vào một khối to để định vị thư mục chứa nó.
    - **NÊN XÓA**: Các tệp tin cá nhân lỗi thời nằm trong thư mục người dùng như `C:\Users\<Tên_User>\Downloads`, `Videos`, `Documents`. (Ví dụ: các file bộ cài `.iso`, `.zip`, `.exe` khổng lồ tải từ lâu).
    - **KHÔNG ĐƯỢC XÓA**: Các tệp tin nằm trong thư mục `C:\Windows` hoặc `C:\Program Files` trừ khi bro chắc chắn 100% chúng là tệp rác của một ứng dụng cũ đã gỡ cài đặt.

---

## 2. Dọn dẹp thư mục Windows.old (Bản sao lưu Windows cập nhật cũ)

Sau mỗi đợt cập nhật Windows lớn, thư mục `Windows.old` sẽ được tạo ra tại ổ C để lưu trữ dữ liệu của bản Windows trước đó, nặng từ 10GB - 30GB. Để xóa nó an toàn, hãy làm theo các bước chính chủ dưới đây:

1.  Mở giao diện Cài đặt bằng tổ hợp phím **Windows + I**.
2.  Chọn mục **System** (Hệ thống) -> Chọn tiếp **Storage** (Lưu trữ).
3.  Chọn **Temporary files** (Tệp tạm thời).
4.  Đợi hệ thống quét trong giây lát. Sau đó tìm và tích chọn mục **Previous Windows installation(s)** (Bản cài đặt Windows trước đó).
5.  Nhấn nút **Remove files** (Xóa tệp) ở phía trên cùng để bắt đầu xóa.

---

## 3. Gỡ cài đặt ứng dụng/game khổng lồ không sử dụng

1.  Vào **Settings** (Win + I) -> **Apps** -> **Installed apps** (Ứng dụng đã cài đặt).
2.  Tại thanh tìm kiếm lọc, nhấn vào bộ lọc **Sort by** -> Chọn **Size (Large to small)** để sắp xếp các ứng dụng nặng nhất lên trên cùng.
3.  Xem xét danh sách các game hoặc phần mềm đồ họa/lập trình cũ không còn dùng nữa, nhấn vào dấu **3 chấm (...)** cạnh dung lượng ứng dụng -> Chọn **Uninstall** để gỡ cài đặt sạch sẽ.

---

## 4. Xóa bộ nhớ đệm Docker (Developer)

Nếu máy tính của bro có cài đặt Docker Desktop, các container cũ, volume dư thừa và image không gắn thẻ (dangling images) tích tụ lâu ngày có thể chiếm hàng chục GB ổ C.

*   Mở một Terminal bất kỳ (PowerShell hoặc CMD).
*   Chạy lệnh dọn dẹp triệt để dưới đây:
    ```bash
    docker system prune -a --volumes -f
    ```
    *Lệnh này sẽ xóa sạch các container đã dừng, network dư thừa, và toàn bộ images không được container nào sử dụng, giải phóng dung lượng cực kỳ lớn.*
