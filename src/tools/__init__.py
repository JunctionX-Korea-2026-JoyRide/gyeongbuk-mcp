"""FastMCP tool functions."""

from tools.accessibility import (
    recommend_car_free_neighborhoods,
    search_nearby_bus_stops,
    search_nearby_hospitals,
    search_nearby_markets,
)
from tools.demographics import get_age_population_ratio
from tools.safety import get_safety_grade

__all__ = [
    "get_age_population_ratio",
    "get_safety_grade",
    "recommend_car_free_neighborhoods",
    "search_nearby_bus_stops",
    "search_nearby_hospitals",
    "search_nearby_markets",
]
