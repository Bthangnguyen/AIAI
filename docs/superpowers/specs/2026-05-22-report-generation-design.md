# BẢN THIẾT KẾ SPEC: HỆ THỐNG SINH BÁO CÁO KỸ THUẬT TỰ ĐỘNG
## Dự án: AI-Driven Dynamic Itinerary Optimizer

Bản thiết kế này chi tiết hóa cách thức xây dựng kịch bản Python (`scripts/generate_report.py`) sử dụng thư viện `python-docx` để tự động hóa việc xuất bản tài liệu báo cáo kỹ thuật "10/10" bằng Tiếng Việt học thuật. Tài liệu này được thiết kế theo cấu trúc phân hệ (C4 Model) của hệ thống thực tế và đảm bảo độ sạch 100% khi dịch ngược sang LaTeX bằng Pandoc.

---

## 1. Thiết lập Định dạng Word chuẩn học thuật & LaTeX-Ready

Để đảm bảo tài liệu được biên dịch hoàn hảo qua Pandoc, kịch bản Python sẽ định nghĩa các Styles chuẩn XML của Word và áp dụng các thông số sau:

*   **Font chữ:** `Times New Roman` cho toàn bộ tài liệu.
*   **Kích cỡ chữ (Font Size):**
    *   Tiêu đề báo cáo (Title): `24pt`, Bold, Paragraph Space Before = `12pt`, After = `12pt`.
    *   Heading 1 (Phần chính): `16pt`, Bold, Paragraph Space Before = `12pt`, After = `6pt`.
    *   Heading 2 (Phần con): `13pt`, Bold, Paragraph Space Before = `12pt`, After = `4pt`.
    *   Heading 3 (Mục nhỏ): `12pt`, Bold, Italic, Paragraph Space Before = `6pt`, After = `2pt`.
    *   Body Text (Nội dung): `12pt`, Regular, Paragraph Space Before = `0pt`, After = `6pt`.
