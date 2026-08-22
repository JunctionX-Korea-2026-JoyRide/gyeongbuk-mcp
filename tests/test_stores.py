"""Tests for commercial-business API, filtering, and snapshot ingestion."""

from __future__ import annotations

import asyncio
import csv
import sqlite3
from collections.abc import Mapping
from io import StringIO
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest

from clients.public_data import DataSourceError
from clients.stores import StoreClient, parse_store_row
from models.location import Coordinates
from services.snapshot_builder import _create_schema, _load_stores, _store_member_name
from services.stores import StoreService


def _store_row(**overrides: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "bizesId": "B1",
        "bizesNm": "한빛 커피",
        "brchNm": "본점",
        "indsLclsCd": "I2",
        "indsLclsNm": "음식점",
        "indsMclsCd": "I212",
        "indsMclsNm": "비알코올음료점",
        "indsSclsCd": "I21201",
        "indsSclsNm": "커피전문점",
        "ksicCd": "I56112",
        "ksicNm": "커피 전문점",
        "rdnmAdr": "경상북도 포항시 북구 중앙로 1",
        "lnoAdr": "경상북도 포항시 북구 죽도동 1",
        "lon": "129.365",
        "lat": "36.036",
    }
    row.update(overrides)
    return row


class StoreGateway:
    """Return one business per page and record API parameters."""

    def __init__(self) -> None:
        self.params: list[dict[str, str | int | float]] = []

    async def get(self, url: str, params: Mapping[str, str | int | float]) -> dict[str, Any]:
        assert url.endswith("/storeListInRadius")
        self.params.append(dict(params))
        page = int(params["pageNo"])
        return {
            "response": {
                "header": {"resultCode": "00"},
                "body": {
                    "totalCount": 2,
                    "stdrYm": "202606",
                    "items": {"item": _store_row(bizesId=f"B{page}")},
                },
            }
        }


def test_store_client_paginates_and_maps_industry_code() -> None:
    gateway = StoreGateway()

    rows, as_of = asyncio.run(
        StoreClient(gateway, "test-key").search_radius(
            36.036, 129.365, 1000, industry_code="I21201", rows=1
        )
    )

    assert [row["bizesId"] for row in rows] == ["B1", "B2"]
    assert as_of == "2026-06"
    assert all(params["indsSclsCd"] == "I21201" for params in gateway.params)
    assert [params["pageNo"] for params in gateway.params] == [1, 2]


def test_store_client_requires_service_key() -> None:
    with pytest.raises(DataSourceError, match="DATA_GO_KR_SERVICE_KEY"):
        asyncio.run(StoreClient(StoreGateway(), None).search_radius(36.0, 129.0, 1000))


class StoreRowsClient:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    async def search_radius(
        self,
        latitude: float,
        longitude: float,
        radius_m: int,
        industry_code: str | None = None,
        rows: int = 1000,
    ) -> tuple[list[dict[str, Any]], str | None]:
        del latitude, longitude, radius_m, industry_code, rows
        return self.rows, "2026-06"


def test_store_service_filters_normalizes_deduplicates_and_sorts() -> None:
    rows = [
        _store_row(bizesId="B2", bizesNm="한빛-커피", lon="129.3655"),
        _store_row(bizesId="B1", bizesNm="한빛 커피", lon="129.3651"),
        _store_row(bizesId="B1", bizesNm="중복", lon="129.3652"),
        _store_row(bizesId="FAR", bizesNm="한빛커피", lat="36.2"),
    ]
    service = StoreService(StoreRowsClient(rows))

    result = asyncio.run(
        service.search_nearby(
            Coordinates(latitude=36.036, longitude=129.365),
            1000,
            industry_code="i212",
            industry_name="커피 전문점",
            name_query="한빛 커피",
            result_limit=2,
        )
    )

    assert [store.business_id for store in result.stores] == ["B1", "B2"]
    assert result.stores[0].distance_m < result.stores[1].distance_m
    assert result.stores[0].estimated_walk_minutes == 1
    assert result.source.as_of == "2026-06"


