"""SQLite-backed clients for downloaded public-data snapshots."""

from __future__ import annotations

import asyncio
import math
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

from clients.public_data import DataSourceError


class _LocalDatabase:
    """Open short-lived read-only SQLite connections for async callers."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    async def rows(self, query: str, parameters: tuple[object, ...] = ()) -> list[dict[str, Any]]:
        """Execute a fixed query without blocking the event loop."""

        return await asyncio.to_thread(self._rows_sync, query, parameters)

    def _rows_sync(self, query: str, parameters: tuple[object, ...]) -> list[dict[str, Any]]:
        if not self._database_path.is_file():
            raise DataSourceError("로컬 데이터베이스가 없습니다. 먼저 `make data`를 실행해 주세요.")
        try:
            uri = f"file:{self._database_path.resolve()}?mode=ro"
            with sqlite3.connect(uri, uri=True) as connection:
                connection.row_factory = sqlite3.Row
                return [dict(row) for row in connection.execute(query, parameters).fetchall()]
        except sqlite3.Error as exc:
            raise DataSourceError("로컬 공공데이터를 읽을 수 없습니다.") from exc


class LocalHiraClient:
    """Expose locally ingested HIRA rows through the HIRA client contract."""

    def __init__(self, database_path: Path) -> None:
        self._database = _LocalDatabase(database_path)

    async def search_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_m: int,
        department_code: str | None = None,
        rows: int = 100,
    ) -> list[dict[str, Any]]:
        """Return candidate hospitals from a coordinate bounding box."""

        latitude_delta = radius_m / 111_000
        longitude_delta = radius_m / 90_000
        department_clause = ""
        parameters: tuple[object, ...] = (
            latitude - latitude_delta,
            latitude + latitude_delta,
            longitude - longitude_delta,
            longitude + longitude_delta,
        )
        if department_code:
            department_clause = (
                " AND EXISTS (SELECT 1 FROM hospital_departments d "
                "WHERE d.institution_id = h.institution_id AND d.department_code = ?)"
            )
            parameters = (*parameters, department_code)
        parameters = (*parameters, rows)
        return await self._database.rows(
            "SELECT institution_id AS ykiho, name AS yadmNm, address AS addr, "
            "phone AS telno, institution_type AS clCdNm, latitude AS YPos, longitude AS XPos "
            "FROM hospitals h WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?"
            f"{department_clause} LIMIT ?",
            parameters,
        )

    async def departments(self, institution_id: str) -> list[str]:
        """Return declared department names for one hospital."""

        rows = await self._database.rows(
            "SELECT department_name FROM hospital_departments "
            "WHERE institution_id = ? ORDER BY department_code",
            (institution_id,),
        )
        return [str(row["department_name"]) for row in rows]


class LocalTagoClient:
    """Expose downloaded stop, route, and frequency rows through the TAGO contract."""

    def __init__(self, database_path: Path) -> None:
        self._database = _LocalDatabase(database_path)

    async def nearby_stops(self, latitude: float, longitude: float) -> list[dict[str, Any]]:
        """Return stops within a broad box; the service applies the exact radius."""

        return await self._database.rows(
            "SELECT stop_id AS nodeid, city_code AS citycode, name AS nodenm, "
            "latitude AS gpslati, longitude AS gpslong FROM bus_stops "
            "WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?",
            (latitude - 0.08, latitude + 0.08, longitude - 0.10, longitude + 0.10),
        )

    async def routes_for_stop(self, city_code: str, stop_id: str) -> list[dict[str, Any]]:
        """Return routes matched to one downloaded stop."""

        return await self._database.rows(
            "SELECT r.route_id AS routeid, r.route_number AS routeno, "
            "r.route_type AS routetp FROM bus_routes r "
            "JOIN bus_stop_routes sr ON sr.route_id = r.route_id "
            "JOIN bus_stops s ON s.stop_id = sr.stop_id "
            "WHERE s.city_code = ? AND s.stop_id = ? ORDER BY r.route_number",
            (city_code, stop_id),
        )

    async def route_info(
        self, city_code: str, route_id: str, stop_id: str | None = None
    ) -> dict[str, Any] | None:
        """Return route-level or stop-specific pattern frequency data."""

        rows = await self._database.rows(
            "SELECT f.first_bus AS startvehicletime, f.last_bus AS endvehicletime, "
            "f.interval_weekday AS intervaltime, f.interval_saturday AS intervalsattime, "
            "f.interval_sunday AS intervalsuntime, f.trips_weekday AS weekdaytrips, "
            "f.trips_saturday AS saturdaytrips, f.trips_sunday AS sundaytrips, "
            "f.frequency_basis AS frequencybasis "
            "FROM bus_route_frequencies f JOIN bus_routes r ON r.route_id = f.route_id "
            "WHERE r.city_code = ? AND f.route_id = ?",
            (city_code, route_id),
        )
        if rows:
            return rows[0]
        if stop_id is None:
            return None
        pattern_rows = await self._database.rows(
            "SELECT MIN(f.first_bus) AS startvehicletime, "
            "MAX(f.last_bus) AS endvehicletime, NULL AS intervaltime, "
            "NULL AS intervalsattime, NULL AS intervalsuntime, "
            "SUM(f.trips_weekday) AS weekdaytrips, "
            "SUM(f.trips_saturday) AS saturdaytrips, "
            "SUM(f.trips_sunday) AS sundaytrips, "
            "'published_trip_count' AS frequencybasis "
            "FROM bus_pattern_frequencies f JOIN bus_route_patterns p "
            "ON p.pattern_id = f.pattern_id JOIN bus_routes r ON r.route_id = p.route_id "
            "WHERE r.city_code = ? AND r.route_id = ? AND p.pattern_id IN "
            "(SELECT DISTINCT ps.pattern_id FROM bus_pattern_stops ps WHERE ps.stop_id = ?)",
            (city_code, route_id, stop_id),
        )
        if not pattern_rows or pattern_rows[0]["weekdaytrips"] is None:
            return None
        return pattern_rows[0]


class LocalMarketClient:
    """Expose downloaded national standard market rows through the market contract."""

    def __init__(self, database_path: Path) -> None:
        self._database = _LocalDatabase(database_path)

    async def search_region(self, region: str, rows: int = 1000) -> list[dict[str, Any]]:
        """Return markets whose downloaded address contains a region name."""

        del rows
        return await self._database.rows(
            "SELECT name AS mrktNm, road_address AS rdnmadr, lot_address AS lnmadr, "
            "market_type AS mrktType, opening_cycle AS mrktEstblCycle, "
            "latitude, longitude, reference_date AS referenceDate FROM markets "
            "WHERE road_address LIKE ? OR lot_address LIKE ? ORDER BY name",
            (f"%{region}%", f"%{region}%"),
        )


class LocalStoreClient:
    """Expose downloaded commercial-business rows through the store contract."""

    def __init__(self, database_path: Path) -> None:
        self._database = _LocalDatabase(database_path)

    async def search_radius(
        self,
        latitude: float,
        longitude: float,
        radius_m: int,
        industry_code: str | None = None,
        rows: int = 1000,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Return businesses from a coordinate bounding box and source date."""

        del rows
        latitude_delta = radius_m / 111_000
        longitude_delta = radius_m / (111_000 * math.cos(math.radians(latitude)))
        industry_clause = ""
        parameters: tuple[object, ...] = (
            latitude - latitude_delta,
            latitude + latitude_delta,
            longitude - longitude_delta,
            longitude + longitude_delta,
        )
        if industry_code:
            industry_column = {
                2: "industry_large_code",
                4: "industry_medium_code",
                6: "industry_small_code",
            }.get(len(industry_code))
            if industry_column is None:
                raise DataSourceError(
                    "industry_code는 영문·숫자 2자리, 4자리 또는 6자리여야 합니다."
                )
            industry_clause = f" AND {industry_column} = ?"
            parameters = (*parameters, industry_code.upper())
        businesses = await self._database.rows(
            "SELECT business_id AS bizesId, name AS bizesNm, branch_name AS brchNm, "
            "industry_large_code AS indsLclsCd, industry_large_name AS indsLclsNm, "
            "industry_medium_code AS indsMclsCd, industry_medium_name AS indsMclsNm, "
            "industry_small_code AS indsSclsCd, industry_small_name AS indsSclsNm, "
            "standard_industry_code AS ksicCd, standard_industry_name AS ksicNm, "
            "road_address AS rdnmAdr, lot_address AS lnoAdr, longitude AS lon, latitude AS lat "
            "FROM stores WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?"
            f"{industry_clause}",
            parameters,
        )
        metadata = await self._database.rows(
            "SELECT value FROM metadata WHERE key = 'stores_as_of'"
        )
        as_of = str(metadata[0]["value"]) if metadata else None
        return businesses, as_of


