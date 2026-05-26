"""Compute structured metrics for a multi-plan alternative."""

from typing import Dict, List, Any, Optional

from ..models.domain import TravelItineraryDay, POI
from ..services.itinerary_validator import ItineraryValidator
from ..services.diversity_scorer import DiversityScorer
from ..services.travel_solver import compute_fatigue_cost


def compute_plan_metrics(
    days_data: List[Dict[str, Any]],
    pois: List[POI],
    budget_total: Optional[float] = None,
    max_fatigue_per_day: int = 15,
) -> Dict[str, Any]:
    """Return metrics dict for web PlanMetrics type."""
    if not days_data:
        return {
            "total_cost": 0,
            "total_travel_min": 0,
            "poi_count": 0,
            "total_distance_km": 0.0,
            "fatigue_score": 0.0,
            "diversity_score": 0.0,
            "warnings": {"meal": False, "outdoor_heat": False, "budget": False},
            "validation_messages": [],
        }

    poi_map = {p.id: p for p in pois}
    total_travel = sum(d.get("total_travel_min", 0) for d in days_data)
    total_fee = sum(d.get("total_entrance_fee", 0) for d in days_data)
    total_dist = sum(d.get("total_distance_km", 0) for d in days_data)
    poi_count = sum(
        d.get("num_pois", len([s for s in d.get("stops", []) if s.get("poi_id") != "__rest_break__"]))
        for d in days_data
    )

    categories: List[str] = []
    total_fatigue = 0
    max_fatigue_cap = max(max_fatigue_per_day * len(days_data), 1)

    for day in days_data:
        day_fatigue = 0
        for stop in day.get("stops", []):
            pid = stop.get("poi_id")
            if not pid or pid == "__rest_break__":
                continue
            poi = poi_map.get(pid)
            if poi:
                categories.append(poi.category)
                day_fatigue += compute_fatigue_cost(poi)
        total_fatigue += min(day_fatigue, max_fatigue_per_day)

    diversity = DiversityScorer().score(categories, "mixed") if categories else 0.0
    fatigue_ratio = min(1.0, total_fatigue / max_fatigue_cap)

    day_objs = [TravelItineraryDay.model_validate(d) for d in days_data]
    validation = ItineraryValidator().validate(day_objs, poi_map, {})
    validation_messages = [f"[{i.severity}] {i.message}" for i in validation.issues]

    budget_limit = budget_total if budget_total else None
    budget_warn = budget_limit is not None and total_fee > budget_limit

    return {
        "total_cost": round(total_fee),
        "total_travel_min": total_travel,
        "poi_count": poi_count,
        "total_distance_km": round(total_dist, 1),
        "fatigue_score": round(fatigue_ratio, 2),
        "diversity_score": round(diversity, 2),
        "warnings": {
            "meal": any(i.rule == "meal_missing" for i in validation.issues),
            "outdoor_heat": any(i.rule == "outdoor_heat" for i in validation.issues),
            "budget": budget_warn,
        },
        "validation_messages": validation_messages,
    }
