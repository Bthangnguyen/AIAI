import asyncio
import os
import sys
import json
import pytest
from httpx import AsyncClient

# Add parent dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

@pytest.mark.anyio
async def test_weird_scenario():
    print("🧪 Testing Vector Similarity for: 'đá gà', 'chèo thuyền'...")
    
    from app.database import AsyncSessionFactory
    from app.services.spatial_filter import SpatialFilterService
    from app.services.embedding_service import EmbeddingService
    from app.schemas.trip import LLMDataContract
    
    spatial_service = SpatialFilterService()
    embed_service = EmbeddingService()
    
    # We want to see if 'đá gà' (cockfighting) matches 'Elephant Arena'
    # and 'chèo thuyền' (rowing) matches 'Boat Tour'
    test_tags = ["đá gà", "chèo thuyền"]
    
    # 1. Generate Query Vector
    tag_text = embed_service.build_poi_text(
        name="query", category="preference",
        tags=test_tags, description="",
    )
    print(f"   Query text: {tag_text}")
    query_vector = await embed_service.aembed_text(tag_text)
    
    # 2. Mock Contract
    contract = LLMDataContract(
        budget_max=None,
        radius_km=20.0,
        num_days=2,
        tags=test_tags,
        locked_pois=[],
        hotel_lat=16.4637,
        hotel_lon=107.5905,
        hotel_name="Saigon Morin"
    )

    async with AsyncSessionFactory() as session:
        print("   Searching Vector DB...")
        pois = await spatial_service.get_optimized_pois(
            contract=contract,
            db_session=session,
            query_vector=query_vector
        )
        
        print("\n--- SEMANTIC SEARCH RESULTS ---")
        print(f"Found {len(pois)} POIs.")
        
        for i, poi in enumerate(pois[:10]):
            # The 'similarity' isn't explicitly in POIResponse but the order should reflect it
            print(f"{i+1}. {poi.name} ({poi.category})")
            print(f"   Tags: {poi.tags}")
            print(f"   Desc: {poi.description[:80]}...")

if __name__ == "__main__":
    asyncio.run(test_weird_scenario())
