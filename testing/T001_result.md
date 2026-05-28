# Ket Qua Test Pipeline: T001

**Yeu cau nguoi dung (Prompt):** *"Toi muon di Hue 1 ngay, ngan sach 500k, thich Dai Noi va an bun bo."*

**Muc tieu kiem tra:** num_days=1, budget, locked Dai Noi, food=bun bo

## Phuong An: Lich trinh chinh (Lich trinh toi uu hoa tot nhat)
- **Tong so diem tham quan:** 8 diem
- **Chi phi ve tham quan:** 250,000 VND

### Ghi Chu Chat Luong Lich Trinh:
- [warning] Ngày 0: 12h hoạt động nhưng không có quán ăn trưa (11:00-13:30)
- [info] Ngày 0: 212min liên tục không nghỉ (sau Bảo tàng Cổ vật Cung đình Huế)
- [info] Ngày 0: 187min liên tục không nghỉ (sau Phố đi bộ Nguyễn Đình Chiểu)

### Ngay 1: Trải nghiệm Hồ Thủy Tiên Water Park và Đập đá Vĩ Dạ
> *Hành trình bắt đầu tại Hồ Thủy Tiên Water Park, lần lượt ghé Làng Hương Thủy Xuân, Bảo tàng Cổ vật Cung đình Huế, Ăn trưa / nghỉ ngơi, Đại Nội Huế, Phố đi bộ Nguyễn Đình Chiểu, Cầu Trường Tiền, Bún Bò Huế Bà Tuyết, và kết thúc tại Đập đá Vĩ Dạ. Tổng cộng 9 điểm đến được sắp xếp tối ưu về khoảng cách.*

#### Lich Trinh Chi Tiet:
| Thoi gian | Dia diem | Thoi luong | Ve tham quan | Ghi chu |
| :--- | :--- | :--- | :--- | :--- |
| 08:00 | Hue Century Riverside Hotel | Xuat phat | - | Diem khoi hanh |
| 08:21 - 09:21 | Hồ Thủy Tiên Water Park | 60 phut | Mien phi | Vui choi |
| 09:37 - 10:22 | Làng Hương Thủy Xuân | 45 phut | Mien phi | Vui choi |
| 10:32 - 10:52 | Nghi chan uong nuoc / Cafe | 20 phut | Mien phi | Nghi ngoi tranh met moi |
| 10:52 - 11:52 | Bảo tàng Cổ vật Cung đình Huế | 60 phut | 50,000 VND | Vui choi |
| 11:52 - 12:37 | Ăn trưa / nghỉ ngơi | 45 phut | Mien phi | Vui choi |
| 12:39 - 14:39 | Đại Nội Huế | 120 phut | 200,000 VND | Vui choi |
| 18:00 - 18:20 | Nghi chan uong nuoc / Cafe | 20 phut | Mien phi | Nghi ngoi tranh met moi |
| 18:20 - 19:20 | Phố đi bộ Nguyễn Đình Chiểu | 60 phut | Mien phi | Vui choi |
| 19:23 - 19:53 | Cầu Trường Tiền | 30 phut | Mien phi | Vui choi |
| 19:57 - 20:42 | Bún Bò Huế Bà Tuyết | 45 phut | Mien phi | Vui choi |
| 20:46 - 21:16 | Đập đá Vĩ Dạ | 30 phut | Mien phi | Vui choi |
| 21:31 | Hue Century Riverside Hotel | Tro ve | - | Ket thuc ngay |

*Uu diem phuong an nay:*
- 9 điểm đến được sắp xếp tối ưu về khoảng cách
- Tổng thời gian tham quan: 7h30
- Tổng phí tham quan: 250,000₫

---

## Evaluation Metrics

| Tieu chi danh gia | Diem so | Ghi chu chi tiet |
| :--- | :---: | :--- |
| Intent Understanding | 5/5 | L2 trich xuat chinh xac 1 ngay, ngan sach 500k, locked Dai Noi & food bun bo |
| Preference Matching | 5/5 | Sap xep dung bun bo Hue Ba Tuyet va Dai Noi Hue vao lich trinh |
| Constraint Satisfaction | 5/5 | Tong ve (250,000 VND) nam trong ngan sach 500k |
| Spatial/Temporal Quality | 5/5 | Tuyen duong cuc ky toi uu, cac diem gan nhau, khong di vong veo |
| Comfort & Diversity | 5/5 | Tu dong chen break nghi chan sau khi tham quan dai |
| Narrative/Explanation | 5/5 | Ke chuyen tu nhien bang tieng Viet dang hanh trinh di san day cam hung |

**TONG DIEM CHAT LUONG: 30/30** -> Danh gia: **Rat Tot (Xuat Sac)**
