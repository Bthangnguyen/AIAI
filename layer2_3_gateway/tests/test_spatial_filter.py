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
