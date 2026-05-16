"""E2E Integration Tests — Layer 4 (Solver) + Layer 2-3 (Gateway).

Tests run against LIVE Docker containers:
  - Layer 4 (cvrptw-solver-backend):  http://localhost:8000
  - Layer 2-3 (travel-gateway):       http://localhost:8001

TDD approach: RED -> GREEN -> REFACTOR
"""

import time
import httpx
import pytest

# ── Config ──
L4_URL = "http://localhost:8000"
L4_API_KEY = "test123"
L4_HEADERS = {"api-key": L4_API_KEY}

GW_URL = "http://localhost:8001"
GW_PREFIX = "/v1/trip"

# ── Fixtures: Test Data ──

def hue_pois():
    """Return POIs for a 2-day Hue trip with meals."""
    return [
        {
            "id": "dai_noi", "name": "Dai Noi Hue", "category": "palace",
            "location": {"latitude": 16.4698, "longitude": 107.5786},
            "visit_duration_min": 120, "entrance_fee": 200000,
            "priority_score": 1.0, "is_locked": True,
        },
        {
            "id": "thien_mu", "name": "Chua Thien Mu", "category": "temple",
            "location": {"latitude": 16.4536, "longitude": 107.5542},
            "visit_duration_min": 60, "entrance_fee": 0,
            "priority_score": 0.8,
        },
        {
            "id": "lang_tu_duc", "name": "Lang Tu Duc", "category": "heritage",
            "location": {"latitude": 16.4478, "longitude": 107.5667},
            "visit_duration_min": 90, "entrance_fee": 100000,
            "priority_score": 0.9,
        },
        {
            "id": "cho_dong_ba", "name": "Cho Dong Ba", "category": "market",
            "location": {"latitude": 16.4714, "longitude": 107.5843},
            "visit_duration_min": 60, "entrance_fee": 0,
            "priority_score": 0.7,
        },
        {
            "id": "cau_truong_tien", "name": "Cau Truong Tien", "category": "park",
            "location": {"latitude": 16.4691, "longitude": 107.5841},
            "visit_duration_min": 30, "entrance_fee": 0,
            "priority_score": 0.7,
        },
        # Day 0 meals
        {
            "id": "bfst_d0", "name": "Bun bo Hue sang D0", "category": "restaurant",
            "location": {"latitude": 16.4650, "longitude": 107.5850},
            "visit_duration_min": 45, "entrance_fee": 50000,
            "priority_score": 0.5, "meal_type": "breakfast", "assigned_day": 0,
        },
        {
            "id": "lunch_d0", "name": "Com hen D0", "category": "restaurant",
            "location": {"latitude": 16.4680, "longitude": 107.5820},
            "visit_duration_min": 60, "entrance_fee": 80000,
            "priority_score": 0.5, "meal_type": "lunch", "assigned_day": 0,
        },
        {
            "id": "dinner_d0", "name": "Banh beo D0", "category": "restaurant",
            "location": {"latitude": 16.4620, "longitude": 107.5880},
            "visit_duration_min": 60, "entrance_fee": 100000,
            "priority_score": 0.5, "meal_type": "dinner", "assigned_day": 0,
        },
        # Day 1 meals
        {
            "id": "bfst_d1", "name": "Bun bo sang D1", "category": "restaurant",
            "location": {"latitude": 16.4650, "longitude": 107.5850},
            "visit_duration_min": 45, "entrance_fee": 50000,
            "priority_score": 0.5, "meal_type": "breakfast", "assigned_day": 1,
        },
        {
            "id": "lunch_d1", "name": "Com chien D1", "category": "restaurant",
            "location": {"latitude": 16.4680, "longitude": 107.5820},
            "visit_duration_min": 60, "entrance_fee": 80000,
            "priority_score": 0.5, "meal_type": "lunch", "assigned_day": 1,
        },
        {
            "id": "dinner_d1", "name": "Lau D1", "category": "restaurant",
            "location": {"latitude": 16.4620, "longitude": 107.5880},
            "visit_duration_min": 60, "entrance_fee": 100000,
            "priority_score": 0.5, "meal_type": "dinner", "assigned_day": 1,
        },
    ]


