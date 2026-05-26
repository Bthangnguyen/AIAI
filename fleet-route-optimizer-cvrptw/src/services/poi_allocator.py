"""POI Allocator — Stage 1 of Two-Stage travel solver.

Assigns POIs to days using combined scoring:
  score = w1 * geo_proximity + w2 * time_compatibility + w3 * priority
Then enforces capacity (max_daily_minutes) and budget constraints.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import math

from ..models.domain import POI, Hotel, DayPlan, TravelConstraints, Location
from ..config import get_logger

logger = get_logger(__name__)


@dataclass
class AllocationResult:
    """Result of POI-to-day allocation."""
    day_assignments: Dict[int, List[str]]  # day_index -> list of POI ids
    dropped_poi_ids: List[str] = field(default_factory=list)
    dropped_reasons: Dict[str, str] = field(default_factory=dict)


class POIAllocator:
    """Assigns POIs to travel days using geo + time + hotel scoring."""

    def __init__(self, w_geo: float = 0.5, w_time: float = 0.2, w_priority: float = 0.3):
        self.w_geo = w_geo
        self.w_time = w_time
        self.w_priority = w_priority

    def allocate(
        self,
        pois: List[POI],
        hotels: List[Hotel],
        days: List[DayPlan],
        constraints: TravelConstraints,
    ) -> AllocationResult:
        """Allocate POIs to days.

        Algorithm:
        1. Build hotel lookup (day_index -> hotel)
        2. Soft-filter: drop POIs that are clearly over budget with low priority
        3. Score each (POI, day) pair
        4. Greedy assign: best-scoring POI-day pair first
        5. Enforce capacity per day (max_daily_minutes)
        """
        # Build hotel lookup
        hotel_map = {h.id: h for h in hotels}
        day_hotel = {}
        for day in days:
            if day.hotel_id and day.hotel_id in hotel_map:
                day_hotel[day.day_index] = hotel_map[day.hotel_id]
            elif hotels:
                day_hotel[day.day_index] = hotels[0]

        # Soft budget filter
        remaining_pois, dropped_ids, dropped_reasons = self._soft_budget_filter(
            pois, constraints
        )

        # Score and assign
        day_assignments = {d.day_index: [] for d in days}
        day_used_minutes = {d.day_index: 0 for d in days}
        day_used_budget = {d.day_index: 0.0 for d in days}
        day_limits = {d.day_index: d for d in days}

        budget_per_day = None
        if constraints.budget_total is not None:
            budget_per_day = constraints.budget_total / max(constraints.num_days, 1)

        # Calculate scores for all (poi, day) pairs
        scored_pairs = []
        for poi in remaining_pois:
            for day in days:
                hotel = day_hotel.get(day.day_index)
                score = self._score(poi, day, hotel)
                scored_pairs.append((score, poi, day.day_index))

        # Sort descending by score
        scored_pairs.sort(key=lambda x: x[0], reverse=True)

        assigned_poi_ids = set()
        for score, poi, day_idx in scored_pairs:
            if poi.id in assigned_poi_ids:
                continue

            day = day_limits[day_idx]

            # Check capacity
            if day_used_minutes[day_idx] + poi.visit_duration_min > day.max_daily_minutes:
                continue

            # Check max POIs per day
            if len(day_assignments[day_idx]) >= day.max_pois:
                continue

            # Check budget
            if budget_per_day is not None:
                if day_used_budget[day_idx] + poi.entrance_fee > budget_per_day:
                    continue

            # Assign
            day_assignments[day_idx].append(poi.id)
            day_used_minutes[day_idx] += poi.visit_duration_min
            day_used_budget[day_idx] += poi.entrance_fee
            assigned_poi_ids.add(poi.id)

        # Collect unassigned POIs
        for poi in remaining_pois:
            if poi.id not in assigned_poi_ids:
                dropped_ids.append(poi.id)
                dropped_reasons[poi.id] = "capacity_or_budget_overflow"

        logger.info(
            f"POI Allocation: {len(assigned_poi_ids)} assigned, "
            f"{len(dropped_ids)} dropped across {len(days)} days"
        )

        return AllocationResult(
            day_assignments=day_assignments,
            dropped_poi_ids=dropped_ids,
            dropped_reasons=dropped_reasons,
        )

    def _soft_budget_filter(
        self, pois: List[POI], constraints: TravelConstraints
    ) -> tuple:
        """Remove POIs that clearly exceed budget with low value ratio."""
        if constraints.budget_total is None:
            return pois, [], {}

        budget = constraints.budget_total
        dropped_ids = []
        dropped_reasons = {}
        remaining = []

        for poi in pois:
            # Drop if single POI costs >50% of total budget AND priority < 0.3
            if poi.entrance_fee > budget * 0.5 and poi.priority_score < 0.3:
                dropped_ids.append(poi.id)
                dropped_reasons[poi.id] = "budget_soft_filter"
                logger.info(
                    f"Soft-filter dropped: {poi.id} "
                    f"(fee={poi.entrance_fee}, priority={poi.priority_score})"
                )
            else:
                remaining.append(poi)

        return remaining, dropped_ids, dropped_reasons

    def _score(self, poi: POI, day: DayPlan, hotel: Optional[Hotel]) -> float:
        """Score a (POI, day) pair. Higher = better fit."""
        geo_score = 0.0
        if hotel:
            dist = self._haversine(
                poi.location.latitude, poi.location.longitude,
                hotel.location.latitude, hotel.location.longitude,
            )
            # Normalize: closer = higher score (max 1.0 at 0km, 0.0 at 50+km)
            geo_score = max(0.0, 1.0 - dist / 50.0)

        time_score = 0.0
        if poi.time_window:
            day_mid = (day.start_time_min + day.end_time_min) / 2
            poi_mid = (poi.time_window.start_min + poi.time_window.end_min) / 2
            # Closer midpoints = better time compatibility
            time_diff = abs(day_mid - poi_mid)
            time_score = max(0.0, 1.0 - time_diff / 720.0)
        else:
            time_score = 0.5

        priority_score = poi.priority_score

        return (
            self.w_geo * geo_score
            + self.w_time * time_score
            + self.w_priority * priority_score
        )

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine distance in km."""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (math.sin(dlat / 2) ** 2
             + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        return 6371.0 * 2 * math.asin(math.sqrt(a))
