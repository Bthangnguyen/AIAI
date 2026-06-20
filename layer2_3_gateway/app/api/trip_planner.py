"""Orchestrator API: Text → L2 → L3 → L4 pipeline (JSON + SSE streaming).

PRODUCTION-HARDENED ARCHITECTURE:
- DB I/O ISOLATION: LLM + Embedding calls (2-5s) execute OUTSIDE any DB session.
  DB session only opens for the 50ms spatial query then immediately returns to pool.
- ZERO Depends(get_db): All endpoints use _run_pipeline() which owns its own session.
- Pool cannot be exhausted by LLM latency or L4 solve time under ANY load.
- Firebase Auth: Protected endpoints require a valid Firebase ID token.
"""

import json as json_lib
import uuid
import asyncio
import time
import unicodedata
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.responses import StreamingResponse

from app.database import AsyncSessionFactory
from app.schemas.trip import TripPlanRequest, TripPlanResponse, LLMDataContract, POIResponse, ChatProcessRequest, ChatProcessResponse
from app.schemas.re_route import MobileReRouteRequest, ReRouteResponse
from app.services.llm_extractor import LLMExtractorService
from app.services.distribution_policy import apply_distribution_policy
from app.services.edit_intent_planner import EditIntentPlanner
from app.services.spatial_filter import SpatialFilterService
from app.services.layer4_client import Layer4Client
from app.services.embedding_service import EmbeddingService
from app.services.cost_estimator import CostEstimatorService
from app.utils.logging import AppLogger

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.middleware.firebase_verify import get_current_user, get_optional_user, FirebaseUser

router = APIRouter(prefix="/v1/trip")
logger = AppLogger().get_logger()

class UUIDEncoder(json_lib.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)

def json_dumps(obj, **kwargs):
    return json_lib.dumps(obj, cls=UUIDEncoder, **kwargs)

