"""Shared geographic models."""

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """A WGS84 latitude/longitude pair."""

    latitude: float = Field(ge=33.0, le=39.5)
    longitude: float = Field(ge=124.0, le=132.0)


class DataSourceMetadata(BaseModel):
    """Provenance and freshness information returned with public data."""

    source_name: str
    source_url: str
    as_of: str | None = None
    is_estimated: bool = False
    estimation_method: str | None = None
