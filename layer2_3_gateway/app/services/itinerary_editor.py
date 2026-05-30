# -*- coding: utf-8 -*-
"""Deterministic in-memory itinerary editor for post-draft operations."""

from __future__ import annotations

import copy
import math
import re
import unicodedata
from typing import Any, Dict, Iterable, Optional

from app.schemas.trip import POIResponse

DEFAULT_START_MIN = 480
DEFAULT_VISIT_MIN = 60
DEFAULT_HOTEL_LOCATION = {"latitude": 16.4637, "longitude": 107.5905}


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    text = value.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(value: str | None) -> set[str]:
    return {tok for tok in _normalize(value).split() if len(tok) > 1}


def haversine_distance(loc1: Dict[str, Any], loc2: Dict[str, Any]) -> float:
    lat1 = math.radians(float(loc1.get("latitude", 0.0)))
    lon1 = math.radians(float(loc1.get("longitude", 0.0)))
    lat2 = math.radians(float(loc2.get("latitude", 0.0)))
    lon2 = math.radians(float(loc2.get("longitude", 0.0)))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def estimate_travel_time(loc1: Dict[str, Any], loc2: Dict[str, Any], speed_kmh: float = 22.0) -> int:
    km = haversine_distance(loc1, loc2)
    if km <= 0.05:
        return 0
    return max(5, int(math.ceil((km / speed_kmh) * 60)))