async def _enrich_itinerary_with_db(itinerary: dict) -> dict:
    if not itinerary or not itinerary.get("days"):
        return itinerary
    
    import os
    if os.environ.get("MOCK_LLM") == "True" or os.environ.get("MOCK_LLM") == "true":
        logger.info("Enriching itinerary offline via CSV dataset")
        import csv
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_file = os.path.join(base_dir, "ingestion", "sample_data", "hue_pois.csv")
        poi_map = {}
        if os.path.exists(csv_file):
            with open(csv_file, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    poi_map[row["name"]] = {
                        "name": row["name"],
                        "category": row["category"],
                        "description": row["description"] or "",
                        "tags": [t.strip() for t in row["tags"].split(",") if t.strip()],
                        "entrance_fee": float(row["entrance_fee"] or 0.0),
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"])
                    }
                    
        for day in itinerary.get("days", []):
            for stop in day.get("stops", []):
                sname = stop.get("poi_name") or stop.get("name")
                p = None
                if sname in poi_map:
                    p = poi_map[sname]
                else:
                    for k, v in poi_map.items():
                        if sname and (sname.lower() in k.lower() or k.lower() in sname.lower()):
                            p = v
                            break
                if p:
                    stop["poi_name"] = p["name"]
                    stop["category"] = p["category"]
                    stop["description"] = stop.get("description") or p["description"]
                    stop["tags"] = p["tags"]
                    stop["entrance_fee"] = p["entrance_fee"]
                    stop["location"] = {
                        "latitude": p["latitude"],
                        "longitude": p["longitude"]
                    }
        return itinerary

    from app.models.poi import PointOfInterest
    from geoalchemy2.functions import ST_AsGeoJSON
    from sqlalchemy import select
    import json as json_lib
    import uuid
    
    poi_ids = set()
    for day in itinerary.get("days", []):
        for stop in day.get("stops", []):
            pid = stop.get("poiId") or stop.get("poi_id")
            if pid:
                poi_ids.add(str(pid))
                
    if not poi_ids:
        return itinerary
        
    valid_poi_ids = []
    for pid in poi_ids:
        try:
            uuid.UUID(str(pid))
            valid_poi_ids.append(str(pid))
        except ValueError:
            continue
            
    if not valid_poi_ids:
        return itinerary
        
    POI = PointOfInterest
    stmt = select(POI, ST_AsGeoJSON(POI.coordinates).label("geojson")).where(POI.uuid.in_(valid_poi_ids))
    
    async with AsyncSessionFactory() as db_session:
        res = await db_session.execute(stmt)
        rows = res.all()
        
        poi_map = {}
        for poi, geojson_str in rows:
            geojson = json_lib.loads(geojson_str) if geojson_str else None
            lat = geojson["coordinates"][1] if geojson else 0.0
            lon = geojson["coordinates"][0] if geojson else 0.0
            poi_map[str(poi.uuid)] = {
                "name": poi.name,
                "category": poi.category,
                "description": poi.description or "",
                "tags": poi.tags or [],
                "entrance_fee": poi.entrance_fee or poi.price or 0.0,
                "latitude": lat,
                "longitude": lon
            }
            
        for day in itinerary.get("days", []):
            for stop in day.get("stops", []):
                pid = stop.get("poiId") or stop.get("poi_id")
                if pid and str(pid) in poi_map:
                    p = poi_map[str(pid)]
                    stop["poi_id"] = str(pid)
                    stop["poi_name"] = stop.get("poi_name") or stop.get("name") or stop.get("note") or p["name"]
                    stop["category"] = p["category"]
                    vnote = stop.get("vibe_note")
                    if vnote:
                        stop["vibe_note"] = vnote
                        stop["description"] = vnote
                    else:
                        stop["description"] = stop.get("description") or p["description"]
                    stop["tags"] = p["tags"]
                    stop["entrance_fee"] = p["entrance_fee"]
                    stop["location"] = {
                        "latitude": p["latitude"],
                        "longitude": p["longitude"]
                    }
                    
    return itinerary

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Service singletons (stateless, thread-safe)
llm_service = LLMExtractorService()
spatial_service = SpatialFilterService()
layer4_client = Layer4Client()
embed_service = EmbeddingService()
cost_estimator = CostEstimatorService()


class IdempotencyManager:
    def __init__(self, ttl_seconds=300):
        self.ttl = ttl_seconds
        self.cache = {}  # key -> {"status": "pending" | "completed", "response": data, "timestamp": time}
        self.lock = asyncio.Lock()

    async def get_or_set(self, key: str):
        async with self.lock:
            now = time.time()
            self.cache = {k: v for k, v in self.cache.items() if now - v["timestamp"] < self.ttl}
            
            if key in self.cache:
                return self.cache[key]
            
            self.cache[key] = {
                "status": "pending",
                "response": None,
                "timestamp": now
            }
            return None

    async def set_completed(self, key: str, response):
        async with self.lock:
            if key in self.cache:
                self.cache[key]["status"] = "completed"
                self.cache[key]["response"] = response
                self.cache[key]["timestamp"] = time.time()
                
    async def remove(self, key: str):
        async with self.lock:
            self.cache.pop(key, None)


idempotency_manager = IdempotencyManager()


def _poi_row_to_response(row: Any) -> POIResponse:
    poi = row.PointOfInterest
    geojson = json_lib.loads(row.geojson) if row.geojson else None
    lat = geojson["coordinates"][1] if geojson else 0.0
    lon = geojson["coordinates"][0] if geojson else 0.0
    return POIResponse(
        uuid=poi.uuid,
        name=poi.name,
        category=poi.category,
        category_group=poi.category_group,
        description=poi.description,
        latitude=lat,
        longitude=lon,
        visit_duration_min=poi.visit_duration_min,
        price=poi.price,
        entrance_fee=poi.entrance_fee,
        open_time=poi.open_time,
        close_time=poi.close_time,
        priority_score=poi.priority_score,
        tags=poi.tags,
    )


MICRO_INTENT_ALIASES = {
    "bun_bo": ("bun_bo", "bun bo", "bún bò", "bun_bo_hue", "bún bò huế"),
    "com_hen": ("com_hen", "com hen", "cơm hến", "bun_hen", "bún hến"),
    "che_hue": ("che_hue", "che", "chè", "chè huế", "hue_sweet_soup"),
    "cafe_muoi": ("cafe_muoi", "salt_coffee", "cafe muoi", "cà phê muối", "ca phe muoi"),
    "vegetarian": ("vegetarian", "vegan", "chay", "ăn chay", "quan_chay"),
}


MICRO_INTENT_CATEGORY = {
    "bun_bo": "food",
    "com_hen": "food",
    "che_hue": "food",
    "cafe_muoi": "cafe",
    "vegetarian": "food",
}

EDIT_MICRO_TAG_ALIASES = {
    "che": "che_hue",
    "dessert": "che_hue",
}


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value.lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    return text


def _detect_required_micro_intents(contract: LLMDataContract, prompt: str) -> list[str]:
    """Detect user-mentioned concrete dishes/drinks that must be represented."""
    sources = [
        prompt or "",
        " ".join(contract.tags or []),
        " ".join(contract.food_preferences or []),
        contract.distribution_description or "",
    ]
    haystack = _normalize_text(" | ".join(sources))
    required: list[str] = []
    for micro_tag, aliases in MICRO_INTENT_ALIASES.items():
        if any(_normalize_text(alias) in haystack for alias in aliases):
            required.append(micro_tag)
    return required


def _poi_matches_micro_tag(poi: POIResponse, micro_tag: str) -> bool:
    """Return True when a POI represents a concrete requested dish/drink."""
    aliases = MICRO_INTENT_ALIASES.get(micro_tag, (micro_tag,))
    tag_text = " ".join(str(tag) for tag in (poi.tags or []))
    haystack = _normalize_text(" | ".join([
        poi.name or "",
        poi.description or "",
        poi.category or "",
        poi.category_group or "",
        tag_text,
    ]))
    return any(_normalize_text(alias) in haystack for alias in aliases)


async def _resolve_required_micro_pois(
    contract: LLMDataContract,
    required_micro_tags: list[str],
    db_session,
) -> list[POIResponse]:
    """Resolve one best POI per required micro intent and lock it for Layer 4."""
    if not required_micro_tags:
        return []

    from sqlalchemy import select, func, or_
    from app.models.poi import PointOfInterest
    from geoalchemy2.functions import ST_AsGeoJSON

    POI = PointOfInterest
    resolved: list[POIResponse] = []
    used_ids: set[str] = set()

    for micro_tag in required_micro_tags:
        aliases = list(MICRO_INTENT_ALIASES.get(micro_tag, (micro_tag,)))
        category_group = MICRO_INTENT_CATEGORY.get(micro_tag)

        tag_conditions = [POI.tags.overlap([micro_tag])]
        for alias in aliases:
            norm_alias = _normalize_text(alias)
            tag_conditions.append(func.coalesce(func.array_to_string(POI.tags, ","), "").ilike(f"%{norm_alias}%"))
            tag_conditions.append(POI.name.ilike(f"%{alias}%"))
            tag_conditions.append(POI.description.ilike(f"%{alias}%"))

        conditions = [or_(*tag_conditions)]
        if category_group:
            conditions.append(or_(
                func.lower(POI.category_group) == category_group,
                func.lower(POI.category) == category_group,
            ))
        if contract.budget_max:
            conditions.append(POI.price <= contract.budget_max)
        if contract.time_window:
            conditions.append(POI.open_time <= contract.time_window.end_min)
            conditions.append(POI.close_time >= contract.time_window.start_min)

        query_vector = None
        try:
            query_vector = await embed_service.aembed_text(f"{micro_tag} Hue local food cafe")
        except Exception as exc:
            logger.warning(f"Micro-intent embedding unavailable for {micro_tag}: {exc}")

        stmt = select(POI, ST_AsGeoJSON(POI.coordinates).label("geojson")).where(*conditions)
        if query_vector is not None:
            stmt = stmt.where(POI.tags_vector.isnot(None)).order_by(
                POI.tags_vector.cosine_distance(query_vector),
                POI.priority_score.desc(),
            )
        else:
            stmt = stmt.order_by(POI.priority_score.desc())
        stmt = stmt.limit(8)

        result = await db_session.execute(stmt)
        rows = result.all()
        selected = None
        for row in rows:
            candidate = _poi_row_to_response(row)
            if str(candidate.uuid) not in used_ids:
                selected = candidate
                break
        if selected:
            selected.is_locked = True
            selected.utility_score = max(selected.utility_score or 0.5, 0.98)
            selected.priority_score = max(selected.priority_score or 0.5, 0.95)
            resolved.append(selected)
            used_ids.add(str(selected.uuid))
            logger.info(f"Locked micro intent {micro_tag}: {selected.name}")
        else:
            logger.warning(f"No POI found for required micro intent: {micro_tag}")

    return resolved


def _merge_required_micro_pois(
    pois: list[POIResponse],
    required_pois: list[POIResponse],
    target_count: int = 50,
) -> list[POIResponse]:
    """Merge locked POIs and suppress duplicate micro-intent candidates."""
    if not required_pois:
        return pois

    required_by_id = {str(p.uuid): p for p in required_pois}
    required_micro_tags = [
        micro_tag
        for micro_tag in MICRO_INTENT_ALIASES
        if any(_poi_matches_micro_tag(required, micro_tag) for required in required_pois)
    ]
    merged_required = list(required_by_id.values())
    existing_non_required: list[POIResponse] = []

    for poi in pois:
        key = str(poi.uuid)
        if key in required_by_id:
            locked = required_by_id[key]
            poi.is_locked = True
            poi.utility_score = max(poi.utility_score or 0.5, locked.utility_score or 0.98)
            poi.priority_score = max(poi.priority_score or 0.5, locked.priority_score or 0.95)
            required_by_id[key] = poi
        elif any(_poi_matches_micro_tag(poi, micro_tag) for micro_tag in required_micro_tags):
            # If the user explicitly asked for bun_bo/com_hen/che/cafe_muoi,
            # lock one good representative instead of letting the scorer fill
            # the day with repeated versions of the same dish.
            continue
        else:
            existing_non_required.append(poi)

    merged_required = list(required_by_id.values())
    room = max(0, target_count - len(merged_required))
    return merged_required + existing_non_required[:room]


VIETNAMESE_SYNONYMS = {
    "lon": ["heo"],
    "heo": ["lon"],
    "cha gio": ["nem ran"],
    "nem ran": ["cha gio"],
}


def _normalize_and_tokenize(text: str) -> list[str]:
    if not text:
        return []
    import re
    norm = _normalize_text(text)
    norm = re.sub(r'[^\w\s]', ' ', norm)
    return [w for w in norm.split() if len(w) >= 2]


def _clean_and_norm_tags(tags: list | None) -> list[str]:
    if not tags:
        return []
    cleaned = []
    for t in tags:
        if isinstance(t, str):
            cleaned.append(_normalize_text(t.strip('[]"\'')))
    return cleaned


def _token_match_score(query_tokens: list[str], field_tokens: list[str]) -> float:
    if not query_tokens or not field_tokens:
        return 0.0
    score = 0.0
    field_set = set(field_tokens)
    for q_t in query_tokens:
        if q_t in field_set:
            score += 1.0
            continue
        syns = VIETNAMESE_SYNONYMS.get(q_t, [])
        for syn in syns:
            if syn in field_set:
                score += 0.8
                break
    return score


async def _resolve_edit_add_poi(
    query: str,
    category: str | None = None,
    micro_tags: list[str] | None = None,
    time_window: dict[str, int] | None = None,
    limit: int = 1,
) -> list[POIResponse]:
    """Resolve an add/replace edit with wide semantic recall and soft reranking."""
    from sqlalchemy import select, or_, func, cast, String
    from app.models.poi import PointOfInterest
    from geoalchemy2.functions import ST_AsGeoJSON

    POI = PointOfInterest
    text = (query or "").strip()
    tags = [
        EDIT_MICRO_TAG_ALIASES.get(_normalize_text(t), _normalize_text(t))
        for t in (micro_tags or [])
        if t
    ]
    category_norm = _normalize_text(category)
    start_min = int((time_window or {}).get("start_min") or 0)
    end_min = int((time_window or {}).get("end_min") or 1440)

    query_vector = None
    if text:
        try:
            query_vector = await embed_service.aembed_text(text)
        except Exception as exc:
            logger.warning(f"Edit POI vector search unavailable, using SQL fallback: {exc}")

    async with AsyncSessionFactory() as db_session:
        if query_vector is not None:
            stmt = (
                select(
                    POI,
                    ST_AsGeoJSON(POI.coordinates).label("geojson"),
                    POI.tags_vector.cosine_distance(query_vector).label("semantic_distance"),
                )
                .where(POI.tags_vector.isnot(None))
                .order_by(POI.tags_vector.cosine_distance(query_vector), POI.priority_score.desc())
                .limit(max(80, limit * 20))
            )
        else:
            # SQL fallback with smart token-based matching and synonyms
            conditions = []
            if text:
                query_tokens = _normalize_and_tokenize(text)
                search_words = set(query_tokens)
                for w in query_tokens:
                    raw_words = [w]
                    for raw_w in text.lower().split():
                        if _normalize_text(raw_w) == w:
                            raw_words.append(raw_w)
                    for rw in raw_words:
                        search_words.add(rw)
                        for syn in VIETNAMESE_SYNONYMS.get(w, []):
                            search_words.add(syn)
                            search_words.add(_normalize_text(syn))
                            
                for sw in search_words:
                    conditions.append(POI.name.ilike(f"%{sw}%"))
                    conditions.append(POI.description.ilike(f"%{sw}%"))
                    conditions.append(func.coalesce(func.array_to_string(POI.tags, ','), '').ilike(f"%{sw}%"))
                
            stmt = select(POI, ST_AsGeoJSON(POI.coordinates).label("geojson"))
            if conditions:
                stmt = stmt.where(or_(POI.priority_score >= 0.4, *conditions))
            stmt = stmt.order_by(POI.priority_score.desc()).limit(400)
            
        db_res = await db_session.execute(stmt)
        rows = db_res.all()

    def score_row(row: Any) -> tuple[float, POIResponse]:
        poi_resp = _poi_row_to_response(row)
        fields = " ".join([
            poi_resp.name or "",
            poi_resp.category or "",
            poi_resp.category_group or "",
            poi_resp.description or "",
            " ".join(poi_resp.tags or []),
        ])
        haystack = _normalize_text(fields)
        poi_tags = set(_clean_and_norm_tags(poi_resp.tags))
        poi_category = _normalize_text(poi_resp.category_group or poi_resp.category)

        distance = float(getattr(row, "semantic_distance", 0.45) or 0.45)
        score = max(0.0, 1.0 - min(distance, 2.0) / 2.0)
        
        if text:
            norm_name = _normalize_text(poi_resp.name)
            norm_text = _normalize_text(text)
            if norm_text == norm_name:
                score += 2.0
            elif norm_text in norm_name:
                score += 1.0
            else:
                query_tokens = _normalize_and_tokenize(text)
                name_tokens = _normalize_and_tokenize(poi_resp.name)
                haystack_tokens = _normalize_and_tokenize(fields)
                
                overlap_name = _token_match_score(query_tokens, name_tokens)
                overlap_haystack = _token_match_score(query_tokens, haystack_tokens)
                score += 0.3 * overlap_name + 0.05 * overlap_haystack

        if category_norm and category_norm == poi_category:
            score += 0.25
        elif category_norm and category_norm in haystack:
            score += 0.12
            
        if tags:
            overlap = len(set(tags).intersection(poi_tags))
            if overlap:
                score += min(0.25, 0.12 * overlap)
            elif any(tag in haystack for tag in tags):
                score += 0.08
                
        if time_window and poi_resp.open_time <= end_min and poi_resp.close_time >= start_min:
            score += 0.08
        if poi_category in {"hotel", "accommodation", "lodging"}:
            score -= 1.0
        score += min(0.1, float(poi_resp.priority_score or 0.0) * 0.05)
        return score, poi_resp

    ranked = sorted((score_row(row) for row in rows), key=lambda item: item[0], reverse=True)
    if tags:
        hard_matched = [
            item for item in ranked
            if any(_poi_matches_micro_tag(item[1], tag) for tag in tags)
        ]
        if hard_matched:
            ranked = hard_matched
    picked = [poi for score, poi in ranked if score > -0.2][:limit]
    if picked:
        logger.info(
            "Edit semantic resolver picked: %s for query=%r category=%r tags=%s",
            [p.name for p in picked],
            text,
            category,
            micro_tags,
        )
    else:
        logger.warning("Edit semantic resolver found no POI for query=%r category=%r tags=%s", text, category, micro_tags)
    return picked


def _poi_suggestion_payload(poi: POIResponse) -> dict[str, Any]:
    return {
        "id": str(poi.uuid),
        "uuid": str(poi.uuid),
        "name": poi.name,
        "category": poi.category_group or poi.category,
        "description": poi.description or "",
        "tags": poi.tags or [],
        "estimatedDurationMinutes": poi.visit_duration_min or 60,
        "estimatedCost": (poi.entrance_fee if poi.entrance_fee and poi.entrance_fee > 0 else (poi.price or 0)),
        "rating": 4.5,
        "lat": poi.latitude,
        "lng": poi.longitude,
        "price": poi.price,
        "entrance_fee": poi.entrance_fee,
        "visit_duration_min": poi.visit_duration_min,
    }


async def _attach_edit_suggestions(pending_edit_plan: dict[str, Any] | None) -> dict[str, Any] | None:
    if not pending_edit_plan:
        return pending_edit_plan
    operations = list(pending_edit_plan.get("operations") or [])
    all_suggestions: list[dict[str, Any]] = []
    for op in operations:
        if op.get("type") not in {"add_place", "replace_place"}:
            continue
        query = op.get("query") or op.get("target")
        if not query:
            continue
        candidates = await _resolve_edit_add_poi(
            query=query,
            category=op.get("target_category"),
            micro_tags=op.get("target_micro_tags") or [],
            time_window=op.get("time_window") or None,
            limit=5,
        )
        suggestions = [_poi_suggestion_payload(poi) for poi in candidates]
        op["suggestions"] = suggestions
        all_suggestions.extend({
            **suggestion,
            "target_day": op.get("target_day"),
            "operation_type": op.get("type"),
        } for suggestion in suggestions)
    pending_edit_plan["operations"] = operations
    if all_suggestions:
        pending_edit_plan["suggestions"] = all_suggestions
    return pending_edit_plan


def _mark_confirmed(contract: LLMDataContract, field: str) -> None:
    if field not in contract.confirmed_fields:
        contract.confirmed_fields.append(field)


def _merge_unique(left: list[str] | None, right: list[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in list(left or []) + list(right or []):
        key = str(value).strip()
        if key and key.lower() not in seen:
            seen.add(key.lower())
            result.append(key)
    return result


def _is_supported_destination(destination: str | None) -> bool:
    if not destination:
        return False
    raw = destination.lower()
    normalized = unicodedata.normalize("NFD", raw)
    asciiish = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return (
        any(token in raw for token in ["huế", "hue", "huáº¿"])
        or "hue" in asciiish
        or asciiish.startswith("hu")
        or " hu" in asciiish
    )


def _normalize_supported_destination(contract: LLMDataContract, request: TripPlanRequest) -> bool:
    """Accept Hue from either extracted fields or the original prompt."""
    if contract.destination and not _is_supported_destination(contract.destination):
        return False
    if _is_supported_destination(contract.destination):
        contract.destination = "Hue"
        return True
    if _is_supported_destination(request.destination) or _is_supported_destination(request.user_prompt):
        contract.destination = "Hue"
        _mark_confirmed(contract, "destination")
        return True
    return False


def _apply_request_overrides(contract: LLMDataContract, request: TripPlanRequest) -> LLMDataContract:
    """Apply manual request overrides from forms directly on top of the contract."""
    if request.destination:
        if not contract.destination or request.destination != "Huế":
            contract.destination = request.destination
            _mark_confirmed(contract, "destination")

    if request.num_days:
        contract.num_days = request.num_days
        _mark_confirmed(contract, "num_days")

    if request.budget is not None and not contract.budget_is_unlimited:
        contract.budget_max = request.budget
        _mark_confirmed(contract, "budget")

    if request.preferences:
        contract.tags = _merge_unique(contract.tags, request.preferences)
        _mark_confirmed(contract, "interests")

    if request.hotel_lat is not None:
        contract.hotel_lat = request.hotel_lat
    if request.hotel_lon is not None:
        contract.hotel_lon = request.hotel_lon
    if request.hotel_name:
        contract.hotel_name = request.hotel_name
    if request.hotel_lat is not None or request.hotel_lon is not None or request.hotel_name:
        contract.hotel_confirmed = True
        _mark_confirmed(contract, "hotel")

    return contract


async def _run_pipeline(
    request: TripPlanRequest,
) -> tuple[LLMDataContract, List[POIResponse], bool]:
    """L2 → Embed → L3 pipeline with TOTAL DB I/O isolation."""
    logger.info(f"🚀 _run_pipeline STARTED for prompt: {request.user_prompt}")
    
    prompt = request.user_prompt.strip()
    if len(prompt) < 10 or len(prompt) > 500:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "LLM_PARSE_ERROR", "message": "Độ dài mô tả lịch trình phải từ 10 đến 500 ký tự."}
        )

    # ──── PHASE A: NETWORK I/O (NO DB SESSION) ────
    if request.contract is not None:
        contract = request.contract.model_copy(deep=True)
        logger.info("Using confirmed manual contract from request; skipping LLM extraction")
    else:
        contract = await llm_service.extract_intent(
            user_prompt=request.user_prompt,
            hotel_lat=request.hotel_lat,
            hotel_lon=request.hotel_lon,
            hotel_name=request.hotel_name,
            num_days=request.num_days or 1,
        )

    # Apply manual overrides (e.g. from web form elements)
    contract = _apply_request_overrides(contract, request)

    # Spatial scope check: Huế/Hue only
    if not _normalize_supported_destination(contract, request):
        raise HTTPException(
            status_code=400,
            detail={"error_code": "LLM_PARSE_ERROR", "message": "Hiện tại hệ thống chỉ hỗ trợ lên lịch trình tại Huế. Vui lòng ghi rõ 'Huế' trong mô tả chuyến đi."}
        )

    # Validate insufficient intent
    is_empty_tags = not contract.tags or contract.tags == ["general"]
    is_empty_locked = not contract.locked_pois
    is_empty_vibe_and_type = not contract.vibe and not contract.trip_type
    
    if is_empty_tags and is_empty_locked and is_empty_vibe_and_type:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "LLM_INSUFFICIENT_INTENT",
                "message": "Không thể lập lịch trình do thiếu sở thích hoặc thông tin chi tiết về chuyến đi. Vui lòng bổ sung sở thích (ví dụ: văn hóa, ẩm thực, lăng tẩm...)."
            }
        )

    apply_distribution_policy(contract, request.user_prompt)

    # Validate trip duration constraints
    if contract.num_days is not None and (contract.num_days < 1 or contract.num_days > 7):
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "LLM_INVALID_DURATION",
                "message": f"Số ngày du lịch ({contract.num_days} ngày) không hợp lệ. Lập lịch trình hỗ trợ từ 1 đến 7 ngày."
            }
        )

    # Validate budget limits
    if contract.budget_max is not None and contract.budget_max < 50000:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "LLM_INVALID_BUDGET",
                "message": f"Ngân sách tối đa {contract.budget_max:,.0f} VND quá thấp. Vui lòng nhập tối thiểu 50,000 VND."
            }
        )

    query_vector = None
    semantic_terms: List[str] = []
    semantic_terms.extend(getattr(contract, "tags", None) or [])
    semantic_terms.extend(getattr(contract, "food_preferences", None) or [])
    semantic_terms.extend(getattr(contract, "avoid_tags", None) or [])
    trip_type = getattr(contract, "trip_type", None)
    if trip_type:
        semantic_terms.append(trip_type)
    semantic_terms = [str(t).strip() for t in semantic_terms if str(t).strip()]

    # Locked POIs are force-included separately. Keeping their names out of the
    # semantic retrieval vector prevents one locked culture POI from pulling an
    # entire culture cluster into a food/cafe-heavy trip.
    if semantic_terms or getattr(contract, "distribution_description", None):
        if getattr(contract, "distribution_description", None):
            tag_text = embed_service.build_distribution_query_text(
                distribution_description=contract.distribution_description or "",
                tags=semantic_terms,
                destination=contract.destination or "Huế"
            )
        else:
            tag_text = embed_service.build_poi_text(
                name="query", category="preference",
                tags=semantic_terms, description="",
            )
        try:
            query_vector = await embed_service.aembed_text(tag_text)
        except Exception as e:
            logger.warning(f"Embedding failed, falling back to priority_score: {e}")

    # ──── PHASE B: DATABASE I/O (FLASH OPEN/CLOSE ~50ms) ────
    hotel_fallback = False
    import os
    if os.environ.get("MOCK_LLM") == "True" or os.environ.get("MOCK_LLM") == "true":
        logger.info("MOCK_LLM is enabled: using local CSV database fallback (offline mode)")
        if contract.hotel_lat is None or contract.hotel_lon is None:
            contract.hotel_name = "Hue default hotel"
            contract.hotel_lat = 16.4637
            contract.hotel_lon = 107.5905
            hotel_fallback = True
        import csv
        import math
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_file = os.path.join(base_dir, "ingestion", "sample_data", "hue_pois.csv")
        raw_pois = []
        if os.path.exists(csv_file):
            with open(csv_file, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    raw_pois.append({
                        "uuid": uuid.UUID(row["uuid"]) if row.get("uuid") else uuid.uuid4(),
                        "name": row["name"],
                        "category": row["category"],
                        "description": row["description"],
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                        "visit_duration_min": int(row["visit_duration_min"]),
                        "price": float(row["price"]),
                        "entrance_fee": float(row["entrance_fee"]),
                        "open_time": int(row["open_time"]),
                        "close_time": int(row["close_time"]),
                        "priority_score": float(row.get("priority_score", 0.8)),
                        "tags": [t.strip() for t in row["tags"].split(",") if t.strip()],
                        "is_outdoor": row["is_outdoor"].lower() == "true",
                    })
        
        scored = []
        for p in raw_pois:
            lat1, lon1, lat2, lon2 = contract.hotel_lat, contract.hotel_lon, p["latitude"], p["longitude"]
            dist = math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2) * 111.0
            if dist > contract.radius_km:
                continue
            if contract.budget_max and p["entrance_fee"] > contract.budget_max:
                continue
                
            score = p["priority_score"]
            if contract.tags:
                match_count = len(set(contract.tags).intersection(p["tags"]))
                score += match_count * 0.1
                
            poi_resp = POIResponse(
                uuid=p["uuid"],
                name=p["name"],
                category=p["category"],
                description=p["description"],
                latitude=p["latitude"],
                longitude=p["longitude"],
                visit_duration_min=p["visit_duration_min"],
                price=p["price"],
                entrance_fee=p["entrance_fee"],
                open_time=p["open_time"],
                close_time=p["close_time"],
                priority_score=p["priority_score"],
                tags=p["tags"],
                is_locked=False,
                utility_score=score
            )
            if contract.locked_pois and any(lp.lower() in p["name"].lower() for lp in contract.locked_pois):
                poi_resp.is_locked = True
                poi_resp.utility_score = 0.99
                
            scored.append(poi_resp)
            
        scored.sort(key=lambda x: x.utility_score, reverse=True)
        pois = scored[:50]
    else:
        async with AsyncSessionFactory() as db_session:
            if contract.hotel_lat is None or contract.hotel_lon is None:
                hotel_fallback = True
                from sqlalchemy import select, func, or_
                from geoalchemy2.functions import ST_AsGeoJSON
                from app.models.poi import PointOfInterest
                import json as json_lib
                
                POI = PointOfInterest
                stmt = select(
                    POI.uuid,
                    POI.name,
                    POI.price,
                    ST_AsGeoJSON(POI.coordinates).label("geojson"),
                ).where(
                    or_(
                        func.lower(POI.category_group) == "hotel",
                        func.lower(POI.category) == "hotel",
                        POI.category.ilike("%Khách sạn%"),
                    )
                )
                if contract.budget_max:
                    per_night_cap = max(
                        250_000,
                        contract.budget_max * 0.25 / max(1, (contract.num_days or 1) - 1),
                    )
                    stmt = stmt.where(or_(POI.price == 0, POI.price <= per_night_cap))
                stmt = stmt.order_by(POI.priority_score.desc()).limit(1)
                
                result = await db_session.execute(stmt)
                row = result.first()
                if row:
                    hotel_fallback = False
                    contract.hotel_name = row.name
                    contract.lodging_budget_per_night = float(row.price or 0)
                    contract.lodging_selection.status = "needs_lodging"
                    contract.lodging_selection.selection_method = "db_poi"
                    contract.lodging_selection.name = row.name
                    contract.lodging_selection.hotel_poi_id = str(row.uuid)
                    geojson = json_lib.loads(row.geojson)
                    contract.hotel_lon = geojson["coordinates"][0]
                    contract.hotel_lat = geojson["coordinates"][1]
                    contract.lodging_selection.lon = contract.hotel_lon
                    contract.lodging_selection.lat = contract.hotel_lat
                    logger.info(f"🏨 Auto-selected hotel: {contract.hotel_name}")
                else:
                    contract.hotel_name = "Hue Default Hotel"
                    contract.hotel_lat = 16.4637
                    contract.hotel_lon = 107.5905
                    logger.warning("No hotel found matching criteria, using default.")

            pois = await spatial_service.get_optimized_pois(
                contract=contract,
                db_session=db_session,
                query_vector=query_vector,
            )

            required_micro_tags = _detect_required_micro_intents(contract, request.user_prompt)
            if required_micro_tags:
                required_pois = await _resolve_required_micro_pois(
                    contract=contract,
                    required_micro_tags=required_micro_tags,
                    db_session=db_session,
                )
                pois = _merge_required_micro_pois(pois, required_pois)
                logger.info(
                    f"Required micro coverage: tags={required_micro_tags}, "
                    f"locked={len(required_pois)}, pool={len(pois)}"
                )

    return contract, pois, hotel_fallback


