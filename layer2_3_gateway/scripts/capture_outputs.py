import asyncio
import json
from httpx import AsyncClient
from unittest.mock import patch
from app.main import app
from app.schemas.trip import LLMDataContract, TimeWindowSpec

async def run_scenarios():
    outputs = {}
    with patch("app.services.llm_extractor.LLMExtractorService.extract_intent") as mock_extract:
        async with AsyncClient(app=app, base_url="http://testserver/trip") as client:
            
            # S1: Happy Path
            print("Running S1...")
            mock_extract.return_value = LLMDataContract(
                hotel_lat=16.4637, hotel_lon=107.5905, hotel_name="Saigon Morin",
                num_days=1, budget_max=500000, tags=["culture", "history"], radius_km=10.0
            )
            r1 = await client.post("/plan_trip", json={
                "user_prompt": "Tôi muốn đi dạo trung tâm Huế 1 ngày. Ngân sách 500k, lịch sử",
                "hotel_lat": 16.4637, "hotel_lon": 107.5905, "hotel_name": "Saigon Morin", "num_days": 1,
            })
            outputs["Mức độ 1: Happy Path"] = r1.json() if r1.status_code == 200 else f"Error {r1.status_code}"

            # S2: Hard Constraints
            print("Running S2...")
            mock_extract.return_value = LLMDataContract(
                hotel_lat=16.4637, hotel_lon=107.5905, hotel_name="Saigon Morin",
                num_days=1, locked_pois=["Đại Nội Huế", "Chùa Thiên Mụ"], radius_km=10.0
            )
            r2 = await client.post("/plan_trip", json={
                "user_prompt": "Đi Huế 1 ngày bắt buộc thăm lăng tẩm và Đại Nội",
                "hotel_lat": 16.4637, "hotel_lon": 107.5905, "hotel_name": "Saigon Morin", "num_days": 1,
            })
            outputs["Mức độ 2: Hard Constraints"] = r2.json() if r2.status_code == 200 else f"Error {r2.status_code}"

            # S3: Fallback Tiers
            print("Running S3...")
            mock_extract.return_value = LLMDataContract(
                hotel_lat=16.4637, hotel_lon=107.5905, hotel_name="Vincom Hue",
                num_days=1, tags=["beach"], radius_km=5.0
            )
            r3 = await client.post("/plan_trip", json={
                "user_prompt": "Tôi muốn đi tắm biển Thuận An",
                "hotel_lat": 16.4637, "hotel_lon": 107.5905, "hotel_name": "Vincom Hue", "num_days": 1,
            })
            outputs["Mức độ 3: Fallback Tiers"] = r3.json() if r3.status_code == 200 else f"Error {r3.status_code}"

            # S4: Multi Day
            print("Running S4...")
            mock_extract.return_value = LLMDataContract(
                hotel_lat=16.4637, hotel_lon=107.5905, hotel_name="Saigon Morin",
                num_days=3, radius_km=20.0
            )
            r4 = await client.post("/plan_trip", json={
                "user_prompt": "Gia đình đi Huế 3 ngày",
                "hotel_lat": 16.4637, "hotel_lon": 107.5905, "hotel_name": "Saigon Morin", "num_days": 3,
            })
            outputs["Mức độ 4: Multi Day"] = r4.json() if r4.status_code == 200 else f"Error {r4.status_code}"

            # S5: System Resilience (Let it throw to trigger real fallback)
            print("Running S5...")
            mock_extract.side_effect = Exception("Simulated LLM API Key Error")
            r5 = await client.post("/plan_trip", json={
                "user_prompt": "Test fallback",
                "hotel_lat": 16.4637, "hotel_lon": 107.5905, "hotel_name": "Saigon Morin", "num_days": 1,
            })
            outputs["Mức độ 5: System Resilience"] = r5.json() if r5.status_code == 200 else f"Error {r5.status_code}"
            mock_extract.side_effect = None

            # S6: Time Window
            print("Running S6...")
            mock_extract.return_value = LLMDataContract(
                hotel_lat=16.4637, hotel_lon=107.5905, hotel_name="Saigon Morin",
                num_days=1, time_window=TimeWindowSpec(start_min=1320, end_min=1440), radius_km=10.0
            )
            r6 = await client.post("/plan_trip", json={
                "user_prompt": "Tôi đi từ 10h đêm đến 12h đêm",
                "hotel_lat": 16.4637, "hotel_lon": 107.5905, "hotel_name": "Saigon Morin", "num_days": 1,
            })
            outputs["Mức độ 6: Time Window"] = r6.json() if r6.status_code == 200 else f"Error {r6.status_code}"

    with open("/home/code/test_outputs.json", "w", encoding="utf-8") as f:
        json.dump(outputs, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(run_scenarios())
