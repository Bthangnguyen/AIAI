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

# 9 category groups mapping DB categories → distribution keys
CATEGORY_GROUP_MAP = {
    "food": {"restaurant", "nhà hàng", "quán ăn", "bún bò", "bánh mì",
             "cháo", "bún", "cơm", "hải sản", "chả cuốn", "cơm hến",
             "bánh canh", "bánh ướt", "bánh bèo", "bánh ít", "bắp",
             "bình dân", "chay", "cung đình", "bánh khoái", "food"},
    "cafe": {"cafe", "cà phê", "trà", "coffee", "tea"},
    "culture": {"historic", "historical", "history", "temple", "tourism_attraction",
                "culture", "cultural", "heritage", "museum", "bảo tàng", "landmark",
                "UNESCO", "Hoàng thành", "Kinh thành", "ca Huế", "dân gian", "tour"},
    "nature": {"nature", "park", "công viên", "garden", "lake", "river", "beach"},
    "nightlife": {"bar", "night_market", "pub", "karaoke", "nightlife", "entertainment"},
    "shopping": {"shop", "chợ", "market", "mua sắm", "shopping"},
    "art": {"gallery", "art", "nghệ thuật"},
    "wellness": {"spa", "massage", "wellness"},
    "adventure": {"trekking", "outdoor", "sport", "hiking", "adventure"},
}


def _resolve_category_group(poi: POIResponse) -> str:
    """Resolve POI's category group with CATEGORY_GROUP_MAP fallback."""
    if poi.category_group:
        return poi.category_group.lower().strip()
    cat_lower = (poi.category or "").lower().strip()
    for group, members in CATEGORY_GROUP_MAP.items():
        if cat_lower in members:
            return group
    return "culture"


