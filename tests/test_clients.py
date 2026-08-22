"""Tests for public-data parsing and frequency estimation."""

import pytest

from clients.public_data import DataSourceError, extract_items, require_service_key
from clients.tago import estimate_daily_trips, parse_route_frequency


def test_extract_items_supports_standard_envelope() -> None:
    payload = {
        "response": {
            "header": {"resultCode": "00"},
            "body": {"items": {"item": {"name": "one"}}},
        }
    }

    assert extract_items(payload) == [{"name": "one"}]


def test_extract_items_rejects_upstream_error() -> None:
    payload = {"response": {"header": {"resultCode": "99"}, "body": {}}}

    try:
        extract_items(payload)
    except DataSourceError as exc:
        assert "오류" in str(exc)
    else:
        raise AssertionError("upstream error must be surfaced")


def test_require_service_key_has_actionable_error() -> None:
    try:
        require_service_key(None)
    except DataSourceError as exc:
        assert "DATA_GO_KR_SERVICE_KEY" in str(exc)
    else:
        raise AssertionError("missing key must fail")


def test_estimate_daily_trips_handles_normal_and_overnight_routes() -> None:
    assert estimate_daily_trips("06:00", "22:00", 60) == 17
    assert estimate_daily_trips("2300", "0100", 60) == 3
    assert estimate_daily_trips("0600", "2200", None) is None


def test_parse_route_frequency_uses_service_day_interval() -> None:
    row = {
        "startvehicletime": "0600",
        "endvehicletime": "2200",
        "intervaltime": "20",
        "intervalsattime": "30",
        "intervalsuntime": "60",
    }

    result = parse_route_frequency(row, "sunday")

    assert result["interval_minutes"] == 60
    assert result["daily_trips"] == 17
    assert result["frequency_basis"] == "api_summary"


def test_parse_route_frequency_prefers_explicit_downloaded_trip_count() -> None:
    row = {
        "startvehicletime": "0600",
        "endvehicletime": "2200",
        "intervaltime": "60",
        "weekdaytrips": "42",
    }

    result = parse_route_frequency(row, "weekday")

    assert result["daily_trips"] == 42
    assert result["frequency_basis"] == "api_summary"


@pytest.mark.parametrize(
    ("service_day", "expected_trips"),
    [("weekday", 5), ("saturday", 4), ("sunday", 3)],
)
def test_parse_route_frequency_selects_explicit_service_day_count(
    service_day: str, expected_trips: int
) -> None:
    row = {
        "startvehicletime": "0700",
        "endvehicletime": "1830",
        "weekdaytrips": "5",
        "saturdaytrips": "4",
        "sundaytrips": "3",
        "frequencybasis": "published_trip_count",
    }

    result = parse_route_frequency(row, service_day)  # type: ignore[arg-type]

    assert result["daily_trips"] == expected_trips
    assert result["frequency_basis"] == "published_trip_count"
