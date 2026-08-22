"""MCP tool for nearby commercial-business searches."""

from __future__ import annotations

from typing import Annotated

from fastmcp.exceptions import ToolError
from pydantic import Field, StringConstraints

from clients.local_data import LocalStoreClient
from clients.public_data import DataSourceError, HttpJsonGateway
from clients.stores import StoreClient
from config import Settings
from models.location import Coordinates
from models.stores import StoreSearchResult
from services.stores import StoreService

Latitude = Annotated[float, Field(ge=33.0, le=39.5)]
Longitude = Annotated[float, Field(ge=124.0, le=132.0)]
RadiusMeters = Annotated[int, Field(ge=1, le=2000)]
IndustryCode = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_upper=True,
        pattern=r"^[0-9A-Z]{2}(?:[0-9A-Z]{2}){0,2}$",
    ),
]
SearchText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
ResultLimit = Annotated[int, Field(ge=1, le=100)]


async def search_nearby_stores(
    latitude: Latitude,
    longitude: Longitude,
    radius_m: RadiusMeters = 1000,
    industry_code: IndustryCode | None = None,
    industry_name: SearchText | None = None,
    name_query: SearchText | None = None,
    result_limit: ResultLimit = 20,
) -> StoreSearchResult:
    """Find operating commercial businesses within a straight-line radius."""

    try:
        settings = Settings.from_env()
        if settings.data_mode == "file":
            client = LocalStoreClient(settings.local_database_path)
            service = StoreService(
                client,
                settings.walking_speed_m_per_minute,
                file_mode=True,
            )
        else:
            gateway = HttpJsonGateway(settings.http_timeout_seconds)
            service = StoreService(
                StoreClient(gateway, settings.data_go_kr_service_key),
                settings.walking_speed_m_per_minute,
            )
        return await service.search_nearby(
            Coordinates(latitude=latitude, longitude=longitude),
            radius_m,
            industry_code,
            industry_name,
            name_query,
            result_limit,
        )
    except DataSourceError as exc:
        raise ToolError(str(exc)) from exc
