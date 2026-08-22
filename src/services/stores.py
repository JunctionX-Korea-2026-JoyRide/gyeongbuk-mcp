"""Deterministic filtering and distance calculations for commercial businesses."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from typing import Any, Protocol, cast

from clients.public_data import DataSourceError
from clients.stores import STORE_API_URL, STORE_FILE_URL, parse_store_row
from models.location import Coordinates, DataSourceMetadata
from models.stores import Store, StoreSearchResult
from services.geo import estimated_walk_minutes, haversine_distance_m


class StoresClient(Protocol):
    """Data access required for nearby store searches."""

    async def search_radius(
        self,
        latitude: float,
        longitude: float,
        radius_m: int,
        industry_code: str | None = None,
        rows: int = 1000,
    ) -> tuple[list[dict[str, Any]], str | None]: ...


class StoreService:
    """Normalize, filter, and rank nearby operating businesses."""

    def __init__(
        self,
        client: StoresClient,
        walking_speed_m_per_minute: float = 60.0,
        file_mode: bool = False,
    ) -> None:
        if walking_speed_m_per_minute <= 0:
            raise ValueError("Walking speed must be positive")
        self._client = client
        self._walking_speed = walking_speed_m_per_minute
        self._file_mode = file_mode

    async def search_nearby(
        self,
        origin: Coordinates,
        radius_m: int,
        industry_code: str | None = None,
        industry_name: str | None = None,
        name_query: str | None = None,
        result_limit: int = 20,
    ) -> StoreSearchResult:
        """Return matching businesses ordered by exact straight-line distance."""

        if not 1 <= radius_m <= 2000:
            raise DataSourceError("radius_m은 1 이상 2000 이하의 정수여야 합니다.")
        if not 1 <= result_limit <= 100:
            raise DataSourceError("result_limit은 1 이상 100 이하의 정수여야 합니다.")
        code = _validate_industry_code(industry_code)
        normalized_industry = _optional_query(industry_name, "industry_name")
        normalized_name = _optional_query(name_query, "name_query")
        rows, as_of = await self._client.search_radius(
            origin.latitude,
            origin.longitude,
            radius_m,
            code,
        )
        stores_by_id: dict[str, tuple[float, Store]] = {}
        for row in rows:
            normalized = parse_store_row(row)
            if normalized is None or not _matches_filters(
                normalized, code, normalized_industry, normalized_name
            ):
                continue
            latitude = cast(float, normalized["latitude"])
            longitude = cast(float, normalized["longitude"])
            distance = haversine_distance_m(
                origin.latitude,
                origin.longitude,
                latitude,
                longitude,
            )
            if distance > radius_m:
                continue
            business_id = cast(str, normalized["business_id"])
            store = Store(
                business_id=business_id,
                name=cast(str, normalized["name"]),
                branch_name=cast(str | None, normalized["branch_name"]),
                industry_large_code=cast(str, normalized["industry_large_code"]),
                industry_large_name=cast(str, normalized["industry_large_name"]),
                industry_medium_code=cast(str, normalized["industry_medium_code"]),
                industry_medium_name=cast(str, normalized["industry_medium_name"]),
                industry_small_code=cast(str, normalized["industry_small_code"]),
                industry_small_name=cast(str, normalized["industry_small_name"]),
                standard_industry_code=cast(str | None, normalized["standard_industry_code"]),
                standard_industry_name=cast(str | None, normalized["standard_industry_name"]),
                address=cast(str, normalized["address"]),
                coordinates=Coordinates(latitude=latitude, longitude=longitude),
                distance_m=round(distance, 1),
                estimated_walk_minutes=estimated_walk_minutes(distance, self._walking_speed),
            )
            existing = stores_by_id.get(business_id)
            if existing is None or distance < existing[0]:
                stores_by_id[business_id] = (distance, store)
        stores = [
            item[1]
            for item in sorted(
                stores_by_id.values(),
                key=lambda item: (item[0], item[1].name, item[1].business_id),
            )[:result_limit]
        ]
        return StoreSearchResult(
            stores=stores,
            radius_m=radius_m,
            walking_speed_m_per_minute=self._walking_speed,
            source=DataSourceMetadata(
                source_name="소상공인시장진흥공단 상가(상권)정보",
                source_url=STORE_FILE_URL if self._file_mode else STORE_API_URL,
                as_of=as_of or ("2026-06-30" if self._file_mode else None),
                is_estimated=True,
                estimation_method=(
                    f"업소 좌표와 기준점의 직선거리를 분당 {self._walking_speed:g}m 보행속도로 환산"
                ),
            ),
            warnings=[
                "영업 상태는 원본 기준이며 실시간 영업 여부·영업시간·전화번호를 보장하지 않습니다.",
                "실제 보행로, 경사, 횡단보도와 건물 출입구는 반영되지 않습니다.",
                "상가업소번호는 원본 분류 개편 시 변경될 수 있습니다.",
            ],
        )


def _validate_industry_code(value: str | None) -> str | None:
    if value is None:
        return None
    code = value.strip().upper()
    if re.fullmatch(r"[0-9A-Z]{2}(?:[0-9A-Z]{2}){0,2}", code) is None:
        raise DataSourceError("industry_code는 영문·숫자 2자리, 4자리 또는 6자리여야 합니다.")
    return code


def _optional_query(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    normalized = _normalize_text(value)
    if not normalized:
        raise DataSourceError(f"{field}에는 검색할 문자가 필요합니다.")
    return normalized


def _matches_filters(
    row: Mapping[str, str | float | None],
    industry_code: str | None,
    industry_name: str | None,
    name_query: str | None,
) -> bool:
    if industry_code is not None:
        code_field = {
            2: "industry_large_code",
            4: "industry_medium_code",
            6: "industry_small_code",
        }[len(industry_code)]
        if row[code_field] != industry_code:
            return False
    if industry_name is not None:
        industry_names = (
            row["industry_large_name"],
            row["industry_medium_name"],
            row["industry_small_name"],
        )
        if not any(industry_name in _normalize_text(str(name)) for name in industry_names if name):
            return False
    if name_query is not None:
        business_names = (row["name"], row["branch_name"])
        if not any(name_query in _normalize_text(str(name)) for name in business_names if name):
            return False
    return True


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^0-9a-z가-힣]", "", normalized)
