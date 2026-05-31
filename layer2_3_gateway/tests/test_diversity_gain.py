"""Unit tests for fine-grained tag/sub-category level diversity scoring."""
import pytest
from uuid import uuid4
from app.schemas.trip import LLMDataContract, POIResponse
from app.services.utility_scorer import UtilityScorer


def test_generic_category_diversity_decay():
    scorer = UtilityScorer()
    contract = LLMDataContract(destination="Huế")

    poi1 = POIResponse(
        uuid=uuid4(),
        name="Restaurant A",
        category="restaurant",
        latitude=16.46,
        longitude=107.59,
        tags=["food"],
        visit_duration_min=45,
    )
    
    poi2 = POIResponse(
        uuid=uuid4(),
        name="Restaurant B",
        category="restaurant",
        latitude=16.46,
        longitude=107.59,
        tags=["food"],
        visit_duration_min=45,
    )

    # First restaurant: no existing categories
    existing_cats = {}
    breakdown1 = scorer.score_poi(poi1, contract, 0.5, existing_cats)
    
    # Record first restaurant
    existing_cats[poi1.category] = existing_cats.get(poi1.category, 0) + 1
    
    # Second restaurant: generic category exists
    breakdown2 = scorer.score_poi(poi2, contract, 0.5, existing_cats)

    assert breakdown1.diversity_gain == 1.0
    assert breakdown2.diversity_gain == 0.45
    assert breakdown2.diversity_gain < breakdown1.diversity_gain


def test_fine_grained_spiritual_diversity_decay():
    scorer = UtilityScorer()
    contract = LLMDataContract(destination="Huế")

    pagoda1 = POIResponse(
        uuid=uuid4(),
        name="Chùa Thiên Mụ",
        category="culture",
        latitude=16.46,
        longitude=107.59,
        tags=["chùa", "temple", "spiritual"],
        visit_duration_min=60,
    )
    
    pagoda2 = POIResponse(
        uuid=uuid4(),
        name="Chùa Từ Hiếu",
        category="culture",
        latitude=16.46,
        longitude=107.59,
        tags=["chùa", "temple", "spiritual"],
        visit_duration_min=60,
    )

    tomb = POIResponse(
        uuid=uuid4(),
        name="Lăng Khải Định",
        category="culture",
        latitude=16.46,
        longitude=107.59,
        tags=["mausoleum", "tomb"],
        visit_duration_min=60,
    )

    existing_cats = {}
    existing_tags = {}

    # First pagoda: no existing categories or tags
    breakdown_p1 = scorer.score_poi(pagoda1, contract, 0.5, existing_cats, existing_tags)
    
    # Record first pagoda
    existing_cats[pagoda1.category] = existing_cats.get(pagoda1.category, 0) + 1
    for k in scorer._get_fine_grained_keys(pagoda1):
        existing_tags[k] = existing_tags.get(k, 0) + 1

    # A royal tomb (different sub-category under 'culture', so culture count becomes 2)
    breakdown_t = scorer.score_poi(tomb, contract, 0.5, existing_cats, existing_tags)
    
    # Record royal tomb
    existing_cats[tomb.category] = existing_cats.get(tomb.category, 0) + 1
    for k in scorer._get_fine_grained_keys(tomb):
        existing_tags[k] = existing_tags.get(k, 0) + 1

    # Second pagoda (same sub-category as first pagoda)
    breakdown_p2 = scorer.score_poi(pagoda2, contract, 0.5, existing_cats, existing_tags)

    # Assertions
    assert breakdown_p1.diversity_gain == 1.0
    
    # Tomb is culture category repeat count=1 -> cat_gain = 0.45, not tomb/spiritual repeat -> tag_gain = 1.0 -> min = 0.45
    assert breakdown_t.diversity_gain == 0.45 
    
    # Pagoda 2 is culture category repeat count=2 -> cat_gain = 0.15. 
    # Tag repeat is count=1 -> tag_gain = 0.50. Min is min(0.15, 0.50) = 0.15.
    assert breakdown_p2.diversity_gain == 0.15
