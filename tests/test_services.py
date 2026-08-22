"""Tests for accessibility aggregation and recommendation scoring."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from clients.hira import HiraClient
from clients.markets import MarketClient
from clients.tago import TagoClient
from models.location import Coordinates
from services.accessibility import AccessibilityService
from services.geo import estimated_walk_minutes, haversine_distance_m
from services.recommendations import NeighborhoodRecommendationService


class FakeGateway:
    """Return fixture envelopes based on the requested endpoint."""

    async def get(self, url: str, params: Mapping[str, str | int | float]) -> dict[str, Any]:
        del params
        if "tn_pubr_public_trdit_mrkt_api" in url:
            return _payload(
                [
                    {
                        "mrktNm": "죽도시장",
                        "rdnmadr": "경상북도 포항시 북구 죽도시장길",
                        "latitude": "36.036",
                        "longitude": "129.365",
                        "mrktType": "상설시장",
                    }
                ]
            )
        if "getHospBasisList" in url:
            return _payload(
                [
                    {
                        "ykiho": "H1",
                        "yadmNm": "포항의원",
                        "addr": "경상북도 포항시 북구",
                        "YPos": "36.037",
                        "XPos": "129.365",
                        "clCdNm": "의원",
                    }
                ]
            )
        if "getCrdntPrxmtSttnList" in url:
            return _payload(
                [
                    {
                        "nodeid": "S1",
                        "citycode": "37010",
                        "nodenm": "죽도시장",
                        "gpslati": "36.0365",
                        "gpslong": "129.365",
                    },
                    {
                        "nodeid": "FAR",
                        "citycode": "37010",
                        "nodenm": "먼정류장",
                        "gpslati": "36.2",
                        "gpslong": "129.365",
                    },
                ]
            )
        if "getSttnThrghRouteList" in url:
            return _payload([{"routeid": "R1", "routeno": "105", "routetp": "간선"}])
        if "getRouteInfoIem" in url:
            return _payload(
                [
                    {
                        "startvehicletime": "0600",
                        "endvehicletime": "2200",
                        "intervaltime": "60",
                    }
                ]
            )
        raise AssertionError(f"unexpected URL: {url}")


def _payload(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "response": {
            "header": {"resultCode": "00"},
            "body": {"items": {"item": items}},
        }
    }


def _service() -> AccessibilityService:
    gateway = FakeGateway()
    return AccessibilityService(
        HiraClient(gateway, "test-key"),
        TagoClient(gateway, "test-key"),
        MarketClient(gateway, "test-key"),
    )


def test_geo_calculations_are_deterministic() -> None:
    distance = haversine_distance_m(36.0, 129.0, 36.001, 129.0)

    assert 110 < distance < 112
    assert estimated_walk_minutes(distance, 60) == 2


def test_search_bus_stops_filters_radius_and_daily_frequency() -> None:
    result = asyncio.run(
        _service().search_bus_stops(
            Coordinates(latitude=36.036, longitude=129.365),
            max_walk_minutes=10,
            minimum_daily_trips=5,
            service_day="weekday",
        )
    )

    assert [stop.name for stop in result.stops] == ["죽도시장"]
    assert result.stops[0].estimated_daily_trips == 17
    assert result.source.is_estimated is True


def test_recommendation_requires_market_hospital_and_bus() -> None:
    result = asyncio.run(
        NeighborhoodRecommendationService(_service()).recommend(
            "포항시",
            hospital_max_walk_minutes=15,
            bus_max_walk_minutes=10,
            minimum_daily_bus_trips=5,
        )
    )

    assert len(result.recommendations) == 1
    recommendation = result.recommendations[0]
    assert recommendation.rank == 1
    assert recommendation.candidate_name == "죽도시장 생활권"
    assert recommendation.nearest_hospital.name == "포항의원"
    assert recommendation.qualifying_bus_stops[0].estimated_daily_trips == 17
    assert "행정동" in result.warnings[0]
