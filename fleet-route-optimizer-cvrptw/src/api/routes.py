"""API route handlers for Travel Optimizer routing engine."""

import asyncio
from fastapi import APIRouter, HTTPException, Body, Query, Depends

from ..models.api import TravelPlanRequest, ReRouteRequest
from ..models.domain import TravelItinerary, TravelItineraryDay
from ..services.travel_plan_service import TravelPlanService
from ..config import get_logger
from .dependencies import verify_api_key

logger = get_logger(__name__)
router = APIRouter()

# Singleton service instance
travel_service = TravelPlanService()


@router.get('/health')
async def health_check():
    """
    Health check endpoint.
    
    Returns 'ready' if solver is not running, 'busy' otherwise.
    """
    if travel_service.is_busy():
        return {"status": "busy", "message": "Solver is currently running"}
    return {"status": "ready"}


@router.post('/plan', response_model=TravelItinerary)
async def plan_travel_endpoint(
    request: TravelPlanRequest = Body(...),
    time_limit: int = Query(30, description="Solver time limit per day", ge=1, le=600),
    solver: str = Query("ortools", description="Solver type"),
    _: None = Depends(verify_api_key)
):
    """
    Create optimized multi-day travel itinerary (async).

    Accepts POIs, hotels, and constraints from Layer 3.
    Uses asyncio.to_thread to avoid blocking the event loop.
    Returns optimized per-day routes with timing and costs.
    """
    try:
        result = await asyncio.to_thread(
            travel_service.plan,
            request=request,
            time_limit_per_day=time_limit,
            solver_type=solver,
        )
        return result
    except ValueError as e:
        # Solver busy
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Error during travel planning")
        raise HTTPException(status_code=500, detail=f"Planning error: {str(e)}")


@router.post('/re-route', response_model=TravelItineraryDay)
async def re_route_endpoint(
    request: ReRouteRequest = Body(...),
    time_limit: int = Query(15, description="Solver time limit in seconds", ge=1, le=120),
    solver: str = Query("ortools", description="Solver type"),
    _: None = Depends(verify_api_key)
):
    """
    Re-route remaining POIs from current location (JIT).

    Used when a traveler needs to recalculate their route mid-day,
    e.g. due to traffic changes detected by Mapbox Live Traffic.
    Creates a virtual depot at current_location and optimizes
    the route for remaining unvisited POIs.
    """
    try:
        result = await asyncio.to_thread(
            travel_service.re_route,
            request=request,
            time_limit=time_limit,
            solver_type=solver,
        )
        return result
    except ValueError as e:
        # Solver busy
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Error during re-routing")
        raise HTTPException(status_code=500, detail=f"Re-routing error: {str(e)}")