@router.post("/plan_trip", response_model=TripPlanResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def plan_trip(request: Request, body: TripPlanRequest, user: FirebaseUser = Depends(get_current_user)):
    """Full pipeline (JSON): Text → LLM → Spatial → OR-Tools. Requires Firebase Auth."""
    logger.info(f"🔐 plan_trip called by user: {user.uid} ({user.email})")
    
    idempotency_key = request.headers.get("X-Idempotency-Key")
    if idempotency_key:
        cached = await idempotency_manager.get_or_set(idempotency_key)
        if cached:
            if cached["status"] == "pending":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error_code": "DUPLICATE_REQUEST", "message": "Yêu cầu của bạn đang được xử lý. Vui lòng đợi."}
                )
            elif cached["status"] == "completed":
                logger.info("Idempotency hit: returning completed response")
                return cached["response"]

    try:
        contract, pois, hotel_fallback = await _run_pipeline(body)

        if not pois:
            response_data = TripPlanResponse(
                status="error", llm_contract=contract, pois=[],
                message="Không tìm thấy địa điểm du lịch nào phù hợp với yêu cầu của bạn.",
            )
            if idempotency_key:
                await idempotency_manager.set_completed(idempotency_key, response_data.model_dump())
            return response_data

        locked_count = sum(1 for p in pois if p.is_locked)
        l4_result = await layer4_client.plan(pois=pois, contract=contract)

        if l4_result and "error_code" in l4_result:
            raise HTTPException(
                status_code=400,
                detail={"error_code": l4_result["error_code"], "message": l4_result["message"]}
            )

        if l4_result:
            l4_result["hotel_fallback"] = hotel_fallback
            l4_result = cost_estimator.enrich(l4_result, contract, hotel_fallback=hotel_fallback)

        response_data = TripPlanResponse(
            status="success" if l4_result else "partial",
            llm_contract=contract, pois=pois,
            locked_pois=locked_count, layer4_result=l4_result,
            message="Tối ưu lịch trình thành công!" if l4_result else "Lỗi lập lịch trình.",
        )

        if idempotency_key:
            await idempotency_manager.set_completed(idempotency_key, response_data.model_dump())
        return response_data

    except Exception as e:
        if idempotency_key:
            await idempotency_manager.remove(idempotency_key)
        raise e


