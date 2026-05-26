"""Generate multiple alternative itinerary plans with anti-overlap."""

import copy
import logging
from typing import List, Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)

PLAN_PROFILES = {
    "balanced": {
        "label": "Cân bằng",
        "description": "Kết hợp tham quan, ăn uống, và nghỉ ngơi hài hòa",
        "time_limit": 120,
        "budget_factor": 1.0,
        "max_pois_factor": 1.0,
        "max_fatigue_factor": 1.0,
    },
    "budget": {
        "label": "Tiết kiệm",
        "description": "Ưu tiên trải nghiệm miễn phí và giá rẻ",
        "time_limit": 60,
        "budget_factor": 0.7,
        "max_pois_factor": 1.0,
        "max_fatigue_factor": 1.0,
    },
    "chill": {
        "label": "Thoải mái",
        "description": "Ít điểm, nhiều thời gian thư giãn",
        "time_limit": 60,
        "budget_factor": 1.0,
        "max_pois_factor": 0.65,
        "max_fatigue_factor": 0.7,
    },
}


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


class MultiPlanner:
    """Generates multiple alternative itinerary plans sequentially."""

    def plan_alternatives(
        self,
        base_pois: List,
        base_hotels: List,
        base_days: List,
        solve_func: Callable,
        styles: Optional[List[str]] = None,
        matrix: Optional[Dict] = None,
        **base_kwargs,
    ) -> List[Dict[str, Any]]:
        """Generate multiple alternative plans with anti-overlap.
        
        Args:
            base_pois: Original POI list
            base_hotels: Hotel list
            base_days: DayPlan list
            solve_func: Function(pois, hotels, days, matrix, time_limit, **kwargs) -> List[TravelItineraryDay]
            styles: List of style names (default: balanced, budget, chill)
            matrix: Distance/duration matrix
            
        Returns:
            List of plan dicts with style, label, description, days, overlap_warning
        """
        styles = styles or ["balanced", "budget", "chill"]
        plans = []
        all_used_poi_ids = []  # list of sets per plan

        for style in styles:
            profile = PLAN_PROFILES.get(style, PLAN_PROFILES["balanced"])

            # Deep copy and modify POIs based on profile + anti-overlap
            modified_pois = copy.deepcopy(base_pois)
            modified_days = copy.deepcopy(base_days)

            # Anti-overlap: reduce priority of previously-used POIs
            used_so_far = set()
            for used_set in all_used_poi_ids:
                used_so_far |= used_set

            if used_so_far:
                for poi in modified_pois:
                    if poi.id in used_so_far and not poi.is_locked:
                        poi.priority_score *= 0.75  # 25% reduction

            # Budget factor
            budget_factor = profile.get("budget_factor", 1.0)

            # Max POIs factor
            pois_factor = profile.get("max_pois_factor", 1.0)
            if pois_factor != 1.0:
                for dp in modified_days:
                    dp.max_pois = max(2, int(dp.max_pois * pois_factor))

            # Fatigue factor
            fatigue_factor = profile.get("max_fatigue_factor", 1.0)
            modified_kwargs = dict(base_kwargs)
            if fatigue_factor != 1.0:
                base_fatigue = modified_kwargs.get("max_fatigue_per_day", 15)
                modified_kwargs["max_fatigue_per_day"] = int(base_fatigue * fatigue_factor)

            try:
                days_result = solve_func(
                    pois=modified_pois,
                    hotels=base_hotels,
                    days=modified_days,
                    matrix=matrix,
                    time_limit=profile["time_limit"],
                    **modified_kwargs,
                )
            except Exception as e:
                logger.error(f"Multi-plan {style} failed: {e}")
                continue

            if not days_result:
                logger.warning(f"Multi-plan {style}: no solution")
                continue

            # Collect used POI IDs
            this_plan_pois = set()
            for day in days_result:
                for stop in day.stops:
                    this_plan_pois.add(stop.poi_id)

            # Check overlap with previous plans
            overlap_warning = None
            for i, prev_set in enumerate(all_used_poi_ids):
                jaccard = jaccard_similarity(this_plan_pois, prev_set)
                if jaccard > 0.75:
                    overlap_warning = f"Overlap {jaccard:.0%} with plan {i+1}"
                    logger.warning(f"Multi-plan {style}: {overlap_warning}")

            all_used_poi_ids.append(this_plan_pois)

            plans.append({
                "style": style,
                "label": profile["label"],
                "description": profile["description"],
                "days": days_result,
                "overlap_warning": overlap_warning,
            })

        return plans
