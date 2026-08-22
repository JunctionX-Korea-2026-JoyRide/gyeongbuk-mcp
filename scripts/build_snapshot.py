"""Command-line entry point for building the local public-data snapshot."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from services.snapshot_builder import build_snapshot  # noqa: E402


def main() -> None:
    """Build the default project snapshot and print deterministic row counts."""

    summary = build_snapshot(
        PROJECT_ROOT / "data/raw",
        PROJECT_ROOT / "data/reference",
        PROJECT_ROOT / "data/processed/gyeongbuk.sqlite3",
    )
    print(f"database={summary.database_path}")
    print(f"hospitals={summary.hospitals}")
    print(f"departments={summary.departments}")
    print(f"bus_stops={summary.bus_stops}")
    print(f"bus_routes={summary.bus_routes}")
    print(f"bus_stop_routes={summary.bus_stop_routes}")
    print(f"bus_frequencies={summary.bus_frequencies}")
    print(f"bus_route_patterns={summary.bus_route_patterns}")
    print(f"bus_pattern_stops={summary.bus_pattern_stops}")
    print(f"bus_pattern_frequencies={summary.bus_pattern_frequencies}")
    print(f"bus_frequency_routes={summary.bus_frequency_routes}")
    print(f"markets={summary.markets}")
    print(f"stores={summary.stores}")
    print(f"population_age_bands={summary.population_age_bands}")
    print(f"safety_grades={summary.safety_grades}")


if __name__ == "__main__":
    main()
