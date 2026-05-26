# Layer 4 Solver v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chuyển Layer 4 sang OR-Tools multi-depot với mandatory meals, diversity penalty, global budget, và 120s time limit.

**Architecture:** Bỏ POIAllocator, build problem array với starts/ends per day. Giải toàn bộ trip trong 1 lời gọi OR-Tools. Hỗ trợ JIT re-route vẫn dùng single-depot logic.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic, OR-Tools 9.7+

---

### Task 1: Update Domain & API Models

**Files:**
- Modify: `src/models/domain.py`
- Modify: `src/models/api.py`

- [ ] **Step 1: Write failing test**
Update `tests/` (hoặc test tạm qua python snippet) để parse 1 `POI` với fields `meal_type`, `assigned_day`, `intensity`, và `DayPlan` với `start_hotel_id`, `end_hotel_id`.
- [ ] **Step 2: Implement Domain changes**
Mở `src/models/domain.py`. 
Thêm vào `POI`:
```python
    meal_type: Optional[Literal["breakfast", "lunch", "dinner"]] = Field(None, description="Loại bữa ăn (nếu có)")
    assigned_day: Optional[int] = Field(None, description="Ngày được chỉ định cho bữa ăn này (bắt buộc nếu có meal_type)")
    intensity: Literal["heavy", "medium", "light"] = Field("medium", description="Mức độ nặng/nhẹ của POI để tính rhythm penalty")
```
Thêm vào `DayPlan`:
```python
    start_hotel_id: Optional[str] = Field(None, description="Hotel xuất phát (nếu khác hotel chính)")
    end_hotel_id: Optional[str] = Field(None, description="Hotel kết thúc (nếu đổi hotel giữa trip)")
```

- [ ] **Step 3: Implement API changes**
Mở `src/models/api.py`.
Sửa default `time_limit` trong `SolverConfig` từ 60 lên 120:
```python
    time_limit: int = Field(120, description="Time limit in seconds", ge=1, le=3600)
```

- [ ] **Step 4: Commit**
`git commit -m "feat(models): add fields for v2 solver"`

---

### Task 2: Base Solver Interface & OR-Tools Solver API

**Files:**
- Modify: `src/core/solvers/base.py`
- Modify: `src/core/solvers/ortools_solver.py`

- [ ] **Step 1: Update BaseSolver**
Mở `src/core/solvers/base.py`. Cập nhật docstring/type hinting của `solve()` hoặc pass thêm `kwargs` (ví dụ `diversity_penalty`, `rhythm_penalty`) nếu chưa cho phép kwargs. (Tuỳ cấu trúc hiện tại).
```python
    @abstractmethod
    def solve(
        self,
        problem_data: Dict[str, Any],
        time_limit: int = 60,
        distance_weight: float = 1.0,
        **kwargs
    ) -> Dict[str, Any]:
        pass
```

- [ ] **Step 2: Update ORToolsSolver**
Mở `src/core/solvers/ortools_solver.py` và truyền `kwargs` vào `ORToolsSolverImpl.solve`:
```python
        return self._impl.solve(
            problem_data=problem_data,
            time_limit=time_limit,
            distance_weight=distance_weight,
            **kwargs
        )
```

- [ ] **Step 3: Commit**
`git commit -m "refactor(core): update solver interfaces for penalties"`

---

### Task 3: Rewrite ORToolsSolverImpl (Multi-depot & Constraints)

**Files:**
- Modify: `src/core/solvers/ortools_impl.py`

- [ ] **Step 1: Update RoutingIndexManager init**
Trong `solve()`, thay `depot` bằng `starts` và `ends` nếu được truyền vào.
```python
        starts = problem_data.get('starts')
        ends = problem_data.get('ends')
        if starts is not None and ends is not None:
            manager = pywrapcp.RoutingIndexManager(
                len(problem_data['distance_matrix']),
                problem_data['num_vehicles'],
                starts, ends
            )
        else:
            manager = pywrapcp.RoutingIndexManager(
                len(problem_data['distance_matrix']),
                problem_data['num_vehicles'],
                problem_data.get('depot', 0)
            )
```

- [ ] **Step 2: Vehicle Capacities**
```python
        vehicle_capacities = problem_data.get('vehicle_capacities', [problem_data.get('max_daily_minutes', 600)] * problem_data['num_vehicles'])
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index, 0, vehicle_capacities, True, 'Capacity'
        )
```

- [ ] **Step 3: Diversity & Rhythm Penalty in Distance Callback**
```python
        diversity_penalty = kwargs.get("diversity_penalty", 50000)
        rhythm_penalty = kwargs.get("rhythm_penalty", 30000)
        categories = problem_data.get('categories', [])
        intensities = problem_data.get('intensities', [])

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            base_cost = int(problem_data['distance_matrix'][from_node][to_node] * 100)
            
            # Nếu 1 trong 2 node là depot/hotel thì không phạt
            if from_node < len(starts) or to_node < len(ends):
                return base_cost
                
            if categories and from_node < len(categories) and to_node < len(categories):
                if categories[from_node] == categories[to_node]:
                    base_cost += diversity_penalty
                    
            if intensities and from_node < len(intensities) and to_node < len(intensities):
                if intensities[from_node] == "heavy" and intensities[to_node] == "heavy":
                    base_cost += rhythm_penalty
                    
            return base_cost
```

