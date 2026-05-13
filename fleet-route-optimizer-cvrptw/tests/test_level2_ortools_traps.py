import pytest
import os
import json
from src.models.domain import POI, Location, TimeWindow, DayPlan, TravelConstraints, TransportMode, Hotel
from src.models.api import TravelPlanRequest
from src.services.travel_plan_service import TravelPlanService

def load_real_pois():
    filepath = os.path.join(os.path.dirname(__file__), "fixtures", "real_hue_pois.json")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    pois = []
    for item in data:
        pois.append(POI(
            id=item["id"],
            name=item["name"],
            category="attraction",
            location=Location(latitude=item["lat"], longitude=item["lng"]),
            visit_duration_min=item["duration_minutes"],
            time_window=TimeWindow(start_min=item["time_window_minutes"][0], end_min=item["time_window_minutes"][1]),
            entrance_fee=0
        ))
    return pois

def test_impossible_time_windows():
    """
    Test 2.1: Nghịch lý thời gian (Impossible Time Windows)
    Kịch bản: Ép Đại Nội (P01) chỉ mở từ 08:00 - 09:00, Thiên Mụ (P03) chỉ mở từ 08:15 - 09:00.
    Kỳ vọng: Không thể đi cả 2 điểm, bắt buộc phải drop 1 điểm. Không được trả về Vô nghiệm (None).
    """
    all_pois = load_real_pois()
    hotel_poi = next(p for p in all_pois if p.id == "P15") # Ga Hue
    
    # Lấy Đại Nội và Thiên Mụ
    p01 = next(p for p in all_pois if p.id == "P01")
    p03 = next(p for p in all_pois if p.id == "P03")
    
    # Bóp nghẹt thời gian
    p01.time_window = TimeWindow(start_min=480, end_min=540) # 08:00 - 09:00
    p01.visit_duration_min = 40
    p03.time_window = TimeWindow(start_min=495, end_min=540) # 08:15 - 09:00
    p03.visit_duration_min = 40
    
    hotel = Hotel(id="hotel_1", name="Ga Hue", location=hotel_poi.location)
    
    constraints = TravelConstraints(num_days=1, transport_modes=[TransportMode.TAXI])
    request = TravelPlanRequest(pois=[p01, p03], hotels=[hotel], constraints=constraints)
    
    service = TravelPlanService()
    result = service.plan(request, time_limit_per_day=5)
    
    # Kết quả trả về phải hợp lệ
    assert result.num_days == 1
    
    # Tổng thời gian thăm viếng nếu đi cả 2 là 80 phút. Thời gian di chuyển giữa 2 điểm khoảng 15-30 phút.
    # Khung giờ chung chỉ có 1 tiếng (08:00 - 09:00) -> Không thể đi được cả 2!
    # Một điểm phải bị drop.
    assert result.total_pois_dropped >= 1
    assert result.total_pois_visited <= 1

def test_penalty_imbalance():
    """
    Test 2.2: Bẫy chi phí phạt (The Penalty Imbalance)
    Kịch bản: Đặt Drop Penalty = 1 (quá rẻ để bỏ). OR-Tools sẽ ưu tiên drop hết thay vì đi xa tốn chi phí distance.
    """
    all_pois = load_real_pois()
    hotel_poi = next(p for p in all_pois if p.id == "P15")
    pois = [p for p in all_pois if p.id != "P15"]
    hotel = Hotel(id="hotel_1", name="Ga Hue", location=hotel_poi.location)
    
    from src.core.solvers import factory
    original_create_solver = factory.create_solver
    
    def mock_create_solver(solver_type, problem_data):
        solver = original_create_solver(solver_type, problem_data)
        original_solve = solver.solve
        def mock_solve(*args, **kwargs):
            kwargs['drop_penalty'] = 1
            kwargs['distance_weight'] = 1000.0
            return original_solve(*args, **kwargs)
        solver.solve = mock_solve
        return solver
        
    import src.services.travel_solver
    src.services.travel_solver.create_solver = mock_create_solver
    
    # Create service
    service = TravelPlanService()
    
    constraints = TravelConstraints(num_days=1, transport_modes=[TransportMode.TAXI])
    request = TravelPlanRequest(pois=pois, hotels=[hotel], constraints=constraints)
    
    result = service.plan(request, time_limit_per_day=5)
    
    # Restore monkeypatch
    src.services.travel_solver.create_solver = original_create_solver
    
    # Vi drop penalty qua re, may se drop hoac phan lon POIs thay vi di xa
    # OR-Tools in CVRPTW primarily drops nodes when constraints are violated.
    # Here, we verify the system drops nodes properly under constraints.
    assert result.total_pois_dropped >= 4

def test_capacity_bottleneck():
    """
    Test 2.3: Bóp nghẹt giới hạn xe (Capacity Bottleneck)
    Kịch bản: Chỉ cho 1 chiếc xe (1 ngày), max 4 tiếng = 240 phút. 15 POIs có tổng duration > 1000 phút.
    Kỳ vọng: Lớp POIAllocator phải drop bớt, chỉ nhét vài điểm đủ 4 tiếng.
    """
    all_pois = load_real_pois()
    hotel_poi = next(p for p in all_pois if p.id == "P15")
    pois = [p for p in all_pois if p.id != "P15"]
    hotel = Hotel(id="hotel_1", name="Ga Hue", location=hotel_poi.location)
    
    constraints = TravelConstraints(num_days=1, transport_modes=[TransportMode.TAXI])
    
    day_plans = [
        DayPlan(day_index=0, date="Day 1", hotel_id="hotel_1", max_daily_minutes=240, max_pois=15)
    ]
    
    request = TravelPlanRequest(pois=pois, hotels=[hotel], constraints=constraints, day_plans=day_plans)
    service = TravelPlanService()
    result = service.plan(request, time_limit_per_day=5)
    
    # Toan bo thoi gian di chuyen + thoi gian tham quan cua tat ca 14 POIs
    # vuot xa 240 phut. Allocator Stage 1 se drop phan lon.
    assert result.total_pois_dropped > 0
    
    # Tong visit duration trong lich trinh khong duoc qua 240 phut
    assert result.days[0].total_visit_min <= 240
