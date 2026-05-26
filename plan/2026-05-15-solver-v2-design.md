# Layer 4 Solver v2 — Multi-Depot Travel Optimizer

## Problem Statement

Hiện tại Layer 4 giải từng ngày riêng biệt (single-depot, single-vehicle), POI allocation dùng heuristic scoring.
Solver v2 chuyển sang **multi-depot OR-Tools** — tất cả ngày trong 1 model, OR-Tools tự assign POI vào ngày tối ưu.

## Design Decisions (Approved)

| Feature | Decision |
|---|---|
| Meals | POI thực tế từ Layer 3, bắt buộc 3 bữa/ngày (breakfast, lunch, dinner) |
| Budget | Global only: `sum(entrance_fee) ≤ budget_total` |
| Multi-depot | True multi-depot. Ngày N end tại hotel ngày N+1 |
| Diversity | Penalty trong arc cost: same-category consecutive bị phạt |
| Architecture | Bỏ Stage 1 (POI Allocator), OR-Tools làm hết |
| Re-route | Chỉ ngày hiện tại, GPS depot, end tại hotel |
| Full day | Mỗi ngày: 3 meals + xen kẽ heavy/light + buổi tối riêng |

---

## 1. Multi-Depot OR-Tools Model

### Node Layout

```
Index 0..H-1:  Hotels (H = unique hotels)
Index H..N-1:  POIs (including meal POIs)
```

### Vehicle = Day

```python
num_vehicles = num_days  # 3 ngày = 3 vehicles

# Ví dụ: 3 ngày, Hotel_A (idx 0), Hotel_B (idx 1)
# Ngày 0: A→...→A, Ngày 1: A→...→B, Ngày 2: B→...→B
starts = [0, 0, 1]
ends   = [0, 1, 1]

manager = pywrapcp.RoutingIndexManager(
    num_total_nodes,
    num_vehicles,
    starts,
    ends
)
```

### Per-Vehicle Constraints

Mỗi "vehicle" (ngày) có:
- **Riêng capacity** (max_daily_minutes): `AddDimensionWithVehicleCapacity(..., [600, 600, 480])`
- **Riêng time window**: Ngày 0 = 8:00–21:00, Ngày 2 = 9:00–20:00 (tùy DayPlan)
- **Riêng start/end depot**: Từ `starts[]` / `ends[]`

---

## 2. Meal Nodes

### Data Model

Layer 3 gửi meal POI với field mới:

```python
class POI(BaseModel):
    # ... existing fields ...
    meal_type: Optional[str] = None  # "breakfast" | "lunch" | "dinner" | None
    assigned_day: Optional[int] = None  # Day index this meal belongs to
```

### OR-Tools Constraints

```python
# Meal POIs: locked to specific vehicle (day)
for meal_poi in meal_pois:
    node_index = manager.NodeToIndex(meal_poi.solver_index)
    # Chỉ vehicle (day) được assign mới có thể ghé
    routing.SetAllowedVehiclesForIndex([meal_poi.assigned_day], node_index)
    # KHÔNG thêm AddDisjunction → bắt buộc phải ghé
```

### Time Windows cho Meals

| Meal | Default Time Window |
|---|---|
| Breakfast | 07:00–09:00 (420–540 min) |
| Lunch | 11:30–13:30 (690–810 min) |
| Dinner | 18:00–20:00 (1080–1200 min) |

Meal POI đã có `time_window` từ Layer 3 tương ứng các khung giờ trên.

---

## 3. Diversity Penalty

### Same-Category Penalty (Arc Cost)

```python
DIVERSITY_PENALTY = 50000  # Scaled ×100 = 500 "distance units"

def distance_callback(from_index, to_index):
    from_node = manager.IndexToNode(from_index)
    to_node = manager.IndexToNode(to_index)
    base_cost = int(distance_matrix[from_node][to_node] * 100)

    # Skip depot nodes
    if from_node in hotel_indices or to_node in hotel_indices:
        return base_cost

    # Same category consecutive → penalty
    if categories[from_node] == categories[to_node]:
        base_cost += DIVERSITY_PENALTY

    return base_cost
```

### Heavy/Light Rhythm (Arc Cost)