@router.post("/plan_trip_stream")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def plan_trip_stream(request: Request, body: TripPlanRequest, user: FirebaseUser = Depends(get_current_user)):
    """SSE streaming: pushes route chunks in real-time. Requires Firebase Auth."""
    logger.info(f"📡 SSE REQUEST from user: {user.uid} ({user.email}), host: {request.client.host}")
    
    idempotency_key = request.headers.get("X-Idempotency-Key")
    if idempotency_key:
        cached = await idempotency_manager.get_or_set(idempotency_key)
        if cached:
            if cached["status"] == "pending":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error_code": "DUPLICATE_REQUEST", "message": "Yêu cầu của bạn đang được xử lý. Vui lòng đợi."}
                )
            elif cached["status"] == "completed":
                logger.info("Idempotency hit (stream): returning completed response")
                async def cached_generator():
                    yield f"data: {json_dumps(cached['response'])}\n\n"
                    yield "data: [DONE]\n\n"
                return StreamingResponse(
                    cached_generator(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                )

    try:
        contract, pois, hotel_fallback = await _run_pipeline(body)
    except HTTPException as e:
        if idempotency_key:
            await idempotency_manager.remove(idempotency_key)
        raise e
    except Exception as e:
        if idempotency_key:
            await idempotency_manager.remove(idempotency_key)
        raise HTTPException(
            status_code=400,
            detail={"error_code": "LLM_PARSE_ERROR", "message": f"Không hiểu mô tả chuyến đi: {str(e)}"}
        )

    async def event_generator():
        yield f"data: {json_dumps({'step': 'l2_done', 'tags': contract.tags, 'locked': contract.locked_pois})}\n\n"

        if not pois:
            err_payload = {'step': 'error', 'error_code': 'NO_FEASIBLE_ROUTE', 'message': 'Không tìm thấy địa điểm nào phù hợp.'}
            yield f"data: {json_dumps(err_payload)}\n\n"
            yield "data: [DONE]\n\n"
            if idempotency_key:
                await idempotency_manager.set_completed(idempotency_key, err_payload)
            return

        # Gửi toàn bộ danh sách POIs (kèm giá, tag, mô tả thực tế) để frontend đưa vào POI_CACHE
        pois_json = [p.model_dump(mode='json') if hasattr(p, 'model_dump') else p for p in pois]
        yield f"data: {json_dumps({'step': 'l3_done', 'pois_found': len(pois), 'locked_count': sum(1 for p in pois if p.is_locked), 'pois': pois_json})}\n\n"

        try:
            plan_result = None
            async for chunk in layer4_client.plan_stream(pois=pois, contract=contract, hotel_fallback=hotel_fallback):
                if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
                    try:
                        data_content = json_lib.loads(chunk[6:].strip())
                        if "days" in data_content or "status" in data_content or "error_code" in data_content:
                            if "error_code" not in data_content and "days" in data_content:
                                data_content = cost_estimator.enrich(data_content, contract, hotel_fallback=hotel_fallback)
                                chunk = f"data: {json_dumps(data_content)}\n\n"
                            plan_result = data_content
                    except Exception:
                        pass
                yield chunk

            if idempotency_key and plan_result:
                await idempotency_manager.set_completed(idempotency_key, plan_result)
        except Exception as e:
            err_payload = {'step': 'error', 'error_code': 'NO_FEASIBLE_ROUTE', 'message': str(e)}
            yield f"data: {json_dumps(err_payload)}\n\n"
            yield "data: [DONE]\n\n"
            if idempotency_key:
                await idempotency_manager.remove(idempotency_key)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/plan_alternatives")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def plan_alternatives(request: Request, body: TripPlanRequest, user: FirebaseUser = Depends(get_current_user)):
    """Generate Balanced / Budget / Chill alternatives via Layer 4 /plan-multi solver. Requires Auth."""
    logger.info(f"🔐 plan_alternatives called by user: {user.uid}")
    try:
        contract, pois, hotel_fallback = await _run_pipeline(body)
        if not pois:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy địa điểm du lịch nào phù hợp với yêu cầu của bạn.",
            )

        result = await layer4_client.plan_alternatives(pois=pois, contract=contract, time_limit=60)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Layer 4 multi-plan solver unavailable",
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"plan_alternatives error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat_process", response_model=ChatProcessResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def chat_process(request: Request, body: ChatProcessRequest, user: Optional[FirebaseUser] = Depends(get_optional_user)):
    """Processes a chat turn conversationally. Supports optional auth for local development."""
    user_uid = user.uid if user else "mock-uid-12345"
    logger.info(f"💬 chat_process called by user: {user_uid}")
    
    if body.current_itinerary:
        body.current_itinerary = await _enrich_itinerary_with_db(body.current_itinerary)
    
    # Ghi log debug ra file để chẩn đoán chính xác
    try:
        with open("/tmp/gateway_debug.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- REQUEST DEBUG ---\n")
            f.write(f"has_draft: {getattr(body, 'has_draft', None)}\n")
            f.write(f"current_itinerary is None: {body.current_itinerary is None}\n")
            if body.current_itinerary:
                f.write(f"current_itinerary keys: {list(body.current_itinerary.keys())}\n")
            f.write(f"body JSON: {body.model_dump_json(indent=2)}\n")
    except Exception as e:
        logger.error(f"Failed to write gateway_debug.log: {e}")
        
    logger.warning(f"DEBUG_PRINT_LOGGER: has_draft={body.has_draft}, current_itinerary_is_none={body.current_itinerary is None}")
    history_dict = [{"role": h.role, "content": h.content} for h in body.history]
    normalized_msg = (body.message or "").strip().lower()
    is_edit_confirmation = bool(
        body.pending_edit_plan
        and llm_service._is_confirmation(body.message)
    )
    is_edit_rejection = bool(
        body.pending_edit_plan
        and any(word in _normalize_text(body.message) for word in (
            "huy", "khong dong y", "khong sua", "giu nguyen", "dont", "cancel", "no", 
            "khong", "tu choi", "bo qua", "keep"
        ))
    )

    if is_edit_confirmation:
        contract_to_use = body.current_contract.model_copy(deep=True)
        operation_dicts = list((body.pending_edit_plan or {}).get("operations") or [])
        import re
        for op in operation_dicts:
            op_type = op.get("type")
            if op_type == "change_budget" and op.get("amount") is not None:
                contract_to_use.budget_max = float(op.get("amount"))
                contract_to_use.budget_is_unlimited = False
                if "budget" not in contract_to_use.confirmed_fields:
                    contract_to_use.confirmed_fields.append("budget")
            elif op_type == "change_pace" and op.get("value") is not None:
                contract_to_use.preferred_pace = op.get("value")
                if "pace" not in contract_to_use.confirmed_fields:
                    contract_to_use.confirmed_fields.append("pace")
            elif op_type == "change_duration":
                raw_val = str(op.get("value") or op.get("target") or "").lower()
                match = re.search(r"(\d+)\s*ngày", raw_val)
                if match:
                    contract_to_use.num_days = int(match.group(1))
                    if "num_days" not in contract_to_use.confirmed_fields:
                        contract_to_use.confirmed_fields.append("num_days")
                elif "thêm một ngày" in raw_val or "thêm 1 ngày" in raw_val or "tăng 1 ngày" in raw_val:
                    contract_to_use.num_days = (contract_to_use.num_days or 1) + 1
                elif "bớt một ngày" in raw_val or "bớt 1 ngày" in raw_val or "giảm 1 ngày" in raw_val:
                    contract_to_use.num_days = max(1, (contract_to_use.num_days or 1) - 1)
            elif op_type == "add_preference" and op.get("target"):
                pref = op.get("target")
                if not contract_to_use.tags:
                    contract_to_use.tags = []
                if pref not in contract_to_use.tags:
                    contract_to_use.tags.append(pref)
                if "interests" not in contract_to_use.confirmed_fields:
                    contract_to_use.confirmed_fields.append("interests")
            elif op_type == "avoid_preference" and op.get("target"):
                avoid = op.get("target")
                if not contract_to_use.avoid_tags:
                    contract_to_use.avoid_tags = []
                if avoid not in contract_to_use.avoid_tags:
                    contract_to_use.avoid_tags.append(avoid)

        result = {
            "status": "ready",
            "reply": "Dạ, em đã cập nhật lịch trình và chi phí theo các thay đổi anh xác nhận rồi ạ.",
            "updated_contract": contract_to_use,
            "phase": "ready",
            "missing_fields": [],
            "next_question": None,
            "requires_confirmation": False,
            "edit_intent": None,
            "pending_edit_plan": None,
        }
    elif is_edit_rejection:
        result = {
            "status": "ready",
            "reply": "Dạ, em đã hủy yêu cầu chỉnh sửa và giữ nguyên lịch trình cũ cho mình ạ.",
            "updated_contract": body.current_contract,
            "phase": "ready",
            "missing_fields": [],
            "next_question": None,
            "requires_confirmation": False,
            "edit_intent": None,
            "pending_edit_plan": None,
        }
    else:
        deterministic_intent = None
        if False and getattr(body, "has_draft", False) and not is_edit_confirmation:
            planned = EditIntentPlanner().build(body.message or "")
            if planned.operations:
                deterministic_intent = planned

        if deterministic_intent is not None:
            pending = deterministic_intent.constraints
            result = {
                "status": "clarifying",
                "reply": pending.get("assistant_reply") or "Em sẽ chuẩn bị chỉnh lịch. Anh xác nhận em sửa nhé?",
                "updated_contract": body.current_contract,
                "phase": "editing",
                "missing_fields": [],
                "next_question": None,
                "requires_confirmation": True,
                "edit_intent": deterministic_intent,
                "pending_edit_plan": pending,
            }
        else:
            result = await llm_service.process_chat_turn(
                message=body.message,
                history=history_dict,
                current_contract=body.current_contract,
                has_draft=getattr(body, "has_draft", False),
                current_itinerary=body.current_itinerary,
            )
    
    updated_itinerary = None
    edit_intent = result.get("edit_intent")
    pending_edit_plan = result.get("pending_edit_plan")
    if getattr(body, "has_draft", False) and not is_edit_rejection:
        deterministic_intent = EditIntentPlanner().build(body.message or "")
        if not is_edit_confirmation and not (edit_intent and getattr(edit_intent, "operations", None)) and deterministic_intent.operations:
            edit_intent = None
            pending_edit_plan = deterministic_intent.constraints
            result["edit_intent"] = deterministic_intent
            result["pending_edit_plan"] = deterministic_intent.constraints
            result["status"] = "clarifying"
            result["phase"] = "editing"
            result["requires_confirmation"] = True
            result["reply"] = deterministic_intent.constraints.get("assistant_reply") or result.get("reply")
    if getattr(body, "has_draft", False) and pending_edit_plan and not is_edit_confirmation and not is_edit_rejection:
        pending_edit_plan = await _attach_edit_suggestions(pending_edit_plan)
        result["pending_edit_plan"] = pending_edit_plan

    if getattr(body, "has_draft", False) and body.current_itinerary and (edit_intent or is_edit_confirmation or is_edit_rejection):
        from app.services.itinerary_editor import ItineraryEditorService
        from app.schemas.trip import POIResponse
        from sqlalchemy import select, or_
        from app.models.poi import PointOfInterest
        from geoalchemy2.functions import ST_AsGeoJSON
        import json as json_lib
        
        editor_service = ItineraryEditorService()
        action = edit_intent.action if edit_intent else "modify_itinerary"
        target = edit_intent.target if edit_intent else None
        should_apply_edit = bool(
            (is_edit_confirmation or (result.get("status") == "ready" and not result.get("requires_confirmation", False)))
            and not is_edit_rejection
        )
        operation_dicts = []
        if is_edit_confirmation:
            operation_dicts = list((body.pending_edit_plan or {}).get("operations") or [])
        elif edit_intent and getattr(edit_intent, "operations", None):
            operation_dicts = [op.model_dump(exclude_none=True) for op in edit_intent.operations]
        elif edit_intent:
            operation_dicts = [{
                "type": action,
                "target": target,
                "target_count": edit_intent.target_count,
                **(edit_intent.constraints or {}),
            }]
        
        try:
            if not should_apply_edit:
                updated_itinerary = None
            elif operation_dicts:
                working_itinerary = body.current_itinerary
                for op in operation_dicts:
                    op_type = op.get("type")
                    op_target = op.get("target") or op.get("query")
                    target_day = op.get("target_day")
                    if isinstance(target_day, int) and target_day < 0:
                        target_day = len((working_itinerary or {}).get("days", []))
                    if op_type == "remove_place" and op_target:
                        working_itinerary = editor_service.remove_stop(
                            itinerary=working_itinerary,
                            target=op_target,
                            target_day=target_day,
                            target_count=int(op.get("target_count") or 999),
                            micro_tags=op.get("target_micro_tags") or [],
                            category=op.get("target_category"),
                        )
                    elif op_type in {"move_place", "change_time"} and op_target:
                        position = op.get("position")
                        moved_itinerary = editor_service.move_stop(
                            itinerary=working_itinerary,
                            target=op_target,
                            target_day=target_day,
                            preferred_time_min=op.get("target_time_min"),
                            after_target=op.get("relative_to") if position == "after" else None,
                            position=position,
                        )
                        if moved_itinerary.get("status") == "warning" and op_type == "move_place":
                            resolved_pois = await _resolve_edit_add_poi(
                                query=op_target,
                                category=op.get("target_category"),
                                micro_tags=op.get("target_micro_tags") or [],
                                time_window=op.get("time_window") or None,
                                limit=1,
                            )
                            if resolved_pois:
                                day_index = max(0, int(target_day or 1) - 1)
                                working_itinerary = editor_service.add_stop(
                                    itinerary=working_itinerary,
                                    day_index=day_index,
                                    poi=resolved_pois[0],
                                    after_target=op.get("relative_to") if position == "after" else None,
                                    preferred_time_min=op.get("target_time_min") or (op.get("time_window") or {}).get("start_min"),
                                    position=position,
                                )
                            else:
                                working_itinerary = moved_itinerary
                        else:
                            working_itinerary = moved_itinerary
                    elif op_type == "swap_places" and op_target and op.get("relative_to"):
                        working_itinerary = editor_service.swap_stops(
                            itinerary=working_itinerary,
                            target_a=op_target,
                            target_b=op.get("relative_to"),
                        )
                    elif op_type == "replace_place" and op_target:
                        resolved_pois = await _resolve_edit_add_poi(
                            query=op.get("query") or op.get("value") or op_target,
                            category=op.get("target_category"),
                            micro_tags=op.get("target_micro_tags") or [],
                            time_window=op.get("time_window") or None,
                            limit=1,
                        )
                        if resolved_pois:
                            working_itinerary = editor_service.replace_stop(
                                itinerary=working_itinerary,
                                old_name=op_target,
                                new_poi=resolved_pois[0],
                                target_day=target_day,
                            )
                    elif op_type == "add_place" and op_target:
                        resolved_pois = await _resolve_edit_add_poi(
                            query=op_target,
                            category=op.get("target_category"),
                            micro_tags=op.get("target_micro_tags") or [],
                            time_window=op.get("time_window") or None,
                            limit=1,
                        )
                        if resolved_pois:
                            day_index = max(0, int(target_day or 1) - 1)
                            working_itinerary = editor_service.add_stop(
                                itinerary=working_itinerary,
                                day_index=day_index,
                                poi=resolved_pois[0],
                                after_target=op.get("relative_to") if op.get("position") == "after" else None,
                                preferred_time_min=op.get("target_time_min") or (op.get("time_window") or {}).get("start_min"),
                                position=op.get("position"),
                            )
                updated_itinerary = working_itinerary
                if is_edit_confirmation:
                    pending_edit_plan = None
            rebuild_actions = {
                "rebuild_requested", "change_budget", "change_pace", 
                "change_duration", "change_time_window", "change_time", "add_preference", 
                "avoid_preference", "change_distribution"
            }
            is_rebuild_in_ops = any(op.get("type") in rebuild_actions for op in operation_dicts) if operation_dicts else False
            if should_apply_edit and (not operation_dicts or is_rebuild_in_ops) and (action in rebuild_actions or is_rebuild_in_ops):
                from app.schemas.trip import TripPlanRequest
                contract_to_use = result.get("updated_contract")
                if not contract_to_use:
                    contract_to_use = body.current_contract
                
                rebuild_req = TripPlanRequest(
                    user_prompt=body.message,
                    num_days=contract_to_use.num_days,
                    budget=contract_to_use.budget_max,
                    destination=contract_to_use.destination or "Huế",
                    hotel_lat=contract_to_use.hotel_lat,
                    hotel_lon=contract_to_use.hotel_lon,
                    hotel_name=contract_to_use.hotel_name,
                    contract=contract_to_use
                )
                
                new_contract, new_pois, hotel_fallback = await _run_pipeline(rebuild_req)
                l4_result = await layer4_client.plan(pois=new_pois, contract=new_contract)
                if l4_result and "error_code" not in l4_result:
                    updated_itinerary = l4_result
                else:
                    logger.error(f"JIT Rebuild solver error: {l4_result}")
            elif should_apply_edit and not operation_dicts and action == "remove_place" and target:
                updated_itinerary = editor_service.remove_stop(
                    itinerary=body.current_itinerary,
                    target=target
                )
                updated_itinerary = editor_service.remove_stop(
                    itinerary=body.current_itinerary,
                    target=target
                )
            elif should_apply_edit and not operation_dicts and action == "add_place" and target:
                resolved_pois = await _resolve_edit_add_poi(query=target, limit=1)
                if resolved_pois:
                    target_day = edit_intent.constraints.get("target_day", 1) if edit_intent is not None else 1
                    try:
                        day_index = max(0, int(target_day) - 1)
                    except (ValueError, TypeError):
                        day_index = 0
                    updated_itinerary = editor_service.add_stop(
                        itinerary=body.current_itinerary,
                        day_index=day_index,
                        poi=resolved_pois[0],
                    )
            elif should_apply_edit and not operation_dicts and action == "replace_place" and target:
                new_place_query = body.message
                import re as re_lib
                parts = re_lib.split(r'(?i)\s+bằng\s+|\s+thành\s+|\s+with\s+|\s+to\s+', body.message)
                if len(parts) > 1:
                    new_place_query = parts[1]
                
                POI = PointOfInterest
                stmt = select(POI, ST_AsGeoJSON(POI.coordinates).label("geojson")).where(
                    or_(
                        POI.name.ilike(f"%{new_place_query.strip()}%"),
                        POI.category.ilike(f"%{new_place_query.strip()}%"),
                    )
                ).order_by(POI.priority_score.desc()).limit(1)
                
                async with AsyncSessionFactory() as db_session:
                    db_res = await db_session.execute(stmt)
                    row = db_res.first()
                    if row:
                        poi_obj = row.PointOfInterest
                        geojson = json_lib.loads(row.geojson) if row.geojson else None
                        lat = geojson["coordinates"][1] if geojson else 0.0
                        lon = geojson["coordinates"][0] if geojson else 0.0
                        
                        poi_resp = POIResponse(
                            uuid=poi_obj.uuid,
                            name=poi_obj.name,
                            category=poi_obj.category,
                            description=poi_obj.description,
                            latitude=lat,
                            longitude=lon,
                            visit_duration_min=poi_obj.visit_duration_min,
                            price=poi_obj.price,
                            entrance_fee=poi_obj.entrance_fee,
                            open_time=poi_obj.open_time,
                            close_time=poi_obj.close_time,
                            priority_score=poi_obj.priority_score,
                            tags=poi_obj.tags,
                        )
                        
                        updated_itinerary = editor_service.replace_stop(
                            itinerary=body.current_itinerary,
                            old_name=target,
                            new_poi=poi_resp
                        )
        except Exception as ex:
            logger.error(f"JIT Editing failed: {ex}", exc_info=True)
            
    if updated_itinerary and isinstance(updated_itinerary, dict):
        contract_for_enrichment = result.get("updated_contract") or body.current_contract
        if contract_for_enrichment:
            updated_itinerary = CostEstimatorService().enrich(updated_itinerary, contract_for_enrichment, hotel_fallback=False) or updated_itinerary

        budget_total = updated_itinerary.get("budget_total") or (contract_for_enrichment.budget_max if contract_for_enrichment else None)
        budget_used = updated_itinerary.get("budget_used", 0) or updated_itinerary.get("total_entrance_fee", 0)
        
        if budget_total and budget_used > budget_total:
            warning_msg = f"\n\n⚠️ *Lưu ý*: Việc chỉnh sửa này làm tổng chi phí vé tham quan ({int(budget_used):,}đ) vượt quá ngân sách ban đầu của bạn ({int(budget_total):,}đ) một chút nhé."
            if not result["reply"].endswith(warning_msg):
                result["reply"] += warning_msg
            
    return ChatProcessResponse(
        status=result["status"],
        reply=result["reply"],
        updated_contract=result["updated_contract"],
        phase=result.get("phase"),
        missing_fields=result.get("missing_fields", []),
        next_question=result.get("next_question"),
        requires_confirmation=result.get("requires_confirmation", False),
        edit_intent=edit_intent,
        pending_edit_plan=pending_edit_plan,
        updated_itinerary=updated_itinerary,
    )