*   **Khoảng cách dòng (Line Spacing):** `1.5 lines`.
*   **Căn lề (Margins):** Top = `2.0cm`, Bottom = `2.0cm`, Left = `3.0cm` (để đóng gáy), Right = `2.0cm`.
*   **Danh sách (Lists):** Sử dụng các kiểu mẫu chuẩn `List Bullet` và `List Number` có sẵn trong Word.
*   **Mã nguồn (Code Blocks):** Sử dụng font chữ `Consolas`, kích cỡ `9.5pt`, thụt lề trái `0.5 inches`, bọc trong khung viền hoặc bảng lưới đơn cell và đóng khung bằng ba dấu nháy ngược (```) để Pandoc chuyển trực tiếp sang `\begin{lstlisting}`.

---

## 2. Cấu trúc nội dung chi tiết & Tài liệu kỹ thuật hệ thống

Báo cáo được tự động sinh ra sẽ bao gồm 5 phần lớn dựa trên mã nguồn thực tế:

### PHẦN 1: NGHIÊN CỨU KHỐI MOBILE APP (REACT NATIVE & EXPO)
*   **Kiến trúc tổng quan:** Giới thiệu phân hệ Mobile (Layer 5) phát triển trên nền Expo Router & TypeScript, sử dụng Ignite CLI Template.
*   **Dịch vụ lõi `TripService`:**
    *   API `checkHealth()`: Kiểm tra trạng thái sẵn sàng của Gateway trước khi thực hiện luồng lập lịch.
    *   API `planTripStream()`: Giao tiếp qua kết nối SSE (`react-native-sse`) để nhận dòng dữ liệu JSON liên tục.
    *   API `reRoute()`: Gửi yêu cầu tái tối ưu hóa lộ trình JIT (Just-In-Time) mid-day.
*   **Dịch vụ Định vị ngầm `BackgroundLocationService`:**
    *   Sử dụng `expo-location` và `expo-task-manager` đăng ký tác vụ ngầm `BACKGROUND_LOCATION_TASK` chạy theo chu kỳ 1 phút hoặc khoảng cách 100m.
    *   Logic kiểm tra trễ lịch trình: So sánh GPS hiện tại với kế hoạch tham quan và gửi thông báo đẩy gợi ý người dùng tái tối ưu lộ trình.
*   **Sơ đồ khối (Mermaid):** Luồng xử lý định vị chạy ngầm và gọi JIT Re-route từ Mobile.

### PHẦN 2: NGHIÊN CỨU KHỐI GATEWAY (FASTAPI ORCHESTRATOR)
*   **Kiến trúc Pipeline Gateway (Layer 2 & Layer 3):**
    *   Tách biệt I/O DB để cô lập hoàn toàn các cuộc gọi API LLM/Embedding tốn thời gian (2-5s) bên ngoài DB session, tránh làm nghẽn Connection Pool.
*   **Layer 2 - LLM Intent Extractor (`llm_extractor.py`):**
    *   Sử dụng thư viện `Instructor` phi chặn cùng mô hình OpenAI (`AsyncOpenAI`) để chuẩn hóa yêu cầu tự nhiên thành `LLMDataContract`.
    *   Quét từ khóa ăn chay (`vegetarian`) tự động và chặn lỗi 0-day đối với địa danh chung chung trong `locked_pois`.
*   **Layer 3 - Spatial & Semantic Hybrid Search (`spatial_filter.py`):**
    *   Truy vấn kết hợp giữa không gian PostGIS (`ST_DWithin`) trên kiểu dữ liệu `Geography` và độ tương đồng ngữ nghĩa vector `pgvector` sử dụng chỉ mục HNSW qua toán tử Cosine distance `<=>`.
    *   Cơ chế mở rộng bán kính tự động `FALLBACK_TIERS` (4 cấp từ 10km đến 30km, tự động nới lỏng ngân sách và bộ lọc nhãn nếu số điểm tìm thấy nhỏ hơn ngưỡng `MIN_POI_THRESHOLD = 10`).
*   **Chỉ số Tiện ích POI (`UtilityScorer`):** Trình bày chi tiết công thức toán học tính điểm hữu dụng $U_i$ của địa điểm $i$ dựa trên 8 chiều trọng số:
    $$U_i = 0.28 \cdot S_{sem} + 0.18 \cdot Q_{qual} + 0.14 \cdot L_{loc} + 0.10 \cdot N_{nov} + 0.10 \cdot B_{bud} + 0.10 \cdot C_{com} + 0.06 \cdot D_{dist} + 0.04 \cdot G_{div}$$
*   **Sơ đồ khối (Mermaid):** Luồng tuần tự của Pipeline Gateway L2 -> L3 kết hợp DB isolation.

### PHẦN 3: NGHIÊN CỨU KHỐI ROUTING ENGINE (OR-TOOLS CVRP CORE)
*   **Mô hình hóa Toán học CVRPTW Solver:** Trình bày chi tiết các công thức LaTeX đại diện cho:
    *   *Biến quyết định:* $x_{ijk} = 1$ nếu xe $k$ di chuyển từ điểm $i$ sang điểm $j$, ngược lại bằng $0$.
    *   *Hàm mục tiêu:* Tối thiểu hóa tổng chi phí quãng đường di chuyển và các hình phạt trùng lặp thể loại/quá tải mệt mỏi liên tục, đồng thời tối đa hóa tiện ích tham quan các POIs không bị bỏ qua bằng drop penalty:
        $$\min \sum_{i,j,k} d_{ij} \cdot x_{ijk} + \sum_{k} P_{fixed} \cdot y_k + \sum_{\text{diversity}} P_{div} + \sum_{\text{rhythm}} P_{rhy} - \sum_{i \in \text{dropped}} P_{drop}(U_i)$$
        *Với trọng số drop penalty của điểm không khóa được gán tỷ lệ thuận với điểm hữu dụng: $P_{drop}(U_i) = 100,000 + U_i \cdot 900,000$.*
    *   *Ràng buộc sức bền (Fatigue Capacity):* Tích lũy độ nặng tham quan của địa điểm và giới hạn theo ngày.
    *   *Ràng buộc tránh nắng trưa gắt:* Sử dụng phương thức `RemoveInterval(avoid_start, avoid_end)` trên biến tích lũy thời gian (Time Dimension) đối với các điểm ngoài trời (`is_outdoor = True`) trong khung giờ 12:00 - 14:00.
    *   *Ràng buộc khóa điểm ăn uống (`meal_assignments`):* Khóa cứng biến phương tiện của điểm ăn trưa về đúng ngày chỉ định.
*   **Hậu xử lý (Post-Solve Pipeline):**
    *   `RestBreakInserter`: Cơ chế tự động quét hành trình và chèn địa điểm ảo `__rest_break__` (20 phút) nếu thời gian hoạt động liên tục vượt quá 180 phút.
    *   `ItineraryValidator`: Khung kiểm chuẩn 4 quy tắc vàng chất lượng tour (Meal missing, Consecutive heavy, Outdoor heat, Rest needed).
    *   `MultiPlanner`: Giải thuật sinh 3 phương án Balanced, Budget, Chill sử dụng hình phạt chồng chéo (giảm 25% utility của POIs đã chọn ở phương án trước).
*   **Thuật toán tái tối ưu (Mid-day Re-routing):** Cơ chế tạo Depot ảo tại tọa độ GPS hiện tại của người dùng, lọc bỏ các địa điểm đã đi qua và thiết lập bài toán CVRPTW mới để giải quyết các điểm còn lại.
*   **Mã nguồn:** Ràng buộc Fatigue và Tránh nắng nóng ngoài trời bằng OR-Tools.

### PHẦN 4: NGHIÊN CỨU KHỐI DATA/INFRASTRUCTURE
*   **Hạ tầng chạy Local:** Thiết kế WBS triển khai các dịch vụ Docker (PostgreSQL + PostGIS + pgvector nạp chỉ mục HNSW, OSRM Server chạy regional routing map Thừa Thiên Huế).
*   **Quy trình di cư dữ liệu (Data Migrations):** Sử dụng `Alembic` để quản lý sơ đồ bảng `PointOfInterest` chứa tọa độ địa lý `Geography(Point, 4326)` và vector nhúng 1536 chiều `Vector(1536)`.
*   **SQLite Distance Cache:** Thiết kế cơ sở dữ liệu đệm SQLite để lưu trữ khoảng cách & thời gian di chuyển giữa các cặp POIs, giảm thiểu 90% tần suất gọi API đến OSRM Server giúp tăng tốc bộ giải thuật.

### PHẦN 5: TỔNG HỢP VÀ KẾT LUẬN
*   **Tóm tắt theo từng khối** (Mobile, Gateway, Routing, Infra).
*   **Danh sách vấn đề cần tối ưu tiếp theo (Issues WBS):** Độ phủ dữ liệu đường giao thông của OSRM ở vùng sâu vùng xa, tối ưu hóa pin điện thoại khi quét GPS ngầm, độ trễ truy vấn vector ban đầu (cold-start latency).
*   **Đề xuất bước tiếp theo:** Tích hợp kiểm thử tự động E2E, mở rộng tập POIs ra các tỉnh thành du lịch trọng điểm khác tại Việt Nam.

---

## 3. Kế hoạch xác minh chất lượng tài liệu

*   **Bước 1: Chạy Python Script để sinh ra file Word:** `python scripts/generate_report.py`.
*   **Bước 2: Xác minh cấu trúc XML và kiểu dáng trong Word:** Mở file `.docx` kiểm tra căn lề, font chữ, độ thụt dòng và khoảng cách đoạn.
*   **Bước 3: Biên dịch thử nghiệm sang LaTeX qua Pandoc:**
    ```bash
    pandoc "AI_Travel_Optimizer_Architecture_Report.docx" -s -o test_report.tex --extract-media=./media
    ```
*   **Bước 4: Kiểm tra tính tương thích biên dịch:** Đảm bảo toàn bộ tiêu đề, danh sách, khối mã nguồn Consolas và công thức toán học LaTeX thô được dịch chính xác 100% sang mã nguồn LaTeX sạch.
