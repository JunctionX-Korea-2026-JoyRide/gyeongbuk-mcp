"""Regression tests for the documented public MCP output contracts."""

import pytest
from pydantic import BaseModel

from models.accessibility import (
    BusRouteFrequency,
    BusStopAccessibility,
    BusStopSearchResult,
    Hospital,
    HospitalSearchResult,
    MarketSearchResult,
    NeighborhoodRecommendation,
    NeighborhoodRecommendationResult,
    TraditionalMarket,
)
from models.demographics import AgePopulationRatioResult
from models.location import Coordinates, DataSourceMetadata
from models.safety import SafetyGradeResult


@pytest.mark.parametrize(
    ("model", "expected_fields"),
    [
        (Coordinates, ("latitude", "longitude")),
        (
            DataSourceMetadata,
            ("source_name", "source_url", "as_of", "is_estimated", "estimation_method"),
        ),
        (
            Hospital,
            (
                "institution_id",
                "name",
                "address",
                "phone",
                "institution_type",
                "departments",
                "coordinates",
                "distance_m",
                "estimated_walk_minutes",
            ),
        ),
        (
            HospitalSearchResult,
            (
                "hospitals",
                "max_walk_minutes",
                "walking_speed_m_per_minute",
                "source",
                "warnings",
            ),
        ),
        (
            BusRouteFrequency,
            (
                "route_id",
                "route_number",
                "route_type",
                "daily_trips",
                "first_bus",
                "last_bus",
                "interval_minutes",
                "frequency_basis",
            ),
        ),
        (
            BusStopAccessibility,
            (
                "stop_id",
                "name",
                "coordinates",
                "distance_m",
                "estimated_walk_minutes",
                "estimated_daily_trips",
                "routes",
            ),
        ),
        (
            BusStopSearchResult,
            ("stops", "service_day", "minimum_daily_trips", "source", "warnings"),
        ),
        (
            TraditionalMarket,
            (
                "name",
                "address",
                "market_type",
                "opening_cycle",
                "coordinates",
                "distance_m",
                "estimated_walk_minutes",
                "reference_date",
            ),
        ),
        (MarketSearchResult, ("markets", "source", "warnings")),
        (
            NeighborhoodRecommendation,
            (
                "rank",
                "candidate_name",
                "anchor",
                "score",
                "nearest_market",
                "nearest_hospital",
                "qualifying_bus_stops",
                "reasons",
                "caveats",
            ),
        ),
        (
            NeighborhoodRecommendationResult,
            ("region", "recommendations", "criteria", "warnings"),
        ),
        (
            AgePopulationRatioResult,
            (
                "region_code",
                "region_name",
                "region_level",
                "age_from",
                "age_to",
                "age_population",
                "total_population",
                "ratio_percent",
                "as_of",
                "source",
                "warnings",
            ),
        ),
        (
            SafetyGradeResult,
            (
                "region_name",
                "region_level",
                "category",
                "grade",
                "grade_direction",
                "publication_year",
                "statistics_year",
                "comparison_group",
                "source",
                "warnings",
            ),
        ),
    ],
)
def test_documented_output_model_fields(
    model: type[BaseModel], expected_fields: tuple[str, ...]
) -> None:
    assert tuple(model.model_fields) == expected_fields
