"""Post-solve rest break insertion.

Walks through solved itinerary stops and inserts virtual rest breaks
when continuous activity exceeds the rest interval threshold.
"""

from typing import Dict, List
from ..models.domain import DayPlan, TravelItineraryDay, TravelItineraryStop, Location


class RestBreakInserter:
    """Inserts rest breaks into solved itinerary days."""

    FOOD_CATEGORIES = {
        "restaurant",
        "nhÃ  hÃ ng",
        "quÃ¡n Äƒn",
        "street_food",
        "food",
        "cafe",
        "coffee",
        "market",
        "chá»£",
    }
    FOOD_TAGS = {"food", "street_food", "local_food", "cafe", "coffee", "dessert", "snack"}

    def apply_day_rhythm(
        self,
        day: TravelItineraryDay,
        poi_map: Dict,
        day_plan: DayPlan | None = None,
    ) -> TravelItineraryDay:
        """Normalize any solved day into a more realistic human rhythm.

        The solver optimizes feasibility and route order, which can compress a
        full-day itinerary into the earliest possible hours. This pass keeps the
        solved order and travel times, but spreads flexible stops into morning,
        midday, afternoon, and evening bands so the result feels usable.
        """
        stops = list(day.stops)
        real_stops = [s for s in stops if not s.poi_id.startswith("__")]
        if len(real_stops) < 4:
            return day

        start_min = day_plan.start_time_min if day_plan else min(s.arrival_time_min for s in real_stops)
        end_min = day_plan.end_time_min if day_plan else max(s.departure_time_min for s in real_stops)
        available_span = max(0, end_min - start_min)
        active_span = max(s.departure_time_min for s in real_stops) - min(s.arrival_time_min for s in real_stops)

        if available_span < 300 or active_span >= available_span * 0.65:
            return day

        anchors = self._rhythm_anchors(start_min, end_min, len(real_stops))
        previous_departure = None
        for idx, stop in enumerate(real_stops):
            poi = poi_map.get(stop.poi_id)
            target_arrival = anchors[min(idx, len(anchors) - 1)]
            if poi and getattr(poi, "time_window", None):
                latest = max(poi.time_window.start_min, poi.time_window.end_min - stop.visit_duration_min)
                target_arrival = min(max(target_arrival, poi.time_window.start_min), latest)
            if previous_departure is not None:
                target_arrival = max(target_arrival, previous_departure + stop.travel_time_from_prev_min)
            stop.arrival_time_min = min(target_arrival, max(start_min, end_min - stop.visit_duration_min))
            stop.departure_time_min = stop.arrival_time_min + stop.visit_duration_min
            previous_departure = stop.departure_time_min

        self._make_sequential(stops)
        day.stops = stops
        return day

    def insert_breaks(
        self,
        day: TravelItineraryDay,
        poi_map: Dict,
        rest_interval_min: int = 180,
        rest_duration_min: int = 20,
    ) -> TravelItineraryDay:
        """Insert rest breaks when activity gap exceeds threshold.
        
        Args:
            day: Solved itinerary day
            poi_map: Dict[poi_id -> POI] for looking up categories
            rest_interval_min: Insert rest after this many active minutes
            rest_duration_min: Duration of each rest break
            
        Returns:
            Updated TravelItineraryDay with rest breaks inserted
        """
        rest_categories = {"cafe", "restaurant", "nhà hàng", "quán ăn", "spa", "rest"}
        stops = list(day.stops)
        if not stops:
            return day

        new_stops = []
        active_since_rest = 0

        for i, stop in enumerate(stops):
            poi = poi_map.get(stop.poi_id)
            cat = (poi.category or "").lower() if poi else ""

            active_since_rest += stop.travel_time_from_prev_min + stop.visit_duration_min

            # Reset on rest-type POI
            if cat in rest_categories:
                active_since_rest = 0
                new_stops.append(stop)
                continue

            # Check if we need a rest break before this stop
            if active_since_rest > rest_interval_min and i > 0:
                # Insert rest at current location
                rest_start = stop.arrival_time_min
                rest_stop = TravelItineraryStop(
                    poi_id="__rest_break__",
                    poi_name="Nghỉ ngơi",
                    location=stop.location,
                    arrival_time_min=max(0, rest_start),
                    departure_time_min=max(0, rest_start) + rest_duration_min,
                    visit_duration_min=rest_duration_min,
                    travel_time_from_prev_min=0,
                    entrance_fee=0.0,
                )
                new_stops.append(rest_stop)
                stop.travel_time_from_prev_min = 0
                active_since_rest = 0

            new_stops.append(stop)

        # Update day with new stops
        self._make_sequential(new_stops)
        day.stops = new_stops
        day.total_visit_min = sum(s.visit_duration_min for s in new_stops if not s.poi_id.startswith("__"))
        day.num_pois = sum(1 for s in new_stops if not s.poi_id.startswith("__"))
        return day

    def insert_meal_breaks(
        self,
        day: TravelItineraryDay,
        poi_map: Dict,
        lunch_window: tuple[int, int] = (690, 810),
        dinner_window: tuple[int, int] = (1080, 1200),
        meal_duration_min: int = 45,
    ) -> TravelItineraryDay:
        """Insert visible meal breaks when a long day has no meal in meal windows."""
        stops = list(day.stops)
        if not stops:
            return day

        def is_meal(stop: TravelItineraryStop) -> bool:
            poi = poi_map.get(stop.poi_id)
            cat = (getattr(poi, "category", "") or "").lower() if poi else ""
            tags = {str(t).lower() for t in (getattr(poi, "tags", None) or [])}
            return (
                cat in {"restaurant", "nhà hàng", "quán ăn", "street_food", "food", "cafe"}
                or bool(tags.intersection({"food", "street_food", "local_food", "cafe"}))
            )

        first_arrival = min(s.arrival_time_min for s in stops)
        last_departure = max(s.departure_time_min for s in stops)
        active_span = last_departure - first_arrival

        additions: list[TravelItineraryStop] = []
        
        # Only insert lunch if the traveler's active travel span substantially covers the lunch window
        can_insert_lunch = (
            active_span >= 300
            and first_arrival < lunch_window[1] - 30
            and last_departure > lunch_window[0] + 30
        )
        if can_insert_lunch and not any(is_meal(s) and lunch_window[0] <= s.arrival_time_min <= lunch_window[1] for s in stops):
            lunch_start = max(lunch_window[0], first_arrival)
            additions.append(self._meal_stop(day, stops, "lunch", "Ăn trưa / nghỉ ngơi", lunch_start, meal_duration_min))
            
        # Only insert dinner if the traveler's active travel span substantially covers the dinner window
        can_insert_dinner = (
            active_span >= 600
            and first_arrival < dinner_window[1] - 30
            and last_departure > dinner_window[0] + 30
        )
        if can_insert_dinner and not any(is_meal(s) and dinner_window[0] <= s.arrival_time_min <= dinner_window[1] for s in stops):
            dinner_start = max(dinner_window[0], first_arrival)
            additions.append(self._meal_stop(day, stops, "dinner", "Ăn tối / nghỉ ngơi", dinner_start, meal_duration_min))

        if not additions:
            return day

        all_stops = sorted(stops + additions, key=lambda s: (s.arrival_time_min, s.poi_id))
        previous_departure = day.stops[0].arrival_time_min if day.stops else first_arrival
        for idx, stop in enumerate(all_stops):
            if idx == 0:
                previous_departure = stop.departure_time_min
                continue
            if stop.arrival_time_min < previous_departure + stop.travel_time_from_prev_min:
                stop.arrival_time_min = previous_departure + stop.travel_time_from_prev_min
                stop.departure_time_min = stop.arrival_time_min + stop.visit_duration_min
            previous_departure = stop.departure_time_min

        day.stops = all_stops
        day.total_visit_min = sum(
            s.visit_duration_min for s in all_stops
            if not s.poi_id.startswith("__meal_") and s.poi_id != "__rest_break__"
        )
        day.num_pois = sum(
            1 for s in all_stops
            if not s.poi_id.startswith("__meal_") and s.poi_id != "__rest_break__"
        )
        return day

    def insert_food_tour_pacing(
        self,
        day: TravelItineraryDay,
        poi_map: Dict,
        day_plan: DayPlan | None = None,
        min_food_ratio: float = 0.4,
        pacing_duration_min: int = 30,
    ) -> TravelItineraryDay:
        """Add digestion/walking gaps for food-heavy days.

        Food tours should feel like a crawl, not a compressed checklist. When a
        day is mostly eateries/cafes, insert light walking/rest stops between
        clusters so consecutive dishes are not scheduled back-to-back.
        """
        stops = list(day.stops)
        real_stops = [s for s in stops if not s.poi_id.startswith("__")]
        if len(real_stops) < 5:
            return day

        food_count = sum(1 for s in real_stops if self._is_food_stop(s, poi_map))
        if food_count / max(1, len(real_stops)) < min_food_ratio:
            return day

        self._spread_food_tour_stops(real_stops, day_plan)

        paced: list[TravelItineraryStop] = []
        food_streak = 0
        break_count = 0

        for idx, stop in enumerate(stops):
            paced.append(stop)
            if stop.poi_id.startswith("__"):
                food_streak = 0
                continue

            if self._is_food_stop(stop, poi_map):
                food_streak += 1
            else:
                food_streak = 0

            has_next_real = any(not s.poi_id.startswith("__") for s in stops[idx + 1:])
            next_real = next((s for s in stops[idx + 1:] if not s.poi_id.startswith("__")), None)
            natural_gap = (next_real.arrival_time_min - stop.departure_time_min) if next_real else 0
            if food_streak >= 2 and has_next_real and natural_gap >= pacing_duration_min + 10:
                break_count += 1
                walk_start = stop.departure_time_min + max(0, (natural_gap - pacing_duration_min) // 2)
                paced.append(TravelItineraryStop(
                    poi_id=f"__food_walk_{break_count}__",
                    poi_name="Đi dạo / nghỉ nhẹ",
                    location=stop.location,
                    arrival_time_min=walk_start,
                    departure_time_min=walk_start + pacing_duration_min,
                    visit_duration_min=pacing_duration_min,
                    travel_time_from_prev_min=stop.travel_time_from_prev_min,
                    travel_time_to_next_min=0,
                    entrance_fee=0.0,
                ))
                food_streak = 0

        if break_count == 0:
            return day

        self._make_sequential(paced)
        day.stops = paced
        day.total_visit_min = sum(
            s.visit_duration_min for s in paced
            if not s.poi_id.startswith("__meal_")
            and not s.poi_id.startswith("__food_walk_")
            and s.poi_id != "__rest_break__"
        )
        day.num_pois = sum(
            1 for s in paced
            if not s.poi_id.startswith("__meal_")
            and not s.poi_id.startswith("__food_walk_")
            and s.poi_id != "__rest_break__"
        )
        return day

    @staticmethod
    def _spread_food_tour_stops(stops: list[TravelItineraryStop], day_plan: DayPlan | None = None) -> None:
        if not stops:
            return
        start_min = day_plan.start_time_min if day_plan else 540
        end_min = day_plan.end_time_min if day_plan else 1260
        is_full_day = (end_min - start_min) >= 540
        templates = {}
        if is_full_day and start_min <= 600 and end_min >= 1200:
            templates = {
                5: [540, 615, 690, 960, 1110],
                6: [540, 615, 690, 870, 990, 1110],
                7: [540, 615, 690, 870, 960, 1110, 1200],
                8: [540, 615, 690, 810, 900, 990, 1110, 1200],
            }
        anchors = templates.get(len(stops))
        if anchors is None:
            usable_end = max(start_min, end_min - 30)
            step = max(45, (usable_end - start_min) // max(1, len(stops) - 1))
            anchors = [start_min + idx * step for idx in range(len(stops))]

        previous_departure = None
        for idx, stop in enumerate(stops):
            target_arrival = anchors[min(idx, len(anchors) - 1)]
            if previous_departure is not None:
                target_arrival = max(target_arrival, previous_departure + stop.travel_time_from_prev_min)
            stop.arrival_time_min = target_arrival
            stop.departure_time_min = stop.arrival_time_min + stop.visit_duration_min
            previous_departure = stop.departure_time_min

    @staticmethod
    def _rhythm_anchors(start_min: int, end_min: int, count: int) -> list[int]:
        span = max(1, end_min - start_min)
        if count <= 1:
            return [start_min]

        ratios_by_count = {
            4: [0.06, 0.28, 0.55, 0.78],
            5: [0.05, 0.22, 0.40, 0.62, 0.82],
            6: [0.04, 0.18, 0.34, 0.52, 0.70, 0.86],
            7: [0.04, 0.16, 0.28, 0.43, 0.58, 0.74, 0.88],
            8: [0.03, 0.14, 0.25, 0.37, 0.50, 0.64, 0.78, 0.90],
        }
        ratios = ratios_by_count.get(count)
        if ratios is None:
            ratios = [idx / max(1, count - 1) for idx in range(count)]

        anchors = [start_min + int(span * ratio) for ratio in ratios]
        return [max(start_min, min(end_min, anchor)) for anchor in anchors]

    def _is_food_stop(self, stop: TravelItineraryStop, poi_map: Dict) -> bool:
        poi = poi_map.get(stop.poi_id)
        if not poi:
            return False
        cat = (getattr(poi, "category", "") or "").lower()
        tags = {str(t).lower() for t in (getattr(poi, "tags", None) or [])}
        return cat in self.FOOD_CATEGORIES or bool(tags.intersection(self.FOOD_TAGS))

    @staticmethod
    def _make_sequential(stops: list[TravelItineraryStop]) -> None:
        previous_departure = None
        for stop in stops:
            if previous_departure is None:
                previous_departure = stop.departure_time_min
                continue
            earliest_arrival = previous_departure + stop.travel_time_from_prev_min
            if stop.arrival_time_min < earliest_arrival:
                stop.arrival_time_min = earliest_arrival
                stop.departure_time_min = stop.arrival_time_min + stop.visit_duration_min
            previous_departure = stop.departure_time_min

    @staticmethod
    def _meal_stop(
        day: TravelItineraryDay,
        stops: List[TravelItineraryStop],
        meal_id: str,
        label: str,
        start_min: int,
        duration_min: int,
    ) -> TravelItineraryStop:
        anchor = min(stops, key=lambda s: abs(s.arrival_time_min - start_min))
        return TravelItineraryStop(
            poi_id=f"__meal_{meal_id}__",
            poi_name=label,
            location=anchor.location,
            arrival_time_min=start_min,
            departure_time_min=start_min + duration_min,
            visit_duration_min=duration_min,
            travel_time_from_prev_min=0,
            travel_time_to_next_min=0,
            entrance_fee=0.0,
        )
