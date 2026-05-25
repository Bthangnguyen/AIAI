# 📋 Checklist: Thêm Field Mới vào POI

> Ví dụ minh họa: Thêm `photo_url`, `rating`, `review_count`, `golden_hour_start`

---

## Tổng quan: 5 điểm phải sửa

```
CSV Data  ──►  Ingestion Script  ──►  PostgreSQL  ──►  ORM Model  ──►  Pydantic Schema  ──►  API Response
  (1)              (2)                   (3)             (4)              (5)                  (tự động)
```

---

## Bước 1: CSV Source Data
**File:** `ingestion/sample_data/hue_pois.csv`

Thêm cột mới vào CSV:
```csv
name,lat,lon,...,photo_url,rating,review_count,golden_hour_start
Đại Nội Huế,16.4698,107.5786,...,https://photos.google/abc,4.8,2340,420
```

---

## Bước 2: Ingestion Script — INSERT SQL
**File:** `ingestion/ingest_pois.py`

### 2a. Cập nhật INSERT_SQL (dòng 29-49):
```sql
INSERT INTO travel.poi
    (...các cột cũ..., photo_url, rating, review_count, golden_hour_start)
VALUES
    (..., :photo_url, :rating, :review_count, :golden_hour_start)
ON CONFLICT ON CONSTRAINT uq_poi_name_coord DO UPDATE SET
    ...các cột cũ...,
    photo_url = EXCLUDED.photo_url,
    rating = EXCLUDED.rating,
    review_count = EXCLUDED.review_count,
    golden_hour_start = EXCLUDED.golden_hour_start,
    datetime_modified = NOW()
```

### 2b. Cập nhật logic xử lý trong hàm _process_row():
```python
params = {
    ...các field cũ...,
    "photo_url": row.get("photo_url", None),
    "rating": float(row.get("rating", 0.0)),
    "review_count": int(row.get("review_count", 0)),
    "golden_hour_start": int(row.get("golden_hour_start", -1)),  # -1 = không có
}
```

---

## Bước 3: PostgreSQL — ALTER TABLE
**Chạy migration SQL hoặc dùng Alembic:**

```sql
ALTER TABLE travel.poi
    ADD COLUMN photo_url       TEXT           DEFAULT NULL,
    ADD COLUMN rating          DOUBLE PRECISION DEFAULT 0.0,
    ADD COLUMN review_count    INTEGER        DEFAULT 0,
    ADD COLUMN golden_hour_start INTEGER      DEFAULT -1;

-- Optional: Index nếu cần filter/sort theo rating
CREATE INDEX idx_poi_rating ON travel.poi (rating DESC);
```

> **Lưu ý:** ALTER TABLE trên bảng có dữ liệu sẵn sẽ KHÔNG mất data.
> Các row cũ sẽ nhận giá trị DEFAULT.

---

## Bước 4: ORM Model — SQLAlchemy
**File:** `app/models/poi.py` (dòng 60-70)

Thêm field mới vào class `PointOfInterest`:
```python
# Existing fields...
is_outdoor: Mapped[bool] = mapped_column(Boolean, default=False)
weather_penalty: Mapped[float] = mapped_column(Float, default=0.0)

# ── NEW: Media & Engagement ──
photo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
rating: Mapped[float] = mapped_column(Float, default=0.0)
review_count: Mapped[int] = mapped_column(Integer, default=0)

# ── NEW: Golden Hour ──
golden_hour_start: Mapped[int] = mapped_column(Integer, default=-1)  # minutes from midnight, -1 = N/A
```

---

## Bước 5: Pydantic Schema — API Response
**File:** `app/schemas/trip.py` (class POIResponse, dòng 34-51)

```python
class POIResponse(BaseModel):
    ...các field cũ...
    tags: Optional[List[str]] = None
    is_locked: bool = False

    # ── NEW ──
    photo_url: Optional[str] = None
    rating: float = 0.0
    review_count: int = 0
    golden_hour_start: int = -1  # -1 = no golden hour data
```

---

## Bước 5b: Spatial Filter — SELECT columns
**File:** `app/services/spatial_filter.py` (_query_tier, dòng ~184-189)

Thêm field mới vào câu SELECT:
```python
stmt = select(
    POI.uuid, POI.name, POI.category, POI.description,
    ...các cột cũ...,
    POI.photo_url, POI.rating, POI.review_count,  # NEW
    POI.golden_hour_start,                         # NEW
    ST_AsGeoJSON(POI.coordinates).label("geojson"),
).where(and_(*conditions))
```

Và cập nhật `_row_to_poi()` (dòng ~207-230):
```python
return POIResponse(
    ...các field cũ...,
    photo_url=row.photo_url,
    rating=row.rating,
    review_count=row.review_count,
    golden_hour_start=row.golden_hour_start,
)
```

---

## Tóm tắt Impact Map

| # | File | Dòng code thay đổi | Độ phức tạp |
|---|---|---|---|
| 1 | `sample_data/hue_pois.csv` | Thêm cột | Trivial |
| 2 | `ingestion/ingest_pois.py` | INSERT SQL + params | ~10 dòng |
| 3 | PostgreSQL `ALTER TABLE` | Migration SQL | 1 lệnh |
| 4 | `app/models/poi.py` | ORM columns | ~4 dòng |
| 5a | `app/schemas/trip.py` | Pydantic fields | ~4 dòng |
| 5b | `app/services/spatial_filter.py` | SELECT + mapping | ~6 dòng |

**Tổng: ~25 dòng code + 1 lệnh SQL.** Kiến trúc đã đủ modular để thêm field mới trong < 15 phút.

---

## Riêng Golden Hour: Logic đặc biệt ở Layer 4

`golden_hour_start` không chỉ là "hiển thị". Nó có thể ảnh hưởng đến Solver:

```python
# Trong Layer 4: OR-Tools constraint
# Nếu POI có golden_hour, ưu tiên xếp vào khung giờ đó
if poi.golden_hour_start > 0:
    # Thêm soft time window bonus:
    # arrival_time gần golden_hour → priority_score tăng
    solver.add_soft_time_window(
        poi_index, poi.golden_hour_start, bonus=1000
    )
```

Điều này có nghĩa Layer 4 cũng cần sửa để tận dụng field mới — nhưng đó là tính năng chứ không phải migration.