POI model thêm field `intensity`:
```python
class POI(BaseModel):
    # ... existing fields ...
    intensity: str = "medium"  # "heavy" | "medium" | "light"
```

```python
RHYTHM_PENALTY = 30000  # Smaller than diversity

# heavy → heavy consecutive → penalty
if intensity[from_node] == "heavy" and intensity[to_node] == "heavy":
    base_cost += RHYTHM_PENALTY
```

---

## 4. Global Budget (Post-Solve Validation)

OR-Tools không có native cross-vehicle sum constraint. Budget xử lý bằng post-solve:

```python
def solve_with_budget(all_pois, hotels, days, budget_total):
    # 1. Solve full model
    solution = solve_multi_depot(all_pois, hotels, days)

    # 2. Check budget
    visited = extract_visited_pois(solution)
    total_fee = sum(p.entrance_fee for p in visited)

    if total_fee <= budget_total:
        return solution

    # 3. Over budget → drop lowest-priority non-locked, non-meal POIs
    droppable = [p for p in visited if not p.is_locked and p.meal_type is None]
    droppable.sort(key=lambda p: p.priority_score)

    excluded = set()
    while total_fee > budget_total and droppable:
        drop = droppable.pop(0)
        excluded.add(drop.id)
        total_fee -= drop.entrance_fee

    # 4. Re-solve without excluded POIs
    remaining = [p for p in all_pois if p.id not in excluded]
    return solve_multi_depot(remaining, hotels, days)
```

---

## 5. Loại bỏ constraint thừa

### ❌ Max time per route (Constraint #5 trong phân tích trước)

```python
# TRƯỚC (thừa):
max_time = int(max(tw[1] for tw in time_windows) * 100)
routing.AddDimension(time_callback_index, max_time, max_time, ...)

# SAU: max_time = per-vehicle day end time
# Mỗi vehicle có time window riêng → dùng per-vehicle capacity
```

Thay bằng per-vehicle time limit từ `DayPlan.end_time_min`.

### ❌ Stage 1 POI Allocator

File `poi_allocator.py` sẽ bị deprecated. Logic soft_budget_filter chuyển vào post-solve validation.

---

## 6. Re-Route (Giữ nguyên kiến trúc)

Re-route KHÔNG dùng multi-depot. Vẫn single-depot, single-vehicle:

```python
def re_route(request):
    # Depot = GPS hiện tại
    # End = Hotel của ngày hôm đó (hoặc ngày mai nếu đổi hotel)
    # Vehicle = 1
    # POIs = remaining_poi_ids (bao gồm meals chưa ăn)

    manager = pywrapcp.RoutingIndexManager(
        num_locations, 1,
        starts=[0],  # GPS position
        ends=[hotel_index]  # Hotel
    )
    # ... solve single day ...
```

---

## 7. File Changes Summary

| File | Action | Description |
|---|---|---|
| `models/domain.py` | MODIFY | Add `meal_type`, `assigned_day`, `intensity` to POI |
| `models/api.py` | MODIFY | Update request models |
| `core/solvers/ortools_impl.py` | MAJOR REWRITE | Multi-depot, diversity penalty, meal constraints |
| `core/solvers/base.py` | MODIFY | Update interface for multi-depot |
| `core/solvers/ortools_solver.py` | MODIFY | Update wrapper |
| `services/travel_solver.py` | MAJOR REWRITE | Build multi-day problem, budget validation |
| `services/travel_plan_service.py` | SIMPLIFY | Remove POI Allocator dependency |
| `services/poi_allocator.py` | DEPRECATE | No longer used |
| `services/distance_cache.py` | NO CHANGE | |
| `api/routes.py` | MINOR | Add budget validation to flow |

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Solve time tăng (30 POI × 3 ngày) | Tăng time_limit lên 60s cho plan, giữ 15s cho re-route |
| OR-Tools không tìm được solution | Tăng disjunction penalty cho non-locked POIs, cho phép drop |
| Budget re-solve loop vô hạn | Max 3 iterations, sau đó trả solution tốt nhất |
| Meal assignment conflict | Layer 3 đảm bảo gửi đúng 1 meal/type/day |
