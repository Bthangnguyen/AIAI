import os
import sys
import csv
import json
import math
import asyncio
from uuid import UUID, uuid4

# 1. Load environment variables from travel.env
env_file = r"D:\Workspaces\AI travel optimizer\Routing Engine\layer2_3_gateway\travel.env"
if os.path.exists(env_file):
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

# 2. Setup path resolution
GATEWAY_PATH = r"D:\Workspaces\AI travel optimizer\Routing Engine\layer2_3_gateway"
SOLVER_PATH = r"D:\Workspaces\AI travel optimizer\Routing Engine\fleet-route-optimizer-cvrptw"

sys.path.insert(0, GATEWAY_PATH)
sys.path.insert(0, SOLVER_PATH)

from app.services.llm_extractor import LLMExtractorService
from app.services.utility_scorer import UtilityScorer
from app.schemas.trip import POIResponse, POIScoreBreakdown, LLMDataContract
from src.models.domain import (
    Location, TimeWindow, Hotel, DayPlan, TravelConstraints, TransportMode,
    POI as DomainPOI
)
from src.models.api import TravelPlanRequest, SolverConfig
from src.services.travel_plan_service import TravelPlanService

def haversine_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 6371.0 * 2 * math.asin(math.sqrt(a))

def offline_get_optimized_pois(contract: LLMDataContract, raw_pois: list) -> list:
    locked_pois = []
    locked_uuids = set()
    if contract.locked_pois:
        for name_query in contract.locked_pois:
            name_query_clean = name_query.lower().strip()
            if name_query_clean in {"hue", "hue", "da nang", "da nang", "ha noi", "ha noi"}:
                continue
            for raw_p in raw_pois:
                if name_query_clean in raw_p["name"].lower():
                    dist = haversine_distance(contract.hotel_lat, contract.hotel_lon, raw_p["latitude"], raw_p["longitude"])
                    if dist <= 50.0 and raw_p["uuid"] not in locked_uuids:
                        p_resp = POIResponse(
                            uuid=raw_p["uuid"],
                            name=raw_p["name"],
                            category=raw_p["category"],
                            description=raw_p["description"],
                            latitude=raw_p["latitude"],
                            longitude=raw_p["longitude"],
                            visit_duration_min=raw_p["visit_duration_min"],
                            price=raw_p["price"],
                            entrance_fee=raw_p["entrance_fee"],
                            open_time=raw_p["open_time"],
                            close_time=raw_p["close_time"],
                            priority_score=raw_p["priority_score"],
                            tags=raw_p["tags"],
                            is_locked=True
                        )
                        breakdown = POIScoreBreakdown(
                            semantic_score=1.0, quality_score=p_resp.priority_score,
                            localness_score=0.9, novelty_score=0.9, comfort_score=0.8,
                            budget_score=0.8, distance_score=0.8, diversity_gain=1.0
                        )
                        p_resp.score_breakdown = breakdown
                        p_resp.utility_score = 0.95
                        locked_pois.append(p_resp)
                        locked_uuids.add(p_resp.uuid)
                        break
    remaining_slots = 50 - len(locked_pois)
    if remaining_slots > 0:
        for raw_p in raw_pois:
            if raw_p["uuid"] in locked_uuids:
                continue
            poi_resp = POIResponse(
                uuid=raw_p["uuid"],
                name=raw_p["name"],
                category=raw_p["category"],
                description=raw_p["description"],
                latitude=raw_p["latitude"],
                longitude=raw_p["longitude"],
                visit_duration_min=raw_p["visit_duration_min"],
                price=raw_p["price"],
                entrance_fee=raw_p["entrance_fee"],
                open_time=raw_p["open_time"],
                close_time=raw_p["close_time"],
                priority_score=raw_p["priority_score"],
                tags=raw_p["tags"],
                is_locked=False
            )
            breakdown = POIScoreBreakdown(
                semantic_score=0.5, quality_score=poi_resp.priority_score,
                localness_score=0.5, novelty_score=0.5, comfort_score=0.5,
                budget_score=0.5, distance_score=0.5, diversity_gain=1.0
            )
            poi_resp.score_breakdown = breakdown
            poi_resp.utility_score = 0.5
            locked_pois.append(poi_resp)
            locked_uuids.add(poi_resp.uuid)
            if len(locked_pois) >= 50:
                break
    return locked_pois[:50]

