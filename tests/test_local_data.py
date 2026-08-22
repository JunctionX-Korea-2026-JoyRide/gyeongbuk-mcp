"""Tests for the downloaded-file SQLite runtime."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest

from clients.local_data import (
    LocalDemographicsClient,
    LocalHiraClient,
    LocalMarketClient,
    LocalSafetyClient,
    LocalTagoClient,
)
from clients.public_data import DataSourceError
from models.location import Coordinates
from services.accessibility import AccessibilityService
from services.demographics import DemographicsService
from services.safety import SafetyService


def _database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE hospitals (
                institution_id TEXT, name TEXT, address TEXT, phone TEXT,
                institution_type TEXT, latitude REAL, longitude REAL
            );
            CREATE TABLE hospital_departments (
                institution_id TEXT, department_code TEXT, department_name TEXT
            );
            CREATE TABLE bus_stops (
                stop_id TEXT, name TEXT, normalized_name TEXT, city_code TEXT,
                city_name TEXT, latitude REAL, longitude REAL, reference_date TEXT
            );
            CREATE TABLE bus_routes (
                route_id TEXT, route_number TEXT, route_type TEXT,
                city_code TEXT, reference_date TEXT
            );
            CREATE TABLE bus_stop_routes (stop_id TEXT, route_id TEXT);
            CREATE TABLE bus_route_frequencies (
                route_id TEXT, first_bus TEXT, last_bus TEXT,
                interval_weekday INTEGER, interval_saturday INTEGER, interval_sunday INTEGER,
                trips_weekday INTEGER, trips_saturday INTEGER, trips_sunday INTEGER,
                frequency_basis TEXT, reference_date TEXT, source_url TEXT
            );
            CREATE TABLE bus_route_patterns (
                pattern_id TEXT, route_id TEXT, route_detail TEXT
            );
            CREATE TABLE bus_pattern_stops (
                pattern_id TEXT, stop_id TEXT, stop_sequence INTEGER
            );
            CREATE TABLE bus_pattern_frequencies (
                schedule_id TEXT, pattern_id TEXT, first_bus TEXT, last_bus TEXT,
                trips_weekday INTEGER, trips_saturday INTEGER, trips_sunday INTEGER,
                frequency_basis TEXT, reference_date TEXT, source_document TEXT,
                source_page INTEGER, source_url TEXT, notes TEXT
            );
            CREATE TABLE markets (
                name TEXT, market_type TEXT, road_address TEXT, lot_address TEXT,
                opening_cycle TEXT, latitude REAL, longitude REAL, reference_date TEXT
            );
            CREATE TABLE population_age_bands (
                region_code TEXT, region_name TEXT, normalized_name TEXT, region_level TEXT,
                as_of TEXT, age_from INTEGER, age_to INTEGER, population INTEGER,
                total_population INTEGER
            );
            CREATE TABLE safety_grades (
                region_name TEXT, normalized_name TEXT, region_level TEXT, category TEXT,
                grade INTEGER, publication_year INTEGER, statistics_year INTEGER,
                comparison_group TEXT
            );

            INSERT INTO hospitals VALUES
                ('H1', '포항의원', '경상북도 포항시', '054-000-0000', '의원', 36.036, 129.365);
            INSERT INTO hospital_departments VALUES ('H1', '01', '내과');
            INSERT INTO bus_stops VALUES
                ('S1', '죽도시장', '죽도시장', '37010', '경상북도 포항시',
                 36.0362, 129.365, '2025-10-31');
            INSERT INTO bus_routes VALUES
                ('pohang:110', '110', '포항시 시내버스', '37010', '2026-05-12');
            INSERT INTO bus_stop_routes VALUES ('S1', 'pohang:110');
            INSERT INTO bus_route_frequencies VALUES
                ('pohang:110', '05:20', '22:30', 25, 25, 25, 42, 42, 42,
                 'conservative_interval_estimate', '2026-08-23', 'https://example.test');
            INSERT INTO markets VALUES
                ('죽도시장', '상설장', '경상북도 포항시 북구', '', '매일',
                 36.036, 129.365, '2025-11-10');
            INSERT INTO population_age_bands VALUES
                ('4711054500', '경상북도 포항시 북구 죽도동', '경상북도포항시북구죽도동',
                 'town', '202607', 70, 79, 1800, 12000);
            INSERT INTO safety_grades VALUES
                ('경상북도 포항시', '경상북도포항시', 'city_county', 'crime',
                 3, 2025, 2024, '시');
            """
        )


