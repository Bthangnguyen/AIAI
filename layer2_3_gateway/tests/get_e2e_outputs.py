import asyncio
import json
from httpx import AsyncClient
from app.main import app
from app.config import settings
from psycopg_pool import AsyncConnectionPool

# Mock embedding service to return a flat 1536-dimension mock vector
from unittest.mock import patch, AsyncMock

async def run_scenario(client, name, prompt, num_days, budget=None):
    print(f"\n=======================================================")
    print(f"RUNNING SCENARIO: {name}")
    print(f"Prompt: {prompt}")
    print(f"=======================================================")
    
    body = {
        "user_prompt": prompt,
        "hotel_lat": 16.4637,
        "hotel_lon": 107.5905,
        "hotel_name": "Saigon Morin",
        "num_days": num_days
    }
    if budget:
        body["budget"] = budget

    response = await client.post("/trip/plan_trip", json=body)
    if response.status_code == 200:
        data = response.json()
        filename = f"tests/output_{name.lower().replace(' ', '_').replace('/', '_')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ Success! Response saved to {filename}")
        
        # Print a neat summary of the output
        print(f"\n--- State Contract Extracted ---")
        print(json.dumps(data.get("llm_contract"), indent=2, ensure_ascii=False))
        
        pois = data.get("pois", [])
        print(f"\n--- Filtered POIs ({len(pois)} spots) ---")
        for i, poi in enumerate(pois[:5]):
            print(f" {i+1}. {poi['name']} ({poi['category']}) - Tags: {poi['tags']}")
        if len(pois) > 5:
            print(f" ... and {len(pois)-5} more spots.")
            
        l4 = data.get("layer4_result")
        if l4:
            print(f"\n--- Layer 4 Itinerary ---")
            days = l4.get("days", [])
            print(f" Total Days: {len(days)}")
            for d in days:
                places = d.get("places", [])
                place_names = [p["name"] for p in places]
                print(f"   * Day {d['day_index']}: {' -> '.join(place_names)}")
            print(f" Dropped POIs: {len(l4.get('dropped_pois', []))} spots")
            print(f" Budget Used: {l4.get('budget_used')} VND / Limit: {l4.get('budget_total')} VND")
    else:
        print(f"✗ Failed! Status code: {response.status_code}")
        print(response.text)

async def main():
    _conninfo = settings.get_conn_str()
    app.async_pool = AsyncConnectionPool(conninfo=_conninfo)
    
    with patch("app.services.embedding_service.EmbeddingService.aembed_text", AsyncMock(return_value=[0.0]*1536)):
        async with AsyncClient(
            app=app,
            base_url="http://testserver/v1",
            headers={"Content-Type": "application/json"},
        ) as client:
            # Scenario 1: Vegetarian + Seafood allergy
            await run_scenario(
                client,
                "Dietary and Allergy",
                "Tôi muốn đi Huế 2 ngày ngân sách 1tr5, bị dị ứng hải sản nặng và chỉ ăn chay",
                2
            )
            
            # Scenario 2: Active Outdoor Sports
            await run_scenario(
                client,
                "Active Outdoor",
                "Đi Huế 3 ngày, thích đi leo núi trekking dã ngoại ngoài trời mạo hiểm chèo thuyền",
                3
            )
            
            # Scenario 3: Royal History
            await run_scenario(
                client,
                "Royal History",
                "Tôi muốn đi Huế 2 ngày 2 triệu, ưu tiên di tích cổ kính lịch sử cung đình triều Nguyễn",
                2
            )
            
    await app.async_pool.close()

if __name__ == "__main__":
    asyncio.run(main())
