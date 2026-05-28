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
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.responses import StreamingResponse

from app.database import AsyncSessionFactory
from app.schemas.trip import TripPlanRequest, TripPlanResponse, LLMDataContract, POIResponse, ChatProcessRequest, ChatProcessResponse
from app.schemas.re_route import MobileReRouteRequest, ReRouteResponse
from app.services.llm_extractor import LLMExtractorService
from app.services.spatial_filter import SpatialFilterService
from app.services.layer4_client import Layer4Client
from app.services.embedding_service import EmbeddingService
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

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Service singletons (stateless, thread-safe)
llm_service = LLMExtractorService()
spatial_service = SpatialFilterService()
layer4_client = Layer4Client()
embed_service = EmbeddingService()


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

    # Vague intent fallback heuristics
    is_empty_tags = not contract.tags or contract.tags == ["general"]
    is_empty_locked = not contract.locked_pois
    is_empty_vibe_and_type = not contract.vibe and not contract.trip_type
    
    if is_empty_tags and is_empty_locked and is_empty_vibe_and_type:
        contract.tags = ["culture", "street_food", "sightseeing"]
        contract.vibe = "chill"
        contract.trip_type = "mixed"
        logger.info("Vague intent detected for Hue. Applying high-quality default preferences.")

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
    if contract.tags:
        if getattr(contract, "distribution_description", None):
            tag_text = embed_service.build_distribution_query_text(
                distribution_description=contract.distribution_description,
                tags=contract.tags,
                destination=contract.destination or "Huế"
            )
        else:
            tag_text = embed_service.build_poi_text(
                name="query", category="preference",
                tags=contract.tags, description="",
            )
        try:
            query_vector = await embed_service.aembed_text(tag_text)
        except Exception as e:
            logger.warning(f"Embedding failed, falling back to priority_score: {e}")

    # ──── PHASE B: DATABASE I/O (FLASH OPEN/CLOSE ~50ms) ────
    hotel_fallback = False
    async with AsyncSessionFactory() as db_session:
        if contract.hotel_lat is None or contract.hotel_lon is None:
            hotel_fallback = True
            from sqlalchemy import select
            from geoalchemy2.functions import ST_AsGeoJSON
            from app.models.poi import PointOfInterest
            import json as json_lib
            
            POI = PointOfInterest
            stmt = select(POI.name, ST_AsGeoJSON(POI.coordinates).label("geojson")).where(
                POI.category.ilike("%Khách sạn%")
            )
            if contract.budget_max:
                stmt = stmt.where(POI.price <= contract.budget_max * 0.3)
            stmt = stmt.order_by(POI.priority_score.desc()).limit(1)
            
            result = await db_session.execute(stmt)
            row = result.first()
            if row:
                contract.hotel_name = row.name
                geojson = json_lib.loads(row.geojson)
                contract.hotel_lon = geojson["coordinates"][0]
                contract.hotel_lat = geojson["coordinates"][1]
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
                yield chunk
                if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
                    try:
                        data_content = json_lib.loads(chunk[6:].strip())
                        if "days" in data_content or "status" in data_content or "error_code" in data_content:
                            plan_result = data_content
                    except Exception:
                        pass

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
    
    result = await llm_service.process_chat_turn(
        message=body.message,
        history=history_dict,
        current_contract=body.current_contract,
        has_draft=getattr(body, "has_draft", False),
    )
    
    updated_itinerary = None
    edit_intent = result.get("edit_intent")
    
    if getattr(body, "has_draft", False) and body.current_itinerary and edit_intent:
        from app.services.itinerary_editor import ItineraryEditorService
        from app.schemas.trip import POIResponse
        from sqlalchemy import select, or_
        from app.models.poi import PointOfInterest
        from geoalchemy2.functions import ST_AsGeoJSON
        import json as json_lib
        
        editor_service = ItineraryEditorService()
        action = edit_intent.action
        target = edit_intent.target
        
        try:
            rebuild_actions = {
                "rebuild_requested", "change_budget", "change_pace", 
                "change_time_window", "change_time", "add_preference", 
                "avoid_preference", "change_distribution"
            }
            if action in rebuild_actions:
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
            elif action == "remove_place" and target:
                updated_itinerary = editor_service.remove_stop(
                    itinerary=body.current_itinerary,
                    target=target
                )
            elif action == "add_place" and target:
                POI = PointOfInterest
                stmt = select(POI, ST_AsGeoJSON(POI.coordinates).label("geojson")).where(
                    or_(
                        POI.name.ilike(f"%{target.strip()}%"),
                        POI.category.ilike(f"%{target.strip()}%"),
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
                        
                        target_day = edit_intent.constraints.get("target_day", 1)
                        try:
                            day_index = max(0, int(target_day) - 1)
                        except (ValueError, TypeError):
                            day_index = 0
                        updated_itinerary = editor_service.add_stop(
                            itinerary=body.current_itinerary,
                            day_index=day_index,
                            poi=poi_resp
                        )
            elif action == "replace_place" and target:
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
            
    return ChatProcessResponse(
        status=result["status"],
        reply=result["reply"],
        updated_contract=result["updated_contract"],
        phase=result.get("phase"),
        edit_intent=edit_intent,
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
        # Hướng xử lý dự phòng: Làm sạch câu tiếng Việt và tìm kiếm SQL substring
        clean_query = query.strip()
        prefixes = [
            r"^(quán|tiệm|cửa hàng|nhà hàng|địa điểm|điểm|món|quán ăn|ăn|uống)\s+",
            r"^(quán|tiệm|cửa hàng|nhà hàng|địa điểm|điểm|món|quán ăn|ăn|uống)\s+bán\s+"
        ]
        for prefix in prefixes:
            clean_query = re.sub(prefix, "", clean_query, flags=re.IGNORECASE)
        clean_query = clean_query.strip()
        
        conditions = []
        if query.strip():
            conditions.append(POI.name.ilike(f"%{query.strip()}%"))
        if clean_query and clean_query != query.strip():
            conditions.append(POI.name.ilike(f"%{clean_query}%"))
        if clean_query:
            conditions.append(POI.category.ilike(f"%{clean_query}%"))
            conditions.append(func.coalesce(func.array_to_string(POI.tags, ','), '').ilike(f"%{clean_query}%"))
            
        if not conditions:
            return []
            
        stmt = select(
            POI, ST_AsGeoJSON(POI.coordinates).label("geojson")
        ).where(or_(*conditions)).order_by(POI.priority_score.desc()).limit(limit)
        
    async with AsyncSessionFactory() as db_session:
        result = await db_session.execute(stmt)
        rows = result.all()
        
        pois = []
        for row in rows:
            poi = row.PointOfInterest
            geojson = json_lib.loads(row.geojson) if row.geojson else None
            lat = geojson["coordinates"][1] if geojson else 0.0
            lon = geojson["coordinates"][0] if geojson else 0.0
            
            pois.append(POIResponse(
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
            ))
        return pois


@router.post("/re_route")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def re_route(request: Request, body: MobileReRouteRequest, user: FirebaseUser = Depends(get_current_user)):
    """Proxy re-route request from mobile to Layer 4. Requires Firebase Auth."""
    logger.info(f"🔄 re_route called by user: {user.uid}")
    try:
        result = await layer4_client.re_route(
            current_lat=body.current_lat,
            current_lon=body.current_lon,
            current_time_min=body.current_time_min,
            remaining_poi_ids=body.remaining_poi_ids,
            original_itinerary=body.original_itinerary,
            day_index=body.day_index,
            excluded_poi_ids=body.excluded_poi_ids,
        )

        if result is None:
            return ReRouteResponse(
                status="error",
                message="Layer 4 solver unavailable or returned no result",
            )

        solver_status = result.get("status", "success")
        return ReRouteResponse(
            status=solver_status, 
            day=result if solver_status in ["success", "optimized_with_warning"] else None,
            message=result.get("message")
        )

    except Exception as e:
        logger.error(f"Re-route proxy error: {e}")
        return ReRouteResponse(status="error", message=str(e))
