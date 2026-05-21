import pytest
import asyncio
import time
import uuid
from src.models.domain import POI, Location, TimeWindow, DayPlan, TravelConstraints, TransportMode, Hotel
from src.models.api import TravelPlanRequest
from src.services.travel_plan_service import TravelPlanService

def generate_random_pois(count: int):
    pois = []
    import random
    random.seed(42)
    for i in range(count):
        pois.append(POI(
            id=f"P_{i}",
            name=f"Point {i}",
            category="attraction",
            location=Location(latitude=16.4 + random.random()*0.1, longitude=107.5 + random.random()*0.1),
            visit_duration_min=30,
            time_window=TimeWindow(start_min=480, end_min=1020),
            entrance_fee=0
        ))
    return pois

def test_concurrency_request():
    """
    Test 3.3: Concurrency Request
    """
    service = TravelPlanService()
    hotel = Hotel(id="hotel_1", name="Ga Hue", location=Location(latitude=16.458315, longitude=107.575916))
    constraints = TravelConstraints(num_days=1, transport_modes=[TransportMode.TAXI])
    
    async def make_request(i):
        pois = generate_random_pois(5)
        request = TravelPlanRequest(pois=pois, hotels=[hotel], constraints=constraints)
        result = await asyncio.to_thread(service.plan, request, 2)
        return result
    
    async def run_all():
        start_time = time.time()
        results = await asyncio.gather(*[make_request(i) for i in range(10)])
        elapsed = time.time() - start_time
        
        assert len(results) == 10
        for r in results:
            assert r.status == "success"
        print(f"Test 3.3 completed in {elapsed:.2f} seconds.")
    
    asyncio.run(run_all())

def test_matrix_explosion():
    """
    Test 3.2: Matrix Explosion
    """
    service = TravelPlanService()
    hotel = Hotel(id="hotel_1", name="Ga Hue", location=Location(latitude=16.458315, longitude=107.575916))
    constraints = TravelConstraints(num_days=1, transport_modes=[TransportMode.TAXI])
    pois = generate_random_pois(100)
    
    request = TravelPlanRequest(pois=pois, hotels=[hotel], constraints=constraints)
    
    start_time = time.time()
    day_plans = [DayPlan(day_index=0, date="Day 1", hotel_id="hotel_1", max_daily_minutes=1440, max_pois=100)]
    request.day_plans = day_plans
    
    result = service.plan(request, time_limit=3)
    elapsed = time.time() - start_time
    
    assert result.status == "success"
    assert elapsed < 15.0
    print(f"Test 3.2 Matrix 100x100 completed in {elapsed:.2f} seconds.")

def test_osrm_timeout_fallback(monkeypatch):
    """
    Test 3.1: Traffic API Timeout
    """
    import urllib.request
    from urllib.error import URLError
    
    def mock_urlopen(*args, **kwargs):
        raise URLError("Simulated OSRM Timeout")
        
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    
    service = TravelPlanService()
    hotel = Hotel(id="hotel_1", name="Ga Hue", location=Location(latitude=16.458315, longitude=107.575916))
    constraints = TravelConstraints(num_days=1, transport_modes=[TransportMode.TAXI])
    pois = generate_random_pois(5)
    
    request = TravelPlanRequest(pois=pois, hotels=[hotel], constraints=constraints)
    result = service.plan(request, time_limit=2)
    
    assert result.status == "success"
    assert result.total_pois_visited > 0
    print(f"Test 3.1 OSRM API Timeout fallback OK.")
