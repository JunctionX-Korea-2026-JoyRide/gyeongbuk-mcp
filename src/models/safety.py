"""Structured outputs for official regional safety grades."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from models.location import DataSourceMetadata

SafetyCategory = Literal[
    "traffic_accident",
    "fire",
    "crime",
    "life_safety",
    "suicide",
    "infectious_disease",
]


class SafetyGradeResult(BaseModel):
    """Relative regional safety grade for one official safety category."""

    region_name: str
    region_level: str
    category: SafetyCategory
    grade: int = Field(ge=1, le=5)
    grade_direction: str
    publication_year: int
    statistics_year: int
    comparison_group: str
    source: DataSourceMetadata
    warnings: list[str] = Field(default_factory=list)
