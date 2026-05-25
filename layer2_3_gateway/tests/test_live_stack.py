"""Live integration tests — hit running Docker stack on localhost.

Requires:
  - scripts/bootstrap-fullstack.ps1 completed successfully
  - LIVE_INTEGRATION=1
  - layer2_3_gateway/travel.env with valid LLM key

Run:
  cd layer2_3_gateway
  $env:LIVE_INTEGRATION="1"
  python -m pytest tests/test_live_stack.py -v -m live --noconftest
"""

import json
import os

import httpx
import pytest

GW_URL = os.getenv("LIVE_GATEWAY_URL", "http://localhost:8001")
GW_PREFIX = "/v1/trip"
L4_URL = os.getenv("LIVE_SOLVER_URL", "http://localhost:8000")
LIVE = os.getenv("LIVE_INTEGRATION") == "1"

pytestmark = pytest.mark.live


def _require_live():
    if not LIVE:
        pytest.skip("Set LIVE_INTEGRATION=1 to run live stack tests")


def _gw_ready() -> bool:
    try:
        r = httpx.get(f"{GW_URL}{GW_PREFIX}/health", timeout=5.0)
        return r.status_code == 200 and r.json().get("status") == "ready"
    except httpx.HTTPError:
        return False


def _l4_ready() -> bool:
    try:
        r = httpx.get(f"{L4_URL}/health", timeout=5.0)
        return r.status_code == 200 and r.json().get("status") == "ready"
    except httpx.HTTPError:
        return False


@pytest.fixture(autouse=True)
def live_stack_guard():
    _require_live()
    if not _gw_ready():
        pytest.fail(
            f"Gateway not ready at {GW_URL}. Run: .\\scripts\\bootstrap-fullstack.ps1"
        )


def test_live_gateway_health():
    resp = httpx.get(f"{GW_URL}{GW_PREFIX}/health", timeout=10.0)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_live_solver_health():
    if not _l4_ready():
        pytest.fail(f"Solver not ready at {L4_URL}. Start fleet-route docker backend.")
    resp = httpx.get(f"{L4_URL}/health", timeout=10.0)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_live_chat_process_clarifying_or_ready():
    resp = httpx.post(
        f"{GW_URL}{GW_PREFIX}/chat_process",
        json={
            "message": "Đi Huế 3 ngày",
            "history": [],
            "current_contract": {
                "destination": None,
                "budget_max": None,
                "radius_km": 10.0,
                "num_days": 1,
                "tags": [],
                "locked_pois": [],
            },
        },
        timeout=60.0,
    )
    if resp.status_code == 429:
        pytest.fail(f"LLM rate limited: {resp.text[:300]}")
    assert resp.status_code == 200, resp.text[:500]
    body = resp.json()
    assert body["status"] in ("clarifying", "ready")
    if body["status"] == "clarifying":
        assert body["updated_contract"]["destination"] == "Huế"
        assert body["updated_contract"]["num_days"] == 3


def test_live_plan_trip_stream_sse_stages():
    with httpx.Client(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
        with client.stream(
            "POST",
            f"{GW_URL}{GW_PREFIX}/plan_trip_stream",
            json={
                "user_prompt": "Đi Huế 2 ngày ngân sách 1 triệu, thích văn hóa",
                "hotel_lat": 16.4637,
                "hotel_lon": 107.5909,
                "hotel_name": "Pilgrimage Village",
                "num_days": 2,
            },
        ) as response:
            if response.status_code == 429:
                pytest.fail(f"LLM rate limited: {response.read().decode()[:300]}")
            assert response.status_code == 200, response.read().decode()[:500]

            stages: list[str] = []
            buf = ""
            for chunk in response.iter_text():
                buf += chunk
                while "\n\n" in buf:
                    block, buf = buf.split("\n\n", 1)
                    for line in block.splitlines():
                        if not line.startswith("data: "):
                            continue
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            stages.append("[DONE]")
                            continue
                        try:
                            data = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        if "stage" in data:
                            stages.append(data["stage"])

    assert "intent_extraction_started" in stages
    assert "narrative_completed" in stages
    assert "[DONE]" in stages
    assert len(stages) >= 7


def test_live_plan_trip_returns_layer4():
    resp = httpx.post(
        f"{GW_URL}{GW_PREFIX}/plan_trip",
        json={
            "user_prompt": "Đi Huế 2 ngày ngân sách 1 triệu, thích văn hóa",
            "hotel_lat": 16.4637,
            "hotel_lon": 107.5909,
            "hotel_name": "Pilgrimage Village",
            "num_days": 2,
        },
        timeout=180.0,
    )
    if resp.status_code == 429:
        pytest.fail(f"LLM rate limited: {resp.text[:300]}")
    if resp.status_code == 500:
        pytest.fail(f"Gateway error (check DB ingest + LLM key): {resp.text[:400]}")
    assert resp.status_code == 200, resp.text[:500]
    data = resp.json()
    assert data["status"] in ("success", "partial", "error")
    if data["status"] in ("success", "partial"):
        l4 = data.get("layer4_result")
        assert l4 is not None
        assert len(l4.get("days", [])) >= 1
