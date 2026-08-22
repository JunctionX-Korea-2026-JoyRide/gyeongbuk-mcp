"""MCP tool for downloaded regional safety grades."""

from __future__ import annotations

from typing import Annotated

from fastmcp.exceptions import ToolError
from pydantic import Field

from clients.local_data import LocalSafetyClient
from clients.public_data import DataSourceError
from config import Settings
from models.safety import SafetyCategory, SafetyGradeResult
from services.safety import SafetyService


async def get_safety_grade(
    region: Annotated[str, Field(min_length=1, max_length=100)],
    category: SafetyCategory = "crime",
    publication_year: Annotated[int | None, Field(ge=2015, le=2100)] = None,
) -> SafetyGradeResult:
    """Return an official relative safety grade; lower grades are safer."""

    settings = Settings.from_env()
    service = SafetyService(LocalSafetyClient(settings.local_database_path))
    try:
        return await service.get_safety_grade(region, category, publication_year)
    except DataSourceError as exc:
        raise ToolError(str(exc)) from exc
