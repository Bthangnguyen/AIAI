import asyncio
import os
import sys

# Setup Windows asyncio policy for psycopg compatibility
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, './layer2_3_gateway')
from dotenv import load_dotenv
load_dotenv('layer2_3_gateway/travel.env')

from app.api.trip_planner import plan_trip_stream
from app.schemas.trip import TripPlanRequest
from starlette.requests import Request

async def run():
    request_data = TripPlanRequest(
        user_prompt='Đi Huế 1 ngày chill, thích di tích lịch sử và ăn uống',
        hotel_lat=None,
        hotel_lon=None,
        hotel_name=None,
        num_days=1
    )
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/trip/plan_trip_stream",
        "headers": [],
        "client": ("127.0.0.1", 12345),
    }
    req = Request(scope)
    
    try:
        response = await plan_trip_stream(req, request_data)
        async for chunk in response.body_iterator:
            print("YIELD:", chunk.strip())
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
