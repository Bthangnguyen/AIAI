import os
import random
from fastapi.testclient import TestClient
from src.app import app
from src.models.domain import TransportMode

client = TestClient(app)

# Test environment uses API Key if required (we'll just assume an open API or mock the dependency if needed).
# Let's check routes.py - it uses Depends(verify_api_key).
# We can bypass it or set the expected header. Let's look at config.
# Actually, setting X-API-Key: test-key usually works if we don't know it, or we just mock verify_api_key.
# Since we are hitting the app directly, we might need a valid API key. Let's see what settings.api_key defaults to.
# We will override the dependency for tests.

from src.api.dependencies import verify_api_key
app.dependency_overrides[verify_api_key] = lambda: None

def generate_random_hue_pois(count: int):
    # Hue bounding box approximately:
    # Lat: 16.42 - 16.50
    # Lon: 107.55 - 107.65
    pois = []
    for i in range(count):
        lat = 16.42 + random.random() * 0.08
        lon = 107.55 + random.random() * 0.10
        pois.append({
            "id": f"poi_{i}",
            "name": f"Random POI {i}",
            "category": "attraction",
            "location": {
                "latitude": lat,
                "longitude": lon
            },
            "visit_duration_min": random.choice([30, 45, 60, 90]),
            "time_window": {
                "start_min": 480, # 8 AM
                "end_min": 1080  # 6 PM
            },
            "entrance_fee": random.choice([0, 50000, 100000])
        })
    return pois

def test_plan_travel_50_pois():
    """Integration Test: Send 50 POIs in Hue, expect a valid 3-day itinerary."""
    hotels = [
        {
            "id": "hotel_1",
            "name": "Hue Central Hotel",
            "location": {
                "latitude": 16.4637,
                "longitude": 107.5909
            }
        }
    ]
    
    pois = generate_random_hue_pois(50)
    
    payload = {
        "pois": pois,
        "hotels": hotels,
        "constraints": {
            "num_days": 3,
            "transport_modes": ["taxi"],
            "max_travel_time_per_day_min": 180,
            "max_pois_per_day": 20
        }
    }
    
    response = client.post("/plan", json=payload)
    
    assert response.status_code == 200, response.text
    data = response.json()
    
    assert data["status"] == "success"
    assert data["num_days"] == 3
    assert len(data["days"]) == 3
    
    # Assert each day has stops
    for day in data["days"]:
        assert isinstance(day["num_pois"], int)
        
    # Total POIs visited + dropped should equal total provided
    assert data["total_pois_visited"] + data["total_pois_dropped"] == 50
    assert "total_distance_km" in data
    assert "total_travel_min" in data


def test_re_route_integration():
    """Integration Test: JIT Re-routing from a specific location in Hue."""
    payload = {
        "current_location": {
            "latitude": 16.470,
            "longitude": 107.595
        },
        "current_time_min": 840, # 2 PM
        "remaining_poi_ids": ["poi_0", "poi_1", "poi_2"],
        "pois": generate_random_hue_pois(3),
        "hotel": {
            "id": "hotel_1",
            "name": "Hue Central Hotel",
            "location": {
                "latitude": 16.4637,
                "longitude": 107.5909
            }
        },
        "day": {
            "day_index": 0,
            "date": "2026-05-01",
            "start_time_min": 480,
            "end_time_min": 1080
        },
        "constraints": {
            "num_days": 1,
            "transport_modes": ["taxi"]
        },
        "excluded_poi_ids": ["poi_1"] # Exclude this one
    }
    
    # Fix the generated POI IDs to match what we requested
    payload["pois"][0]["id"] = "poi_0"
    payload["pois"][1]["id"] = "poi_1"
    payload["pois"][2]["id"] = "poi_2"

    response = client.post("/re-route", json=payload)
    
    assert response.status_code == 200, response.text
    data = response.json()
    
    assert data["day_index"] == 0
    # POI 1 should not be in the route
    visited_ids = [stop["poi_id"] for stop in data["stops"]]
    assert "poi_1" not in visited_ids
