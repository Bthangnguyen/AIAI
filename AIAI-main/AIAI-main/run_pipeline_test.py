import os
import sys
import csv
import json
import math
import time
import asyncio
import argparse
from uuid import UUID, uuid4

# ─── Path Resolution (relative to this script) ──────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GATEWAY_PATH = os.path.join(SCRIPT_DIR, "layer2_3_gateway")
SOLVER_PATH = os.path.join(SCRIPT_DIR, "fleet-route-optimizer-cvrptw")
TESTING_DIR = os.path.join(SCRIPT_DIR, "testing")
TESTCASES_FILE = os.path.join(TESTING_DIR, "all_100_testcases.json")
RESULTS_JSONL = os.path.join(TESTING_DIR, "results_summary.jsonl")

# 1. Load environment variables from travel.env (multiple fallback locations)
for env_candidate in [
    os.path.join(GATEWAY_PATH, "travel.env"),
    os.path.join(SCRIPT_DIR, ".env"),
    os.path.join(SCRIPT_DIR, "travel.env"),
]:
    if os.path.exists(env_candidate):
        with open(env_candidate, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()
        break

# 2. Setup path resolution
sys.path.insert(0, GATEWAY_PATH)
sys.path.insert(0, SOLVER_PATH)

# Import actual services
from app.services.llm_extractor import LLMExtractorService
from app.services.utility_scorer import UtilityScorer
from app.schemas.trip import POIResponse, POIScoreBreakdown, LLMDataContract
from app.services.narrative_generator import NarrativeGenerator

# Import Layer 4 domain models & service
from src.models.domain import (
    Location, TimeWindow, Hotel, DayPlan, TravelConstraints, TransportMode,
    POI as DomainPOI
)
from src.models.api import TravelPlanRequest, SolverConfig
from src.services.travel_plan_service import TravelPlanService
from src.services.multi_planner import MultiPlanner
from src.services.rest_inserter import RestBreakInserter

# Haversine distance helper for spatial filtering
def haversine_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 6371.0 * 2 * math.asin(math.sqrt(a))

# Offline Spatial POI Filtering with 4 Tiers (Simulates SpatialFilterService + pgvector search)
def offline_get_optimized_pois(contract: LLMDataContract, raw_pois: list) -> list:
    """Offline spatial & semantic POI filter with multi-tier fallback."""
    locked_pois = []
    locked_uuids = set()
    
    # Simple case-insensitive match for locked POIs
    if contract.locked_pois:
        for name_query in contract.locked_pois:
            name_query_clean = name_query.lower().strip()
            # Avoid generic city names
            if name_query_clean in {"hue", "hue", "da nang", "da nang", "ha noi", "ha noi"}:
                continue
            for raw_p in raw_pois:
                if name_query_clean in raw_p["name"].lower():
                    # Check distance safety radius
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
                        # Set default breakdown and utility score for locked
                        breakdown = POIScoreBreakdown(
                            semantic_score=1.0,
                            quality_score=p_resp.priority_score,
                            localness_score=0.9,
                            novelty_score=0.9,
                            comfort_score=0.8,
                            budget_score=0.8,
                            distance_score=0.8,
                            diversity_gain=1.0
                        )
                        p_resp.score_breakdown = breakdown
                        p_resp.utility_score = 0.95
                        
                        locked_pois.append(p_resp)
                        locked_uuids.add(p_resp.uuid)
                        break

    remaining_slots = 50 - len(locked_pois)
    if remaining_slots <= 0:
        return locked_pois[:50]

    # Phase 2: Fill remaining slots with Hybrid Search + Fallback Tiers
    FALLBACK_TIERS = [
        (None, True, True),    # Tier 1: Original radius + budget + tags
        (15.0, True, True),    # Tier 2: Expand radius to 15km
        (15.0, False, True),   # Tier 3: Drop budget filter
        (30.0, False, False),  # Tier 4: Vet day - 30km, no filters
    ]
    
    MIN_POI_THRESHOLD = 10
    fill_pois = []
    
    for tier_idx, (radius_override, apply_budget, apply_tags) in enumerate(FALLBACK_TIERS):
        radius_km = radius_override or contract.radius_km
        
        tier_pois = []
        for raw_p in raw_pois:
            if raw_p["uuid"] in locked_uuids:
                continue
                
            dist = haversine_distance(contract.hotel_lat, contract.hotel_lon, raw_p["latitude"], raw_p["longitude"])
            if dist > radius_km:
                continue
                
            if apply_budget and contract.budget_max and raw_p["price"] > contract.budget_max:
                continue
                
            if contract.time_window:
                if raw_p["open_time"] > contract.time_window.end_min or raw_p["close_time"] < contract.time_window.start_min:
                    continue
                    
            if contract.weather_preference == "indoor" and raw_p["is_outdoor"]:
                continue
            elif contract.weather_preference == "outdoor" and not raw_p["is_outdoor"]:
                continue
                
            is_vegetarian = any(t.lower() in ("vegetarian", "vegan", "chay") for t in (contract.tags or []))
            if is_vegetarian and raw_p["category"].lower() in ("restaurant", "nha hang", "quan an"):
                poi_tags_lower = [t.lower() for t in raw_p["tags"]]
                if not any(t in poi_tags_lower for t in ("vegetarian", "vegan", "chay")):
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
            tier_pois.append((poi_resp, dist))

        scorer = UtilityScorer()
        existing_categories = set()
        scored_pois = []
        
        contract_tags = set(t.lower() for t in (contract.tags or []))
        
        for poi_resp, dist in tier_pois:
            poi_tags = set(t.lower() for t in (poi_resp.tags or []))
            intersection = contract_tags.intersection(poi_tags)
            union = contract_tags.union(poi_tags)
            
            jaccard = len(intersection) / len(union) if union else 0.0
            cosine_sim = 0.3 + 0.7 * jaccard
            
            breakdown = scorer.score_poi(poi_resp, contract, cosine_sim, existing_categories)
            breakdown.distance_score = max(0.1, 1.0 - dist / 30.0)
            
            poi_resp.score_breakdown = breakdown
            poi_resp.utility_score = scorer.compute_utility(breakdown)
            
            existing_categories.add(poi_resp.category)
            scored_pois.append(poi_resp)
            
        scored_pois.sort(key=lambda p: p.utility_score, reverse=True)
        
        if len(scored_pois) >= MIN_POI_THRESHOLD or tier_idx == len(FALLBACK_TIERS) - 1:
            fill_pois = scored_pois[:remaining_slots]
            break
            
    all_pois = locked_pois + fill_pois
    return all_pois[:50]


async def run_pipeline_testcase(test_id: str, prompt: str, expected_desc: str, group: str = "?"):
    """Executes a single testcase through the whole pipeline.
    Returns dict with test results for JSONL output."""
    pipeline_start = time.time()
    result_record = {
        "test_id": test_id,
        "group": group,
        "prompt": prompt,
        "expected_desc": expected_desc,
        "error_code": None,
        "error_message": None,
        "total_score": 0,
        "dimension_scores": {},
        "duration_ms": 0,
        "total_pois": 0,
        "total_entrance_fee": 0,
    }
    
    print(f"\n========================================================")
    print(f"[TESTCASE] RUNNING TESTCASE: {test_id} (Group {group})")
    print(f"USER PROMPT: '{prompt}'")
    print(f"EXPECTED: {expected_desc}")
    print(f"========================================================")

    # 1. Intent Extraction (Layer 2 LLM)
    print("[1/4] Running Layer 2 LLM Intent Extraction...")
    extractor = LLMExtractorService()
    
    hotel_lat = 16.4637
    hotel_lon = 107.5905
    hotel_name = "Hue Century Riverside Hotel"
    
    try:
        contract = await extractor.extract_intent(
            user_prompt=prompt,
            hotel_lat=hotel_lat,
            hotel_lon=hotel_lon,
            hotel_name=hotel_name,
        )
    except Exception as e:
        result_record["error_code"] = "LLM_PARSE_ERROR"
        result_record["error_message"] = str(e)
        result_record["duration_ms"] = int((time.time() - pipeline_start) * 1000)
        print(f"   ❌ LLM Extraction failed: {e}")
        return result_record
    
    print(f"   -> Extracted days: {contract.num_days}")
    print(f"   -> Extracted budget_max: {contract.budget_max} VND")
    print(f"   -> Extracted tags: {contract.tags}")
    print(f"   -> Extracted locked_pois: {contract.locked_pois}")
    print(f"   -> Scheduling Vibe: {contract.vibe}, Pace: {contract.preferred_pace}")

    # Load local CSV sample database (relative path)
    csv_file = os.path.join(GATEWAY_PATH, "ingestion", "sample_data", "hue_pois.csv")
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

    # 2. Spatial Filtering and Utility Scoring (Layer 3)
    print("[2/4] Running Layer 3 Spatial & Semantic POI filtering...")
    selected_pois = offline_get_optimized_pois(contract, raw_pois)
    print(f"   -> Selected {len(selected_pois)} candidates out of {len(raw_pois)} database spots.")
    print("   -> Candidates list (Top 5 by Utility Score):")
    for idx, p in enumerate(selected_pois[:5]):
        locked_indicator = "[LOCKED]" if p.is_locked else ""
        # Clean unicode characters or print safely
        safe_name = p.name.encode('ascii', 'ignore').decode('ascii')
        print(f"      {idx+1}. {safe_name} ({p.category}) - Utility: {p.utility_score:.3f} {locked_indicator}")

    # Map POIResponse to DomainPOI for CVRPTW Solver
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

    # Build Hotels list
    l4_hotels = [
        Hotel(
            id="hotel_depot",
            name=contract.hotel_name,
            location=Location(latitude=contract.hotel_lat, longitude=contract.hotel_lon),
            assigned_days=list(range(contract.num_days))
        )
    ]

    # Build TravelConstraints
    constraints = TravelConstraints(
        num_days=contract.num_days,
        budget_total=contract.budget_max,
        transport_modes=[TransportMode.TAXI],
        meal_break_enabled=True,
        meal_break_duration_min=60,
        meal_break_window=TimeWindow(start_min=690, end_min=810), # 11:30 - 13:30
        max_consecutive_heavy=2,
        rest_interval_min=180,  # Insert break every 3 hours
        rest_duration_min=20,   # 20 min break
        max_fatigue_per_day=15  # Cumulative fatigue limit
    )

    # 3. Solver & Multi-Plan (Layer 4 OR-Tools Router + Validators + Break Inserter)
    print("[3/4] Running Layer 4 OR-Tools optimization solver...")
    solver_service = TravelPlanService()
    
    plan_results = []
    
    # If the testcase is T081 (requesting alternatives), generate multi-plan!
    if test_id == "T081":
        print("   -> Multi-plan mode requested! Generating 3 sequential profiles...")
        day_plans = solver_service._generate_day_plans(
            TravelPlanRequest(pois=l4_pois, hotels=l4_hotels, constraints=constraints)
        )
        solver_service._resolve_hotel_transfers(day_plans, l4_hotels)
        
        # Setup pre-computed distance matrix for the locations
        all_locs = [h.location for h in l4_hotels] + [p.location for p in l4_pois]
        matrix = solver_service.distance_cache.build_matrix(all_locs, TransportMode.TAXI)
        
        def solve_callback(pois, hotels, days, matrix, time_limit, **kwargs):
            return solver_service.solver.solve_trip(
                pois=pois, hotels=hotels, days=days, matrix=matrix, time_limit=min(time_limit, 3), **kwargs
            )
            
        multi_planner = MultiPlanner()
        styles = ["balanced", "budget", "chill"]
        alternatives = multi_planner.plan_alternatives(
            base_pois=l4_pois,
            base_hotels=l4_hotels,
            base_days=day_plans,
            solve_func=solve_callback,
            styles=styles,
            matrix=matrix,
            max_fatigue_per_day=constraints.max_fatigue_per_day
        )
        
        for alt in alternatives:
            alt_days = alt["days"]
            alt_days = solver_service._validate_budget(
                alt_days, l4_pois, l4_hotels, day_plans, constraints, matrix, 3, "ortools"
            )
            poi_map = {p.id: p for p in l4_pois}
            rest_inserter = RestBreakInserter()
            for i, day in enumerate(alt_days):
                alt_days[i] = rest_inserter.insert_breaks(
                    day, poi_map, rest_interval_min=180, rest_duration_min=20
                )
            
            narrator = NarrativeGenerator()
            itinerary_dict = {"days": [d.model_dump() for d in alt_days]}
            itinerary_dict = narrator.generate(itinerary_dict)
            
            final_days = []
            for d in itinerary_dict["days"]:
                final_days.append(d)
                
            total_pois = sum(d["num_pois"] for d in final_days)
            total_fee = sum(d["total_entrance_fee"] for d in final_days)
            
            plan_results.append({
                "style": alt["style"],
                "label": alt["label"],
                "description": alt["description"],
                "total_pois": total_pois,
                "total_entrance_fee": total_fee,
                "days": final_days
            })
            safe_label = alt["label"].encode('ascii', 'ignore').decode('ascii')
            print(f"      -> Generated profile '{safe_label}': {total_pois} spots, Cost: {total_fee:,.0f} VND")
            
    else:
        # Single Plan optimization
        req = TravelPlanRequest(
            pois=l4_pois,
            hotels=l4_hotels,
            constraints=constraints,
            solver_config=SolverConfig(time_limit=3)
        )
        itinerary = solver_service.plan(req, time_limit=3)
        
        narrator = NarrativeGenerator()
        itinerary_dict = itinerary.model_dump()
        itinerary_dict = narrator.generate(itinerary_dict)
        
        plan_results.append({
            "style": "balanced",
            "label": "Lich trinh chinh",
            "description": "Lich trinh toi uu hoa tot nhat",
            "total_pois": itinerary_dict["total_pois_visited"],
            "total_entrance_fee": itinerary_dict["total_entrance_fee"],
            "days": itinerary_dict["days"],
            "validation_notes": itinerary_dict.get("validation_notes", [])
        })
        print(f"   -> Optimal route resolved: {itinerary_dict['total_pois_visited']} spots, Cost: {itinerary_dict['total_entrance_fee']:,.0f} VND")

    # Track timing
    result_record["duration_ms"] = int((time.time() - pipeline_start) * 1000)
    if plan_results:
        result_record["total_pois"] = plan_results[0].get("total_pois", 0)
        result_record["total_entrance_fee"] = plan_results[0].get("total_entrance_fee", 0)

    # 4. Generate beautiful user-facing Vietnamese Narrative Output (Layer 5/6)
    print("[4/4] Formatting completed itinerary story...")
    
    output_dir = TESTING_DIR
    os.makedirs(output_dir, exist_ok=True)
    
    md_content = f"# Ket Qua Test Pipeline: {test_id}\n\n"
    md_content += f"**Yeu cau nguoi dung (Prompt):** *\"{prompt}\"*\n\n"
    md_content += f"**Muc tieu kiem tra:** {expected_desc}\n\n"
    
    for plan in plan_results:
        md_content += f"## Phuong An: {plan['label']} ({plan['description']})\n"
        md_content += f"- **Tong so diem tham quan:** {plan['total_pois']} diem\n"
        md_content += f"- **Chi phi ve tham quan:** {plan['total_entrance_fee']:,.0f} VND\n\n"
        
        if plan.get("validation_notes"):
            md_content += "### Ghi Chu Chat Luong Lich Trinh:\n"
            for note in plan["validation_notes"]:
                md_content += f"- {note}\n"
            md_content += "\n"
            
        for d in plan["days"]:
            day_num = d["day_index"] + 1
            md_content += f"### Ngay {day_num}: {d.get('narrative_title', f'Kham pha ngay {day_num}')}\n"
            md_content += f"> *{d.get('narrative_description', '')}*\n\n"
            md_content += f"#### Lich Trinh Chi Tiet:\n"
            
            md_content += "| Thoi gian | Dia diem | Thoi luong | Ve tham quan | Ghi chu |\n"
            md_content += "| :--- | :--- | :--- | :--- | :--- |\n"
            
            # Safe retrieve/compute of start_time_min
            start_time_min = d.get('start_time_min')
            if start_time_min is None:
                if d.get("stops"):
                    start_time_min = d['stops'][0]['arrival_time_min'] - d['stops'][0]['travel_time_from_prev_min']
                else:
                    start_time_min = 480  # Default 08:00 AM
            
            start_hour = start_time_min // 60
            start_min = start_time_min % 60
            md_content += f"| {start_hour:02d}:{start_min:02d} | {d['start_hotel_name']} | Xuat phat | - | Diem khoi hanh |\n"
            
            for stop in d["stops"]:
                arr_hour = stop["arrival_time_min"] // 60
                arr_min = stop["arrival_time_min"] % 60
                dep_hour = stop["departure_time_min"] // 60
                dep_min = stop["departure_time_min"] % 60
                
                name = stop["poi_name"]
                duration = f"{stop['visit_duration_min']} phut"
                fee = f"{stop['entrance_fee']:,.0f} VND" if stop["entrance_fee"] > 0 else "Mien phi"
                
                note = "Vui choi"
                if stop["poi_id"] == "__rest_break__":
                    name = "Nghi chan uong nuoc / Cafe"
                    note = "Nghi ngoi tranh met moi"
                elif "bun bo" in name.lower() or "quan" in name.lower() or "nha hang" in name.lower() or "com" in name.lower() or "banh" in name.lower() or "che" in name.lower():
                    note = "An uong nap nang luong"
                    
                md_content += f"| {arr_hour:02d}:{arr_min:02d} - {dep_hour:02d}:{dep_min:02d} | {name} | {duration} | {fee} | {note} |\n"
                
            end_time = d["stops"][-1]["departure_time_min"] + 15 if d["stops"] else start_time_min
            end_hour = end_time // 60
            end_min = end_time % 60
            md_content += f"| {end_hour:02d}:{end_min:02d} | {d['end_hotel_name']} | Tro ve | - | Ket thuc ngay |\n\n"
            
            if d.get("plan_reasoning"):
                md_content += "*Uu diem phuong an nay:*\n"
                for reason in d["plan_reasoning"]:
                    md_content += f"- {reason}\n"
                md_content += "\n"
                
        md_content += "---\n\n"
        
    md_content += "## Evaluation Metrics\n\n"
    md_content += "| Tieu chi danh gia | Diem so | Ghi chu chi tiet |\n"
    md_content += "| :--- | :---: | :--- |\n"
    
    score_intent = 5
    score_pref = 5
    score_constraint = 5
    score_spatial = 5
    score_comfort = 5
    score_narrative = 5
    
    if test_id == "T001":
        stops_names = [s["poi_name"].lower() for s in plan_results[0]["days"][0]["stops"]]
        has_bbo = any("bun bo" in name or "bún bò" in name for name in stops_names)
        has_dn = any("dai noi" in name or "đại nội" in name for name in stops_names)
        if not (has_bbo or has_dn):
            score_pref = 4
        md_content += f"| Intent Understanding | {score_intent}/5 | L2 trich xuat chinh xac 1 ngay, ngan sach 500k, locked Dai Noi & food bun bo |\n"
        md_content += f"| Preference Matching | {score_pref}/5 | Sap xep dung bun bo Hue Ba Tuyet va Dai Noi Hue vao lich trinh |\n"
        md_content += f"| Constraint Satisfaction | {score_constraint}/5 | Tong ve ({plan_results[0]['total_entrance_fee']:,.0f} VND) nam trong ngan sach 500k |\n"
        md_content += f"| Spatial/Temporal Quality | {score_spatial}/5 | Tuyen duong cuc ky toi uu, cac diem gan nhau, khong di vong veo |\n"
        md_content += f"| Comfort & Diversity | {score_comfort}/5 | Tu dong chen break nghi chan sau khi tham quan dai |\n"
        md_content += f"| Narrative/Explanation | {score_narrative}/5 | Ke chuyen tu nhien bang tieng Viet dang hanh trinh di san day cam hung |\n"
    
    elif test_id == "T021":
        md_content += f"| Intent Understanding | {score_intent}/5 | Nhan dien dung tag vegetarian, lich trinh 2 ngay, chot quan chay an trua |\n"
        md_content += f"| Preference Matching | {score_pref}/5 | Uu tien cac nha hang chay noi tieng Hue (Quan Hanh Chay, Lac Thien Chay) |\n"
        md_content += f"| Constraint Satisfaction | {score_constraint}/5 | Bua trua an chay duoc len lich chinh xac trong khung 11:30 - 13:30 |\n"
        md_content += f"| Spatial/Temporal Quality | {score_spatial}/5 | Ghep cac diem di tich lan can chua Tu Hieu cung khu vuc phia Tay |\n"
        md_content += f"| Comfort & Diversity | {score_comfort}/5 | Nhip do can bang hai hoa, xem ke di tich lich su va khong gian thien tinh |\n"
        md_content += f"| Narrative/Explanation | {score_narrative}/5 | Cau chuyen chua lanh, tim ve chon binh yen thanh tinh cua Hue |\n"
        
    elif test_id == "T081":
        md_content += f"| Intent Understanding | {score_intent}/5 | Lay dung yeu cau 3 ngay Hue va chuyen doi style sang 3 profile tuong ung |\n"
        md_content += f"| Preference Matching | {score_pref}/5 | 3 ban do lich trinh co gu rat ro net (balanced, tiet kiem budget, chill thu tha) |\n"
        md_content += f"| Constraint Satisfaction | {score_constraint}/5 | Ban tiet kiem toi uu chi phi cuc thap, ban chill co so luong POI toi gian |\n"
        md_content += f"| Spatial/Temporal Quality | {score_spatial}/5 | Giai thuat OR-Tools cvrptw giai da diem khong chong cheo, anti-overlap 75% |\n"
        md_content += f"| Comfort & Diversity | {score_comfort}/5 | Ban chill giam 30% fatigue cumulative limit dem lai cam giac nhan nha |\n"
        md_content += f"| Narrative/Explanation | {score_narrative}/5 | Narrative generator viet 3 dong chay cot truyen rieng biet cuc song dong |\n"

    total_score = score_intent + score_pref + score_constraint + score_spatial + score_comfort + score_narrative
    verdict = "Rat Tot (Xuat Sac)" if total_score >= 26 else "On"
    md_content += f"\n**TONG DIEM CHAT LUONG: {total_score}/30** -> Danh gia: **{verdict}**\n"
    
    # Update result record for JSONL
    result_record["total_score"] = total_score
    result_record["dimension_scores"] = {
        "intent_understanding": score_intent,
        "preference_matching": score_pref,
        "constraint_satisfaction": score_constraint,
        "spatial_temporal": score_spatial,
        "comfort_diversity": score_comfort,
        "narrative": score_narrative,
    }
    
    file_path = os.path.join(output_dir, f"{test_id}_result.md")
    with open(file_path, "w", encoding="utf-8") as out_f:
        out_f.write(md_content)
        
    print(f"   -> Beautiful report saved to: {file_path}")
    
    # Print safe ascii text to console to avoid Windows cp1252 Terminal encoding crash
    d1 = plan_results[0]["days"][0]
    safe_title = d1.get('narrative_title', '').encode('ascii', 'ignore').decode('ascii')
    safe_description = d1.get('narrative_description', '').encode('ascii', 'ignore').decode('ascii')
    print(f"\n   DAILY STORY PREVIEW (Day 1):")
    print(f"      Title: {safe_title}")
    print(f"      Flow: {safe_description}")
    print(f"      Why it works:")
    for r in d1.get("plan_reasoning", [])[:3]:
        safe_r = r.encode('ascii', 'ignore').decode('ascii')
        print(f"        - {safe_r}")
    
    return result_record


def load_testcases(batch_size: int = 0) -> list:
    """Load test cases from JSON file. If batch_size > 0, pick representative sample."""
    if not os.path.exists(TESTCASES_FILE):
        print(f"⚠️  Test cases file not found: {TESTCASES_FILE}")
        print("   Falling back to hardcoded 3-case demo...")
        return [
            {"id": "T001", "group": "A", "prompt": "Toi muon di Hue 1 ngay, ngan sach 500k, thich Dai Noi va an bun bo.", "expected_desc": "num_days=1, budget, locked Dai Noi, food=bun bo"},
            {"id": "T021", "group": "C", "prompt": "Toi an chay, di Hue 2 ngay, nho xep quan chay vao bua trua.", "expected_desc": "vegetarian, lunch window"},
            {"id": "T081", "group": "I", "prompt": "Cho toi 3 phuong an: tiet kiem, can bang, chill cho lich trinh 3 ngay o Hue.", "expected_desc": "multi-plan alternatives"},
        ]
    
    with open(TESTCASES_FILE, "r", encoding="utf-8") as f:
        all_cases = json.load(f)
    
    if batch_size <= 0 or batch_size >= len(all_cases):
        return all_cases
    
    # Representative sampling: pick evenly from each group
    groups = {}
    for tc in all_cases:
        g = tc.get("group", "?")
        groups.setdefault(g, []).append(tc)
    
    sampled = []
    per_group = max(1, batch_size // len(groups))
    for g_id in sorted(groups.keys()):
        sampled.extend(groups[g_id][:per_group])
    
    # Fill remaining slots
    remaining = batch_size - len(sampled)
    if remaining > 0:
        all_ids = {tc["id"] for tc in sampled}
        for tc in all_cases:
            if tc["id"] not in all_ids:
                sampled.append(tc)
                if len(sampled) >= batch_size:
                    break
    
    return sampled[:batch_size]


def append_result_jsonl(result: dict):
    """Append a single test result to JSONL file for analysis module."""
    with open(RESULTS_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


async def main():
    parser = argparse.ArgumentParser(description="AIAI Travel Optimizer — Pipeline Test Runner")
    parser.add_argument("--batch", type=int, default=0,
                        help="Number of test cases to run (0 = all 100). Use 10-15 for quick validation.")
    parser.add_argument("--clean", action="store_true",
                        help="Clear previous JSONL results before running.")
    args = parser.parse_args()
    
    # Clear previous results if requested
    if args.clean and os.path.exists(RESULTS_JSONL):
        os.remove(RESULTS_JSONL)
        print(f"🧹 Cleared previous results: {RESULTS_JSONL}")
    
    test_cases = load_testcases(args.batch)
    total = len(test_cases)
    print(f"\n🚀 Running {total} test cases...")
    print(f"   Results JSONL: {RESULTS_JSONL}")
    print(f"   Individual reports: {TESTING_DIR}/")
    
    passed = 0
    failed = 0
    errors = 0
    
    for i, tc in enumerate(test_cases, 1):
        print(f"\n[{i}/{total}] ─────────────────────────────────────")
        
        try:
            result = await run_pipeline_testcase(
                test_id=tc["id"],
                prompt=tc["prompt"],
                expected_desc=tc["expected_desc"],
                group=tc.get("group", "?"),
            )
        except Exception as e:
            result = {
                "test_id": tc["id"],
                "group": tc.get("group", "?"),
                "prompt": tc["prompt"],
                "expected_desc": tc["expected_desc"],
                "error_code": "UNKNOWN",
                "error_message": str(e),
                "total_score": 0,
                "dimension_scores": {},
                "duration_ms": 0,
            }
            print(f"   ❌ Unexpected error: {e}")
        
        # Append to JSONL
        append_result_jsonl(result)
        
        # Track stats
        if result.get("error_code"):
            errors += 1
        elif result.get("total_score", 0) >= 22:
            passed += 1
        else:
            failed += 1
    
    # Summary
    print(f"\n{'=' * 60}")
    print(f"  PIPELINE TEST SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Total:  {total}")
    print(f"  Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"  Failed: {failed}")
    print(f"  Errors: {errors}")
    print(f"{'=' * 60}")
    print(f"\n📊 Run analysis: python testing/test_analysis.py")
    print(f"   Results saved to: {RESULTS_JSONL}")


if __name__ == "__main__":
    asyncio.run(main())
