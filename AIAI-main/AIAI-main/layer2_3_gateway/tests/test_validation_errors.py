"""Tests for detailed LLM intent validation checks in trip planner."""
import pytest
from fastapi import HTTPException
from app.schemas.trip import TripPlanRequest, LLMDataContract
from app.api.trip_planner import _run_pipeline
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.anyio


async def test_run_pipeline_short_prompt():
    """Verify that a prompt less than 10 characters raises LLM_PARSE_ERROR."""
    request = TripPlanRequest(user_prompt="Đi Huế")
    with pytest.raises(HTTPException) as exc_info:
        await _run_pipeline(request)
    
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == "LLM_PARSE_ERROR"


@patch("app.api.trip_planner.llm_service.extract_intent", new_callable=AsyncMock)
async def test_run_pipeline_unsupported_destination(mock_extract):
    """Verify that unsupported destinations raise LLM_PARSE_ERROR."""
    mock_extract.return_value = LLMDataContract(
        destination="Hà Nội",
        num_days=2,
        tags=["cultural"],
    )
    request = TripPlanRequest(user_prompt="Lên kế hoạch đi Hà Nội du lịch trong 2 ngày")
    
    with pytest.raises(HTTPException) as exc_info:
        await _run_pipeline(request)
        
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == "LLM_PARSE_ERROR"
    assert "Huế" in exc_info.value.detail["message"]


@patch("app.api.trip_planner.llm_service.extract_intent", new_callable=AsyncMock)
async def test_run_pipeline_insufficient_intent(mock_extract):
    """Verify that empty/general intent tags raise LLM_INSUFFICIENT_INTENT."""
    mock_extract.return_value = LLMDataContract(
        destination="Huế",
        num_days=2,
        tags=["general"],
    )
    request = TripPlanRequest(user_prompt="Lên lịch đi Huế 2 ngày")
    
    with pytest.raises(HTTPException) as exc_info:
        await _run_pipeline(request)
        
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == "LLM_INSUFFICIENT_INTENT"


@patch("app.api.trip_planner.llm_service.extract_intent", new_callable=AsyncMock)
async def test_run_pipeline_invalid_duration(mock_extract):
    """Verify that num_days > 7 raises LLM_INVALID_DURATION."""
    mock_extract.return_value = LLMDataContract(
        destination="Huế",
        num_days=10,
        tags=["cultural"],
    )
    request = TripPlanRequest(user_prompt="Tôi muốn đi Huế 10 ngày")
    
    with pytest.raises(HTTPException) as exc_info:
        await _run_pipeline(request)
        
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == "LLM_INVALID_DURATION"


@patch("app.api.trip_planner.llm_service.extract_intent", new_callable=AsyncMock)
async def test_run_pipeline_invalid_budget(mock_extract):
    """Verify that budget < 50000 raises LLM_INVALID_BUDGET."""
    mock_extract.return_value = LLMDataContract(
        destination="Huế",
        num_days=2,
        budget_max=1000,
        tags=["cultural"],
    )
    request = TripPlanRequest(user_prompt="Tôi muốn đi Huế 2 ngày ngân sách 1 nghìn")
    
    with pytest.raises(HTTPException) as exc_info:
        await _run_pipeline(request)
        
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == "LLM_INVALID_BUDGET"
