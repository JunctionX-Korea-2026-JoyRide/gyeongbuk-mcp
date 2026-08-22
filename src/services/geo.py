"""Small, dependency-free geographic calculations."""

from __future__ import annotations

import math

EARTH_RADIUS_M = 6_371_008.8


def haversine_distance_m(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """Return the great-circle distance between two WGS84 coordinates."""

    lat_a = math.radians(latitude_a)
    lat_b = math.radians(latitude_b)
    delta_lat = lat_b - lat_a
    delta_lon = math.radians(longitude_b - longitude_a)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(haversine))


def estimated_walk_minutes(distance_m: float, speed_m_per_minute: float) -> int:
    """Convert straight-line distance to a conservative whole-minute estimate."""

    if speed_m_per_minute <= 0:
        raise ValueError("Walking speed must be positive")
    return math.ceil(distance_m / speed_m_per_minute)