@router.get("/health")
async def health():
    return {"status": "ready", "service": "Layer 2&3 Gateway"}


@router.get("/search_pois", response_model=List[POIResponse])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def search_pois_endpoint(request: Request, query: str, limit: int = 5, user: FirebaseUser = Depends(get_current_user)):
    """Tìm kiếm POI thông minh theo vector similarity (tags_vector) hỗ trợ thao tác Add/Replace POI. Tự động fallback sang SQL search nếu offline/lỗi API."""
    from sqlalchemy import select, or_, func
    from app.models.poi import PointOfInterest
    from geoalchemy2.functions import ST_AsGeoJSON
    import json as json_lib
    import re
    
    POI = PointOfInterest
    
    # 1. Thử nghiệm tìm kiếm bằng Vector Embedding (Semantic Search)
    query_vector = None
    if query.strip():
        try:
            query_vector = await embed_service.aembed_text(query.strip())
        except Exception as e:
            logger.error(f"Semantic vector search embedding failure: {e}")
            
    # 2. Xây dựng câu lệnh truy vấn
    if query_vector is not None:
        # Nếu lấy được vector, sắp xếp theo khoảng cách cosine (cosine distance)
        stmt = select(
            POI, ST_AsGeoJSON(POI.coordinates).label("geojson")
        ).order_by(
            POI.tags_vector.cosine_distance(query_vector),
            POI.priority_score.desc()
        ).limit(limit)
    else:
        # Hướng xử lý dự phòng: SQL fallback kết hợp xếp hạng mềm bằng Python
        query_norm = query.strip()
        words = _normalize_and_tokenize(query_norm)
        
        search_words = set()
        for w in words:
            search_words.add(w)
            search_words.add(_normalize_text(w))
            for raw_w in query_norm.lower().split():
                if _normalize_text(raw_w) == w:
                    search_words.add(raw_w)
            for syn in VIETNAMESE_SYNONYMS.get(w, []):
                search_words.add(syn)
                search_words.add(_normalize_text(syn))
                
        conditions = []
        for sw in search_words:
            conditions.append(POI.name.ilike(f"%{sw}%"))
            conditions.append(POI.category.ilike(f"%{sw}%"))
            conditions.append(func.coalesce(func.array_to_string(POI.tags, ','), '').ilike(f"%{sw}%"))
            conditions.append(POI.description.ilike(f"%{sw}%"))
            
        if not conditions:
            return []
            
        stmt = select(
            POI, ST_AsGeoJSON(POI.coordinates).label("geojson")
        ).where(or_(*conditions)).order_by(POI.priority_score.desc()).limit(200)
        
    async with AsyncSessionFactory() as db_session:
        result = await db_session.execute(stmt)
        rows = result.all()
        
        pois = []
        for row in rows:
            poi = row.PointOfInterest
            geojson = json_lib.loads(row.geojson) if row.geojson else None
            lat = geojson["coordinates"][1] if geojson else 0.0
            lon = geojson["coordinates"][0] if geojson else 0.0
            pois.append((poi, lat, lon))
            
    # Áp dụng bộ lọc xếp hạng mềm bằng Python cho cơ chế SQL fallback
    if query_vector is None and query.strip():
        ranked = []
        query_norm_clean = query.strip().lower()
        query_tokens = _normalize_and_tokenize(query_norm_clean)
        
        for poi, lat, lon in pois:
            poi_name = (poi.name or "").lower()
            poi_desc = (poi.description or "").lower()
            poi_cat = (poi.category or "").lower()
            poi_tags = _clean_and_norm_tags(poi.tags)
            
            score = 0.0
            
            norm_name = _normalize_text(poi.name)
            norm_query = _normalize_text(query_norm_clean)
            if norm_query == norm_name:
                score += 15.0
            elif norm_query in norm_name:
                score += 8.0
                
            name_tokens = _normalize_and_tokenize(poi.name)
            desc_tokens = _normalize_and_tokenize(poi.description)
            cat_tokens = _normalize_and_tokenize(poi.category)
            
            score += _token_match_score(query_tokens, name_tokens) * 3.0
            score += _token_match_score(query_tokens, poi_tags) * 2.0
            score += _token_match_score(query_tokens, cat_tokens) * 1.5
            score += _token_match_score(query_tokens, desc_tokens) * 0.5
            score += float(poi.priority_score or 0.0) * 0.1
            
            if score > 0.1:
                ranked.append((score, poi, lat, lon))
                
        ranked.sort(key=lambda x: x[0], reverse=True)
        pois_to_return = ranked[:limit]
    else:
        pois_to_return = [(poi.priority_score, poi, lat, lon) for poi, lat, lon in pois]
        
    return [
        POIResponse(
            uuid=poi.uuid,
            name=poi.name,
            category=poi.category,
            description=poi.description,
            latitude=lat,
            longitude=lon,
            visit_duration_min=poi.visit_duration_min,
            price=poi.price,
            entrance_fee=poi.entrance_fee,
            open_time=poi.open_time,
            close_time=poi.close_time,
            priority_score=poi.priority_score,
            tags=poi.tags,
            is_locked=False,
        )
        for _, poi, lat, lon in pois_to_return
    ]


