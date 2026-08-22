"""Validation tests for reviewed Pohang branch timetable data."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest

import services.snapshot_builder as snapshot_builder
from services.snapshot_builder import _create_schema, _load_bus_pattern_frequencies

FIELDNAMES = [
    "schedule_id",
    "route_number",
    "route_detail",
    "first_bus",
    "last_bus",
    "trips_weekday",
    "trips_saturday",
    "trips_sunday",
    "reference_date",
    "source_document",
    "source_page",
    "source_url",
    "notes",
]


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    _create_schema(connection)
    connection.execute(
        "INSERT INTO bus_routes VALUES (?, ?, ?, ?, ?)",
        ("pohang:지선", "지선", "포항시 시내버스", "37010", "2026-05-12"),
    )
    connection.execute(
        "INSERT INTO bus_route_patterns VALUES (?, ?, ?)",
        ("P1", "pohang:지선", "정확한 경로"),
    )
    return connection


def _valid_row() -> dict[str, str]:
    return {
        "schedule_id": "schedule-1",
        "route_number": "지선",
        "route_detail": "정확한 경로",
        "first_bus": "07:00",
        "last_bus": "18:30",
        "trips_weekday": "5",
        "trips_saturday": "4",
        "trips_sunday": "3",
        "reference_date": "2026-08-23",
        "source_document": "branch.pdf",
        "source_page": "1",
        "source_url": "https://example.test/timetable",
        "notes": "검수 메모",
    }


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def test_branch_frequency_loader_accepts_exact_pattern_and_day_counts(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "branch.pdf").write_bytes(b"%PDF-test")
    csv_path = tmp_path / "frequencies.csv"
    _write_rows(csv_path, [_valid_row()])
    connection = _connection()

    assert _load_bus_pattern_frequencies(connection, csv_path, raw_dir) == 1
    row = connection.execute(
        "SELECT trips_weekday, trips_saturday, trips_sunday, frequency_basis "
        "FROM bus_pattern_frequencies"
    ).fetchone()
    assert row == (5, 4, 3, "published_trip_count")


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("route_detail", "없는 경로", "없는 노선·노선상세"),
        ("trips_weekday", "-1", "0 이상의 정수"),
        ("first_bus", "25:00", "잘못된 첫차·막차"),
        ("source_page", "0", "1 이상"),
    ],
)
def test_branch_frequency_loader_rejects_invalid_rows(
    tmp_path: Path, field: str, value: str, error: str
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "branch.pdf").write_bytes(b"%PDF-test")
    row = _valid_row()
    row[field] = value
    csv_path = tmp_path / "frequencies.csv"
    _write_rows(csv_path, [row])

    with pytest.raises(ValueError, match=error):
        _load_bus_pattern_frequencies(_connection(), csv_path, raw_dir)


def test_branch_frequency_loader_rejects_missing_pdf(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    csv_path = tmp_path / "frequencies.csv"
    _write_rows(csv_path, [_valid_row()])

    with pytest.raises(FileNotFoundError, match="원본 PDF"):
        _load_bus_pattern_frequencies(_connection(), csv_path, raw_dir)


def test_branch_frequency_loader_rejects_duplicate_schedule_id(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "branch.pdf").write_bytes(b"%PDF-test")
    csv_path = tmp_path / "frequencies.csv"
    _write_rows(csv_path, [_valid_row(), _valid_row()])

    with pytest.raises(ValueError, match="중복 schedule_id"):
        _load_bus_pattern_frequencies(_connection(), csv_path, raw_dir)


def test_snapshot_build_preserves_existing_database_on_pattern_validation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_dir = tmp_path / "raw"
    reference_dir = tmp_path / "reference"
    raw_dir.mkdir()
    reference_dir.mkdir()
    placeholder = raw_dir / "placeholder"
    placeholder.write_bytes(b"input")
    (reference_dir / "pohang_bus_frequencies.csv").write_text("header\n", encoding="utf-8")
    invalid = _valid_row()
    invalid["route_detail"] = "없는 경로"
    _write_rows(reference_dir / "pohang_branch_pattern_frequencies.csv", [invalid])
    output = tmp_path / "snapshot.sqlite3"
    output.write_bytes(b"previous database")

    monkeypatch.setattr(snapshot_builder, "_find_hira_zip", lambda _: placeholder)
    monkeypatch.setattr(snapshot_builder, "_find_csv", lambda *_: placeholder)
    monkeypatch.setattr(snapshot_builder, "_find_population_csv", lambda _: placeholder)
    monkeypatch.setattr(snapshot_builder, "_find_safety_hwpx", lambda _: placeholder)
    monkeypatch.setattr(snapshot_builder, "_load_hospitals", lambda *_: (0, 0))
    monkeypatch.setattr(snapshot_builder, "_load_bus_stops", lambda *_: 0)
    monkeypatch.setattr(snapshot_builder, "_load_bus_frequencies", lambda *_: 0)
    monkeypatch.setattr(snapshot_builder, "_load_markets", lambda *_: 0)
    monkeypatch.setattr(snapshot_builder, "_load_population_age_bands", lambda *_: 0)
    monkeypatch.setattr(snapshot_builder, "_load_safety_grades", lambda *_: 0)

    def load_routes(connection: sqlite3.Connection, _: Path) -> tuple[int, int, int, int]:
        connection.execute(
            "INSERT INTO bus_routes VALUES (?, ?, ?, ?, ?)",
            ("pohang:지선", "지선", "포항시 시내버스", "37010", "2026-05-12"),
        )
        connection.execute(
            "INSERT INTO bus_route_patterns VALUES (?, ?, ?)",
            ("P1", "pohang:지선", "정확한 경로"),
        )
        return 1, 0, 1, 0

    monkeypatch.setattr(snapshot_builder, "_load_pohang_routes", load_routes)

    with pytest.raises(ValueError, match="없는 노선·노선상세"):
        snapshot_builder.build_snapshot(raw_dir, reference_dir, output)

    assert output.read_bytes() == b"previous database"
