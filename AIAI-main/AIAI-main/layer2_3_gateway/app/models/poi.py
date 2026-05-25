"""POI (Point of Interest) ORM model for Layer 3 spatial database."""

import uuid
from datetime import datetime
from typing import Any, Optional

from geoalchemy2.types import Geography  # NOT Geometry — measures in meters natively
from geoalchemy2.functions import ST_AsGeoJSON, ST_DWithin, ST_MakePoint
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column, DateTime, Float, Integer, String, Boolean, Text, Index,
    UniqueConstraint, select, func,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PointOfInterest(Base):
    """POI stored in PostGIS with vector embeddings for semantic search."""

    __tablename__ = "poi"
    __table_args__ = (
        # HNSW index for pgvector semantic similarity (cosine distance)
        Index(
            "idx_poi_tags_vector",
            "tags_vector",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"tags_vector": "vector_cosine_ops"},
        ),
        # GiST spatial index for PostGIS ST_DWithin queries
        Index(
            "idx_poi_coordinates",
            "coordinates",
            postgresql_using="gist",
        ),
        # B-tree indexes for hard constraint filters
        Index("idx_poi_price", "price"),
        Index("idx_poi_weather_penalty", "weather_penalty"),
        # Composite unique: same name at same location = duplicate
        UniqueConstraint("name", "coordinates", name="uq_poi_name_coord"),
        {"schema": "travel"},
    )

    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # GeoAlchemy2: POINT(lon, lat) in SRID 4326 — Geography type
    coordinates = Column(Geography("POINT", srid=4326), nullable=False)

    # pgvector: embedding for semantic similarity search
    tags_vector = Column(Vector(1536), nullable=True)

    # Travel attributes
    visit_duration_min: Mapped[int] = mapped_column(Integer, default=60)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    entrance_fee: Mapped[float] = mapped_column(Float, default=0.0)
    open_time: Mapped[int] = mapped_column(Integer, default=480)   # 08:00
    close_time: Mapped[int] = mapped_column(Integer, default=1260) # 21:00
    priority_score: Mapped[float] = mapped_column(Float, default=0.5)
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    # Weather & outdoor
    is_outdoor: Mapped[bool] = mapped_column(Boolean, default=False)
    weather_penalty: Mapped[float] = mapped_column(Float, default=0.0)

    # Timestamps
    datetime_created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    datetime_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    @classmethod
    async def search_within_radius(
        cls,
        lat: float, lon: float, radius_m: float,
        extra_conditions: list[Any] = None,
        limit: int = 50,
        database_session: Optional[AsyncSession] = None,
    ):
        """Spatial search: find POIs within radius, ordered by distance."""
        center = func.ST_SetSRID(ST_MakePoint(lon, lat), 4326)
        conditions = [ST_DWithin(cls.coordinates, center, radius_m, use_spheroid=True)]
        if extra_conditions:
            conditions.extend(extra_conditions)

        _stmt = select(
            cls.uuid, cls.name, cls.category, cls.description,
            cls.visit_duration_min, cls.price, cls.entrance_fee,
            cls.open_time, cls.close_time, cls.priority_score,
            cls.tags, cls.is_outdoor, cls.weather_penalty,
            ST_AsGeoJSON(cls.coordinates).label("geojson_coordinates"),
        ).where(*conditions).limit(limit)

        _result = await database_session.execute(_stmt)
        return _result.fetchall()