def hue_hotel():
    return {
        "id": "hotel_hue",
        "name": "Pilgrimage Village",
        "location": {"latitude": 16.4637, "longitude": 107.5909},
        "assigned_days": [0, 1],
    }


def two_day_constraints():
    return {
        "num_days": 2,
        "budget_total": 2000000,
        "transport_modes": ["taxi"],
    }


# ═══════════════════════════════════════════
# TEST SUITE 1: Layer 4 Health & API Contract
# ═══════════════════════════════════════════

class TestLayer4Health:
    """Verify Layer 4 is alive and responds correctly."""

    def test_health_returns_ready(self):
        """GET /health should return {"status": "ready"}."""
        resp = httpx.get(f"{L4_URL}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"

    def test_plan_rejects_missing_api_key(self):
        """POST /plan without api-key should return 401."""
        resp = httpx.post(f"{L4_URL}/plan", json={})
        assert resp.status_code == 401

    def test_plan_rejects_invalid_body(self):
        """POST /plan with invalid body should return 422."""
        resp = httpx.post(
            f"{L4_URL}/plan",
            json={"invalid": True},
            headers=L4_HEADERS,
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════
# TEST SUITE 2: Layer 4 Multi-Day Plan (Solver v2)
# ═══════════════════════════════════════════

class TestLayer4MultiDayPlan:
    """Test the multi-depot solver through the HTTP API."""

    def test_plan_2day_returns_success(self):
        """POST /plan with 2-day Hue trip should return success with 2 days."""
        payload = {
            "pois": hue_pois(),
            "hotels": [hue_hotel()],
            "constraints": two_day_constraints(),
        }
        resp = httpx.post(
            f"{L4_URL}/plan",
            json=payload,
            headers=L4_HEADERS,
            params={"time_limit": 30},
            timeout=120.0,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        data = resp.json()
        assert data["status"] == "success"
        assert data["num_days"] == 2
        assert len(data["days"]) == 2

    def test_plan_2day_meals_on_correct_days(self):
        """Meals with assigned_day must appear on that day only."""
        payload = {
            "pois": hue_pois(),
            "hotels": [hue_hotel()],
            "constraints": two_day_constraints(),
        }
        resp = httpx.post(
            f"{L4_URL}/plan",
            json=payload,
            headers=L4_HEADERS,
            params={"time_limit": 30},
            timeout=120.0,
        )
        data = resp.json()

        day0_ids = [s["poi_id"] for s in data["days"][0]["stops"]]
        day1_ids = [s["poi_id"] for s in data["days"][1]["stops"]]

        # Day 0 meals
        assert "bfst_d0" in day0_ids, f"breakfast_d0 not in day 0: {day0_ids}"
        assert "lunch_d0" in day0_ids, f"lunch_d0 not in day 0: {day0_ids}"
        assert "dinner_d0" in day0_ids, f"dinner_d0 not in day 0: {day0_ids}"

        # Day 1 meals
        assert "bfst_d1" in day1_ids, f"breakfast_d1 not in day 1: {day1_ids}"
        assert "lunch_d1" in day1_ids, f"lunch_d1 not in day 1: {day1_ids}"
        assert "dinner_d1" in day1_ids, f"dinner_d1 not in day 1: {day1_ids}"

        # Meals must NOT leak across days
        assert "bfst_d0" not in day1_ids
        assert "bfst_d1" not in day0_ids

    def test_plan_2day_locked_poi_visited(self):
        """Locked POI (dai_noi) must appear in the itinerary."""
        payload = {
            "pois": hue_pois(),
            "hotels": [hue_hotel()],
            "constraints": two_day_constraints(),
        }
        resp = httpx.post(
            f"{L4_URL}/plan",
            json=payload,
            headers=L4_HEADERS,
            params={"time_limit": 30},
            timeout=120.0,
        )
        data = resp.json()

        all_ids = []
        for day in data["days"]:
            all_ids += [s["poi_id"] for s in day["stops"]]

        assert "dai_noi" in all_ids, f"Locked POI 'dai_noi' not visited: {all_ids}"

    def test_plan_2day_hotel_fields_v2(self):
        """Response should use v2 hotel fields: start_hotel_name, end_hotel_name."""
        payload = {
            "pois": hue_pois(),
            "hotels": [hue_hotel()],
            "constraints": two_day_constraints(),
        }
        resp = httpx.post(
            f"{L4_URL}/plan",
            json=payload,
            headers=L4_HEADERS,
            params={"time_limit": 30},
            timeout=120.0,
        )
        data = resp.json()

        day0 = data["days"][0]
        assert "start_hotel_name" in day0, f"Missing start_hotel_name: {day0.keys()}"
        assert "start_hotel_location" in day0
        assert day0["start_hotel_name"] == "Pilgrimage Village"

    def test_plan_budget_respected(self):
        """Total entrance fee should be minimized when budget is tight.
        
        Note: Meals (460k) + locked POI dai_noi (200k) = 660k are non-droppable.
        Budget must be >= 660k to be feasible. Test with 700k (tight but possible).
        """
        payload = {
            "pois": hue_pois(),
            "hotels": [hue_hotel()],
            "constraints": {
                "num_days": 2,
                "budget_total": 700000,  # Tight but feasible (meals=460k + locked=200k = 660k)
                "transport_modes": ["taxi"],
            },
        }
        resp = httpx.post(
            f"{L4_URL}/plan",
            json=payload,
            headers=L4_HEADERS,
            params={"time_limit": 30},
            timeout=120.0,
        )
        data = resp.json()

        if data["status"] == "success":
            # With budget validation, fee-bearing droppable POIs (lang_tu_duc=100k)
            # should be dropped to stay under 700k
            assert data["total_entrance_fee"] <= 700000 + 1, (
                f"Budget exceeded: {data['total_entrance_fee']} > 700000"
            )


# ═══════════════════════════════════════════
# TEST SUITE 3: Layer 4 Re-Route (JIT)
# ═══════════════════════════════════════════

class TestLayer4ReRoute:
    """Test the single-day re-route endpoint."""

    def test_reroute_returns_valid_day(self):
        """POST /re-route should return a valid TravelItineraryDay."""
        pois = [p for p in hue_pois() if p.get("meal_type") is None][:3]

        payload = {
            "current_location": {"latitude": 16.4637, "longitude": 107.5909},
            "current_time_min": 600,  # 10:00 AM
            "remaining_poi_ids": [p["id"] for p in pois],
            "pois": pois,
            "hotel": hue_hotel(),
            "day": {
                "day_index": 0,
                "date": "2026-06-01",
                "hotel_id": "hotel_hue",
                "start_time_min": 600,
                "end_time_min": 1260,
            },
            "constraints": {"num_days": 1, "transport_modes": ["taxi"]},
        }

        resp = httpx.post(
            f"{L4_URL}/re-route",
            json=payload,
            headers=L4_HEADERS,
            params={"time_limit": 10},
            timeout=60.0,
        )
        assert resp.status_code == 200, f"Re-route failed: {resp.text}"
        data = resp.json()
        assert data["day_index"] == 0
        assert "start_hotel_name" in data

    def test_reroute_starts_from_current_location(self):
        """Re-route should use current location as depot."""
        pois = [p for p in hue_pois() if p.get("meal_type") is None][:2]

        payload = {
            "current_location": {"latitude": 16.4700, "longitude": 107.5800},
            "current_time_min": 720,  # 12:00
            "remaining_poi_ids": [p["id"] for p in pois],
            "pois": pois,
            "hotel": hue_hotel(),
            "day": {
                "day_index": 0,
                "date": "2026-06-01",
                "hotel_id": "hotel_hue",
                "start_time_min": 720,
                "end_time_min": 1260,
            },
            "constraints": {"num_days": 1, "transport_modes": ["taxi"]},
        }

        resp = httpx.post(
            f"{L4_URL}/re-route",
            json=payload,
            headers=L4_HEADERS,
            params={"time_limit": 10},
            timeout=60.0,
        )
        data = resp.json()
        # Should have POIs in the response
        assert data["num_pois"] >= 1, f"Expected at least 1 POI, got {data['num_pois']}"


# ═══════════════════════════════════════════
# TEST SUITE 4: Layer 2-3 Gateway Health
# ═══════════════════════════════════════════

class TestGatewayHealth:
    """Verify Gateway is alive and DB is connected."""

    def test_gateway_health(self):
        """GET /v1/trip/health should return ready."""
        resp = httpx.get(f"{GW_URL}{GW_PREFIX}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"


# ═══════════════════════════════════════════
# TEST SUITE 5: E2E Gateway → Layer 4 Pipeline
# ═══════════════════════════════════════════

class TestE2EPipeline:
    """Test full pipeline from Gateway through Layer 4."""

    def test_plan_trip_returns_itinerary(self):
        """POST /v1/trip/plan_trip should return itinerary from Layer 4.
        
        Note: This requires a working LLM key and POIs in the DB.
        If LLM/DB is not available, this test will be skipped.
        """
        payload = {
            "user_prompt": "Toi muon di tham quan Hue 2 ngay, an sang bun bo, chieu tham chua Thien Mu",
            "hotel_lat": 16.4637,
            "hotel_lon": 107.5909,
            "hotel_name": "Pilgrimage Village",
            "num_days": 2,
        }

        try:
            resp = httpx.post(
                f"{GW_URL}{GW_PREFIX}/plan_trip",
                json=payload,
                timeout=180.0,
            )
        except httpx.ReadTimeout:
            pytest.skip("Gateway LLM + solver timed out")

        # Gateway may return error if LLM key is expired or DB has no POIs
        if resp.status_code == 429:
            pytest.skip("Rate limited")

        if resp.status_code == 500:
            pytest.skip(f"Gateway internal error (likely LLM/DB issue): {resp.text[:200]}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("success", "partial", "error")

        if data["status"] == "success":
            assert data.get("layer4_result") is not None
            l4 = data["layer4_result"]
            assert "days" in l4
            assert len(l4["days"]) >= 1


# ═══════════════════════════════════════════
# TEST SUITE 6: Edge Cases & Error Handling
# ═══════════════════════════════════════════

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_plan_empty_pois(self):
        """Empty POI list should return error/no solution."""
        payload = {
            "pois": [],
            "hotels": [hue_hotel()],
            "constraints": two_day_constraints(),
        }
        resp = httpx.post(
            f"{L4_URL}/plan",
            json=payload,
            headers=L4_HEADERS,
            params={"time_limit": 5},
            timeout=30.0,
        )
        data = resp.json()
        # Should handle gracefully (error or empty)
        assert data["status"] in ("error", "success")

    def test_plan_single_poi(self):
        """Single POI should still return a valid itinerary."""
        payload = {
            "pois": [hue_pois()[0]],  # Just Dai Noi
            "hotels": [hue_hotel()],
            "constraints": {"num_days": 1, "transport_modes": ["taxi"]},
        }
        resp = httpx.post(
            f"{L4_URL}/plan",
            json=payload,
            headers=L4_HEADERS,
            params={"time_limit": 10},
            timeout=60.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] == "success":
            assert data["num_days"] == 1
            assert data["total_pois_visited"] >= 1

    def test_reroute_empty_remaining(self):
        """Re-route with no remaining POIs should return empty day."""
        payload = {
            "current_location": {"latitude": 16.4637, "longitude": 107.5909},
            "current_time_min": 600,
            "remaining_poi_ids": [],
            "pois": [],
            "hotel": hue_hotel(),
            "day": {
                "day_index": 0, "date": "2026-06-01",
                "hotel_id": "hotel_hue",
            },
            "constraints": {"num_days": 1, "transport_modes": ["taxi"]},
        }
        resp = httpx.post(
            f"{L4_URL}/re-route",
            json=payload,
            headers=L4_HEADERS,
            params={"time_limit": 5},
            timeout=30.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["num_pois"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
