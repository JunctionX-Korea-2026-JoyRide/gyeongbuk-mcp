"""TAGO bus-stop and route-information client."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from clients.public_data import (
    JsonGateway,
    as_float,
    as_int,
    extract_items,
    require_service_key,
    value,
)

STOP_BASE_URL = "https://apis.data.go.kr/1613000/BusSttnInfoInqireService"
ROUTE_BASE_URL = "https://apis.data.go.kr/1613000/BusRouteInfoInqireService"
ServiceDay = Literal["weekday", "saturday", "sunday"]


class TagoClient:
    """Thin client for nearby stops, their routes, and timetables."""

    def __init__(self, gateway: JsonGateway, service_key: str | None) -> None:
        self._gateway = gateway
        self._service_key = service_key

    async def nearby_stops(self, latitude: float, longitude: float) -> list[dict[str, Any]]:
        """Return stops near one coordinate."""

        payload = await self._gateway.get(
            f"{STOP_BASE_URL}/getCrdntPrxmtSttnList",
            {
                "serviceKey": require_service_key(self._service_key),
                "pageNo": 1,
                "numOfRows": 100,
                "gpsLati": latitude,
                "gpsLong": longitude,
                "_type": "json",
            },
        )
        return extract_items(payload)

    async def routes_for_stop(self, city_code: str, stop_id: str) -> list[dict[str, Any]]:
        """Return routes passing a stop."""

        payload = await self._gateway.get(
            f"{STOP_BASE_URL}/getSttnThrghRouteList",
            {
                "serviceKey": require_service_key(self._service_key),
                "pageNo": 1,
                "numOfRows": 100,
                "cityCode": city_code,
                "nodeid": stop_id,
                "_type": "json",
            },
        )
        return extract_items(payload)

    async def route_info(
        self, city_code: str, route_id: str, stop_id: str | None = None
    ) -> dict[str, Any] | None:
        """Return the first timetable row for a route."""

        del stop_id

        payload = await self._gateway.get(
            f"{ROUTE_BASE_URL}/getRouteInfoIem",
            {
                "serviceKey": require_service_key(self._service_key),
                "cityCode": city_code,
                "routeId": route_id,
                "_type": "json",
            },
        )
        rows = extract_items(payload)
        return rows[0] if rows else None


def parse_stop_row(row: Mapping[str, Any]) -> dict[str, str | float] | None:
    """Normalize a TAGO stop row."""

    stop_id = value(row, "nodeid")
    city_code = value(row, "citycode", "cityCode")
    name = value(row, "nodenm")
    latitude = as_float(value(row, "gpslati"))
    longitude = as_float(value(row, "gpslong"))
    if not stop_id or not city_code or not name or latitude is None or longitude is None:
        return None
    return {
        "stop_id": stop_id,
        "city_code": city_code,
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
    }


def parse_route_row(row: Mapping[str, Any]) -> dict[str, str | None] | None:
    """Normalize a route passing one stop."""

    route_id = value(row, "routeid", "routeId")
    route_number = value(row, "routeno", "routeNo")
    if not route_id or not route_number:
        return None
    return {
        "route_id": route_id,
        "route_number": route_number,
        "route_type": value(row, "routetp", "routeTp"),
    }


def parse_route_frequency(
    row: Mapping[str, Any] | None, service_day: ServiceDay
) -> dict[str, str | int | None]:
    """Extract a timetable and estimate trips from first/last bus and interval."""

    if row is None:
        return {
            "daily_trips": None,
            "first_bus": None,
            "last_bus": None,
            "interval_minutes": None,
            "frequency_basis": None,
        }

    first_bus = value(row, "startvehicletime")
    last_bus = value(row, "endvehicletime")
    interval_field = {
        "weekday": "intervaltime",
        "saturday": "intervalsattime",
        "sunday": "intervalsuntime",
    }[service_day]
    interval = as_int(value(row, interval_field))
    trips_field = {
        "weekday": "weekdaytrips",
        "saturday": "saturdaytrips",
        "sunday": "sundaytrips",
    }[service_day]
    trips = as_int(value(row, trips_field))
    if trips is None:
        trips = estimate_daily_trips(first_bus, last_bus, interval)
    return {
        "daily_trips": trips,
        "first_bus": first_bus,
        "last_bus": last_bus,
        "interval_minutes": interval if interval and interval > 0 else None,
        "frequency_basis": value(row, "frequencybasis") or "api_summary",
    }


def estimate_daily_trips(
    first_bus: str | None, last_bus: str | None, interval_minutes: int | None
) -> int | None:
    """Estimate one-direction daily departures from timetable summary fields."""

    first = _time_to_minutes(first_bus)
    last = _time_to_minutes(last_bus)
    if first is None or last is None or interval_minutes is None or interval_minutes <= 0:
        return None
    if last < first:
        last += 24 * 60
    return (last - first) // interval_minutes + 1


def _time_to_minutes(raw: str | None) -> int | None:
    if raw is None:
        return None
    digits = "".join(character for character in raw if character.isdigit())
    if len(digits) < 3 or len(digits) > 4:
        return None
    digits = digits.zfill(4)
    hour = int(digits[:2])
    minute = int(digits[2:])
    if hour > 23 or minute > 59:
        return None
    return hour * 60 + minute
