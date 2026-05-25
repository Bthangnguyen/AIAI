"""Post-solve itinerary validator — checks quality rules and suggests fixes.

Checks: meal timing, consecutive heavy POIs, outdoor heat, rest gaps.
Returns issues with severity levels and suggested fixes.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class ValidationIssue:
    """A single validation issue found in the itinerary."""
    severity: str  # 'error' | 'warning' | 'info'
    rule: str      # 'meal_missing' | 'consecutive_heavy' | 'outdoor_heat' | 'rest_needed'
    day_index: int
    message: str
    suggested_fix: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of itinerary validation."""
    is_valid: bool
    score: float  # 0.0-1.0 internal quality score
    issues: List[ValidationIssue] = field(default_factory=list)


# Rest-type categories (reset fatigue timer)
REST_CATEGORIES = {"cafe", "restaurant", "nhà hàng", "quán ăn", "spa", "rest"}

# Meal-type categories
MEAL_CATEGORIES = {"restaurant", "nhà hàng", "quán ăn", "street_food", "food"}


class ItineraryValidator:
    """Validates solved itinerary against comfort/quality rules."""

    def validate(
        self,
        days,
        poi_map: Dict,
        constraints: Optional[Dict] = None,
    ) -> ValidationResult:
        """Validate a list of TravelItineraryDay objects.
        
        Args:
            days: List of TravelItineraryDay (from domain.py)
            poi_map: Dict[poi_id -> POI] for looking up POI attributes
            constraints: Dict with optional overrides:
                - max_consecutive_heavy (default: 2)
                - avoid_outdoor_start (default: 720 = 12:00)
                - avoid_outdoor_end (default: 840 = 14:00)
                - rest_interval_min (default: 180)
        """
        constraints = constraints or {}
        issues = []
        issues.extend(self._check_meal_timing(days, poi_map, constraints))
        issues.extend(self._check_consecutive_heavy(days, poi_map, constraints))
        issues.extend(self._check_outdoor_heat(days, poi_map, constraints))
        issues.extend(self._check_rest_needed(days, poi_map, constraints))

        has_errors = any(i.severity == "error" for i in issues)
        score = self._compute_quality_score(issues)

        return ValidationResult(is_valid=not has_errors, score=score, issues=issues)

    def _check_meal_timing(self, days, poi_map, constraints) -> List[ValidationIssue]:
        """Days ≥5h must have a lunch POI between 11:00-13:30 (660-810 min)."""
        issues = []
        lunch_start = constraints.get("lunch_start", 660)   # 11:00
        lunch_end = constraints.get("lunch_end", 810)       # 13:30
        min_duration_for_meal = constraints.get("min_duration_for_meal", 300)  # 5h

        for day in days:
            stops = getattr(day, "stops", [])
            if len(stops) < 2:
                continue

            # Calculate day duration
            first_arrival = min(s.arrival_time_min for s in stops)
            last_departure = max(s.departure_time_min for s in stops)
            day_duration = last_departure - first_arrival

            if day_duration < min_duration_for_meal:
                continue

            # Check for meal POI in lunch window
            has_lunch = False
            for stop in stops:
                poi = poi_map.get(stop.poi_id)
                if not poi:
                    continue
                cat = (poi.category or "").lower()
                meal_type = getattr(poi, "meal_type", None)
                is_meal = meal_type == "lunch" or cat in MEAL_CATEGORIES
                in_window = lunch_start <= stop.arrival_time_min <= lunch_end
                if is_meal and in_window:
                    has_lunch = True
                    break

            if not has_lunch:
                issues.append(ValidationIssue(
                    severity="warning",
                    rule="meal_missing",
                    day_index=day.day_index,
                    message=f"Ngày {day.day_index}: {day_duration//60}h hoạt động nhưng không có quán ăn trưa (11:00-13:30)",
                    suggested_fix="Thêm 1 quán ăn/nhà hàng vào khung 11:00-13:30",
                ))
        return issues

    def _check_consecutive_heavy(self, days, poi_map, constraints) -> List[ValidationIssue]:
        """Warn when >max_consecutive_heavy heavy POIs in a row."""
        issues = []
        max_heavy = constraints.get("max_consecutive_heavy", 2)

        for day in days:
            stops = getattr(day, "stops", [])
            consecutive = 0
            for stop in stops:
                poi = poi_map.get(stop.poi_id)
                if not poi:
                    consecutive = 0
                    continue
                intensity = getattr(poi, "intensity", "medium")
                if intensity == "heavy":
                    consecutive += 1
                    if consecutive > max_heavy:
                        issues.append(ValidationIssue(
                            severity="warning",
                            rule="consecutive_heavy",
                            day_index=day.day_index,
                            message=f"Ngày {day.day_index}: {consecutive} điểm nặng liên tiếp (max: {max_heavy})",
                            suggested_fix="Xen kẽ 1 quán cafe hoặc điểm nhẹ giữa các điểm nặng",
                        ))
                else:
                    consecutive = 0
        return issues

    def _check_outdoor_heat(self, days, poi_map, constraints) -> List[ValidationIssue]:
        """Info when outdoor POI is scheduled during heat window."""
        issues = []
        avoid_start = constraints.get("avoid_outdoor_start", 720)  # 12:00
        avoid_end = constraints.get("avoid_outdoor_end", 840)      # 14:00

        for day in days:
            stops = getattr(day, "stops", [])
            for stop in stops:
                poi = poi_map.get(stop.poi_id)
                if not poi:
                    continue
                is_outdoor = getattr(poi, "is_outdoor", False)
                if not is_outdoor:
                    continue
                # Check overlap with heat window
                if stop.arrival_time_min < avoid_end and stop.departure_time_min > avoid_start:
                    issues.append(ValidationIssue(
                        severity="info",
                        rule="outdoor_heat",
                        day_index=day.day_index,
                        message=f"Ngày {day.day_index}: {poi.name} (ngoài trời) trong khung nóng {avoid_start//60}:00-{avoid_end//60}:00",
                        suggested_fix="Dời sang sáng sớm hoặc chiều muộn",
                    ))
        return issues

    def _check_rest_needed(self, days, poi_map, constraints) -> List[ValidationIssue]:
        """Info when continuous activity exceeds rest interval without a rest stop."""
        issues = []
        rest_interval = constraints.get("rest_interval_min", 180)

        for day in days:
            stops = getattr(day, "stops", [])
            if not stops:
                continue

            active_since_rest = 0
            for i, stop in enumerate(stops):
                poi = poi_map.get(stop.poi_id)
                cat = (poi.category or "").lower() if poi else ""

                # Travel time + visit time
                active_since_rest += stop.travel_time_from_prev_min + stop.visit_duration_min

                # Reset on rest-type POI
                if cat in REST_CATEGORIES:
                    active_since_rest = 0
                    continue

                if active_since_rest > rest_interval:
                    issues.append(ValidationIssue(
                        severity="info",
                        rule="rest_needed",
                        day_index=day.day_index,
                        message=f"Ngày {day.day_index}: {active_since_rest}min liên tục không nghỉ (sau {stop.poi_name})",
                        suggested_fix=f"Thêm nghỉ cafe/ngồi nghỉ sau {stop.poi_name}",
                    ))
                    active_since_rest = 0  # only warn once per gap

        return issues

    @staticmethod
    def _compute_quality_score(issues: List[ValidationIssue]) -> float:
        """Internal quality score: 1.0 = perfect, 0.0 = worst."""
        score = 1.0
        for issue in issues:
            if issue.severity == "error":
                score -= 0.2
            elif issue.severity == "warning":
                score -= 0.1
            elif issue.severity == "info":
                score -= 0.03
        return max(0.0, round(score, 2))
