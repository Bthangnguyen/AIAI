from pydantic import BaseModel, Field


class AdminPoiItem(BaseModel):
    uuid: str
    name: str
    category: str
    tags: list[str] = Field(default_factory=list)
    latitude: float
    longitude: float
    visit_duration_min: int
    open_time: int
    close_time: int
    has_embedding: bool


class AdminPoiListResponse(BaseModel):
    items: list[AdminPoiItem]
    total: int
    limit: int
    offset: int


class AdminPoiUpdateRequest(BaseModel):
    category: str | None = None
    tags: list[str] | None = None


class PoiQaSummaryResponse(BaseModel):
    wrong_coords: int
    duplicates: int
    missing_hours: int
    missing_duration: int
    missing_embedding: int


class AdminPoiQaItem(AdminPoiItem):
    duplicate_group: str | None = None


class AdminPoiQaListResponse(BaseModel):
    issue: str
    items: list[AdminPoiQaItem]
    total: int
    limit: int
    offset: int