@router.post("/re_route")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def re_route(request: Request, body: MobileReRouteRequest, user: FirebaseUser = Depends(get_current_user)):
    """Proxy re-route request from mobile to Layer 4. Requires Firebase Auth."""
    logger.info(f"🔄 re_route called by user: {user.uid}")
    try:
        if body.original_itinerary:
            body.original_itinerary = await _enrich_itinerary_with_db(body.original_itinerary)
            
            # Enrich new POIs that are in remaining_poi_ids but not in original_itinerary stops
            if body.remaining_poi_ids:
                existing_poi_ids = set()
                days = body.original_itinerary.get("days", [])
                target_day = None
                for d in days:
                    if d.get("day_index") == body.day_index:
                        target_day = d
                        break
                if target_day is None and days:
                    target_day = days[min(body.day_index, len(days) - 1)]
                
                if target_day is not None:
                    for stop in target_day.get("stops", []):
                        pid = stop.get("poi_id") or stop.get("poiId")
                        if pid:
                            existing_poi_ids.add(str(pid))
                    
                    new_poi_ids = [pid for pid in body.remaining_poi_ids if pid not in existing_poi_ids and not pid.startswith("__")]
                    
                    valid_new_poi_ids = []
                    for pid in new_poi_ids:
                        try:
                            uuid.UUID(str(pid))
                            valid_new_poi_ids.append(str(pid))
                        except ValueError:
                            continue
                            
                    if valid_new_poi_ids:
                        logger.info(f"🔍 Found new POI IDs to enrich in re-route: {valid_new_poi_ids}")
                        from app.models.poi import PointOfInterest
                        from geoalchemy2.functions import ST_AsGeoJSON
                        from sqlalchemy import select
                        import json as json_lib
                        
                        POI = PointOfInterest
                        stmt = select(POI, ST_AsGeoJSON(POI.coordinates).label("geojson")).where(POI.uuid.in_(valid_new_poi_ids))
                        
                        async with AsyncSessionFactory() as db_session:
                            res = await db_session.execute(stmt)
                            rows = res.all()
                            
                            for poi, geojson_str in rows:
                                geojson = json_lib.loads(geojson_str) if geojson_str else None
                                lat = geojson["coordinates"][1] if geojson else 0.0
                                lon = geojson["coordinates"][0] if geojson else 0.0
                                
                                new_stop = {
                                    "poi_id": str(poi.uuid),
                                    "poi_name": poi.name,
                                    "category": poi.category,
                                    "description": poi.description or "",
                                    "tags": poi.tags or [],
                                    "entrance_fee": poi.entrance_fee or poi.price or 0.0,
                                    "price": poi.entrance_fee or poi.price or 0.0,
                                    "visit_duration_min": poi.visit_duration_min or 60,
                                    "location": {
                                        "latitude": lat,
                                        "longitude": lon
                                    }
                                }
                                target_day.setdefault("stops", []).append(new_stop)
                                logger.info(f"✨ Successfully enriched target_day with new JIT POI: {poi.name}")
        is_manual = body.is_manual or (body.day_index + 1) in body.original_itinerary.get("manualDayNumbers", [])
        result = await layer4_client.re_route(
            current_lat=body.current_lat,
            current_lon=body.current_lon,
            current_time_min=body.current_time_min,
            remaining_poi_ids=body.remaining_poi_ids,
            original_itinerary=body.original_itinerary,
            day_index=body.day_index,
            excluded_poi_ids=body.excluded_poi_ids,
            is_manual=is_manual,
        )

        if result is None:
            return ReRouteResponse(
                status="error",
                message="Layer 4 solver unavailable or returned no result",
            )

        solver_status = result.get("status", "success")
        
        day_result = None
        if solver_status in ["success", "optimized_with_warning"] and "stops" in result:
            try:
                from copy import deepcopy
                updated_itinerary = deepcopy(body.original_itinerary)
                days = updated_itinerary.get("days", [])
                target_day_idx = None
                for idx, d in enumerate(days):
                    if d.get("day_index") == body.day_index or d.get("dayNumber") == body.day_index + 1:
                        target_day_idx = idx
                        break
                if target_day_idx is None and days:
                    target_day_idx = min(body.day_index, len(days) - 1)
                    
                if target_day_idx is not None:
                    # Update stops in the targeted day
                    days[target_day_idx]["stops"] = result["stops"]
                    
                    # 2. Reconstruct the contract
                    contract_dict = (
                        body.original_itinerary.get("llm_contract")
                        or body.original_itinerary.get("llmContract")
                        or {}
                    )
                    contract = LLMDataContract(**contract_dict)
                    
                    # 3. Enrich the entire itinerary
                    enriched = CostEstimatorService().enrich(updated_itinerary, contract)
                    if enriched and "days" in enriched:
                        day_result = enriched["days"][target_day_idx]
                        
                        # Preserve status, message and day_index
                        day_result["status"] = solver_status
                        day_result["message"] = result.get("message")
                        day_result["day_index"] = body.day_index
                    else:
                        day_result = result
                else:
                    day_result = result
            except Exception as enrich_error:
                logger.error(f"Failed to enrich re-route result: {enrich_error}")
                day_result = result
        else:
            day_result = result

        return ReRouteResponse(
            status=solver_status, 
            day=day_result if solver_status in ["success", "optimized_with_warning"] else None,
            message=result.get("message")
        )


    except Exception as e:
        logger.error(f"Re-route proxy error: {e}")
        return ReRouteResponse(status="error", message=str(e))
