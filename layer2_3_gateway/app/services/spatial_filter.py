"""Layer 3: Spatial & Semantic POI filter with multi-tier fallback.

Accepts a pre-computed query_vector from the Orchestrator (v5) to enable
real vector similarity search instead of falling back to priority_score.
"""

import logging
from typing import List, Optional
from sqlalchemy import select, func, and_, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_AsGeoJSON
from geoalchemy2.types import Geography  # Only for casting center point

from app.models.poi import PointOfInterest
from app.schemas.trip import LLMDataContract, POIResponse
from app.services.utility_scorer import UtilityScorer

logger = logging.getLogger(__name__)

# Fallback tiers: (radius_km, apply_budget, apply_tags)
FALLBACK_TIERS = [
    (None, True, True),    # Tier 1: Original radius + budget + tags
    (15.0, True, True),    # Tier 2: Expand radius to 15km
    (15.0, False, True),   # Tier 3: Drop budget filter
    (30.0, False, False),  # Tier 4: Vét đáy — 30km, no filters
]

TARGET_POI_COUNT = 50
MIN_POI_THRESHOLD = 10


class SpatialFilterService:
    """Executes 2-phase spatial + semantic filtering."""

    async def get_optimized_pois(
        self,
        contract: LLMDataContract,
        db_session: AsyncSession,
        query_vector: Optional[list] = None,
    ) -> List[POIResponse]:
        """Main entry: returns up to TARGET_POI_COUNT POIs for Layer 4."""
        # Phase 1: Force Include locked POIs (bounded by 50km safety radius)
        locked_pois = await self._phase1_force_include(
            locked_names=contract.locked_pois,
            hotel_lat=contract.hotel_lat,
            hotel_lon=contract.hotel_lon,
            db_session=db_session,
        )
        locked_uuids = {p.uuid for p in locked_pois}
        remaining_slots = TARGET_POI_COUNT - len(locked_pois)

        logger.debug(f"Phase 1: {len(locked_pois)} locked POIs found")

        # Phase 2: Fill remaining slots with Hybrid Search + Fallback
        fill_pois = await self._phase2_fill_with_fallback(
            contract=contract,
            exclude_uuids=locked_uuids,
            limit=remaining_slots,
            query_vector=query_vector,
            db_session=db_session,
        )

        logger.debug(f"Phase 2: {len(fill_pois)} fill POIs found")

        # Combine & return
        all_pois = locked_pois + fill_pois
        return all_pois[:TARGET_POI_COUNT]

    async def _phase1_force_include(
        self,
        locked_names: List[str],
        hotel_lat: float,
        hotel_lon: float,
        db_session: AsyncSession,
        safety_radius_km: float = 50.0,
    ) -> List[POIResponse]:
        """Query POIs by name within safety radius, mark is_locked=True."""
        if not locked_names:
            return []

        # Sanitize general city names to prevent 0-day empty itinerary bug
        city_blacklist = {
            "huế", "hue", "đà nẵng", "da nang", "hà nội", "ha noi",
            "sài gòn", "sai gon", "hồ chí minh", "ho chi minh", "tp hcm", "tphcm"
        }
        sanitized_names = [
            name for name in locked_names
            if name.lower().strip() not in city_blacklist
        ]
        
        if not sanitized_names:
            return []

        POI = PointOfInterest
        center = func.ST_SetSRID(ST_MakePoint(hotel_lon, hotel_lat), 4326)
        safety_radius_m = safety_radius_km * 1000

        name_conditions = [
            func.lower(POI.name).contains(name.lower())
            for name in sanitized_names
        ]

        stmt = select(
            POI.uuid, POI.name, POI.category, POI.description,
            POI.visit_duration_min, POI.price, POI.entrance_fee,
            POI.open_time, POI.close_time, POI.priority_score,
            POI.tags, POI.is_outdoor,
            ST_AsGeoJSON(POI.coordinates).label("geojson"),
        ).where(and_(
            or_(*name_conditions),
            ST_DWithin(
                POI.coordinates,
                cast(center, Geography),
                safety_radius_m,
                use_spheroid=True,
            ),
        ))

        result = await db_session.execute(stmt)
        rows = result.fetchall()

        return [self._row_to_poi(row, is_locked=True) for row in rows]

    async def _phase2_fill_with_fallback(
        self,
        contract: LLMDataContract,
        exclude_uuids: set,
        limit: int,
        query_vector: Optional[list],
        db_session: AsyncSession,
    ) -> List[POIResponse]:
        """Hybrid search with multi-tier fallback until enough POIs found."""
        if limit <= 0:
            return []

        for tier_idx, (radius_override, apply_budget, apply_tags) in enumerate(FALLBACK_TIERS):
            radius_km = radius_override or contract.radius_km
            radius_m = radius_km * 1000

            pois = await self._query_tier(
                contract=contract,
                radius_m=radius_m,
                apply_budget=apply_budget,
                apply_tags=apply_tags,
                exclude_uuids=exclude_uuids,
                limit=limit,
                query_vector=query_vector,
                db_session=db_session,
            )

            logger.debug(f"Tier {tier_idx+1}: {len(pois)} POIs (radius={radius_km}km)")

            if len(pois) >= MIN_POI_THRESHOLD or tier_idx == len(FALLBACK_TIERS) - 1:
                return pois

        return []

    async def _query_tier(
        self,
        contract: LLMDataContract,
        radius_m: float,
        apply_budget: bool,
        apply_tags: bool,
        exclude_uuids: set,
        limit: int,
        query_vector: Optional[list],
        db_session: AsyncSession,
    ) -> List[POIResponse]:
        """Single-tier query: PostGIS distance + budget + vector cosine similarity."""
        POI = PointOfInterest
        center = func.ST_SetSRID(ST_MakePoint(contract.hotel_lon, contract.hotel_lat), 4326)

        conditions = [
            ST_DWithin(
                POI.coordinates,
                cast(center, Geography),
                radius_m,
                use_spheroid=True,
            ),
            POI.weather_penalty < 50.0,
        ]

        if exclude_uuids:
            conditions.append(POI.uuid.notin_(exclude_uuids))

        for excluded_name in contract.excluded_pois or []:
            clean_name = excluded_name.strip().lower()
            if clean_name:
                conditions.append(~func.lower(POI.name).contains(clean_name))

        if apply_budget and contract.budget_max:
            conditions.append(POI.price <= contract.budget_max)

        if contract.time_window:
            conditions.append(POI.open_time <= contract.time_window.end_min)
            conditions.append(POI.close_time >= contract.time_window.start_min)

        if contract.weather_preference == "indoor":
            conditions.append(POI.is_outdoor == False)
        elif contract.weather_preference == "outdoor":
            conditions.append(POI.is_outdoor == True)

        # Strict vegetarian exclusion
        is_vegetarian = any(
            t.lower() in ("vegetarian", "vegan", "chay")
            for t in (contract.tags or [])
        )
        if is_vegetarian:
            conditions.append(or_(
                and_(
                    func.lower(POI.category) != "restaurant",
                    func.lower(POI.category) != "nhà hàng",
                    func.lower(POI.category) != "quán ăn"
                ),
                POI.tags.overlap(["vegetarian", "vegan", "chay"])
            ))

        stmt = select(
            POI.uuid, POI.name, POI.category, POI.description,
            POI.visit_duration_min, POI.price, POI.entrance_fee,
            POI.open_time, POI.close_time, POI.priority_score,
            POI.tags, POI.is_outdoor,
            ST_AsGeoJSON(POI.coordinates).label("geojson"),
        ).where(and_(*conditions))

        if apply_tags and query_vector is not None:
            # Cosine distance via pgvector <=> operator (uses HNSW index)
            stmt = stmt.order_by(
                POI.tags_vector.cosine_distance(query_vector),
                POI.priority_score.desc(),
            )
        else:
            stmt = stmt.order_by(POI.priority_score.desc())

        stmt = stmt.limit(limit)

        result = await db_session.execute(stmt)
        rows = result.fetchall()

        # Score POIs with UtilityScorer
        scorer = UtilityScorer()
        existing_categories = set()
        scored_pois = []

        for row in rows:
            poi = self._row_to_poi(row, is_locked=False)

            # Cosine similarity: not available as named column, use fallback
            cosine_sim = 0.5

            breakdown = scorer.score_poi(poi, contract, cosine_sim, existing_categories)
            poi.score_breakdown = breakdown
            poi.utility_score = scorer.compute_utility(breakdown)

            existing_categories.add(poi.category)
            scored_pois.append(poi)

        # Sort by utility_score descending
        scored_pois.sort(key=lambda p: p.utility_score, reverse=True)
        return scored_pois

    @staticmethod
    def _row_to_poi(row, is_locked: bool) -> POIResponse:
        """Convert DB row to POIResponse schema."""
        import json
        geojson = json.loads(row.geojson) if row.geojson else None
        lat = geojson["coordinates"][1] if geojson else 0.0
        lon = geojson["coordinates"][0] if geojson else 0.0

        return POIResponse(
            uuid=row.uuid,
            name=row.name,
            category=row.category,
            description=row.description,
            latitude=lat,
            longitude=lon,
            visit_duration_min=row.visit_duration_min,
            price=row.price,
            entrance_fee=row.entrance_fee,
            open_time=row.open_time,
            close_time=row.close_time,
            priority_score=row.priority_score,
            tags=row.tags,
            is_locked=is_locked,
        )
