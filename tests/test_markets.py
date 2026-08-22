"""Tests for traditional-market pagination and local region filtering."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from clients.markets import MarketClient, parse_market_row


class PaginatedGateway:
    """Return one market per page and expose a two-row total."""

    async def get(self, url: str, params: Mapping[str, str | int | float]) -> dict[str, Any]:
        del url
        page = int(params["pageNo"])
        address = "경상북도 포항시 북구" if page == 2 else "경기도 이천시"
        return {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
            "body": {
                "totalCount": 2,
                "items": {
                    "item": {
                        "mrktNm": f"시장{page}",
                        "rdnmadr": address,
                        "latitude": "36.0",
                        "longitude": "129.0",
                        "mrktEstblCycle": "매일",
                    }
                },
            },
        }


def test_market_client_paginates_then_filters_region() -> None:
    result = asyncio.run(MarketClient(PaginatedGateway(), "test-key").search_region("포항시", 1))

    assert [row["mrktNm"] for row in result] == ["시장2"]


def test_parse_market_uses_actual_opening_cycle_field() -> None:
    result = parse_market_row(
        {
            "mrktNm": "죽도시장",
            "rdnmadr": "경상북도 포항시",
            "latitude": "36.0",
            "longitude": "129.0",
            "mrktEstblCycle": "매일",
        }
    )

    assert result is not None
    assert result["opening_cycle"] == "매일"
