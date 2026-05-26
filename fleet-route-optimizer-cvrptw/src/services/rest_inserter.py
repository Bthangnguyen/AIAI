"""Post-solve rest break insertion.

Walks through solved itinerary stops and inserts virtual rest breaks
when continuous activity exceeds the rest interval threshold.
"""

from typing import Dict, List
from ..models.domain import TravelItineraryDay, TravelItineraryStop, Location


class RestBreakInserter:
    """Inserts rest breaks into solved itinerary days."""

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
                rest_start = stop.arrival_time_min - rest_duration_min
                rest_stop = TravelItineraryStop(
                    poi_id="__rest_break__",
                    poi_name="Nghỉ ngơi",
                    location=stop.location,
                    arrival_time_min=max(0, rest_start),
                    departure_time_min=stop.arrival_time_min,
                    visit_duration_min=rest_duration_min,
                    travel_time_from_prev_min=0,
                    entrance_fee=0.0,
                )
                new_stops.append(rest_stop)
                active_since_rest = 0

            new_stops.append(stop)

        # Update day with new stops
        day.stops = new_stops
        day.total_visit_min = sum(s.visit_duration_min for s in new_stops if s.poi_id != "__rest_break__")
        day.num_pois = sum(1 for s in new_stops if s.poi_id != "__rest_break__")
        return day
