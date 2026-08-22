"""Structured outputs for resident-registration population tools."""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.location import DataSourceMetadata


class AgePopulationRatioResult(BaseModel):
    """Population count and share for one inclusive age range."""

    region_code: str
    region_name: str
    region_level: str
    age_from: int = Field(ge=0)
    age_to: int = Field(ge=0)
    age_population: int = Field(ge=0)
    total_population: int = Field(ge=0)
    ratio_percent: float = Field(ge=0, le=100)
    as_of: str
    source: DataSourceMetadata
    warnings: list[str] = Field(default_factory=list)