- [ ] **Step 4: Meal constraints & Locking**
Xóa Disjunction cho Meal POIs (và locked POIs). Áp dụng `SetAllowedVehiclesForIndex`.
```python
        meal_assignments = problem_data.get("meal_assignments", {})
        is_locked_list = problem_data.get("is_locked_list", [])
        
        for node in range(len(problem_data['distance_matrix'])):
            if node < len(starts): continue # Bỏ qua depot
            
            index = manager.NodeToIndex(node)
            if node in meal_assignments:
                # Lock meal to specific vehicle (day)
                routing.SetAllowedVehiclesForIndex([meal_assignments[node]], index)
                # Bắt buộc ghé (không có AddDisjunction)
            elif is_locked_list and node < len(is_locked_list) and is_locked_list[node]:
                # Bắt buộc ghé
                pass
            else:
                # Có thể drop
                routing.AddDisjunction([index], 10_000_000_000)
```

- [ ] **Step 5: Per-vehicle time ranges**
```python
        time_windows = problem_data['time_windows']
        vehicle_time_windows = problem_data.get("vehicle_time_windows", [(480, 1260)] * problem_data['num_vehicles'])
        
        for vehicle_id in range(problem_data['num_vehicles']):
            index = routing.Start(vehicle_id)
            time_dimension.CumulVar(index).SetRange(
                int(vehicle_time_windows[vehicle_id][0] * 100),
                int(vehicle_time_windows[vehicle_id][1] * 100)
            )
```
Xoá bỏ `AddDimension` cho Max Time per Route cũ (nếu có).

- [ ] **Step 6: Extract Multi-Vehicle Solution**
Parse routes cho tất cả vehicles.
```python
        routes = []
        for vehicle_id in range(problem_data['num_vehicles']):
            index = routing.Start(vehicle_id)
            route = []
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                time_var = time_dimension.CumulVar(index)
                route.append({
                    "node": node_index,
                    "arrival_time_min": solution.Min(time_var) / 100.0,
                })
                index = solution.Value(routing.NextVar(index))
            # append end node
            routes.append(route)
            
        return {"routes": routes, ...}
```

- [ ] **Step 7: Commit**
`git commit -m "feat(core): implement OR-Tools multi-depot and callbacks"`

---

### Task 4: Travel Solver Adapter Rewrite

**Files:**
- Modify: `src/services/travel_solver.py`

- [ ] **Step 1: Implement Category to Intensity logic**
```python
def get_intensity(category: str) -> str:
    cat = category.lower()
    if cat in ["temple", "palace", "heritage", "hiking"]: return "heavy"
    if cat in ["cafe", "restaurant", "night_market", "spa", "shopping"]: return "light"
    return "medium"
```

- [ ] **Step 2: Add `solve_trip()`**
```python
    def solve_trip(self, pois: List[POI], hotels: List[Hotel], days: List[DayPlan], matrix: Dict, time_limit: int = 120) -> TravelItinerary:
        # Build node list: hotels then pois
        # Xây starts[], ends[], vehicle_capacities[], vehicle_time_windows[]
        # Tự động gán POI.intensity nếu chưa có
        # Lưu ý: meal_assignments map (node_idx -> day_idx)
        # Truyền problem_data xuống ORToolsSolver
        pass
```

- [ ] **Step 3: Keep `solve_day()` intact**
Sửa đổi nhẹ (nếu cần) để truyền `starts=[0]`, `ends=[hotel_idx]` thay cho `depot=0` để tương thích với signature mới của ORToolsImpl.

- [ ] **Step 4: Commit**
`git commit -m "feat(services): implement solve_trip adapter for multi-depot"`

---

### Task 5: Travel Plan Service Refactor & Global Budget

**Files:**
- Modify: `src/services/travel_plan_service.py`
- Modify: `src/services/poi_allocator.py`

- [ ] **Step 1: Deprecate POIAllocator**
Mở `src/services/poi_allocator.py`, thêm log deprecation warning vào đầu class.

- [ ] **Step 2: Update `_plan_impl`**
Bỏ dòng gọi allocator.
Gọi `self.travel_solver.solve_trip(...)`.
```python
        # Remove allocator logic
        
        # Gọi solve_trip thay vì vòng lặp
        itinerary = self.travel_solver.solve_trip(
            pois=request.pois,
            hotels=request.hotels,
            days=day_plans,
            matrix=matrix,
            time_limit=time_limit
        )
        
        # Budget Validation
        itinerary = self._validate_budget(itinerary, request, matrix, time_limit)
        return itinerary
```

- [ ] **Step 3: Implement `_validate_budget`**
```python
    def _validate_budget(self, itinerary, request, matrix, time_limit, max_retries=3):
        for attempt in range(max_retries):
            # Tính tổng chi phí của các POI có trong itinerary
            total_fee = sum(p.entrance_fee for p in get_visited_pois(itinerary, request.pois))
            
            if not request.constraints.budget_total or total_fee <= request.constraints.budget_total:
                return itinerary
                
            # Drop lowest priority non-locked, non-meal
            # Loại bỏ khỏi request.pois, sau đó gọi lại solve_trip
            
        return itinerary
```

- [ ] **Step 4: Commit**
`git commit -m "feat(services): remove allocator, implement global budget retry"`

---

### Task 6: Testing & Verification

- [ ] **Step 1: Write integration test for meal constraints & diversity**
Tạo file `tests/test_solver_v2.py`. Dựng 1 test đơn giản với 2 ngày, 6 POIs (2 meals, 4 POI thường).
Chạy và assert `len(itinerary.days[0].pois) >= 1` (đã có bữa ăn), check tổng fees, check thời gian giải quyết <= 120s.

- [ ] **Step 2: Verify JIT Rerouting**
Viết 1 đoạn test hoặc chạy lệnh call `/re-route` để đảm bảo API vẫn chạy mượt.

---

**Execution Instructions:**
- Dùng `using-superpowers` để gọi subagent-driven-development (nếu cho phép) hoặc tiến hành inline.
- Chạy từng task, follow log của pytest để đảm bảo đúng syntax Python.
