"""Business logic for medical, transit, and market accessibility."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any, Protocol, cast

from clients.hira import HOSPITAL_URL, parse_hospital_row
from clients.markets import MARKET_URL, parse_market_row
from clients.public_data import DataSourceError
from clients.tago import (
    STOP_BASE_URL,
    ServiceDay,
    parse_route_frequency,
    parse_route_row,
    parse_stop_row,
)
from models.accessibility import (
    BusRouteFrequency,
    BusStopAccessibility,
    BusStopSearchResult,
    Hospital,
    HospitalSearchResult,
    MarketSearchResult,
    TraditionalMarket,
)
from models.location import Coordinates, DataSourceMetadata
from services.geo import estimated_walk_minutes, haversine_distance_m

HOSPITAL_FILE_URL = "https://www.data.go.kr/data/15051059/fileData.do"
POHANG_TIMETABLE_URL = "https://cn.pohang.go.kr/dept/contents.do?mid=0505070000"
MARKET_FILE_URL = "https://www.data.go.kr/data/15012894/standard.do"


class HospitalClient(Protocol):
    """Data access required for hospital searches."""

    async def search_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_m: int,
        department_code: str | None = None,
        rows: int = 100,
    ) -> list[dict[str, Any]]: ...

    async def departments(self, institution_id: str) -> list[str]: ...


class TransitClient(Protocol):
    """Data access required for bus-stop searches."""

    async def nearby_stops(self, latitude: float, longitude: float) -> list[dict[str, Any]]: ...

    async def routes_for_stop(self, city_code: str, stop_id: str) -> list[dict[str, Any]]: ...

    async def route_info(
        self, city_code: str, route_id: str, stop_id: str | None = None
    ) -> dict[str, Any] | None: ...


class MarketsClient(Protocol):
    """Data access required for market searches."""

    async def search_region(self, region: str, rows: int = 1000) -> list[dict[str, Any]]: ...


class AccessibilityService:
    """Combine public-data clients with deterministic distance calculations."""

    def __init__(
        self,
        hira: HospitalClient,
        tago: TransitClient,
        markets: MarketsClient,
        walking_speed_m_per_minute: float = 60.0,
        file_mode: bool = False,
    ) -> None:
        if walking_speed_m_per_minute <= 0:
            raise ValueError("Walking speed must be positive")
        self._hira = hira
        self._tago = tago
        self._markets = markets
        self._walking_speed = walking_speed_m_per_minute
        self._file_mode = file_mode

    async def search_hospitals(
        self,
        origin: Coordinates,
        max_walk_minutes: int,
        department_code: str | None = None,
        include_departments: bool = False,
    ) -> HospitalSearchResult:
        """Find hospitals inside a straight-line walking radius."""

        radius_m = round(max_walk_minutes * self._walking_speed)
        rows = await self._hira.search_nearby(
            origin.latitude,
            origin.longitude,
            radius_m,
            department_code,
        )
        hospitals: list[Hospital] = []
        for row in rows:
            normalized = parse_hospital_row(row)
            if normalized is None:
                continue
            latitude = cast(float, normalized["latitude"])
            longitude = cast(float, normalized["longitude"])
            distance = haversine_distance_m(origin.latitude, origin.longitude, latitude, longitude)
            if distance > radius_m:
                continue
            departments: list[str] = []
            if include_departments:
                departments = await self._hira.departments(cast(str, normalized["institution_id"]))
            hospitals.append(
                Hospital(
                    institution_id=cast(str, normalized["institution_id"]),
                    name=cast(str, normalized["name"]),
                    address=cast(str, normalized["address"]),
                    phone=cast(str | None, normalized["phone"]),
                    institution_type=cast(str | None, normalized["institution_type"]),
                    departments=departments,
                    coordinates=Coordinates(latitude=latitude, longitude=longitude),
                    distance_m=round(distance, 1),
                    estimated_walk_minutes=estimated_walk_minutes(distance, self._walking_speed),
                )
            )
        hospitals.sort(key=lambda hospital: hospital.distance_m)
        return HospitalSearchResult(
            hospitals=hospitals,
            max_walk_minutes=max_walk_minutes,
            walking_speed_m_per_minute=self._walking_speed,
            source=DataSourceMetadata(
                source_name=(
                    "건강보험심사평가원 병의원 현황 다운로드 파일"
                    if self._file_mode
                    else "건강보험심사평가원 병원정보서비스"
                ),
                source_url=HOSPITAL_FILE_URL if self._file_mode else HOSPITAL_URL,
                as_of="2026-06" if self._file_mode else None,
                is_estimated=True,
                estimation_method=(
                    f"기관 좌표와 기준점의 직선거리를 분당 {self._walking_speed:g}m 보행속도로 환산"
                ),
            ),
            warnings=["실제 보행로, 경사, 횡단보도와 건물 출입구는 반영되지 않습니다."],
        )

    async def search_bus_stops(
        self,
        origin: Coordinates,
        max_walk_minutes: int,
        minimum_daily_trips: int,
        service_day: ServiceDay,
        stop_limit: int = 20,
    ) -> BusStopSearchResult:
        """Find nearby stops and estimate daily departures for each route."""

        radius_m = max_walk_minutes * self._walking_speed
        raw_stops = await self._tago.nearby_stops(origin.latitude, origin.longitude)
        stop_inputs: list[tuple[dict[str, str | float], float]] = []
        for row in raw_stops:
            stop = parse_stop_row(row)
            if stop is None:
                continue
            distance = haversine_distance_m(
                origin.latitude,
                origin.longitude,
                cast(float, stop["latitude"]),
                cast(float, stop["longitude"]),
            )
            if distance <= radius_m:
                stop_inputs.append((stop, distance))
        stop_inputs.sort(key=lambda item: item[1])

        warnings: list[str] = []
        enriched = await asyncio.gather(
            *(
                self._enrich_stop(stop, distance, service_day, warnings)
                for stop, distance in stop_inputs[:stop_limit]
            )
        )
        stops = [
            stop
            for stop in enriched
            if stop.estimated_daily_trips is not None
            and stop.estimated_daily_trips >= minimum_daily_trips
        ]
        stops.sort(
            key=lambda stop: (
                stop.distance_m,
                -(stop.estimated_daily_trips or 0),
            )
        )
        return BusStopSearchResult(
            stops=stops,
            service_day=service_day,
            minimum_daily_trips=minimum_daily_trips,
            source=DataSourceMetadata(
                source_name=(
                    "국토교통부 정류장·포항시 노선 및 시간표 다운로드 자료"
                    if self._file_mode
                    else "국토교통부 TAGO 버스정류소·노선정보"
                ),
                source_url=POHANG_TIMETABLE_URL if self._file_mode else STOP_BASE_URL,
                as_of="2026-08-23" if self._file_mode else None,
                is_estimated=True,
                estimation_method=(
                    "간선은 공식 첫차·막차와 최대 배차간격의 보수적 하한을, 지선은 "
                    "해당 정류장을 포함하는 검수 패턴의 게시 운행횟수를 합산; "
                    "도보시간은 직선거리로 환산"
                    if self._file_mode
                    else "노선별 (막차-첫차)/배차간격+1을 합산; 도보시간은 직선거리로 환산"
                ),
            ),
            warnings=_unique(
                [
                    *warnings,
                    (
                        "파일 모드는 포항 53개 노선 중 51개 노선의 배차를 판정합니다. "
                        "임시노선과 호출 기반 죽장DRT는 횟수 미상으로 제외합니다."
                        if self._file_mode
                        else "운행 횟수는 시간표 요약값을 이용한 추정치이며 "
                        "결행·공휴일을 반영하지 않습니다."
                    ),
                    *(
                        [
                            "포항시 게시 시간표가 요일별 값을 구분하지 않아 파일 모드에서는 "
                            "평일·토요일·일요일에 같은 검수값을 적용합니다. 장날·CALL·임시·"
                            "요청 운행은 기본 횟수에서 제외하고 경유 표시는 중복 계수하지 않습니다."
                        ]
                        if self._file_mode
                        else []
                    ),
                    "실제 보행 경로와 정류장 승차 방향은 별도로 확인해야 합니다.",
                ]
            ),
        )

    async def search_markets(
        self,
        region: str,
        origin: Coordinates,
        max_walk_minutes: int,
    ) -> MarketSearchResult:
        """Find registered traditional markets near one coordinate."""

        radius_m = max_walk_minutes * self._walking_speed
        markets = await self.markets_in_region(region, origin)
        markets = [market for market in markets if market.distance_m <= radius_m]
        return MarketSearchResult(
            markets=markets,
            source=DataSourceMetadata(
                source_name="전국전통시장표준데이터",
                source_url=MARKET_FILE_URL if self._file_mode else MARKET_URL,
                as_of="2025-11-26" if self._file_mode else None,
                is_estimated=True,
                estimation_method=(
                    "시장 대표 좌표와 기준점의 직선거리를 "
                    f"분당 {self._walking_speed:g}m 보행속도로 환산"
                ),
            ),
            warnings=["시장 경계·개별 출입구와 실제 보행 경로는 반영되지 않습니다."],
        )

    async def markets_in_region(
        self, region: str, origin: Coordinates | None = None
    ) -> list[TraditionalMarket]:
        """Return normalized markets in a region, optionally measured from an origin."""

        rows = await self._markets.search_region(region)
        markets: list[TraditionalMarket] = []
        seen: set[tuple[str, str]] = set()
        for row in rows:
            normalized = parse_market_row(row)
            if normalized is None:
                continue
            name = cast(str, normalized["name"])
            address = cast(str, normalized["address"])
            if (name, address) in seen:
                continue
            seen.add((name, address))
            latitude = cast(float, normalized["latitude"])
            longitude = cast(float, normalized["longitude"])
            distance = 0.0
            if origin is not None:
                distance = haversine_distance_m(
                    origin.latitude, origin.longitude, latitude, longitude
                )
            markets.append(
                TraditionalMarket(
                    name=name,
                    address=address,
                    market_type=cast(str | None, normalized["market_type"]),
                    opening_cycle=cast(str | None, normalized["opening_cycle"]),
                    coordinates=Coordinates(latitude=latitude, longitude=longitude),
                    distance_m=round(distance, 1),
                    estimated_walk_minutes=estimated_walk_minutes(distance, self._walking_speed),
                    reference_date=cast(str | None, normalized["reference_date"]),
                )
            )
        markets.sort(key=lambda market: market.distance_m)
        return markets

    async def _enrich_stop(
        self,
        stop: Mapping[str, str | float],
        distance: float,
        service_day: ServiceDay,
        warnings: list[str],
    ) -> BusStopAccessibility:
        city_code = cast(str, stop["city_code"])
        stop_id = cast(str, stop["stop_id"])
        try:
            raw_routes = await self._tago.routes_for_stop(city_code, stop_id)
        except DataSourceError:
            warnings.append("일부 정류장의 경유 노선 정보를 가져오지 못했습니다.")
            raw_routes = []

        routes: list[BusRouteFrequency] = []
        for raw_route in raw_routes:
            route = parse_route_row(raw_route)
            if route is None:
                continue
            route_id = cast(str, route["route_id"])
            try:
                raw_frequency = await self._tago.route_info(city_code, route_id, stop_id)
            except DataSourceError:
                warnings.append("일부 노선의 배차 정보를 가져오지 못했습니다.")
                raw_frequency = None
            frequency = parse_route_frequency(raw_frequency, service_day)
            routes.append(
                BusRouteFrequency(
                    route_id=route_id,
                    route_number=cast(str, route["route_number"]),
                    route_type=route["route_type"],
                    daily_trips=cast(int | None, frequency["daily_trips"]),
                    first_bus=cast(str | None, frequency["first_bus"]),
                    last_bus=cast(str | None, frequency["last_bus"]),
                    interval_minutes=cast(int | None, frequency["interval_minutes"]),
                    frequency_basis=cast(Any, frequency["frequency_basis"]),
                )
            )
        known_trips = [route.daily_trips for route in routes if route.daily_trips is not None]
        total_trips = sum(known_trips) if known_trips else None
        return BusStopAccessibility(
            stop_id=stop_id,
            name=cast(str, stop["name"]),
            coordinates=Coordinates(
                latitude=cast(float, stop["latitude"]),
                longitude=cast(float, stop["longitude"]),
            ),
            distance_m=round(distance, 1),
            estimated_walk_minutes=estimated_walk_minutes(distance, self._walking_speed),
            estimated_daily_trips=total_trips,
            routes=routes,
        )


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
