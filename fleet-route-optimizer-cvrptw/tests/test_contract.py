import pytest
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

def test_openapi_schema_contains_travel_endpoints():
    """Verify that the OpenAPI schema correctly defines the Layer 3 <-> Layer 4 contract."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    schema = response.json()
    
    # Check endpoints exist
    paths = schema.get("paths", {})
    assert "/plan" in paths
    assert "/re-route" in paths
    assert "/health" in paths

def test_travel_plan_request_schema():
    """Verify the expected payload format for TravelPlanRequest."""
    response = client.get("/openapi.json")
    schema = response.json()
    
    components = schema.get("components", {}).get("schemas", {})
    
    # Must have the primary components
    assert "TravelPlanRequest" in components
    assert "TravelItinerary" in components
    assert "ReRouteRequest" in components
    
    # Verify TravelPlanRequest constraints
    plan_req = components["TravelPlanRequest"]
    assert "pois" in plan_req["properties"]
    assert "hotels" in plan_req["properties"]
    assert "constraints" in plan_req["properties"]
    
    # Verify TravelItinerary (Output) format
    itinerary = components["TravelItinerary"]
    assert "status" in itinerary["properties"]
    assert "num_days" in itinerary["properties"]
    assert "days" in itinerary["properties"]
    assert "total_pois_visited" in itinerary["properties"]
    assert "budget_total" in itinerary["properties"]
    
    # Check that required fields are actually marked required
    assert "pois" in plan_req["required"]
    assert "hotels" in plan_req["required"]
    assert "constraints" in plan_req["required"]
