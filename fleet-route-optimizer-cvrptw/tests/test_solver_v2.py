"""Integration test for Solver v2 — multi-depot with meals & diversity."""

import time
from src.models.domain import (
    POI, Hotel, DayPlan, Location, TimeWindow, TravelConstraints,
)
from src.services.travel_solver import TravelSolverAdapter, get_intensity


# ── Test Data: 3-day Huế trip ──

HOTEL = Hotel(
    id="hotel_hue", name="Pilgrimage Village",
    location=Location(latitude=16.4637, longitude=107.5909),
    assigned_days=[0, 1, 2],
)

POIS = [
    POI(id="dai_noi", name="Đại Nội Huế", category="palace",
        location=Location(latitude=16.4698, longitude=107.5786),
        visit_duration_min=120, entrance_fee=200000, priority_score=1.0, is_locked=True),
    POI(id="thien_mu", name="Chùa Thiên Mụ", category="temple",
        location=Location(latitude=16.4536, longitude=107.5542),
        visit_duration_min=60, entrance_fee=0, priority_score=0.8),
    POI(id="lang_tu_duc", name="Lăng Tự Đức", category="heritage",
        location=Location(latitude=16.4478, longitude=107.5667),
        visit_duration_min=90, entrance_fee=100000, priority_score=0.9),
    POI(id="cho_dong_ba", name="Chợ Đông Ba", category="market",
        location=Location(latitude=16.4714, longitude=107.5843),
        visit_duration_min=60, entrance_fee=0, priority_score=0.7),
    POI(id="cau_truong_tien", name="Cầu Trường Tiền", category="park",
        location=Location(latitude=16.4691, longitude=107.5841),
        visit_duration_min=30, entrance_fee=0, priority_score=0.7),
    POI(id="bao_tang", name="Bảo tàng Cổ vật Cung đình", category="museum",
        location=Location(latitude=16.4700, longitude=107.5790),
        visit_duration_min=60, entrance_fee=50000, priority_score=0.6),
    # Meal POIs
    POI(id="bfst_d0", name="Bún bò Huế sáng D0", category="restaurant",
        location=Location(latitude=16.4650, longitude=107.5850),
        visit_duration_min=45, entrance_fee=50000, priority_score=0.5,
        meal_type="breakfast", assigned_day=0),
    POI(id="lunch_d0", name="Cơm hến D0", category="restaurant",
        location=Location(latitude=16.4680, longitude=107.5820),
        visit_duration_min=60, entrance_fee=80000, priority_score=0.5,
        meal_type="lunch", assigned_day=0),
    POI(id="dinner_d0", name="Bánh bèo D0", category="restaurant",
        location=Location(latitude=16.4620, longitude=107.5880),
        visit_duration_min=60, entrance_fee=100000, priority_score=0.5,
        meal_type="dinner", assigned_day=0),
    POI(id="bfst_d1", name="Bún bò sáng D1", category="restaurant",
        location=Location(latitude=16.4650, longitude=107.5850),
        visit_duration_min=45, entrance_fee=50000, priority_score=0.5,
        meal_type="breakfast", assigned_day=1),
    POI(id="lunch_d1", name="Cơm chiên D1", category="restaurant",
        location=Location(latitude=16.4680, longitude=107.5820),
        visit_duration_min=60, entrance_fee=80000, priority_score=0.5,
        meal_type="lunch", assigned_day=1),
    POI(id="dinner_d1", name="Lẩu D1", category="restaurant",
        location=Location(latitude=16.4620, longitude=107.5880),
        visit_duration_min=60, entrance_fee=100000, priority_score=0.5,
        meal_type="dinner", assigned_day=1),
]

DAY_PLANS = [
    DayPlan(day_index=0, date="2026-06-01", hotel_id="hotel_hue",
            start_hotel_id="hotel_hue", end_hotel_id="hotel_hue"),
    DayPlan(day_index=1, date="2026-06-02", hotel_id="hotel_hue",
            start_hotel_id="hotel_hue", end_hotel_id="hotel_hue"),
]


def test_intensity_mapping():
    """Verify category → intensity mapping."""
    assert get_intensity("temple") == "heavy"
    assert get_intensity("palace") == "heavy"
    assert get_intensity("cafe") == "light"
    assert get_intensity("restaurant") == "light"
    assert get_intensity("museum") == "medium"
    assert get_intensity("beach") == "medium"
    print("✓ Intensity mapping OK")


def test_solve_trip_basic():
    """Basic multi-depot trip solving with meals."""
    adapter = TravelSolverAdapter()

    t0 = time.time()
    result = adapter.solve_trip(
        pois=POIS,
        hotels=[HOTEL],
        days=DAY_PLANS,
        time_limit=30,  # Reduced for test speed
    )
    elapsed = time.time() - t0

    assert result is not None, "Solver returned None"
    assert len(result) == 2, f"Expected 2 days, got {len(result)}"

    # Check meals are assigned correctly
    day0_poi_ids = [s.poi_id for s in result[0].stops]
    day1_poi_ids = [s.poi_id for s in result[1].stops]

    # Meals must be on their assigned days
    assert "bfst_d0" in day0_poi_ids, f"breakfast_d0 not in day 0: {day0_poi_ids}"
    assert "lunch_d0" in day0_poi_ids, f"lunch_d0 not in day 0: {day0_poi_ids}"
    assert "dinner_d0" in day0_poi_ids, f"dinner_d0 not in day 0: {day0_poi_ids}"
    assert "bfst_d1" in day1_poi_ids, f"breakfast_d1 not in day 1: {day1_poi_ids}"

    # Đại Nội must be visited (locked)
    all_visited = day0_poi_ids + day1_poi_ids
    assert "dai_noi" in all_visited, f"Locked POI 'dai_noi' not visited: {all_visited}"

    # Hotel names should be set
    assert result[0].start_hotel_name == "Pilgrimage Village"

    print(f"✓ solve_trip basic OK (elapsed={elapsed:.1f}s)")
    print(f"  Day 0: {day0_poi_ids}")
    print(f"  Day 1: {day1_poi_ids}")


def test_solve_day_backward_compat():
    """Verify single-day solve_day still works (for re-route)."""
    adapter = TravelSolverAdapter()
    
    pois = [p for p in POIS if p.meal_type is None][:4]  # Just regular POIs
    
    result = adapter.solve_day(
        pois=pois,
        hotel=HOTEL,
        day=DAY_PLANS[0],
        time_limit=10,
    )
    
    assert result is not None, "solve_day returned None"
    assert result.start_hotel_name == "Pilgrimage Village"
    assert result.end_hotel_name == "Pilgrimage Village"
    print(f"✓ solve_day backward compat OK ({result.num_pois} POIs)")


if __name__ == "__main__":
    test_intensity_mapping()
    test_solve_trip_basic()
    test_solve_day_backward_compat()
    print("\n🎉 All v2 tests passed!")
