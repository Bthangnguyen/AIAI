import json as json_lib
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy import func, select

from app.config import settings
from app.database import AsyncSessionFactory
from app.models.poi import PointOfInterest
from app.schemas.admin import (
    AdminPoiItem,
    AdminPoiListResponse,
    AdminPoiQaItem,
    AdminPoiQaListResponse,
    AdminPoiUpdateRequest,
    PoiQaSummaryResponse,
)
from app.services.poi_qa import (
    PoiQaIssueType,
    PoiQaRecord,
    compute_qa_summary,
    filter_pois_by_issue,
)
from app.api.trip_planner import limiter
router = APIRouter(prefix="/v1/admin", tags=["admin"])


async def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not settings.ADMIN_ENABLED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin API disabled")
    if settings.ADMIN_TOKEN and x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


def _row_to_admin_poi(poi: PointOfInterest, geojson: str | None) -> AdminPoiItem:
    parsed = json_lib.loads(geojson) if geojson else None
    lat = parsed["coordinates"][1] if parsed else 0.0
    lon = parsed["coordinates"][0] if parsed else 0.0
    return AdminPoiItem(
        uuid=str(poi.uuid),
        name=poi.name,
        category=poi.category,
        tags=list(poi.tags or []),
        latitude=lat,
        longitude=lon,
        visit_duration_min=poi.visit_duration_min,
        open_time=poi.open_time,
        close_time=poi.close_time,
        has_embedding=poi.tags_vector is not None,
    )


@router.get("/pois", response_model=AdminPoiListResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def list_admin_pois(
    request: Request,
    _: None = Depends(require_admin),
    limit: int = Query(default=50, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
):
    POI = PointOfInterest
    filters = []
    if q and q.strip():
        filters.append(POI.name.ilike(f"%{q.strip()}%"))

    async with AsyncSessionFactory() as db_session:
        count_stmt = select(func.count()).select_from(POI)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = int((await db_session.execute(count_stmt)).scalar_one())

        stmt = select(POI, ST_AsGeoJSON(POI.coordinates).label("geojson")).order_by(POI.name)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.limit(limit).offset(offset)

        result = await db_session.execute(stmt)
        items = [_row_to_admin_poi(row.PointOfInterest, row.geojson) for row in result.all()]

    return AdminPoiListResponse(items=items, total=total, limit=limit, offset=offset)


async def _load_all_poi_qa_records() -> list[PoiQaRecord]:
    POI = PointOfInterest
    async with AsyncSessionFactory() as db_session:
        stmt = select(POI, ST_AsGeoJSON(POI.coordinates).label("geojson")).order_by(POI.name)
        result = await db_session.execute(stmt)
        records: list[PoiQaRecord] = []
        for row in result.all():
            admin_item = _row_to_admin_poi(row.PointOfInterest, row.geojson)
            records.append(
                PoiQaRecord(
                    uuid=admin_item.uuid,
                    name=admin_item.name,
                    category=admin_item.category,
                    tags=admin_item.tags,
                    latitude=admin_item.latitude,
                    longitude=admin_item.longitude,
                    visit_duration_min=admin_item.visit_duration_min,
                    open_time=admin_item.open_time,
                    close_time=admin_item.close_time,
                    has_embedding=admin_item.has_embedding,
                )
            )
        return records


def _to_qa_item(record: PoiQaRecord, duplicate_group: str | None = None) -> AdminPoiQaItem:
    return AdminPoiQaItem(
        uuid=record.uuid,
        name=record.name,
        category=record.category,
        tags=record.tags,
        latitude=record.latitude,
        longitude=record.longitude,
        visit_duration_min=record.visit_duration_min,
        open_time=record.open_time,
        close_time=record.close_time,
        has_embedding=record.has_embedding,
        duplicate_group=duplicate_group,
    )


@router.get("/pois/qa-summary", response_model=PoiQaSummaryResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def admin_poi_qa_summary(
    request: Request,
    _: None = Depends(require_admin),
):
    summary = compute_qa_summary(await _load_all_poi_qa_records())
    return PoiQaSummaryResponse(
        wrong_coords=summary.wrong_coords,
        duplicates=summary.duplicates,
        missing_hours=summary.missing_hours,
        missing_duration=summary.missing_duration,
        missing_embedding=summary.missing_embedding,
    )


@router.get("/pois/qa", response_model=AdminPoiQaListResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def admin_poi_qa_list(
    request: Request,
    issue: PoiQaIssueType = Query(...),
    _: None = Depends(require_admin),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    all_records = await _load_all_poi_qa_records()
    filtered, dup_map = filter_pois_by_issue(all_records, issue)
    slice = filtered[offset : offset + limit]
    items = [_to_qa_item(record, dup_map.get(record.uuid)) for record in slice]
    return AdminPoiQaListResponse(
        issue=issue,
        items=items,
        total=len(filtered),
        limit=limit,
        offset=offset,
    )


@router.patch("/pois/{poi_uuid}", response_model=AdminPoiItem)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def update_admin_poi(
    request: Request,
    poi_uuid: UUID,
    body: AdminPoiUpdateRequest,
    _: None = Depends(require_admin),
):
    if body.category is None and body.tags is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No fields to update")

    POI = PointOfInterest
    async with AsyncSessionFactory() as db_session:
        stmt = select(POI, ST_AsGeoJSON(POI.coordinates).label("geojson")).where(POI.uuid == poi_uuid)
        result = await db_session.execute(stmt)
        row = result.first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")

        poi = row.PointOfInterest
        if body.category is not None:
            poi.category = body.category.strip()
        if body.tags is not None:
            poi.tags = body.tags

        await db_session.commit()
        await db_session.refresh(poi)

        refreshed = await db_session.execute(
            select(POI, ST_AsGeoJSON(POI.coordinates).label("geojson")).where(POI.uuid == poi_uuid)
        )
        updated = refreshed.first()
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")

        return _row_to_admin_poi(updated.PointOfInterest, updated.geojson)
