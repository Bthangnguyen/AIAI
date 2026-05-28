# -*- coding: utf-8 -*-
"""In-memory itinerary editor for post-draft chat operations.

This service is intentionally conservative: it edits the current itinerary JSON
sent by the web client and returns a Layer-4-like itinerary object that the
frontend can map back into an ItineraryDraft. It does not try to solve routing;
for route-quality rebuilds, the gateway still uses the full L2/L3/L4 pipeline.
"""

from __future__ import annotations

import copy
import re
import unicodedata
from typing import Any, Dict, Iterable, Optional

from app.schemas.trip import POIResponse

DEFAULT_START_MIN = 480
DEFAULT_VISIT_MIN = 60
DEFAULT_HOTEL_LOCATION = {"latitude": 16.4637, "longitude": 107.5905}


def _normalize(value: str | None) -> str:
    """Lowercase, remove Vietnamese diacritics, and collapse whitespace."""
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


class ItineraryEditorService:
    """Apply concrete add/remove/replace operations to an existing itinerary."""

    def remove_stop(self, itinerary: Dict[str, Any], target: str) -> Dict[str, Any]:
        draft = self._clone_and_normalize(itinerary)
        target_norm = _normalize(target)
        target_tokens = _tokens(target)

        removed = False
        for day in draft.get("days", []):
            kept = []
            for stop in day.get("stops", []):
                if not removed and self._matches_stop(stop, target_norm, target_tokens):
                    removed = True
                    continue
                kept.append(stop)
            day["stops"] = kept
            self._retime_day(day)

        draft["status"] = "success" if removed else "warning"
        draft["message"] = "Đã xóa địa điểm khỏi lịch trình." if removed else "Không tìm thấy địa điểm cần xóa trong lịch trình hiện tại."
        return self._finalize(draft)

    def add_stop(self, itinerary: Dict[str, Any], day_index: int, poi: POIResponse) -> Dict[str, Any]:
        draft = self._clone_and_normalize(itinerary)
        day = self._ensure_day(draft, day_index)
        day.setdefault("stops", []).append(self._poi_to_stop(poi, day.get("stops", [])))
        self._retime_day(day)
        draft["status"] = "success"
        draft["message"] = f"Đã thêm {poi.name} vào ngày {day.get('day_index', day_index) + 1}."
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
                    # Preserve the old slot when possible so the UI feels stable.
                    next_stop["arrival_time_min"] = stop.get("arrival_time_min", next_stop["arrival_time_min"])
                    next_stop["departure_time_min"] = next_stop["arrival_time_min"] + next_stop.get("visit_duration_min", DEFAULT_VISIT_MIN)
                    next_stops.append(next_stop)
                    replaced = True
                else:
                    next_stops.append(stop)
            day["stops"] = next_stops
            self._retime_day(day)

        draft["status"] = "success" if replaced else "warning"
        draft["message"] = f"Đã thay bằng {new_poi.name}." if replaced else "Không tìm thấy địa điểm cần thay trong lịch trình hiện tại."
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
            normalized_stops = []
            for stop_idx, stop in enumerate(day.get("stops", [])):
                normalized_stops.append(self._normalize_stop(stop, day.get("start_time_min", DEFAULT_START_MIN), stop_idx))
            day["stops"] = normalized_stops
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
        return normalized

    def _poi_to_stop(self, poi: POIResponse, existing_stops: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        existing = list(existing_stops or [])
        last_departure = max((int(s.get("departure_time_min") or s.get("arrival_time_min") or DEFAULT_START_MIN) for s in existing), default=DEFAULT_START_MIN)
        arrival = last_departure + (15 if existing else 0)
        visit = int(poi.visit_duration_min or DEFAULT_VISIT_MIN)
        return {
            "poi_id": str(poi.uuid),
            "poi_name": poi.name,
            "category": poi.category,
            "description": poi.description or "",
            "location": {"latitude": poi.latitude, "longitude": poi.longitude},
            "arrival_time_min": arrival,
            "departure_time_min": arrival + visit,
            "visit_duration_min": visit,
            "entrance_fee": poi.entrance_fee or poi.price or 0,
        }

    def _matches_stop(self, stop: Dict[str, Any], target_norm: str, target_tokens: set[str]) -> bool:
        fields = [
            stop.get("poi_name"),
            stop.get("name"),
            stop.get("category"),
            stop.get("description"),
        ]
        haystack = _normalize(" ".join(str(v) for v in fields if v))
        if not target_norm:
            return False
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
            if index == 0:
                arrival = int(stop.get("arrival_time_min") or current)
            else:
                arrival = max(current + 15, int(stop.get("arrival_time_min") or current + 15))
            stop["arrival_time_min"] = arrival
            stop["departure_time_min"] = arrival + visit
            current = stop["departure_time_min"]
        day["num_pois"] = len([s for s in stops if s.get("poi_id") != "__rest_break__"])
        day["total_visit_min"] = sum(int(s.get("visit_duration_min") or 0) for s in stops)
        day["total_entrance_fee"] = sum(float(s.get("entrance_fee") or 0) for s in stops)
        day.setdefault("total_travel_min", max(0, len(stops) - 1) * 15)
        day.setdefault("total_distance_km", 0.0)

    def _finalize(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        days = draft.get("days", [])
        draft["num_days"] = len(days)
        draft["total_pois_visited"] = sum(int(day.get("num_pois") or 0) for day in days)
        draft["total_entrance_fee"] = sum(float(day.get("total_entrance_fee") or 0) for day in days)
        draft["budget_used"] = draft["total_entrance_fee"]
        draft.setdefault("total_pois_dropped", 0)
        draft.setdefault("total_travel_min", sum(int(day.get("total_travel_min") or 0) for day in days))
        draft.setdefault("total_distance_km", sum(float(day.get("total_distance_km") or 0.0) for day in days))
        return draft
