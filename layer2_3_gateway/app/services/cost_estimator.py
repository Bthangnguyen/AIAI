"""Post-solver lodging, transport leg, and cost enrichment."""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from app.schemas.trip import LLMDataContract


FOOD_SPEND_GROUPS = {"food", "restaurant", "street_food", "local_food", "cafe", "coffee", "dessert", "shopping", "wellness", "nightlife"}
TICKET_GROUPS = {"culture", "museum", "heritage", "temple", "pagoda", "historical", "nature", "adventure"}


MODE_LABELS = {
    "walking": "Đi bộ",
    "bicycle": "Xe đạp",
    "motorbike": "Xe máy",
    "motorbike_hailing": "Xe máy công nghệ",
    "taxi": "Taxi",
    "car": "Ô tô/taxi",
    "mixed": "Di chuyển linh hoạt",
}

MODE_ICONS = {
    "walking": "walk",
    "bicycle": "bicycle",
    "motorbike": "motorbike",
    "motorbike_hailing": "motorbike",
    "taxi": "car",
    "car": "car",
    "mixed": "route",
}


class CostEstimatorService:
    """Attach DB-truth POI costs, lodging, and transport legs to an itinerary."""

    def enrich(self, itinerary: dict[str, Any] | None, contract: LLMDataContract, hotel_fallback: bool = False) -> dict[str, Any] | None:
        if not itinerary or not isinstance(itinerary, dict) or "days" not in itinerary:
            return itinerary

        result = deepcopy(itinerary)
        days = result.get("days") or []
        lodging_plan = self._build_lodging_plan(contract, hotel_fallback)
        result["lodging_plan"] = lodging_plan
        result["transport_plan"] = self._transport_plan_dict(contract)

        total_ticket = 0.0
        total_food = 0.0
        total_transport = 0.0

        for day in days:
            day_ticket = 0.0
            day_food = 0.0
            day_transport = 0.0
            prev_location = self._hotel_location(day, contract)
            prev_id = day.get("start_hotel_id") or "lodging_base"
            prev_name = day.get("start_hotel_name") or lodging_plan.get("name") or "Chỗ ở"
            legs: list[dict[str, Any]] = []

            day["start_lodging"] = self._lodging_ref(day, contract, lodging_plan)
            day["end_lodging"] = self._lodging_ref(day, contract, lodging_plan)
            lodging_location = self._hotel_location(day, contract)

            for stop in day.get("stops", []) or []:
                self._enrich_stop_cost(stop)
                leg = self._build_transport_leg(
                    contract=contract,
                    prev_location=prev_location,
                    next_location=stop.get("location"),
                    from_stop_id=str(prev_id),
                    from_name=str(prev_name),
                    to_stop_id=str(stop.get("poi_id") or ""),
                    to_name=str(stop.get("poi_name") or stop.get("name") or ""),
                    solver_travel_time=stop.get("travel_time_from_prev_min"),
                )
                if prev_id in {"lodging_base", day.get("start_hotel_id")}:
                    leg["is_from_lodging"] = True
                stop["transport_from_prev"] = leg
                stop["distance_from_prev_km"] = leg["distance_km"]
                stop["transport_cost_from_prev"] = leg["transport_cost"]
                legs.append(leg)

                prev_location = stop.get("location") or prev_location
                prev_id = stop.get("poi_id") or prev_id
                prev_name = stop.get("poi_name") or stop.get("name") or prev_name

                day_ticket += float(stop.get("ticket_cost") or 0.0)
                day_food += float(stop.get("expected_spend") or 0.0)
                day_transport += float(leg.get("transport_cost") or 0.0)

            if (day.get("stops") or []) and lodging_location:
                return_leg = self._build_transport_leg(
                    contract=contract,
                    prev_location=prev_location,
                    next_location=lodging_location,
                    from_stop_id=str(prev_id),
                    from_name=str(prev_name),
                    to_stop_id=str(day.get("end_hotel_id") or "lodging_base"),
                    to_name=str(day.get("end_hotel_name") or lodging_plan.get("name") or "Chỗ ở"),
                    solver_travel_time=None,
                )
                return_leg["is_return_to_lodging"] = True
                legs.append(return_leg)
                day_transport += float(return_leg.get("transport_cost") or 0.0)

            day["transport_legs"] = legs
            day_lodging = self._day_lodging_cost(day, lodging_plan)
            day["overnight_stay"] = self._overnight_summary(day, lodging_plan)
            day["day_ticket_cost"] = round(day_ticket)
            day["day_food_cost"] = round(day_food)
            day["day_transport_cost"] = round(day_transport)
            day["day_lodging_cost"] = round(day_lodging)
            day["day_total_cost"] = round(day_ticket + day_food + day_transport + day_lodging)

            total_ticket += day_ticket
            total_food += day_food
            total_transport += day_transport

        lodging_cost = float((lodging_plan or {}).get("total_cost") or 0.0)
        subtotal = total_ticket + total_food + total_transport + lodging_cost
        buffer_amount = self._misc_buffer(subtotal)
        estimated_total = subtotal + buffer_amount
        budget_total = None if contract.budget_is_unlimited else contract.budget_max
        warnings = self._budget_warnings(estimated_total, budget_total, lodging_plan)

        result["cost_summary"] = {
            "poi_ticket_cost": round(total_ticket),
            "food_and_drink_cost": round(total_food),
            "local_transport_cost": round(total_transport),
            "lodging_cost": round(lodging_cost),
            "misc_buffer": round(buffer_amount),
            "estimated_total_cost": round(estimated_total),
            "budget_total": round(budget_total) if budget_total is not None else None,
            "budget_remaining": round(budget_total - estimated_total) if budget_total is not None else None,
            "budget_confidence": self._budget_confidence(result),
            "warnings": warnings,
        }
        result["budget_used"] = result["cost_summary"]["estimated_total_cost"]
        result["budget_total"] = result["cost_summary"]["budget_total"]
        result["total_entrance_fee"] = result["cost_summary"]["poi_ticket_cost"]
        return result

    def _build_lodging_plan(self, contract: LLMDataContract, hotel_fallback: bool) -> dict[str, Any]:
        days = max(1, int(contract.num_days or 1))
        nights = max(0, days - 1)
        has_lodging = getattr(contract, "has_lodging", None)
        budget_scope = getattr(contract, "budget_scope", "unknown") or "unknown"
        include_cost = nights > 0 and not (has_lodging is True and budget_scope != "includes_hotel")
        nightly_rate = self._nightly_rate(contract) if include_cost else 0
        name = contract.hotel_name if contract.hotel_name and contract.hotel_name != "Hotel" else "Chỗ nghỉ trung tâm Huế"
        selection = getattr(contract, "lodging_selection", None)
        mode = "provided_by_user" if has_lodging is True else ("db_selected" if nights > 0 and not hotel_fallback else ("estimated_default" if nights > 0 else "none"))
        return {
            "nights": nights,
            "mode": mode,
            "name": name,
            "nightly_rate": round(nightly_rate),
            "total_cost": round(nightly_rate * nights),
            "included_in_budget": include_cost,
            "estimated": has_lodging is not True and nights > 0 and hotel_fallback,
            "hotel_fallback": bool(hotel_fallback),
            "selection_method": getattr(selection, "selection_method", "none") if selection else "none",
            "hotel_poi_id": getattr(selection, "hotel_poi_id", None) if selection else None,
        }

    def _nightly_rate(self, contract: LLMDataContract) -> float:
        explicit = getattr(contract, "lodging_budget_per_night", None)
        if explicit:
            return float(explicit)
        # If backend selected a DB hotel, its nightly price should already be stored here.
        selection = getattr(contract, "lodging_selection", None)
        if selection and getattr(selection, "status", None) == "needs_lodging":
            hotel_price = getattr(selection, "nightly_rate", None)
            if hotel_price:
                return float(hotel_price)
        budget = float(contract.budget_max or 0.0)
        nights = max(1, int(contract.num_days or 1) - 1)
        if budget and budget / nights < 500_000:
            return 250_000
        return 450_000

    def _enrich_stop_cost(self, stop: dict[str, Any]) -> None:
        category = self._category(stop)
        entrance_fee = float(stop.get("entrance_fee") or 0.0)
        price = float(stop.get("price") or 0.0)

        ticket_cost = 0.0
        expected_spend = 0.0
        price_source = "zero_cost"

        if category in FOOD_SPEND_GROUPS or self._has_any(stop, ("cafe", "coffee", "chè", "che", "dessert")):
            expected_spend = price
            price_source = "db_price" if price > 0 else "zero_cost"
        elif category in TICKET_GROUPS:
            ticket_cost = entrance_fee if entrance_fee > 0 else price
            price_source = "db_entrance_fee" if entrance_fee > 0 else ("db_price" if price > 0 else "zero_cost")
        else:
            ticket_cost = entrance_fee
            expected_spend = price
            price_source = "db_entrance_fee" if entrance_fee > 0 else ("db_price" if price > 0 else "zero_cost")

        stop["ticket_cost"] = round(ticket_cost)
        stop["expected_spend"] = round(expected_spend)
        stop["price_source"] = price_source
        stop["cost_category"] = "food_drink" if expected_spend else ("ticket" if ticket_cost else "free")
        stop["cost_confidence"] = "high"

    def _build_transport_leg(
        self,
        contract: LLMDataContract,
        prev_location: dict[str, Any] | None,
        next_location: dict[str, Any] | None,
        from_stop_id: str,
        from_name: str,
        to_stop_id: str,
        to_name: str,
        solver_travel_time: Any,
    ) -> dict[str, Any]:
        plan = self._transport_plan_dict(contract)
        distance_km = self._distance_km(prev_location, next_location)
        mode = self._leg_mode(distance_km, plan)
        travel_time = self._travel_time(distance_km, solver_travel_time)
        cost = self._transport_cost(distance_km, mode, plan)
        warning = None
        if mode == "walking" and distance_km > float(plan.get("walking_threshold_km") or 1.0):
            warning = "Đoạn này hơi xa để đi bộ, nên cân nhắc taxi/xe máy."

        return {
            "from_stop_id": from_stop_id,
            "from_name": from_name,
            "to_stop_id": to_stop_id,
            "to_name": to_name,
            "mode": mode,
            "mode_label": MODE_LABELS.get(mode, MODE_LABELS["mixed"]),
            "distance_km": round(distance_km, 2),
            "travel_time_min": travel_time,
            "transport_cost": round(cost),
            "cost_policy": plan.get("cost_policy"),
            "cost_scope": plan.get("cost_scope"),
            "icon": MODE_ICONS.get(mode, "route"),
            "warning": warning,
            "distance_confidence": "high" if distance_km > 0 else "missing_or_same_location",
        }

    def _transport_plan_dict(self, contract: LLMDataContract) -> dict[str, Any]:
        plan_obj = getattr(contract, "transport_plan", None)
        if plan_obj:
            plan = plan_obj.model_dump()
        else:
            plan = {}
        modes = [str(m).lower() for m in (contract.transport_modes or [])]
        if plan.get("availability") in (None, "unknown"):
            plan["availability"] = "unknown"
        if getattr(contract, "transport_policy", None) == "system_suggest_per_leg" and plan.get("availability") == "unknown":
            plan["availability"] = "needs_transport"
        if plan.get("primary_mode") in (None, "mixed") and modes:
            plan["primary_mode"] = self._normalize_mode(modes[0])
        plan.setdefault("primary_mode", "mixed")
        plan.setdefault("fallback_mode", "taxi")
        plan.setdefault("cost_policy", "per_leg")
        plan.setdefault("walking_threshold_km", 1.0)
        plan.setdefault("cost_scope", "total_group")
        if plan.get("availability") == "has_own_transport":
            plan["cost_policy"] = "time_only"
        elif plan.get("availability") == "needs_transport" or getattr(contract, "transport_policy", None) == "system_suggest_per_leg":
            default_mode = self._default_hired_mode(contract)
            if self._normalize_mode(str(plan.get("primary_mode") or "mixed")) in {"mixed", "taxi"} and self._party_size(contract) <= 2:
                plan["primary_mode"] = default_mode
            if self._normalize_mode(str(plan.get("fallback_mode") or "mixed")) in {"mixed", "taxi"} and self._party_size(contract) <= 2:
                plan["fallback_mode"] = default_mode
            plan["cost_policy"] = "per_leg"
        return plan

    def _leg_mode(self, distance_km: float, plan: dict[str, Any]) -> str:
        threshold = float(plan.get("walking_threshold_km") or 1.0)
        primary = self._normalize_mode(str(plan.get("primary_mode") or "mixed"))
        if distance_km > 0 and distance_km <= threshold:
            return "walking"
        if primary == "walking" and distance_km > threshold:
            return self._normalize_mode(str(plan.get("fallback_mode") or "taxi"))
        return primary

    def _party_size(self, contract: LLMDataContract) -> int:
        party = getattr(contract, "party", None)
        raw_size = getattr(party, "size", None) if party else None
        if raw_size is None:
            raw_size = getattr(contract, "group_size", None)
        try:
            return max(1, int(raw_size or 1))
        except (TypeError, ValueError):
            return 1

    def _default_hired_mode(self, contract: LLMDataContract) -> str:
        return "taxi" if self._party_size(contract) >= 3 else "motorbike_hailing"

    def _normalize_mode(self, mode: str) -> str:
        mode = mode.lower()
        if mode in {"walk", "di_bo"}:
            return "walking"
        if mode in {"grab", "grab_bike", "bike_hailing"}:
            return "motorbike_hailing"
        if mode in {"private_car", "oto", "o_to"}:
            return "car"
        if mode in MODE_LABELS:
            return mode
        return "mixed"

    def _travel_time(self, distance_km: float, solver_travel_time: Any) -> int:
        try:
            solver_time = int(solver_travel_time or 0)
        except (TypeError, ValueError):
            solver_time = 0
        conservative = 0
        if distance_km > 0:
            buffer_min = 10 if distance_km >= 8 else 5
            conservative = math.ceil(distance_km / 30.0 * 60.0 + buffer_min)
        return max(solver_time, conservative)

    def _transport_cost(self, distance_km: float, mode: str, plan: dict[str, Any]) -> float:
        policy = str(plan.get("cost_policy") or "per_leg")
        if distance_km <= 0 or mode == "walking" or policy in {"none", "time_only"}:
            return 0.0
        if policy == "daily_rental":
            return 0.0
        if mode in {"taxi", "car"}:
            return max(35_000.0, 20_000.0 + distance_km * 14_000.0)
        if mode in {"motorbike", "motorbike_hailing", "mixed"}:
            return max(15_000.0, 12_000.0 + distance_km * 7_000.0)
        return 0.0

    def _hotel_location(self, day: dict[str, Any], contract: LLMDataContract) -> dict[str, Any] | None:
        return (
            day.get("start_hotel_location")
            or day.get("end_hotel_location")
            or (
                {"latitude": contract.hotel_lat, "longitude": contract.hotel_lon}
                if contract.hotel_lat is not None and contract.hotel_lon is not None
                else None
            )
        )

    def _lodging_ref(self, day: dict[str, Any], contract: LLMDataContract, lodging_plan: dict[str, Any]) -> dict[str, Any] | None:
        if int(lodging_plan.get("nights") or 0) <= 0:
            return None
        return {
            "name": lodging_plan.get("name"),
            "location": self._hotel_location(day, contract),
            "estimated": lodging_plan.get("estimated", False),
            "selection_method": lodging_plan.get("selection_method"),
        }

    def _day_lodging_cost(self, day: dict[str, Any], lodging_plan: dict[str, Any]) -> float:
        nights = int(lodging_plan.get("nights") or 0)
        day_index = int(day.get("day_index") or 0)
        if nights <= 0 or day_index >= nights:
            return 0.0
        return float(lodging_plan.get("nightly_rate") or 0.0)

    def _overnight_summary(self, day: dict[str, Any], lodging_plan: dict[str, Any]) -> dict[str, Any] | None:
        nights = int(lodging_plan.get("nights") or 0)
        day_index = int(day.get("day_index") or 0)
        if nights <= 0 or day_index >= nights:
            return None
        cost = self._day_lodging_cost(day, lodging_plan)
        if cost <= 0 and not lodging_plan.get("name"):
            return None
        return {
            "name": lodging_plan.get("name"),
            "nightly_rate": round(cost),
            "estimated": lodging_plan.get("estimated", False),
        }

    def _misc_buffer(self, subtotal: float) -> float:
        return max(50_000.0 if subtotal > 0 else 0.0, subtotal * 0.10)

    def _budget_confidence(self, itinerary: dict[str, Any]) -> str:
        return "high"

    def _budget_warnings(self, estimated_total: float, budget_total: float | None, lodging_plan: dict[str, Any]) -> list[str]:
        warnings: list[str] = []
        if budget_total is not None and estimated_total > budget_total:
            warnings.append("budget_exceeded")
        if int(lodging_plan.get("nights") or 0) > 0:
            warnings.append("lodging_included" if lodging_plan.get("included_in_budget") else "lodging_excluded")
            if lodging_plan.get("estimated"):
                warnings.append("lodging_estimated")
        return warnings

    def _category(self, stop: dict[str, Any]) -> str:
        return str(stop.get("category_group") or stop.get("category") or "").lower()

    def _has_any(self, stop: dict[str, Any], needles: tuple[str, ...]) -> bool:
        haystack = " ".join(
            [
                str(stop.get("poi_name") or ""),
                str(stop.get("name") or ""),
                str(stop.get("description") or ""),
                " ".join(str(t) for t in (stop.get("tags") or [])),
            ]
        ).lower()
        return any(needle in haystack for needle in needles)

    def _distance_km(self, a: dict[str, Any] | None, b: dict[str, Any] | None) -> float:
        if not a or not b:
            return 0.0
        lat1 = self._coord(a, "latitude")
        lon1 = self._coord(a, "longitude")
        lat2 = self._coord(b, "latitude")
        lon2 = self._coord(b, "longitude")
        if None in (lat1, lon1, lat2, lon2):
            return 0.0
        radius = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        h = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return radius * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h)) * 1.25

    def _coord(self, location: dict[str, Any], key: str) -> float | None:
        aliases = {
            "latitude": ("latitude", "lat"),
            "longitude": ("longitude", "lng", "lon"),
        }
        value = None
        for alias in aliases.get(key, (key,)):
            if alias in location:
                value = location.get(alias)
                break
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