class LocalDemographicsClient:
    """Read resident-registration age bands from the local snapshot."""

    def __init__(self, database_path: Path) -> None:
        self._database = _LocalDatabase(database_path)

    async def age_bands(self, region: str, as_of: str | None = None) -> list[dict[str, Any]]:
        """Return matching age-band rows ordered by region, month, and age."""

        region = region.strip()
        if region.isdigit():
            clause = "region_code = ?"
            parameters: tuple[object, ...] = (region,)
        else:
            normalized = _normalize_region(region)
            clause = "(normalized_name = ? OR normalized_name LIKE ?)"
            parameters = (normalized, f"%{normalized}")
        if as_of is not None:
            clause += " AND as_of = ?"
            parameters = (*parameters, as_of)
        return await self._database.rows(
            "SELECT region_code, region_name, region_level, as_of, age_from, age_to, "
            "population, total_population FROM population_age_bands WHERE "
            f"{clause} ORDER BY region_name, as_of DESC, age_from",
            parameters,
        )


class LocalSafetyClient:
    """Read official regional safety grades from the local snapshot."""

    def __init__(self, database_path: Path) -> None:
        self._database = _LocalDatabase(database_path)

    async def grades(
        self, region: str, category: str, publication_year: int | None = None
    ) -> list[dict[str, Any]]:
        """Return matching safety-grade rows ordered newest first."""

        normalized = _normalize_region(region)
        clause = "(normalized_name = ? OR normalized_name LIKE ?) AND category = ?"
        parameters: tuple[object, ...] = (normalized, f"%{normalized}", category)
        if publication_year is not None:
            clause += " AND publication_year = ?"
            parameters = (*parameters, publication_year)
        return await self._database.rows(
            "SELECT region_name, region_level, category, grade, publication_year, "
            "statistics_year, comparison_group FROM safety_grades WHERE "
            f"{clause} ORDER BY publication_year DESC, region_name",
            parameters,
        )


def _normalize_region(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"[^0-9A-Za-z가-힣]", "", normalized).lower()
