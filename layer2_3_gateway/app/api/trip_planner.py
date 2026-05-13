"""Orchestrator API: Text → L2 → L3 → L4 pipeline (JSON + SSE streaming).

PRODUCTION-HARDENED ARCHITECTURE:
- DB I/O ISOLATION: LLM + Embedding calls (2-5s) execute OUTSIDE any DB session.
  DB session only opens for the 50ms spatial query then immediately returns to pool.
- ZERO Depends(get_db): Both endpoints use _run_pipeline() which owns its own session.
- Pool cannot be exhausted by LLM latency or L4 solve time under ANY load.
"""

import json as json_lib
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import StreamingResponse

from app.database import AsyncSessionFactory
from app.schemas.trip import TripPlanRequest, TripPlanResponse, LLMDataContract, POIResponse
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


async def _run_pipeline(
    request: TripPlanRequest,
) -> tuple[LLMDataContract, List[POIResponse]]:
    """L2 → Embed → L3 pipeline with TOTAL DB I/O isolation."""
    # ──── PHASE A: NETWORK I/O (NO DB SESSION) ────
    contract = await llm_service.extract_intent(
        user_prompt=request.user_prompt,
        hotel_lat=request.hotel_lat,
        hotel_lon=request.hotel_lon,
        hotel_name=request.hotel_name,
        num_days=request.num_days,
    )

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
            status="error", llm_contract=contract, pois_found=0,
            message="No POIs found matching your criteria.",
        )

    locked_count = sum(1 for p in pois if p.is_locked)
    l4_result = await layer4_client.plan(pois=pois, contract=contract)

    return TripPlanResponse(
        status="success" if l4_result else "partial",
        llm_contract=contract, pois_found=len(pois),
        locked_pois=locked_count, layer4_result=l4_result,
        message="Route optimized" if l4_result else "Route optimization unavailable",
    )


@router.post("/plan_trip_stream")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def plan_trip_stream(request: Request, body: TripPlanRequest):
    """SSE streaming: pushes route chunks to Mobile App in real-time."""
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


@router.get("/health")
async def health():
    return {"status": "ready", "service": "Layer 2&3 Gateway"}


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

        return ReRouteResponse(status="success", day=result)

    except Exception as e:
        logger.error(f"Re-route proxy error: {e}")
        return ReRouteResponse(status="error", message=str(e))

