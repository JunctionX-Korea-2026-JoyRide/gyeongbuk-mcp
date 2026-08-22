"""MCP tool for downloaded resident-registration population data."""

from __future__ import annotations

from typing import Annotated

from fastmcp.exceptions import ToolError
from pydantic import Field

from clients.local_data import LocalDemographicsClient
from clients.public_data import DataSourceError
from config import Settings
from models.demographics import AgePopulationRatioResult
from services.demographics import DemographicsService


async def get_age_population_ratio(
    region: Annotated[str, Field(min_length=1, max_length=100)],
    age_from: Annotated[int, Field(ge=0, le=130)] = 70,
    age_to: Annotated[int, Field(ge=0, le=130)] = 79,
    as_of: Annotated[str | None, Field(pattern=r"^\d{6}$")] = None,
) -> AgePopulationRatioResult:
    """Return the resident-population share for an inclusive age range."""

    if age_to < age_from:
        raise ToolError("age_to는 age_from 이상이어야 합니다.")
    settings = Settings.from_env()
    service = DemographicsService(LocalDemographicsClient(settings.local_database_path))
    try:
        return await service.get_age_population_ratio(region, age_from, age_to, as_of)
    except DataSourceError as exc:
        raise ToolError(str(exc)) from exc
