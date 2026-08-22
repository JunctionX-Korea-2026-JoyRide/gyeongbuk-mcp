"""Structured outputs for local accessibility tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from models.location import Coordinates, DataSourceMetadata


class Hospital(BaseModel):
    """A nearby medical institution."""

    institution_id: str
    name: str
    address: str
    phone: str | None = None
    institution_type: str | None = None
    departments: list[str] = Field(default_factory=list)
    coordinates: Coordinates
    distance_m: float = Field(ge=0)
    estimated_walk_minutes: int = Field(ge=0)


class HospitalSearchResult(BaseModel):
    """Nearby hospital search result with calculation metadata."""

    hospitals: list[Hospital]
    max_walk_minutes: int
    walking_speed_m_per_minute: float
    source: DataSourceMetadata
    warnings: list[str] = Field(default_factory=list)


class BusRouteFrequency(BaseModel):
    """Estimated daily frequency for one route."""

    route_id: str
    route_number: str
    route_type: str | None = None
    daily_trips: int | None = Field(default=None, ge=0)
    first_bus: str | None = None
    last_bus: str | None = None
    interval_minutes: int | None = Field(default=None, ge=1)
    frequency_basis: (
        Literal["published_trip_count", "conservative_interval_estimate", "api_summary"] | None
    ) = None


class BusStopAccessibility(BaseModel):
    """A stop and its estimated daily service level."""

    stop_id: str
    name: str
    coordinates: Coordinates
    distance_m: float = Field(ge=0)
    estimated_walk_minutes: int = Field(ge=0)
    estimated_daily_trips: int | None = Field(default=None, ge=0)
    routes: list[BusRouteFrequency] = Field(default_factory=list)


class BusStopSearchResult(BaseModel):
    """Nearby bus-stop search result."""

    stops: list[BusStopAccessibility]
    service_day: str
    minimum_daily_trips: int
    source: DataSourceMetadata
    warnings: list[str] = Field(default_factory=list)


class TraditionalMarket(BaseModel):
    """A government-recognized traditional market."""

    name: str
    address: str
    market_type: str | None = None
    opening_cycle: str | None = None
    coordinates: Coordinates
    distance_m: float = Field(ge=0)
    estimated_walk_minutes: int = Field(ge=0)
    reference_date: str | None = None


class MarketSearchResult(BaseModel):
    """Nearby traditional-market search result."""

    markets: list[TraditionalMarket]
    source: DataSourceMetadata
    warnings: list[str] = Field(default_factory=list)


class NeighborhoodRecommendation(BaseModel):
    """A market-centered proxy for a walkable neighborhood candidate."""

    rank: int = Field(ge=1)
    candidate_name: str
    anchor: Coordinates
    score: float = Field(ge=0, le=100)
    nearest_market: TraditionalMarket
    nearest_hospital: Hospital
    qualifying_bus_stops: list[BusStopAccessibility]
    reasons: list[str]
    caveats: list[str]


class NeighborhoodRecommendationResult(BaseModel):
    """Ranked car-free neighborhood candidates."""

    region: str
    recommendations: list[NeighborhoodRecommendation]
    criteria: dict[str, str | int | float]
    warnings: list[str] = Field(default_factory=list)