async def debug_main():
    prompt = "Toi muon di Hue 1 ngay, ngan sach 500k, thich Dai Noi va an bun bo."
    extractor = LLMExtractorService()
    contract = await extractor.extract_intent(
        user_prompt=prompt,
        hotel_lat=16.4637,
        hotel_lon=107.5905,
        hotel_name="Hue Century Riverside Hotel",
    )
    print("Extracted budget:", contract.budget_max)
    print("Extracted locked POIs:", contract.locked_pois)

    csv_file = r"D:\Workspaces\AI travel optimizer\Routing Engine\layer2_3_gateway\ingestion\sample_data\hue_pois.csv"
    raw_pois = []
    with open(csv_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_pois.append({
                "uuid": uuid4(),
                "name": row["name"],
                "category": row["category"],
                "description": row["description"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "visit_duration_min": int(row["visit_duration_min"]),
                "price": float(row["price"]),
                "entrance_fee": float(row["entrance_fee"]),
                "open_time": int(row["open_time"]),
                "close_time": int(row["close_time"]),
                "priority_score": float(row.get("priority_score", 0.8)),
                "tags": [t.strip() for t in row["tags"].split(",") if t.strip()],
                "is_outdoor": row["is_outdoor"].lower() == "true",
            })

    selected_pois = offline_get_optimized_pois(contract, raw_pois)
    l4_pois = []
    for p in selected_pois:
        l4_pois.append(DomainPOI(
            id=str(p.uuid),
            name=p.name,
            category=p.category,
            location=Location(latitude=p.latitude, longitude=p.longitude),
            visit_duration_min=p.visit_duration_min,
            time_window=TimeWindow(start_min=p.open_time, end_min=p.close_time),
            entrance_fee=p.entrance_fee,
            priority_score=p.utility_score,
            tags=p.tags or [],
            description=p.description or "",
            is_locked=p.is_locked,
            is_outdoor=getattr(p, "is_outdoor", False)
        ))

    l4_hotels = [
        Hotel(
            id="hotel_depot",
            name=contract.hotel_name,
            location=Location(latitude=contract.hotel_lat, longitude=contract.hotel_lon),
            assigned_days=[0]
        )
    ]

    constraints = TravelConstraints(
        num_days=contract.num_days,
        budget_total=contract.budget_max,
        transport_modes=[TransportMode.TAXI],
        meal_break_enabled=True,
        meal_break_duration_min=60,
        meal_break_window=TimeWindow(start_min=690, end_min=810),
        max_consecutive_heavy=2,
        rest_interval_min=180,
        rest_duration_min=20,
        max_fatigue_per_day=15
    )

    solver_service = TravelPlanService()
    
    all_locs = [h.location for h in l4_hotels] + [p.location for p in l4_pois]
    matrix = solver_service.distance_cache.build_matrix(all_locs, TransportMode.TAXI)
    day_plans = solver_service._generate_day_plans(
        TravelPlanRequest(pois=l4_pois, hotels=l4_hotels, constraints=constraints)
    )
    solver_service._resolve_hotel_transfers(day_plans, l4_hotels)

    # Inspect the inputs
    print("\n--- Solver Inputs Debug ---")
    print(f"Number of POIs: {len(l4_pois)}")
    print(f"Number of Hotels: {len(l4_hotels)}")
    print(f"Num Days (vehicles): {constraints.num_days}")
    print(f"Hotel Start/End ID for Day 0: {day_plans[0].start_hotel_id} / {day_plans[0].end_hotel_id}")
    print(f"Day time budget: {day_plans[0].max_daily_minutes} minutes")
    print(f"Day window: {day_plans[0].start_time_min} - {day_plans[0].end_time_min}")
    
    # Find the locked POI in l4_pois
    locked_poi = next((p for p in l4_pois if p.is_locked), None)
    if locked_poi:
        print(f"Locked POI name: {locked_poi.name}")
        print(f"Locked POI duration: {locked_poi.visit_duration_min} minutes")
        print(f"Locked POI time window: {locked_poi.time_window.start_min} - {locked_poi.time_window.end_min}")
        print(f"Locked POI fatigue cost: {locked_poi.fatigue_cost if locked_poi.fatigue_cost is not None else 'default'}")
        
    print("Running solve_trip with log_search=True...")
    days_result = solver_service.solver.solve_trip(
        pois=l4_pois,
        hotels=l4_hotels,
        days=day_plans,
        matrix=matrix,
        time_limit=10,
        log_search=True
    )
    print("Result status:", "Success" if days_result else "Failed")

if __name__ == "__main__":
    asyncio.run(debug_main())