def _get_subtype(poi: POIResponse) -> Optional[str]:
    """Detect fine-grained sub-type for diversity dedup within category groups."""
    name_lower = poi.name.lower()
    tags_lower = {t.lower() for t in (poi.tags or [])}

    # Culture sub-types
    if any(w in name_lower for w in ("chùa", "đền", "miếu", "tổ đình", "tịnh xá", "am", "nhà thờ")):
        if not any(w in name_lower for w in ("nhà hàng", "khách sạn", "quán")):
            return "spiritual"
    if any(w in name_lower for w in ("lăng",)) or tags_lower & {"lăng mộ", "mausoleum", "tomb"}:
        return "royal_tomb"
    if any(w in name_lower for w in ("đại nội", "hoàng thành", "tử cấm thành", "ngọ môn")):
        return "palace"
    if any(w in name_lower for w in ("làng nghề", "phường đúc")):
        return "craft_village"

    # Food sub-types (specific dishes - highly detailed classification)
    if any(w in name_lower for w in ("bún bò", "bun bo")):
        return "dish_bun_bo"
    if any(w in name_lower for w in ("cơm hến", "com hen", "bún hến", "bun hen", "xác hến")):
        return "dish_com_hen"
    if any(w in name_lower for w in ("cafe muối", "cafe muoi", "cà phê muối")):
        return "dish_cafe_muoi"
    if any(w in name_lower for w in ("bánh bèo", "bánh nậm", "bánh lọc", "bánh khoái", "bánh ít", "bánh bột lọc", "bánh ram ít")):
        return "dish_banh_hue"
    if any(w in name_lower for w in ("bánh canh", "banh canh")):
        return "dish_banh_canh"
    if name_lower.startswith("chè ") or name_lower == "chè" or " chè " in name_lower or "che hem" in name_lower:
        return "dish_che"
    if any(w in name_lower for w in ("bún mắm", "bun mam")):
        return "dish_bun_mam"
    if any(w in name_lower for w in ("nem lụi", "nem lui")):
        return "dish_nem_lui"
    if any(w in name_lower for w in ("bún thịt nướng", "bun thit nuong", "bún thịt", "thịt nướng")):
        return "dish_bun_thit_nuong"
    if any(w in name_lower for w in ("bánh mì", "banh mi")):
        return "dish_banh_mi"
    if any(w in name_lower for w in ("cháo ", "cháo lòng", "cháo lươn", "cháo vịt", "cháo hành")):
        return "dish_chao"
    if any(w in name_lower for w in ("cơm niêu", "cơm tấm", "cơm gia đình", "cơm gà", "cơm bình dân")):
        return "dish_com_nieu"
    if any(w in name_lower for w in ("ốc ", "quán ốc", "hải sản", "bạch tuộc", "cua ", "ghẹ ")):
        return "dish_hai_san"
    if any(w in name_lower for w in ("bánh ép", "banh ep")):
        return "dish_banh_ep"

    return None


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
            POI.uuid, POI.name, POI.category, POI.category_group, POI.description,
            POI.visit_duration_min, POI.price, POI.entrance_fee,
            POI.open_time, POI.close_time, POI.priority_score,
            POI.tags, POI.is_outdoor,
            ST_AsGeoJSON(POI.coordinates).label("geojson"),
        ).where(and_(
            or_(*name_conditions),
            POI.category_group != "wellness",  # Exclude wellness
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

            # Query MORE than needed so we can apply quota selection
            raw_pois = await self._query_tier(
                contract=contract,
                radius_m=radius_m,
                apply_budget=apply_budget,
                apply_tags=apply_tags,
                exclude_uuids=exclude_uuids,
                limit=limit * 4,  # overfetch for quota balancing
                query_vector=query_vector,
                db_session=db_session,
            )

            logger.debug(f"Tier {tier_idx+1}: {len(raw_pois)} raw POIs (radius={radius_km}km)")

            if len(raw_pois) >= MIN_POI_THRESHOLD or tier_idx == len(FALLBACK_TIERS) - 1:
                # Apply category distribution quotas
                balanced = self._apply_category_quotas(raw_pois, contract, limit)
                logger.info(
                    f"Quota selection: {len(raw_pois)} raw → {len(balanced)} balanced | "
                    f"distribution: {self._summarize_categories(balanced)}"
                )
                return balanced

        return []

    def _apply_category_quotas(
        self,
        pois: List[POIResponse],
        contract: LLMDataContract,
        limit: int,
    ) -> List[POIResponse]:
        """Select POIs respecting target_category_distribution quotas.

        Algorithm:
        1. Pre-filter out disabled optional categories, and cap allowed ones to num_days * 1
        2. Compute quota per category_group from distribution × limit
        3. Group POIs by category_group (already sorted by utility_score)
        4. Pick top-N per group up to quota (min 1 per category if POIs exist)
        5. Fill remaining slots with best-scoring POIs from any category
        """
        # Step 0: Pre-filter optional category groups based on contract flags
        filtered_pois = []
        cafe_count = 0
        art_count = 0
        shop_count = 0
        max_opt = contract.num_days or 1

        for poi in pois:
            group = _resolve_category_group(poi)
            if group == "cafe":
                if not getattr(contract, "allow_cafe", False):
                    continue
                if cafe_count >= max_opt:
                    continue
                cafe_count += 1
            elif group == "art":
                if not getattr(contract, "allow_art", False):
                    continue
                if art_count >= max_opt:
                    continue
                art_count += 1
            elif group == "shopping":
                if not getattr(contract, "allow_shopping", False):
                    continue
                if shop_count >= max_opt:
                    continue
                shop_count += 1
            elif group == "wellness":
                continue # completely omit wellness

            filtered_pois.append(poi)

        pois = filtered_pois

        distribution = contract.target_category_distribution or {}
        if not distribution:
            # Fallback to balanced default instead of no enforcement
            distribution = {
                "food": 0.35, "culture": 0.35, "nature": 0.20,
                "nightlife": 0.05, "adventure": 0.05
            }

        # Step 1: Compute quotas (minimum 1 per category that has POIs)
        quotas: dict[str, int] = {}
        for cat, pct in distribution.items():
            quota = max(1, round(pct * limit))
            quotas[cat] = quota

        # Step 2: Group POIs by category_group
        by_group: dict[str, List[POIResponse]] = {}
        for poi in pois:
            group = _resolve_category_group(poi)
            by_group.setdefault(group, []).append(poi)

        # Step 3: Pick up to quota per group, with sub-type diversity
        selected: List[POIResponse] = []
        selected_uuids: set = set()

        for cat, quota in sorted(quotas.items(), key=lambda x: -x[1]):
            candidates = by_group.get(cat, [])
            taken = 0
            seen_subtypes: set = set()
            # Pass 1: pick 1 per sub-type for diversity (1 bún bò, 1 cơm hến...)
            for poi in candidates:
                if taken >= quota:
                    break
                if poi.uuid in selected_uuids:
                    continue
                subtype = _get_subtype(poi)
                if subtype and subtype in seen_subtypes:
                    continue
                if subtype:
                    seen_subtypes.add(subtype)
                selected.append(poi)
                selected_uuids.add(poi.uuid)
                taken += 1
            # Pass 2: fill remaining quota (allow duplicate sub-types)
            if taken < quota:
                for poi in candidates:
                    if taken >= quota:
                        break
                    if poi.uuid not in selected_uuids:
                        selected.append(poi)
                        selected_uuids.add(poi.uuid)
                        taken += 1

        # Step 4: Fill remaining slots with best-scoring from any group
        remaining = limit - len(selected)
        if remaining > 0:
            for poi in pois:
                if remaining <= 0:
                    break
                if poi.uuid not in selected_uuids:
                    selected.append(poi)
                    selected_uuids.add(poi.uuid)
                    remaining -= 1

        return selected[:limit]

    @staticmethod
    def _summarize_categories(pois: List[POIResponse]) -> str:
        """Summarize category distribution for logging."""
        counts: dict[str, int] = {}
        for poi in pois:
            group = _resolve_category_group(poi)
            counts[group] = counts.get(group, 0) + 1
        return ", ".join(f"{k}:{v}" for k, v in sorted(counts.items(), key=lambda x: -x[1]))

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
            # Exclude accommodation — hotels are not visitable POIs
            POI.category_group != "accommodation",
            # Exclude wellness
            POI.category_group != "wellness",
        ]

        if exclude_uuids:
            conditions.append(POI.uuid.notin_(exclude_uuids))

        for excluded_name in contract.excluded_pois or []:
            clean_name = excluded_name.strip().lower()
            if clean_name:
                conditions.append(~func.lower(POI.name).contains(clean_name))

        # Filter by avoid_tags: exclude POIs whose tags array overlaps with avoided tags
        # Also exclude POIs whose category or category_group matches avoided tags
        # This is defense-in-depth: tags overlap catches tagged POIs, category match catches categorized ones
        if contract.avoid_tags:
            clean_avoid = [t.strip().lower() for t in contract.avoid_tags if t.strip()]
            if clean_avoid:
                # Semantic Expansion of avoid tags (defense-in-depth against morphological and English/Vietnamese mismatches)
                expanded_avoid = set(clean_avoid)
                for t in clean_avoid:
                    if "culture" in t or "cultural" in t or "văn hóa" in t:
                        expanded_avoid.update(["culture", "cultural", "historic", "historical", "văn hóa", "di tích"])
                    if "temple" in t or "pagoda" in t or "chùa" in t or "tâm linh" in t:
                        expanded_avoid.update(["temple", "pagoda", "chùa", "đền", "spiritual", "tâm linh"])
                    if "art" in t or "gallery" in t or "nghệ thuật" in t:
                        expanded_avoid.update(["art", "gallery", "nghệ thuật", "triển lãm"])
                clean_avoid = list(expanded_avoid)

                # 1. Exclude POIs with matching tags (array overlap)
                conditions.append(~POI.tags.overlap(clean_avoid))
                # 2. Exclude POIs with matching category (substring)
                for avoid_tag in clean_avoid:
                    conditions.append(~func.lower(POI.category).contains(avoid_tag))

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
            POI.uuid, POI.name, POI.category, POI.category_group, POI.description,
            POI.visit_duration_min, POI.price, POI.entrance_fee,
            POI.open_time, POI.close_time, POI.priority_score,
            POI.tags, POI.is_outdoor,
            ST_AsGeoJSON(POI.coordinates).label("geojson"),
        ).where(and_(*conditions))

        if apply_tags and query_vector is not None:
            # Cosine distance via pgvector <=> operator (uses HNSW index)
            cos_dist_expr = POI.tags_vector.cosine_distance(query_vector).label("cos_dist")
            stmt = stmt.add_columns(cos_dist_expr)
            stmt = stmt.order_by(
                POI.tags_vector.cosine_distance(query_vector),
                POI.priority_score.desc(),
            )
        else:
            stmt = stmt.order_by(POI.priority_score.desc())

        stmt = stmt.limit(limit)

        result = await db_session.execute(stmt)
        rows = result.fetchall()

        # Quality rank: cosine_similarity × 0.6 + priority_score × 0.4
        scored_pois = []

        for row in rows:
            poi = self._row_to_poi(row, is_locked=False)

            cosine_sim = 0.5
            if apply_tags and query_vector is not None:
                try:
                    if hasattr(row, "cos_dist") and row.cos_dist is not None:
                        cosine_sim = max(0.0, min(1.0, 1.0 - float(row.cos_dist)))
                except Exception as e:
                    logger.warning(f"Failed to extract real cosine distance from row: {e}")

            # Quality rank: cosine_similarity × 0.6 + priority_score × 0.4
            quality_rank = cosine_sim * 0.6 + min(1.0, poi.priority_score) * 0.4
            
            # Keyword exact matching boost for specific user requests (e.g. "bún bò", "chè", "cơm hến", "bánh ép")
            keyword_boost = 0.0
            
            import unicodedata
            def _norm(text: str) -> str:
                if not text:
                    return ""
                text = unicodedata.normalize('NFKD', text)
                text = "".join([c for c in text if not unicodedata.combining(c)])
                return text.lower().replace('đ', 'd').strip()

            poi_name_norm = _norm(poi.name)
            poi_tags_norm = [_norm(t) for t in (poi.tags or [])]
            poi_desc_norm = _norm(poi.description or "")
            
            # Extract user keywords from contract tags or food preferences
            user_keywords = []
            if contract.tags:
                user_keywords.extend([t.lower() for t in contract.tags])
            if getattr(contract, "food_preferences", None):
                user_keywords.extend([f.lower() for f in contract.food_preferences])
            if getattr(contract, "vibe", None):
                user_keywords.append(contract.vibe.lower())
                
            for kw in user_keywords:
                norm_kw = _norm(kw).replace("hue", "").strip()
                if not norm_kw or len(norm_kw) <= 2:
                    continue
                # If user explicitly requested this signature food item and it matches name or tags, give a massive boost
                if norm_kw in poi_name_norm or any(norm_kw in t for t in poi_tags_norm) or norm_kw in poi_desc_norm:
                    keyword_boost = max(keyword_boost, 1.5)  # Massive boost to force exact matches to top
                    
            poi.utility_score = quality_rank + keyword_boost
            scored_pois.append(poi)

        # Sort by quality rank descending
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
            category_group=getattr(row, 'category_group', None),
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
