"""Tests for Layer 3 spatial filter service."""
import pytest
from app.schemas.trip import LLMDataContract


def test_fallback_tiers_defined():
    from app.services.spatial_filter import FALLBACK_TIERS, TARGET_POI_COUNT
    assert len(FALLBACK_TIERS) == 4
    assert TARGET_POI_COUNT == 50


def test_contract_with_locked_pois():
    c = LLMDataContract(
        locked_pois=["Đại Nội Huế", "Lăng Tự Đức"],
        hotel_lat=16.4637,
        hotel_lon=107.5905,
    )
    assert len(c.locked_pois) == 2
    # Remaining slots = 50 - 2 = 48


def test_contract_indoor_preference():
    c = LLMDataContract(
        weather_preference="indoor",
        hotel_lat=16.4637,
        hotel_lon=107.5905,
    )
    assert c.weather_preference == "indoor"


@pytest.mark.anyio
async def test_vegetarian_restaurant_strict_exclusion():
    from app.services.spatial_filter import SpatialFilterService
    from app.database import AsyncSessionFactory
    from app.schemas.trip import LLMDataContract
    
    service = SpatialFilterService()
    contract = LLMDataContract(
        destination="Huế",
        num_days=3,
        budget_max=1000000.0,
        tags=["vegetarian"],
        hotel_lat=16.4637,
        hotel_lon=107.5905,
    )
    
    async with AsyncSessionFactory() as session:
        pois = await service.get_optimized_pois(contract, db_session=session)
        # Check that if any POI has category "restaurant", it MUST have vegetarian in its tags
        for poi in pois:
            if poi.category.lower() in ("restaurant", "nhà hàng", "quán ăn"):
                poi_tags = [t.lower() for t in poi.tags] if poi.tags else []
                assert any(t in poi_tags for t in ("vegetarian", "vegan", "chay"))


@pytest.mark.anyio
async def test_city_name_blacklist_exclusion():
    from app.services.spatial_filter import SpatialFilterService
    from app.database import AsyncSessionFactory
    from app.schemas.trip import LLMDataContract
    
    service = SpatialFilterService()
    contract = LLMDataContract(
        destination="Huế",
        num_days=3,
        budget_max=1000000.0,
        locked_pois=["Huế", "Đại Nội Huế"],
        hotel_lat=16.4637,
        hotel_lon=107.5905,
    )
    
    async with AsyncSessionFactory() as session:
        pois = await service.get_optimized_pois(contract, db_session=session)
        locked_names = [poi.name for poi in pois if poi.is_locked]
        # "Đại Nội Huế" should be locked because it was explicitly requested
        assert any("Đại Nội" in name for name in locked_names)
        # "Chùa Thiên Mụ" should NOT be locked even though its name in the DB contains "Huế"
        assert not any("Thiên Mụ" in name for name in locked_names)


