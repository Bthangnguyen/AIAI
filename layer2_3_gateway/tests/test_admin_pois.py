"""Tests for admin POI list endpoint."""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from fastapi import status

pytestmark = pytest.mark.anyio


async def test_admin_pois_disabled(client: AsyncClient):
    with patch("app.api.admin_pois.settings.ADMIN_ENABLED", False):
        response = await client.get("/admin/pois")
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_admin_pois_search_and_pagination(client: AsyncClient):
    poi = SimpleNamespace(
        uuid=uuid.uuid4(),
        name="Đại Nội Huế",
        category="Di tích",
        tags=["lịch sử"],
        visit_duration_min=120,
        open_time=480,
        close_time=1260,
        tags_vector=[0.0],
    )
    row = SimpleNamespace(PointOfInterest=poi, geojson='{"type":"Point","coordinates":[107.5784,16.4678]}')

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    list_result = MagicMock()
    list_result.all.return_value = [row]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[count_result, list_result])
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("app.api.admin_pois.AsyncSessionFactory", return_value=mock_session):
        response = await client.get("/admin/pois?q=Đại&limit=10&offset=0")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Đại Nội Huế"
    assert body["items"][0]["has_embedding"] is True
    assert body["items"][0]["latitude"] == 16.4678


async def test_admin_poi_qa_summary(client: AsyncClient):
    records = [
        SimpleNamespace(
            uuid=uuid.uuid4(),
            name="Bad",
            category="Test",
            tags=[],
            visit_duration_min=0,
            open_time=1200,
            close_time=600,
            tags_vector=None,
        )
    ]
    row = SimpleNamespace(
        PointOfInterest=records[0],
        geojson='{"type":"Point","coordinates":[107.58,16.47]}',
    )
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[row])))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("app.api.admin_pois.AsyncSessionFactory", return_value=mock_session):
        response = await client.get("/admin/pois/qa-summary")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["missing_duration"] == 1
    assert body["missing_embedding"] == 1


async def test_admin_poi_patch_validation(client: AsyncClient):
    poi_id = uuid.uuid4()
    response = await client.patch(f"/admin/pois/{poi_id}", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_admin_poi_patch_not_found(client: AsyncClient):
    poi_id = uuid.uuid4()
    mock_session = AsyncMock()
    not_found = MagicMock()
    not_found.first.return_value = None
    mock_session.execute = AsyncMock(return_value=not_found)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("app.api.admin_pois.AsyncSessionFactory", return_value=mock_session):
        response = await client.patch(f"/admin/pois/{poi_id}", json={"category": "culture"})

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_admin_poi_patch_updates_category_and_tags(client: AsyncClient):
    poi_id = uuid.uuid4()
    poi = SimpleNamespace(
        uuid=poi_id,
        name="Đại Nội Huế",
        category="Di tích",
        tags=["lịch sử"],
        visit_duration_min=120,
        open_time=480,
        close_time=1260,
        tags_vector=[0.0],
    )
    row = SimpleNamespace(PointOfInterest=poi, geojson='{"type":"Point","coordinates":[107.5784,16.4678]}')
    updated_row = SimpleNamespace(
        PointOfInterest=SimpleNamespace(
            uuid=poi_id,
            name="Đại Nội Huế",
            category="culture",
            tags=["unesco"],
            visit_duration_min=120,
            open_time=480,
            close_time=1260,
            tags_vector=[0.0],
        ),
        geojson='{"type":"Point","coordinates":[107.5784,16.4678]}',
    )

    mock_session = AsyncMock()
    lookup = MagicMock()
    lookup.first.side_effect = [row, updated_row]
    mock_session.execute = AsyncMock(return_value=lookup)
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("app.api.admin_pois.AsyncSessionFactory", return_value=mock_session):
        response = await client.patch(
            f"/admin/pois/{poi_id}",
            json={"category": "culture", "tags": ["unesco"]},
        )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["category"] == "culture"
    assert body["tags"] == ["unesco"]
    mock_session.commit.assert_awaited_once()