def test_store_service_returns_empty_result_and_rejects_invalid_code() -> None:
    service = StoreService(StoreRowsClient([]))
    origin = Coordinates(latitude=36.036, longitude=129.365)

    assert asyncio.run(service.search_nearby(origin, 1000)).stores == []
    with pytest.raises(DataSourceError, match="2자리, 4자리 또는 6자리"):
        asyncio.run(service.search_nearby(origin, 1000, industry_code="bad"))


def test_parse_store_row_rejects_missing_or_out_of_range_data() -> None:
    assert parse_store_row(_store_row(bizesNm="")) is None
    assert parse_store_row(_store_row(lat="99")) is None


STORE_HEADERS = [
    "상가업소번호",
    "상호명",
    "지점명",
    "상권업종대분류코드",
    "상권업종대분류명",
    "상권업종중분류코드",
    "상권업종중분류명",
    "상권업종소분류코드",
    "상권업종소분류명",
    "표준산업분류코드",
    "표준산업분류명",
    "시도명",
    "지번주소",
    "도로명주소",
    "경도",
    "위도",
]


def _csv_store_row(**overrides: str) -> dict[str, str]:
    api_row = _store_row()
    row = {
        "상가업소번호": str(api_row["bizesId"]),
        "상호명": str(api_row["bizesNm"]),
        "지점명": str(api_row["brchNm"]),
        "상권업종대분류코드": str(api_row["indsLclsCd"]),
        "상권업종대분류명": str(api_row["indsLclsNm"]),
        "상권업종중분류코드": str(api_row["indsMclsCd"]),
        "상권업종중분류명": str(api_row["indsMclsNm"]),
        "상권업종소분류코드": str(api_row["indsSclsCd"]),
        "상권업종소분류명": str(api_row["indsSclsNm"]),
        "표준산업분류코드": str(api_row["ksicCd"]),
        "표준산업분류명": str(api_row["ksicNm"]),
        "시도명": "경상북도",
        "지번주소": str(api_row["lnoAdr"]),
        "도로명주소": str(api_row["rdnmAdr"]),
        "경도": str(api_row["lon"]),
        "위도": str(api_row["lat"]),
    }
    row.update(overrides)
    return row


def _store_zip(path: Path, rows: list[dict[str, str]], member_count: int = 1) -> None:
    stream = StringIO()
    writer = csv.DictWriter(stream, STORE_HEADERS)
    writer.writeheader()
    writer.writerows(rows)
    with ZipFile(path, "w") as archive:
        for index in range(member_count):
            prefix = f"part{index}/" if index else ""
            archive.writestr(
                f"{prefix}소상공인시장진흥공단_상가(상권)정보_경북_202606.csv",
                stream.getvalue().encode("utf-8-sig"),
            )


def test_store_snapshot_loader_selects_gyeongbuk_and_skips_invalid_coordinates(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "stores.zip"
    _store_zip(
        archive_path,
        [_csv_store_row(), _csv_store_row(상가업소번호="B2", 위도="")],
    )
    connection = sqlite3.connect(":memory:")
    _create_schema(connection)

    assert _load_stores(connection, archive_path) == 1
    assert connection.execute("SELECT business_id FROM stores").fetchone() == ("B1",)


def test_store_snapshot_loader_rejects_duplicate_ids_and_wrong_province(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.zip"
    _store_zip(duplicate, [_csv_store_row(), _csv_store_row()])
    connection = sqlite3.connect(":memory:")
    _create_schema(connection)
    with pytest.raises(ValueError, match="중복 상가업소번호"):
        _load_stores(connection, duplicate)

    wrong_province = tmp_path / "wrong.zip"
    _store_zip(wrong_province, [_csv_store_row(시도명="경기도")])
    with pytest.raises(ValueError, match="다른 시도"):
        _load_stores(connection, wrong_province)


def test_store_snapshot_requires_exactly_one_gyeongbuk_member(tmp_path: Path) -> None:
    archive_path = tmp_path / "ambiguous.zip"
    _store_zip(archive_path, [_csv_store_row()], member_count=2)

    with ZipFile(archive_path) as archive, pytest.raises(FileNotFoundError, match="하나만"):
        _store_member_name(archive)
