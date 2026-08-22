"""Structured outputs for nearby commercial-business searches."""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.location import Coordinates, DataSourceMetadata


class Store(BaseModel):
    """One operating commercial business from the official store dataset."""

    business_id: str
    name: str
    branch_name: str | None = None
    industry_large_code: str
    industry_large_name: str
    industry_medium_code: str
    industry_medium_name: str
    industry_small_code: str
    industry_small_name: str
    standard_industry_code: str | None = None
    standard_industry_name: str | None = None
    address: str
    coordinates: Coordinates
    distance_m: float = Field(ge=0)
    estimated_walk_minutes: int = Field(ge=0)


class StoreSearchResult(BaseModel):
    """Nearby store search result with calculation and source metadata."""

    stores: list[Store]
    radius_m: int = Field(ge=1, le=2000)
    walking_speed_m_per_minute: float = Field(gt=0)
    source: DataSourceMetadata
    warnings: list[str] = Field(default_factory=list)
