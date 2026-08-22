"""Small Enterprise and Market Service commercial-business client."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, cast

from clients.public_data import (
    JsonGateway,
    as_float,
    extract_items,
    require_service_key,
    value,
)

STORE_API_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInRadius"
STORE_FILE_URL = "https://www.data.go.kr/data/15083033/fileData.do"


class StoreClient:
    """Query operating businesses from the official radius-search API."""

    def __init__(self, gateway: JsonGateway, service_key: str | None) -> None:
        self._gateway = gateway
        self._service_key = service_key

    async def search_radius(
        self,
        latitude: float,
        longitude: float,
        radius_m: int,
        industry_code: str | None = None,
        rows: int = 1000,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Return every API row inside a radius and its source reference month."""

        params: dict[str, str | int | float] = {
            "ServiceKey": require_service_key(self._service_key),
            "pageNo": 1,
            "numOfRows": rows,
            "radius": radius_m,
            "cx": longitude,
            "cy": latitude,
            "type": "json",
        }
        if industry_code:
            params[_industry_parameter(industry_code)] = industry_code.upper()

        page_one = await self._gateway.get(STORE_API_URL, params)
        items = extract_items(page_one)
        total_count = _total_count(page_one)
        as_of = _reference_date(page_one, items)
        for page_number in range(2, math.ceil(total_count / rows) + 1):
            params["pageNo"] = page_number
            payload = await self._gateway.get(STORE_API_URL, params)
            page_items = extract_items(payload)
            items.extend(page_items)
            as_of = as_of or _reference_date(payload, page_items)
        return items, as_of


def parse_store_row(row: Mapping[str, Any]) -> dict[str, str | float | None] | None:
    """Normalize one API or local-snapshot store row."""

    business_id = value(row, "bizesId", "상가업소번호")
    name = value(row, "bizesNm", "상호명")
    address = value(row, "rdnmAdr", "도로명주소", "lnoAdr", "지번주소")
    latitude = as_float(value(row, "lat", "위도"))
    longitude = as_float(value(row, "lon", "경도"))
    large_code = value(row, "indsLclsCd", "상권업종대분류코드")
    large_name = value(row, "indsLclsNm", "상권업종대분류명")
    medium_code = value(row, "indsMclsCd", "상권업종중분류코드")
    medium_name = value(row, "indsMclsNm", "상권업종중분류명")
    small_code = value(row, "indsSclsCd", "상권업종소분류코드")
    small_name = value(row, "indsSclsNm", "상권업종소분류명")
    if not all(
        (
            business_id,
            name,
            address,
            large_code,
            large_name,
            medium_code,
            medium_name,
            small_code,
            small_name,
        )
    ):
        return None
    if (
        latitude is None
        or longitude is None
        or not math.isfinite(latitude)
        or not math.isfinite(longitude)
        or not 33.0 <= latitude <= 39.5
        or not 124.0 <= longitude <= 132.0
    ):
        return None
    return {
        "business_id": business_id,
        "name": name,
        "branch_name": value(row, "brchNm", "지점명"),
        "industry_large_code": cast(str, large_code).upper(),
        "industry_large_name": cast(str, large_name),
        "industry_medium_code": cast(str, medium_code).upper(),
        "industry_medium_name": cast(str, medium_name),
        "industry_small_code": cast(str, small_code).upper(),
        "industry_small_name": cast(str, small_name),
        "standard_industry_code": value(row, "ksicCd", "표준산업분류코드"),
        "standard_industry_name": value(row, "ksicNm", "표준산업분류명"),
        "address": address,
        "latitude": latitude,
        "longitude": longitude,
    }


def _industry_parameter(industry_code: str) -> str:
    code_length = len(industry_code)
    if code_length == 2:
        return "indsLclsCd"
    if code_length == 4:
        return "indsMclsCd"
    if code_length == 6:
        return "indsSclsCd"
    raise ValueError("industry_code must contain 2, 4, or 6 characters")


def _total_count(payload: Mapping[str, Any]) -> int:
    response = payload.get("response", payload)
    if not isinstance(response, Mapping):
        return 0
    body = response.get("body", response)
    if not isinstance(body, Mapping):
        return 0
    raw_total = value(body, "totalCount")
    try:
        return int(raw_total) if raw_total is not None else len(extract_items(payload))
    except ValueError:
        return len(extract_items(payload))


def _reference_date(payload: Mapping[str, Any], items: list[dict[str, Any]]) -> str | None:
    response = payload.get("response", payload)
    body = response.get("body", response) if isinstance(response, Mapping) else None
    raw = value(body, "stdrYm", "stdrDt") if isinstance(body, Mapping) else None
    if raw is None and items:
        raw = value(items[0], "stdrYm", "stdrDt")
    if raw is None:
        return None
    digits = "".join(character for character in raw if character.isdigit())
    if len(digits) >= 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    if len(digits) >= 6:
        return f"{digits[:4]}-{digits[4:6]}"
    return raw
