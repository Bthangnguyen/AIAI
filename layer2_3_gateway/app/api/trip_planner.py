"""Orchestrator API: Text → L2 → L3 → L4 pipeline (JSON + SSE streaming).

PRODUCTION-HARDENED ARCHITECTURE:
- DB I/O ISOLATION: LLM + Embedding calls (2-5s) execute OUTSIDE any DB session.
  DB session only opens for the 50ms spatial query then immediately returns to pool.
- ZERO Depends(get_db): Both endpoints use _run_pipeline() which owns its own session.
- Pool cannot be exhausted by LLM latency or L4 solve time under ANY load.
"""

import json as json_lib
from typing import List
from fastapi import APIRouter, HTTPException, status, Request
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

router = APIRouter(prefix="/v1/trip")
logger = AppLogger().get_logger()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Service singletons (stateless, thread-safe)
llm_service = LLMExtractorService()
spatial_service = SpatialFilterService()
layer4_client = Layer4Client()
embed_service = EmbeddingService()


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


def _apply_request_overrides(contract: LLMDataContract, request: TripPlanRequest) -> LLMDataContract:
    """Apply explicit API fields after extraction, or after receiving a confirmed contract."""
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
) -> tuple[LLMDataContract, List[POIResponse]]:
    """L2 → Embed → L3 pipeline with TOTAL DB I/O isolation."""
    logger.info(f"🚀 _run_pipeline STARTED for prompt: {request.user_prompt}")
    # ──── PHASE A: NETWORK I/O (NO DB SESSION) ────
    if request.contract is not None:
        contract = request.contract.model_copy(deep=True)
        logger.info("Using confirmed contract from request; skipping LLM extraction")
    else:
        contract = await llm_service.extract_intent(
            user_prompt=request.user_prompt,
            hotel_lat=request.hotel_lat,
            hotel_lon=request.hotel_lon,
            hotel_name=request.hotel_name,
            num_days=request.num_days or 1,
        )

    contract = _apply_request_overrides(contract, request)

    query_vector = None
    if contract.tags:
        tag_text = embed_service.build_poi_text(
            name="query", category="preference",
            tags=contract.tags, description="",
        )
        try:
            query_vector = await embed_service.aembed_text(tag_text)
        except Exception as e:
            logger.warning(f"Embedding failed, falling back to priority_score: {e}")

    # ──── PHASE B: DATABASE I/O (FLASH OPEN/CLOSE ~50ms) ────
    async with AsyncSessionFactory() as db_session:
        # Select hotel if missing
        if contract.hotel_lat is None or contract.hotel_lon is None:
            from sqlalchemy import select
            from geoalchemy2.functions import ST_AsGeoJSON
            from app.models.poi import PointOfInterest
            import json as json_lib
            
            POI = PointOfInterest
            # Dùng category là "Khách sạn" hoặc tên có chữ hotel
            stmt = select(POI.name, ST_AsGeoJSON(POI.coordinates).label("geojson")).where(
                POI.category.ilike("%Khách sạn%")
            )
            if contract.budget_max:
                # hotel price heuristic: <= 30% of total budget
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

    return contract, pois


@router.post("/plan_trip", response_model=TripPlanResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def plan_trip(request: Request, body: TripPlanRequest):
    """Full pipeline (JSON): Text → LLM → Spatial → OR-Tools."""
    contract, pois = await _run_pipeline(body)

    if not pois:
        return TripPlanResponse(
            status="error", llm_contract=contract, pois=[],
            message="No POIs found matching your criteria.",
        )

    locked_count = sum(1 for p in pois if p.is_locked)
    l4_result = await layer4_client.plan(pois=pois, contract=contract)

    return TripPlanResponse(
        status="success" if l4_result else "partial",
        llm_contract=contract, pois=pois,
        locked_pois=locked_count, layer4_result=l4_result,
        message="Route optimized" if l4_result else "Route optimization unavailable",
    )


@router.post("/plan_trip_stream")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def plan_trip_stream(request: Request, body: TripPlanRequest):
    """SSE streaming: pushes route chunks to Mobile App in real-time."""
    logger.info(f"📡 SSE REQUEST RECEIVED: plan_trip_stream from {request.client.host}")
    contract, pois = await _run_pipeline(body)

    async def event_generator():
        yield f"data: {json_lib.dumps({'step': 'l2_done', 'tags': contract.tags, 'locked': contract.locked_pois})}\n\n"

        if not pois:
            yield f"data: {json_lib.dumps({'step': 'error', 'message': 'No POIs found'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        yield f"data: {json_lib.dumps({'step': 'l3_done', 'pois_found': len(pois), 'locked_count': sum(1 for p in pois if p.is_locked)})}\n\n"

        try:
            async for chunk in layer4_client.plan_stream(pois=pois, contract=contract):
                yield chunk
        except Exception as e:
            yield f"data: {json_lib.dumps({'step': 'error', 'message': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat_process", response_model=ChatProcessResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def chat_process(request: Request, body: ChatProcessRequest):
    """Processes a chat turn to build travel contract parameters step-by-step."""
    # Convert history schema to dict list expected by service
    history_dict = [{"role": h.role, "content": h.content} for h in body.history]
    
    result = await llm_service.process_chat_turn(
        message=body.message,
        history=history_dict,
        current_contract=body.current_contract,
        has_draft=body.has_draft,
    )
    
    return ChatProcessResponse(**result)


@router.get("/health")
async def health():
    return {"status": "ready", "service": "Layer 2&3 Gateway"}


@router.get("/search_pois", response_model=List[POIResponse])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def search_pois_endpoint(request: Request, query: str, limit: int = 5):
    """Tìm kiếm POI theo tên để hỗ trợ thao tác Add POI."""
    from sqlalchemy import select
    from app.models.poi import PointOfInterest
    from geoalchemy2.functions import ST_AsGeoJSON
    import json as json_lib
    
    POI = PointOfInterest
    stmt = select(
        POI, ST_AsGeoJSON(POI.coordinates).label("geojson")
    ).where(POI.name.ilike(f"%{query}%")).limit(limit)
    
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
async def re_route(request: Request, body: MobileReRouteRequest):
    """Proxy re-route request from mobile to Layer 4.

    Mobile sends current GPS + remaining POI IDs + original itinerary.
    Gateway extracts POI data and forwards to Layer 4 /re-route solver.
    """
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

        # Lấy status thực tế từ solver (vd: infeasible, optimized_with_warning)
        solver_status = result.get("status", "success")
        
        return ReRouteResponse(
            status=solver_status, 
            day=result if solver_status in ["success", "optimized_with_warning"] else None,
            message=result.get("message")
        )

    except Exception as e:
        logger.error(f"Re-route proxy error: {e}")
        return ReRouteResponse(status="error", message=str(e))