class ItineraryEditorService:
    """Apply precise edit operations to a Layer-4-like itinerary draft."""

    def remove_stop(
        self,
        itinerary: Dict[str, Any],
        target: str,
        target_day: int | None = None,
        target_count: int = 1,
        micro_tags: Optional[list[str]] = None,
        category: str | None = None,
    ) -> Dict[str, Any]:
        draft = self._clone_and_normalize(itinerary)
        removed = 0
        target_norm = _normalize(target)
        target_tokens = _tokens(target)

        for day in draft.get("days", []):
            if target_day is not None and self._display_day(day) != target_day:
                continue
            kept = []
            for stop in day.get("stops", []):
                if removed < max(1, target_count) and self._matches_stop(stop, target_norm, target_tokens, micro_tags, category):
                    removed += 1
                    continue
                kept.append(stop)
            day["stops"] = kept
            self._retime_day(day)

        draft["status"] = "success" if removed else "warning"
        draft["message"] = f"Đã xóa {removed} điểm khỏi lịch trình." if removed else "Không tìm thấy điểm cần xóa."
        return self._finalize(draft)

    def add_stop(
        self,
        itinerary: Dict[str, Any],
        day_index: int,
        poi: POIResponse,
        insert_index: int | None = None,
        after_target: str | None = None,
        preferred_time_min: int | None = None,
        position: str | None = None,
    ) -> Dict[str, Any]:
        draft = self._clone_and_normalize(itinerary)
        day = self._ensure_day(draft, day_index)
        stops = day.setdefault("stops", [])
        explicit_insert = insert_index is not None
        if position == "first":
            insert_index = 0
            explicit_insert = True
        elif position == "last":
            insert_index = len(stops)
            explicit_insert = True
        if after_target:
            after_norm = _normalize(after_target)
            after_tokens = _tokens(after_target)
            for idx, stop in enumerate(stops):
                if self._matches_stop(stop, after_norm, after_tokens):
                    insert_index = idx + 1
                    explicit_insert = True
                    break
        if insert_index is None and preferred_time_min is not None:
            insert_index = self._best_index_for_time(stops, preferred_time_min)
        if insert_index is None:
            insert_index = len(stops)

        next_stop = self._poi_to_stop(poi, stops)
        if preferred_time_min is not None:
            next_stop["preferred_time_min"] = preferred_time_min
            next_stop["arrival_time_min"] = preferred_time_min
            next_stop["departure_time_min"] = preferred_time_min + next_stop.get("visit_duration_min", DEFAULT_VISIT_MIN)
        elif explicit_insert:
            next_stop.pop("arrival_time_min", None)
            next_stop.pop("departure_time_min", None)
        stops.insert(max(0, min(insert_index, len(stops))), next_stop)
        self._retime_day(day)
        draft["status"] = "success"
        draft["message"] = f"Đã thêm {poi.name} vào ngày {self._display_day(day)}."
        return self._finalize(draft)

    def replace_stop(self, itinerary: Dict[str, Any], old_name: str, new_poi: POIResponse) -> Dict[str, Any]:
        draft = self._clone_and_normalize(itinerary)
        target_norm = _normalize(old_name)
        target_tokens = _tokens(old_name)
        replaced = False

        for day in draft.get("days", []):
            next_stops = []
            for stop in day.get("stops", []):
                if not replaced and self._matches_stop(stop, target_norm, target_tokens):
                    next_stop = self._poi_to_stop(new_poi, day.get("stops", []))
                    next_stop["arrival_time_min"] = stop.get("arrival_time_min", next_stop["arrival_time_min"])
                    next_stop["departure_time_min"] = next_stop["arrival_time_min"] + next_stop.get("visit_duration_min", DEFAULT_VISIT_MIN)
                    next_stops.append(next_stop)
                    replaced = True
                else:
                    next_stops.append(stop)
            day["stops"] = next_stops
            self._retime_day(day)

        draft["status"] = "success" if replaced else "warning"
        draft["message"] = f"Đã thay bằng {new_poi.name}." if replaced else "Không tìm thấy điểm cần thay."
        return self._finalize(draft)

    def move_stop(
        self,
        itinerary: Dict[str, Any],
        target: str,
        target_day: int | None = None,
        preferred_time_min: int | None = None,
        after_target: str | None = None,
        position: str | None = None,
    ) -> Dict[str, Any]:
        draft = self._clone_and_normalize(itinerary)
        target_norm = _normalize(target)
        target_tokens = _tokens(target)
        moved_stop = None
        source_index = 0

        for day_idx, day in enumerate(draft.get("days", [])):
            kept = []
            for stop in day.get("stops", []):
                if moved_stop is None and self._matches_stop(stop, target_norm, target_tokens):
                    moved_stop = stop
                    source_index = day_idx
                    continue
                kept.append(stop)
            day["stops"] = kept

        if moved_stop is None:
            draft["status"] = "warning"
            draft["message"] = "Không tìm thấy điểm cần chuyển."
            return self._finalize(draft)

        destination_index = (target_day - 1) if target_day and target_day > 0 else source_index
        day = self._ensure_day(draft, destination_index)
        stops = day.setdefault("stops", [])
        insert_index = None
        if position == "first":
            insert_index = 0
        elif position == "last":
            insert_index = len(stops)
        if after_target:
            after_norm = _normalize(after_target)
            after_tokens = _tokens(after_target)
            for idx, stop in enumerate(stops):
                if self._matches_stop(stop, after_norm, after_tokens):
                    insert_index = idx + 1
                    break
        if insert_index is None and preferred_time_min is not None:
            insert_index = self._best_index_for_time(stops, preferred_time_min)
            moved_stop["preferred_time_min"] = preferred_time_min
            moved_stop["arrival_time_min"] = preferred_time_min
            moved_stop["departure_time_min"] = preferred_time_min + moved_stop.get("visit_duration_min", DEFAULT_VISIT_MIN)
        if insert_index is None:
            insert_index = len(stops)
        stops.insert(max(0, min(insert_index, len(stops))), moved_stop)

        for day_item in draft.get("days", []):
            self._retime_day(day_item)
        draft["status"] = "success"
        draft["message"] = f"Đã chuyển {moved_stop.get('poi_name')}."
        return self._finalize(draft)

    def swap_stops(self, itinerary: Dict[str, Any], target_a: str, target_b: str) -> Dict[str, Any]:
        draft = self._clone_and_normalize(itinerary)
        found_a = found_b = None
        norm_a, toks_a = _normalize(target_a), _tokens(target_a)
        norm_b, toks_b = _normalize(target_b), _tokens(target_b)

        for day_idx, day in enumerate(draft.get("days", [])):
            for stop_idx, stop in enumerate(day.get("stops", [])):
                if found_a is None and self._matches_stop(stop, norm_a, toks_a):
                    found_a = (day_idx, stop_idx)
                if found_b is None and self._matches_stop(stop, norm_b, toks_b):
                    found_b = (day_idx, stop_idx)

        if found_a is None or found_b is None:
            draft["status"] = "warning"
            draft["message"] = "Không tìm thấy đủ hai điểm cần đổi chỗ."
            return self._finalize(draft)

        day_a, idx_a = found_a
        day_b, idx_b = found_b
        stops_a = draft["days"][day_a]["stops"]
        stops_b = draft["days"][day_b]["stops"]
        stops_a[idx_a], stops_b[idx_b] = stops_b[idx_b], stops_a[idx_a]
        for day in draft.get("days", []):
            self._retime_day(day)
        draft["status"] = "success"
        draft["message"] = "Đã đổi chỗ hai điểm trong lịch."
        return self._finalize(draft)

    def _clone_and_normalize(self, itinerary: Dict[str, Any]) -> Dict[str, Any]:
        draft = copy.deepcopy(itinerary or {})
        draft.setdefault("status", "success")
        draft.setdefault("days", [])
        for idx, day in enumerate(draft["days"]):
            day.setdefault("day_index", idx)
            day.setdefault("date", f"Day {idx + 1}")
            day.setdefault("start_time_min", DEFAULT_START_MIN)
            day.setdefault("start_hotel_name", day.get("hotel_name") or "Hue Default Hotel")
            day.setdefault("start_hotel_location", day.get("hotel_location") or DEFAULT_HOTEL_LOCATION)
            day.setdefault("end_hotel_name", day.get("hotel_name") or day.get("start_hotel_name") or "Hue Default Hotel")
            day.setdefault("end_hotel_location", day.get("hotel_location") or day.get("start_hotel_location") or DEFAULT_HOTEL_LOCATION)
            day["stops"] = [
                self._normalize_stop(stop, day.get("start_time_min", DEFAULT_START_MIN), stop_idx)
                for stop_idx, stop in enumerate(day.get("stops", []))
            ]
            self._retime_day(day)
        return draft

    def _ensure_day(self, draft: Dict[str, Any], day_index: int) -> Dict[str, Any]:
        safe_index = max(0, int(day_index or 0))
        days = draft.setdefault("days", [])
        while len(days) <= safe_index:
            idx = len(days)
            days.append({
                "day_index": idx,
                "date": f"Day {idx + 1}",
                "start_time_min": DEFAULT_START_MIN,
                "start_hotel_name": "Hue Default Hotel",
                "start_hotel_location": DEFAULT_HOTEL_LOCATION,
                "end_hotel_name": "Hue Default Hotel",
                "end_hotel_location": DEFAULT_HOTEL_LOCATION,
                "stops": [],
            })
        return days[safe_index]

    def _normalize_stop(self, stop: Dict[str, Any], fallback_start: int, index: int) -> Dict[str, Any]:
        normalized = dict(stop)
        visit = int(normalized.get("visit_duration_min") or DEFAULT_VISIT_MIN)
        arrival = normalized.get("arrival_time_min")
        if arrival is None:
            arrival = fallback_start + index * (visit + 15)
        normalized["arrival_time_min"] = int(arrival)
        normalized["visit_duration_min"] = visit
        normalized["departure_time_min"] = int(normalized.get("departure_time_min") or (normalized["arrival_time_min"] + visit))
        normalized.setdefault("poi_name", normalized.get("name") or normalized.get("note") or "Unknown")
        normalized.setdefault("location", DEFAULT_HOTEL_LOCATION)
        normalized.setdefault("entrance_fee", 0)
        normalized.setdefault("category", "general")
        normalized.setdefault("description", "")
        normalized.setdefault("tags", [])
        return normalized

    def _poi_to_stop(self, poi: POIResponse, existing_stops: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        existing = list(existing_stops or [])
        last_departure = max(
            (int(s.get("departure_time_min") or s.get("arrival_time_min") or DEFAULT_START_MIN) for s in existing),
            default=DEFAULT_START_MIN,
        )
        arrival = last_departure + (15 if existing else 0)
        visit = int(poi.visit_duration_min or DEFAULT_VISIT_MIN)
        return {
            "poi_id": str(poi.uuid),
            "poi_name": poi.name,
            "category": poi.category,
            "description": poi.description or "",
            "tags": poi.tags or [],
            "location": {"latitude": poi.latitude, "longitude": poi.longitude},
            "arrival_time_min": arrival,
            "departure_time_min": arrival + visit,
            "visit_duration_min": visit,
            "entrance_fee": poi.entrance_fee or poi.price or 0,
        }

    def _matches_stop(
        self,
        stop: Dict[str, Any],
        target_norm: str,
        target_tokens: set[str],
        micro_tags: Optional[list[str]] = None,
        category: str | None = None,
    ) -> bool:
        fields = [
            stop.get("poi_id"),
            stop.get("id"),
            stop.get("poi_name"),
            stop.get("name"),
            stop.get("category"),
            stop.get("description"),
            " ".join(stop.get("tags") or []),
        ]
        haystack = _normalize(" ".join(str(v) for v in fields if v))
        if category and _normalize(category) not in haystack:
            return False
        if micro_tags and not any(self._micro_tag_matches(haystack, tag) for tag in micro_tags):
            return False
        if not target_norm:
            return bool(micro_tags or category)
        if target_norm in haystack or haystack in target_norm:
            return True
        if target_tokens:
            hay_tokens = set(haystack.split())
            return len(target_tokens.intersection(hay_tokens)) >= min(2, len(target_tokens))
        return False

    def _retime_day(self, day: Dict[str, Any]) -> None:
        current = int(day.get("start_time_min") or DEFAULT_START_MIN)
        stops = day.get("stops", [])
        for index, stop in enumerate(stops):
            visit = int(stop.get("visit_duration_min") or DEFAULT_VISIT_MIN)
            prev_loc = (day.get("start_hotel_location") or DEFAULT_HOTEL_LOCATION) if index == 0 else stops[index - 1].get("location", DEFAULT_HOTEL_LOCATION)
            travel = estimate_travel_time(prev_loc, stop.get("location") or DEFAULT_HOTEL_LOCATION)
            stop["travel_time_from_prev_min"] = travel
            preferred = stop.get("preferred_time_min")
            if preferred is not None:
                preferred = int(preferred)
                if index == 0:
                    current = min(current, max(0, preferred - travel))
                arrival = max(current + travel, preferred)
            else:
                arrival = max(current + travel, int(stop.get("arrival_time_min") or current + travel))
            stop["arrival_time_min"] = arrival
            stop["departure_time_min"] = arrival + visit
            current = stop["departure_time_min"]

        for index, stop in enumerate(stops):
            if index + 1 < len(stops):
                stop["travel_time_to_next_min"] = stops[index + 1].get("travel_time_from_prev_min", 0)
            else:
                end_loc = day.get("end_hotel_location") or day.get("start_hotel_location") or DEFAULT_HOTEL_LOCATION
                stop["travel_time_to_next_min"] = estimate_travel_time(stop.get("location") or DEFAULT_HOTEL_LOCATION, end_loc)

        day["num_pois"] = len([s for s in stops if not str(s.get("poi_id", "")).startswith("__")])
        day["total_visit_min"] = sum(int(s.get("visit_duration_min") or 0) for s in stops)
        day["total_entrance_fee"] = sum(float(s.get("entrance_fee") or 0) for s in stops)
        day["total_travel_min"] = sum(int(s.get("travel_time_from_prev_min") or 0) for s in stops)
        day["total_distance_km"] = round(self._day_distance_km(day), 2)

    _recalculate_day_timings = _retime_day

    def _finalize(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        days = draft.get("days", [])
        draft["num_days"] = len(days)
        draft["total_pois_visited"] = sum(int(day.get("num_pois") or 0) for day in days)
        draft["total_entrance_fee"] = sum(float(day.get("total_entrance_fee") or 0) for day in days)
        draft["budget_used"] = draft["total_entrance_fee"]
        draft["total_pois_dropped"] = int(draft.get("total_pois_dropped") or 0)
        draft["total_travel_min"] = sum(int(day.get("total_travel_min") or 0) for day in days)
        draft["total_distance_km"] = round(sum(float(day.get("total_distance_km") or 0.0) for day in days), 2)
        return draft

    @staticmethod
    def _display_day(day: Dict[str, Any]) -> int:
        return int(day.get("day_number") or day.get("day") or int(day.get("day_index", 0)) + 1)

    @staticmethod
    def _best_index_for_time(stops: list[Dict[str, Any]], preferred_time_min: int) -> int:
        for idx, stop in enumerate(stops):
            if int(stop.get("arrival_time_min") or 0) >= preferred_time_min:
                return idx
        return len(stops)

    @staticmethod
    def _micro_tag_matches(haystack: str, tag: str) -> bool:
        aliases = {
            "bun_bo": ("bun bo", "bun", "bo"),
            "che": ("che", "dessert"),
            "cafe_muoi": ("cafe muoi", "ca phe muoi", "cafe"),
            "vegetarian": ("chay", "vegetarian", "vegan"),
            "dai_noi": ("dai noi", "hoang thanh"),
            "walking_street": ("di dao", "pho di bo", "nguyen hue"),
        }
        return any(alias in haystack for alias in aliases.get(tag, (tag,)))

    @staticmethod
    def _day_distance_km(day: Dict[str, Any]) -> float:
        stops = day.get("stops", [])
        if not stops:
            return 0.0
        total = 0.0
        prev = day.get("start_hotel_location") or DEFAULT_HOTEL_LOCATION
        for stop in stops:
            loc = stop.get("location") or DEFAULT_HOTEL_LOCATION
            total += haversine_distance(prev, loc)
            prev = loc
        end = day.get("end_hotel_location") or day.get("start_hotel_location") or DEFAULT_HOTEL_LOCATION
        total += haversine_distance(prev, end)
        return total
