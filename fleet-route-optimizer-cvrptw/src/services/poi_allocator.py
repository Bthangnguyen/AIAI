"""POI Allocator — Stage 1 of Two-Stage travel solver.

Category-First algorithm (3-phase):
  Phase 1: Compute category quotas from LLM distribution × total_pois
  Phase 2: Distribute quotas evenly across days
  Phase 3: Fill each (day, category) slot with best POI by geo + priority
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import math

from ..models.domain import POI, Hotel, DayPlan, TravelConstraints, Location
from ..config import get_logger

logger = get_logger(__name__)

# Mapping from micro-category to macro group (mirrored from Layer 2/3 utility_scorer.py)
CATEGORY_GROUP_MAP = {
    "food": {"restaurant", "nhà hàng", "quán ăn", "bún bò", "bánh mì",
             "cháo", "bún", "cơm", "hải sản", "chả cuốn", "cơm hến",
             "bánh canh", "bánh ướt", "bánh bèo", "bánh ít", "bắp",
             "bình dân", "chay", "cung đình", "bánh khoái", "food",
             "street_food", "fine_dining", "local_restaurant"},
    "cafe": {"cafe", "cà phê", "trà", "coffee", "tea"},
    "culture": {"historic", "historical", "history", "temple", "tourism_attraction",
                "culture", "cultural", "heritage", "museum", "bảo tàng", "landmark",
                "UNESCO", "Hoàng thành", "Kinh thành", "ca Huế", "dân gian"},
    "nature": {"nature", "park", "công viên", "garden", "lake", "river"},
    "nightlife": {"bar", "night_market", "pub", "karaoke", "nightlife"},
    "shopping": {"shop", "chợ", "market", "mua sắm", "shopping"},
    "art": {"gallery", "art", "nghệ thuật"},
    "wellness": {"spa", "massage", "wellness"},
    "adventure": {"trekking", "outdoor", "sport", "hiking", "adventure"},
}

# Categories to exclude from allocation (not POIs)
EXCLUDED_GROUPS = {"accommodation"}

# Default balanced distribution when LLM doesn't provide one (uses 5 core categories)
DEFAULT_DISTRIBUTION = {
    "food": 0.30,
    "culture": 0.35,
    "nature": 0.20,
    "nightlife": 0.10,
    "adventure": 0.05,
}


@dataclass
class AllocationResult:
    """Result of POI-to-day allocation."""
    day_assignments: Dict[int, List[str]]  # day_index -> list of POI ids
    dropped_poi_ids: List[str] = field(default_factory=list)
    dropped_reasons: Dict[str, str] = field(default_factory=dict)


class POIAllocator:
    """Assigns POIs to travel days using category-first balancing.

    Algorithm:
      Phase 1: Compute hard quotas from target_category_distribution
      Phase 2: Distribute quotas evenly across days
      Phase 3: Fill slots with best POIs by geo + priority
    """

    def __init__(self, w_geo: float = 0.10, w_time: float = 0.10, w_priority: float = 0.30):
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
        """Allocate POIs to days using category-first balancing.

        Algorithm:
        1. Resolve category_group for each POI
        2. Compute category quotas from distribution
        3. Distribute quotas evenly across days
        4. Fill (day, category) slots with best POIs
        5. Handle overflow with fallback assignment
        """
        num_days = len(days)
        if num_days == 0:
            return AllocationResult(day_assignments={})

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

        # Phase 0: Resolve category_group for each POI and filter out non-POIs
        for poi in remaining_pois:
            if not poi.category_group:
                poi.category_group = self._resolve_category_group(poi.category)

        # Filter out accommodation/hotel entries
        remaining_pois = [p for p in remaining_pois if p.category_group not in EXCLUDED_GROUPS]

        # Group POIs by category_group
        pois_by_group: Dict[str, List[POI]] = {}
        for poi in remaining_pois:
            group = poi.category_group or "culture"
            pois_by_group.setdefault(group, []).append(poi)

        # Phase 1: Compute category quotas
        distribution = getattr(constraints, 'target_category_distribution', None)
        if not distribution:
            distribution = DEFAULT_DISTRIBUTION.copy()

        total_pois = len(remaining_pois)
        quotas = self._compute_quotas(distribution, total_pois, pois_by_group)

        logger.info(
            f"Category quotas: {quotas} (total={total_pois}, "
            f"distribution={distribution})"
        )

        # Phase 2: Distribute quotas across days
        day_quotas = self._distribute_to_days(quotas, num_days)

        logger.info(f"Per-day quotas: {day_quotas}")

        # Phase 3: Fill slots with best POIs
        day_assignments = {d.day_index: [] for d in days}
        day_used_minutes = {d.day_index: 0 for d in days}
        day_used_budget = {d.day_index: 0.0 for d in days}
        day_limits = {d.day_index: d for d in days}
        assigned_poi_ids = set()

        budget_per_day = None
        if constraints.budget_total is not None:
            budget_per_day = constraints.budget_total / max(num_days, 1)

        # Build a mutable copy of POI pools by group
        available_by_group: Dict[str, List[POI]] = {
            group: list(pool) for group, pool in pois_by_group.items()
        }

        # Fill each (day, category) slot
        for day in days:
            day_idx = day.day_index
            hotel = day_hotel.get(day_idx)
            day_quota = day_quotas.get(day_idx, {})

            for group, count in day_quota.items():
                pool = available_by_group.get(group, [])
                for _ in range(count):
                    best_poi = self._pick_best_poi(
                        pool, day, hotel, day_used_minutes[day_idx],
                        day_used_budget[day_idx], budget_per_day,
                        assigned_poi_ids, day_limits[day_idx],
                        day_assignments[day_idx],
                    )
                    if best_poi:
                        day_assignments[day_idx].append(best_poi.id)
                        day_used_minutes[day_idx] += best_poi.visit_duration_min
                        day_used_budget[day_idx] += best_poi.entrance_fee
                        assigned_poi_ids.add(best_poi.id)
                        pool.remove(best_poi)

        # Phase 3b: Fallback — assign any remaining unassigned POIs
        unassigned = [p for p in remaining_pois if p.id not in assigned_poi_ids]
        for poi in unassigned:
            best_day_idx = self._find_best_day(
                poi, days, day_hotel, day_used_minutes,
                day_used_budget, budget_per_day, day_limits,
                day_assignments,
            )
            if best_day_idx is not None:
                day_assignments[best_day_idx].append(poi.id)
                day_used_minutes[best_day_idx] += poi.visit_duration_min
                day_used_budget[best_day_idx] += poi.entrance_fee
                assigned_poi_ids.add(poi.id)
            else:
                dropped_ids.append(poi.id)
                dropped_reasons[poi.id] = "capacity_or_budget_overflow"

        # Collect remaining unassigned
        for poi in remaining_pois:
            if poi.id not in assigned_poi_ids:
                if poi.id not in dropped_ids:
                    dropped_ids.append(poi.id)
                    dropped_reasons[poi.id] = "capacity_or_budget_overflow"

        logger.info(
            f"POI Allocation: {len(assigned_poi_ids)} assigned, "
            f"{len(dropped_ids)} dropped across {num_days} days"
        )

        return AllocationResult(
            day_assignments=day_assignments,
            dropped_poi_ids=dropped_ids,
            dropped_reasons=dropped_reasons,
        )

    # ─── Phase 1: Compute Quotas ───

    def _compute_quotas(
        self,
        distribution: Dict[str, float],
        total_pois: int,
        available_by_group: Dict[str, List[POI]],
    ) -> Dict[str, int]:
        """Convert distribution ratios to integer quotas.

        Uses largest-remainder method (Hamilton's method) to ensure sum = total_pois.
        Caps each quota by available POIs in that group.
        """
        # Filter to categories that actually have POIs available
        active_groups = {k: v for k, v in distribution.items()
                         if available_by_group.get(k)}

        if not active_groups:
            # Fallback: distribute evenly across whatever groups have POIs
            groups_with_pois = list(available_by_group.keys())
            per_group = max(1, total_pois // max(len(groups_with_pois), 1))
            return {g: min(per_group, len(available_by_group[g]))
                    for g in groups_with_pois}

        # Re-normalize active distribution to sum=1.0
        total_weight = sum(active_groups.values())
        if total_weight <= 0:
            total_weight = 1.0
        normalized = {k: v / total_weight for k, v in active_groups.items()}

        # Largest-remainder method
        raw = {k: v * total_pois for k, v in normalized.items()}
        floored = {k: int(v) for k, v in raw.items()}

        # Cap by available POIs
        for k in floored:
            available = len(available_by_group.get(k, []))
            floored[k] = min(floored[k], available)

        remainder = total_pois - sum(floored.values())
        # Give remaining slots to categories with largest fractional parts
        by_frac = sorted(
            raw.keys(),
            key=lambda k: raw[k] - floored[k],
            reverse=True,
        )
        for k in by_frac:
            if remainder <= 0:
                break
            available = len(available_by_group.get(k, []))
            if floored[k] < available:
                floored[k] += 1
                remainder -= 1

        return {k: v for k, v in floored.items() if v > 0}

    # ─── Phase 2: Distribute to Days ───

    def _distribute_to_days(
        self, quotas: Dict[str, int], num_days: int,
    ) -> Dict[int, Dict[str, int]]:
        """Distribute category quotas evenly across days.

        E.g., culture:3 across 3 days → {0: 1, 1: 1, 2: 1}
              food:2 across 3 days → {0: 1, 1: 1, 2: 0}
        """
        day_quotas: Dict[int, Dict[str, int]] = {d: {} for d in range(num_days)}

        for cat, count in quotas.items():
            base = count // num_days
            extra = count % num_days
            for d in range(num_days):
                day_count = base + (1 if d < extra else 0)
                if day_count > 0:
                    day_quotas[d][cat] = day_count

        return day_quotas

    # ─── Phase 3: Fill Slots ───

    def _pick_best_poi(
        self,
        pool: List[POI],
        day: DayPlan,
        hotel: Optional[Hotel],
        used_minutes: int,
        used_budget: float,
        budget_per_day: Optional[float],
        assigned_ids: set,
        day_limit: DayPlan,
        current_day_pois: List[str],
    ) -> Optional[POI]:
        """Pick the best POI from the pool for this day slot."""
        best_poi = None
        best_score = -1.0

        for poi in pool:
            if poi.id in assigned_ids:
                continue

            # Check capacity
            if used_minutes + poi.visit_duration_min > day_limit.max_daily_minutes:
                continue

            # Check max POIs per day
            if len(current_day_pois) >= day_limit.max_pois:
                continue

            # Check budget
            if budget_per_day is not None:
                if used_budget + poi.entrance_fee > budget_per_day:
                    continue

            score = self._score(poi, day, hotel)
            if score > best_score:
                best_score = score
                best_poi = poi

        return best_poi

    def _find_best_day(
        self,
        poi: POI,
        days: List[DayPlan],
        day_hotel: Dict,
        day_used_minutes: Dict,
        day_used_budget: Dict,
        budget_per_day: Optional[float],
        day_limits: Dict,
        day_assignments: Dict,
    ) -> Optional[int]:
        """Find the best day for a fallback POI."""
        best_day = None
        best_score = -1.0

        for day in days:
            day_idx = day.day_index
            # Check capacity
            if day_used_minutes[day_idx] + poi.visit_duration_min > day_limits[day_idx].max_daily_minutes:
                continue
            if len(day_assignments[day_idx]) >= day_limits[day_idx].max_pois:
                continue
            if budget_per_day is not None:
                if day_used_budget[day_idx] + poi.entrance_fee > budget_per_day:
                    continue

            hotel = day_hotel.get(day_idx)
            score = self._score(poi, day, hotel)
            if score > best_score:
                best_score = score
                best_day = day_idx

        return best_day

    # ─── Scoring ───

    def _score(self, poi: POI, day: DayPlan, hotel: Optional[Hotel]) -> float:
        """Score a (POI, day) pair. Higher = better fit.

        Weights: geo=0.10, time=0.10, priority=0.30
        (Category balance is handled by hard quotas, not score weights.)
        """
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

    # ─── Category Resolution ───

    @staticmethod
    def _resolve_category_group(category: str) -> str:
        """Map a micro-category string to one of the 9 macro groups.

        Used as fallback when category_group is not set in DB.
        """
        cat_lower = category.lower().strip()
        for group, members in CATEGORY_GROUP_MAP.items():
            if cat_lower in members:
                return group
        return "culture"  # default fallback

    # ─── Budget Filter ───

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

    # ─── Utils ───

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine distance in km."""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (math.sin(dlat / 2) ** 2
             + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        return 6371.0 * 2 * math.asin(math.sqrt(a))
