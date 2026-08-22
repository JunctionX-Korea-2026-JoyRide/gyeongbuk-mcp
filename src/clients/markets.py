"""National standard traditional-market data client."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from clients.public_data import (
    JsonGateway,
    as_float,
    extract_items,
    require_service_key,
    value,
)

MARKET_URL = "https://api.data.go.kr/openapi/tn_pubr_public_trdit_mrkt_api"


class MarketClient:
    """Thin client for government-recognized traditional markets."""

    def __init__(self, gateway: JsonGateway, service_key: str | None) -> None:
        self._gateway = gateway
        self._service_key = service_key

    async def search_region(self, region: str, rows: int = 1000) -> list[dict[str, Any]]:
        """Return markets whose road-name or lot-number address contains a region."""

        page_one = await self._gateway.get(
            MARKET_URL,
            {
                "serviceKey": require_service_key(self._service_key),
                "pageNo": 1,
                "numOfRows": rows,
                "type": "json",
            },
        )
        items = extract_items(page_one)
        total_count = _total_count(page_one)
        for page_number in range(2, math.ceil(total_count / rows) + 1):
            payload = await self._gateway.get(
                MARKET_URL,
                {
                    "serviceKey": require_service_key(self._service_key),
                    "pageNo": page_number,
                    "numOfRows": rows,
                    "type": "json",
                },
            )
            items.extend(extract_items(payload))
        return [
            item
            for item in items
            if region in (value(item, "rdnmadr") or "") or region in (value(item, "lnmadr") or "")
        ]


def parse_market_row(row: Mapping[str, Any]) -> dict[str, str | float | None] | None:
    """Normalize one traditional-market row."""

    name = value(row, "mrktNm")
    address = value(row, "rdnmadr", "lnmadr")
    latitude = as_float(value(row, "latitude"))
    longitude = as_float(value(row, "longitude"))
    if not name or not address or latitude is None or longitude is None:
        return None
    return {
        "name": name,
        "address": address,
        "market_type": value(row, "mrktType"),
        "opening_cycle": value(row, "mrktEstblCycle", "operCycle"),
        "reference_date": value(row, "referenceDate"),
        "latitude": latitude,
        "longitude": longitude,
    }


def _total_count(payload: Mapping[str, Any]) -> int:
    response = payload.get("response", payload)
    if not isinstance(response, Mapping):
        return 0
    body = response.get("body", response)
    if not isinstance(body, Mapping):
        return 0
    raw_total = value(body, "totalCount")
    if raw_total is None:
        return len(extract_items(payload))
    try:
        return int(raw_total)
    except ValueError:
        return len(extract_items(payload))
