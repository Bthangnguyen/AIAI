"""API route handlers for Travel Optimizer routing engine."""

import asyncio
from fastapi import APIRouter, HTTPException, Body, Query, Depends

from ..models.api import TravelPlanRequest, ReRouteRequest
from ..models.domain import TravelItinerary, TravelItineraryDay
from ..models import SolverException, ErrorCode
from ..services.travel_plan_service import TravelPlanService
from ..services.multi_planner import MultiPlanner
from ..config import get_logger
from .dependencies import verify_api_key

logger = get_logger(__name__)
router = APIRouter()

# Singleton service instances
travel_service = TravelPlanService()
multi_planner = MultiPlanner()


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
            time_limit=time_limit,
            solver_type=solver,
        )
        return result
    except SolverException as e:
        raise HTTPException(
            status_code=400,
            detail={"error_code": e.error_code.value, "message": e.message}
        )
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
    except SolverException as e:
        raise HTTPException(
            status_code=400,
            detail={"error_code": e.error_code.value, "message": e.message}
        )
    except ValueError as e:
        # Solver busy
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Error during re-routing")
        raise HTTPException(status_code=500, detail=f"Re-routing error: {str(e)}")


@router.post('/plan-multi')
async def plan_multi_endpoint(
    request: TravelPlanRequest = Body(...),
    time_limit: int = Query(30, description="Solver time limit per plan", ge=1, le=600),
    solver: str = Query("ortools", description="Solver type"),
    styles: str = Query("balanced,budget,chill", description="Comma-separated plan styles"),
    _: None = Depends(verify_api_key)
):
    """
    Generate 3 alternative travel plans with different optimization profiles.

    - **balanced**: Standard optimization (most POIs, balanced fatigue)
    - **budget**: Prioritize free/cheap POIs, tighter budget
    - **chill**: Fewer POIs, more rest, lower fatigue limit

    Anti-overlap: each subsequent plan reduces priority of already-used POIs by 25%.
    """
    try:
        from ..models.domain import TransportMode

        style_list = [s.strip() for s in styles.split(",")]

        # Build base inputs for MultiPlanner
        day_plans = request.day_plans or travel_service._generate_day_plans(request)
        travel_service._resolve_hotel_transfers(day_plans, request.hotels)

        # Prefetch distance matrix
        all_locs = [h.location for h in request.hotels] + [p.location for p in request.pois]
        mode = request.constraints.transport_modes[0] if request.constraints.transport_modes else TransportMode.TAXI
        matrix = travel_service.distance_cache.build_matrix(all_locs, mode)

        # Use MultiPlanner
        plans = await asyncio.to_thread(
            multi_planner.plan_alternatives,
            base_pois=list(request.pois),
            base_hotels=request.hotels,
            base_days=day_plans,
            solve_func=travel_service.solver.solve_trip,
            styles=style_list,
            matrix=matrix,
            solver_type=solver,
        )

        # Serialize results
        results = []
        for plan in plans:
            days_data = [d.model_dump() for d in plan["days"]] if plan.get("days") else []
            results.append({
                "style": plan["style"],
                "label": plan["label"],
                "description": plan["description"],
                "num_days": len(days_data),
                "days": days_data,
                "total_pois": sum(len(d.get("stops", [])) for d in days_data),
                "overlap_warning": plan.get("overlap_warning"),
            })

        return {"status": "success", "plans": results, "num_plans": len(results)}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Error during multi-plan generation")
        raise HTTPException(status_code=500, detail=f"Multi-plan error: {str(e)}")
