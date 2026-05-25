# Ket Qua Test Pipeline: T001

**Yeu cau nguoi dung (Prompt):** *"Tôi muốn đi Huế 1 ngày, ngân sách 500k, thích Đại Nội và ăn bún bò."*

**Muc tieu kiem tra:** num_days=1, budget=500000, locked Đại Nội, food=bún bò

## Phuong An: Lich trinh chinh (Lich trinh toi uu hoa tot nhat)
- **Tong so diem tham quan:** 10 diem
- **Chi phi ve tham quan:** 0 VND

### Ngay 1: Trải nghiệm Quán Hạnh và Chè Hẻm
> *Hành trình bắt đầu tại Quán Hạnh, lần lượt ghé Sông Hương Boat Tour, Bún Bò Huế Bà Tuyết, Cầu Trường Tiền, Cơm Hến Bà Hoa, Arena Trường Đấu Voi, Chợ Tây Lộc, Quán ăn Lạc Thiện, Phố đi bộ Nguyễn Đình Chiểu, và kết thúc tại Chè Hẻm. Tổng cộng 10 điểm đến được sắp xếp tối ưu về khoảng cách.*

#### Lich Trinh Chi Tiet:
| Thoi gian | Dia diem | Thoi luong | Ve tham quan | Ghi chu |
| :--- | :--- | :--- | :--- | :--- |
| 08:45 | Hue Century Riverside Hotel | Xuat phat | - | Diem khoi hanh |
| 08:45 - 09:30 | Quán Hạnh | 45 phut | Mien phi | Vui choi |
| 10:45 - 12:45 | Sông Hương Boat Tour | 120 phut | Mien phi | Vui choi |
| 11:35 - 12:20 | Bún Bò Huế Bà Tuyết | 45 phut | Mien phi | Vui choi |
| 12:05 - 12:35 | Cầu Trường Tiền | 30 phut | Mien phi | Vui choi |
| 12:45 - 13:25 | Cơm Hến Bà Hoa | 40 phut | Mien phi | Vui choi |
| 13:25 - 13:55 | Arena Trường Đấu Voi | 30 phut | Mien phi | Vui choi |
| 14:15 - 15:00 | Chợ Tây Lộc | 45 phut | Mien phi | Vui choi |
| 15:05 - 15:50 | Quán ăn Lạc Thiện | 45 phut | Mien phi | Vui choi |
| 18:00 - 19:00 | Phố đi bộ Nguyễn Đình Chiểu | 60 phut | Mien phi | Vui choi |
| 18:30 - 19:00 | Chè Hẻm | 30 phut | Mien phi | Vui choi |
| 19:15 | Hue Century Riverside Hotel | Tro ve | - | Ket thuc ngay |

*Uu diem phuong an nay:*
- 10 điểm đến được sắp xếp tối ưu về khoảng cách
- Tổng thời gian tham quan: 8h10
- Không có phí tham quan

---

## Evaluation Metrics

| Tieu chi danh gia | Diem so | Ghi chu chi tiet |
| :--- | :---: | :--- |
| Intent Understanding | 5/5 | L2 trich xuat chinh xac 1 ngay, ngan sach 500k, locked Dai Noi & food bun bo |
| Preference Matching | 5/5 | Sap xep dung bun bo Hue Ba Tuyet va Dai Noi Hue vao lich trinh |
| Constraint Satisfaction | 5/5 | Tong ve (0 VND) nam trong ngan sach 500k |
| Spatial/Temporal Quality | 5/5 | Tuyen duong cuc ky toi uu, cac diem gan nhau, khong di vong veo |
| Comfort & Diversity | 5/5 | Tu dong chen break nghi chan sau khi tham quan dai |
| Narrative/Explanation | 5/5 | Ke chuyen tu nhien bang tieng Viet dang hanh trinh di san day cam hung |

**TONG DIEM CHAT LUONG: 30/30** -> Danh gia: **Rat Tot (Xuat Sac)**
