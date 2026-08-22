"""MCP tools for local accessibility and neighborhood recommendations."""

from __future__ import annotations

from typing import Annotated

from fastmcp.exceptions import ToolError
from pydantic import Field

from clients.hira import HiraClient
from clients.local_data import LocalHiraClient, LocalMarketClient, LocalTagoClient
from clients.markets import MarketClient
from clients.public_data import DataSourceError, HttpJsonGateway
from clients.tago import ServiceDay, TagoClient
from config import Settings
from models.accessibility import (
    BusStopSearchResult,
    HospitalSearchResult,
    MarketSearchResult,
    NeighborhoodRecommendationResult,
)
from models.location import Coordinates
from services.accessibility import AccessibilityService
from services.recommendations import NeighborhoodRecommendationService

Latitude = Annotated[float, Field(ge=33.0, le=39.5)]
Longitude = Annotated[float, Field(ge=124.0, le=132.0)]
PositiveMinutes = Annotated[int, Field(ge=1, le=120)]


async def search_nearby_hospitals(
    latitude: Latitude,
    longitude: Longitude,
    max_walk_minutes: PositiveMinutes = 15,
    department_code: str | None = None,
    include_departments: bool = False,
) -> HospitalSearchResult:
    """Find hospitals within an estimated straight-line walking time."""

    try:
        return await _accessibility_service().search_hospitals(
            Coordinates(latitude=latitude, longitude=longitude),
            max_walk_minutes,
            department_code,
            include_departments,
        )
    except DataSourceError as exc:
        raise ToolError(str(exc)) from exc


async def search_nearby_bus_stops(
    latitude: Latitude,
    longitude: Longitude,
    max_walk_minutes: PositiveMinutes = 10,
    minimum_daily_trips: Annotated[int, Field(ge=1, le=1000)] = 5,
    service_day: ServiceDay = "weekday",
) -> BusStopSearchResult:
    """Find nearby stops meeting an estimated daily-service threshold."""

    try:
        return await _accessibility_service().search_bus_stops(
            Coordinates(latitude=latitude, longitude=longitude),
            max_walk_minutes,
            minimum_daily_trips,
            service_day,
        )
    except DataSourceError as exc:
        raise ToolError(str(exc)) from exc


async def search_nearby_markets(
    region: str,
    latitude: Latitude,
    longitude: Longitude,
    max_walk_minutes: PositiveMinutes = 15,
) -> MarketSearchResult:
    """Find registered traditional markets within an estimated walking time."""

    try:
        return await _accessibility_service().search_markets(
            region,
            Coordinates(latitude=latitude, longitude=longitude),
            max_walk_minutes,
        )
    except DataSourceError as exc:
        raise ToolError(str(exc)) from exc


async def recommend_car_free_neighborhoods(
    region: str = "포항시",
    hospital_max_walk_minutes: PositiveMinutes = 15,
    bus_max_walk_minutes: PositiveMinutes = 10,
    minimum_daily_bus_trips: Annotated[int, Field(ge=1, le=1000)] = 5,
    service_day: ServiceDay = "weekday",
    candidate_limit: Annotated[int, Field(ge=1, le=50)] = 20,
    result_limit: Annotated[int, Field(ge=1, le=10)] = 5,
) -> NeighborhoodRecommendationResult:
    """Rank market-centered areas that pass hospital and bus constraints."""

    try:
        service = NeighborhoodRecommendationService(_accessibility_service())
        return await service.recommend(
            region=region,
            hospital_max_walk_minutes=hospital_max_walk_minutes,
            bus_max_walk_minutes=bus_max_walk_minutes,
            minimum_daily_bus_trips=minimum_daily_bus_trips,
            service_day=service_day,
            candidate_limit=candidate_limit,
            result_limit=result_limit,
        )
    except DataSourceError as exc:
        raise ToolError(str(exc)) from exc


def _accessibility_service() -> AccessibilityService:
    settings = Settings.from_env()
    if settings.data_mode == "file":
        return AccessibilityService(
            LocalHiraClient(settings.local_database_path),
            LocalTagoClient(settings.local_database_path),
            LocalMarketClient(settings.local_database_path),
            settings.walking_speed_m_per_minute,
            file_mode=True,
        )
    gateway = HttpJsonGateway(settings.http_timeout_seconds)
    return AccessibilityService(
        HiraClient(gateway, settings.data_go_kr_service_key),
        TagoClient(gateway, settings.data_go_kr_service_key),
        MarketClient(gateway, settings.data_go_kr_service_key),
        settings.walking_speed_m_per_minute,
    )