def test_local_clients_support_accessibility_service(tmp_path: Path) -> None:
    database = tmp_path / "snapshot.sqlite3"
    _database(database)
    service = AccessibilityService(
        LocalHiraClient(database),
        LocalTagoClient(database),
        LocalMarketClient(database),
        file_mode=True,
    )
    origin = Coordinates(latitude=36.036, longitude=129.365)

    hospitals = asyncio.run(service.search_hospitals(origin, 15, include_departments=True))
    buses = asyncio.run(service.search_bus_stops(origin, 10, 5, "weekday"))
    markets = asyncio.run(service.search_markets("포항시", origin, 15))

    assert hospitals.hospitals[0].departments == ["내과"]
    assert hospitals.source.as_of == "2026-06"
    assert buses.stops[0].estimated_daily_trips == 42
    assert buses.stops[0].routes[0].frequency_basis == "conservative_interval_estimate"
    assert buses.source.source_name.startswith("국토교통부 정류장")
    assert markets.markets[0].name == "죽도시장"


def test_local_client_reports_missing_snapshot(tmp_path: Path) -> None:
    client = LocalMarketClient(tmp_path / "missing.sqlite3")

    with pytest.raises(DataSourceError, match="make data"):
        asyncio.run(client.search_region("포항시"))


def test_local_branch_frequency_aggregates_distinct_patterns_per_stop(tmp_path: Path) -> None:
    database = tmp_path / "snapshot.sqlite3"
    _database(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO bus_routes VALUES (?, ?, ?, ?, ?)",
            ("pohang:branch", "지선", "포항시 시내버스", "37010", "2026-05-12"),
        )
        connection.execute("INSERT INTO bus_stop_routes VALUES (?, ?)", ("S1", "pohang:branch"))
        connection.executemany(
            "INSERT INTO bus_route_patterns VALUES (?, ?, ?)",
            [("P1", "pohang:branch", "반복 경로"), ("P2", "pohang:branch", "겹침 경로")],
        )
        connection.executemany(
            "INSERT INTO bus_pattern_stops VALUES (?, ?, ?)",
            [("P1", "S1", 1), ("P1", "S1", 3), ("P2", "S1", 2)],
        )
        connection.executemany(
            "INSERT INTO bus_pattern_frequencies VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "F1",
                    "P1",
                    "07:00",
                    "18:00",
                    3,
                    2,
                    1,
                    "published_trip_count",
                    "2026-08-23",
                    "one.pdf",
                    1,
                    "https://example.test",
                    None,
                ),
                (
                    "F2",
                    "P2",
                    "06:30",
                    "20:00",
                    4,
                    3,
                    2,
                    "published_trip_count",
                    "2026-08-23",
                    "two.pdf",
                    1,
                    "https://example.test",
                    None,
                ),
            ],
        )

    client = LocalTagoClient(database)
    frequency = asyncio.run(client.route_info("37010", "pohang:branch", "S1"))

    assert frequency is not None
    assert frequency["weekdaytrips"] == 7
    assert frequency["saturdaytrips"] == 5
    assert frequency["sundaytrips"] == 3
    assert frequency["startvehicletime"] == "06:30"
    assert frequency["endvehicletime"] == "20:00"
    assert frequency["frequencybasis"] == "published_trip_count"
    assert asyncio.run(client.route_info("37010", "pohang:branch", "missing")) is None


def test_local_demographics_and_safety_services(tmp_path: Path) -> None:
    database = tmp_path / "snapshot.sqlite3"
    _database(database)
    demographics = DemographicsService(LocalDemographicsClient(database))
    safety = SafetyService(LocalSafetyClient(database))

    population = asyncio.run(demographics.get_age_population_ratio("죽도동", 70, 79))
    grade = asyncio.run(safety.get_safety_grade("포항시", "crime"))

    assert population.region_code == "4711054500"
    assert population.ratio_percent == 15.0
    assert grade.grade == 3
    assert grade.statistics_year == 2024


def test_demographics_rejects_non_band_aligned_range(tmp_path: Path) -> None:
    database = tmp_path / "snapshot.sqlite3"
    _database(database)
    service = DemographicsService(LocalDemographicsClient(database))

    with pytest.raises(DataSourceError, match="10세 구간"):
        asyncio.run(service.get_age_population_ratio("죽도동", 70, 75))
