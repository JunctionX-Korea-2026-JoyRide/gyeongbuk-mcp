"""Regression checks for the optional real downloaded-data snapshot."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest

from clients.local_data import LocalTagoClient

SNAPSHOT = Path(__file__).resolve().parents[1] / "data/processed/gyeongbuk.sqlite3"
pytestmark = pytest.mark.skipif(not SNAPSHOT.is_file(), reason="run `make data` first")


def test_real_snapshot_has_expected_pohang_frequency_coverage() -> None:
    with sqlite3.connect(SNAPSHOT) as connection:
        route_count = connection.execute("SELECT COUNT(*) FROM bus_routes").fetchone()[0]
        covered = connection.execute(
            "SELECT COUNT(DISTINCT route_id) FROM ("
            "SELECT route_id FROM bus_route_frequencies UNION "
            "SELECT p.route_id FROM bus_route_patterns p "
            "JOIN bus_pattern_frequencies f ON f.pattern_id = p.pattern_id)"
        ).fetchone()[0]
        unknown = {
            str(row[0])
            for row in connection.execute(
                "SELECT route_number FROM bus_routes WHERE route_id NOT IN ("
                "SELECT route_id FROM bus_route_frequencies UNION "
                "SELECT p.route_id FROM bus_route_patterns p "
                "JOIN bus_pattern_frequencies f ON f.pattern_id = p.pattern_id)"
            )
        }

    assert route_count == 53
    assert covered == 51
    assert unknown == {"임시노선", "죽장DRT"}


@pytest.mark.parametrize(
    ("route_id", "stop_id", "expected_trips"),
    [
        ("pohang:기계1", "PHB352019003", 19),
        ("pohang:양덕", "PHB351001140", 30),
        ("pohang:오천1", "PHB350087069", 7),
    ],
)
def test_real_snapshot_outer_stop_pattern_frequency_is_deterministic(
    route_id: str, stop_id: str, expected_trips: int
) -> None:
    client = LocalTagoClient(SNAPSHOT)

    first = asyncio.run(client.route_info("37010", route_id, stop_id))
    second = asyncio.run(client.route_info("37010", route_id, stop_id))

    assert first == second
    assert first is not None
    assert first["weekdaytrips"] == expected_trips
    assert first["frequencybasis"] == "published_trip_count"
