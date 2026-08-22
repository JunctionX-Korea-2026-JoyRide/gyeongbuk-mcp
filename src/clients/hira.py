"""Health Insurance Review & Assessment Service client."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from clients.public_data import (
    JsonGateway,
    as_float,
    extract_items,
    require_service_key,
    value,
)

HOSPITAL_URL = "https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList"
DEPARTMENT_URL = "https://apis.data.go.kr/B551182/MadmDtlInfoService2.7/getDgsbjtInfo2.7"


class HiraClient:
    """Thin client for hospital lists and department details."""

    def __init__(self, gateway: JsonGateway, service_key: str | None) -> None:
        self._gateway = gateway
        self._service_key = service_key

    async def search_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_m: int,
        department_code: str | None = None,
        rows: int = 100,
    ) -> list[dict[str, Any]]:
        """Return raw HIRA hospitals in a coordinate radius."""

        params: dict[str, str | int | float] = {
            "serviceKey": require_service_key(self._service_key),
            "pageNo": 1,
            "numOfRows": rows,
            "xPos": longitude,
            "yPos": latitude,
            "radius": radius_m,
            "_type": "json",
        }
        if department_code:
            params["dgsbjtCd"] = department_code
        payload = await self._gateway.get(HOSPITAL_URL, params)
        return extract_items(payload)

    async def departments(self, institution_id: str) -> list[str]:
        """Return the declared departments of one institution."""

        payload = await self._gateway.get(
            DEPARTMENT_URL,
            {
                "serviceKey": require_service_key(self._service_key),
                "ykiho": institution_id,
                "pageNo": 1,
                "numOfRows": 100,
                "_type": "json",
            },
        )
        names: list[str] = []
        for row in extract_items(payload):
            name = value(row, "dgsbjtCdNm", "dgsbjtcdnm")
            if name and name not in names:
                names.append(name)
        return names


def parse_hospital_row(row: Mapping[str, Any]) -> dict[str, str | float | None] | None:
    """Normalize one HIRA row while rejecting missing coordinates."""

    latitude = as_float(value(row, "YPos", "ypos"))
    longitude = as_float(value(row, "XPos", "xpos"))
    institution_id = value(row, "ykiho")
    name = value(row, "yadmNm", "yadmnm")
    address = value(row, "addr")
    if latitude is None or longitude is None or not institution_id or not name or not address:
        return None
    return {
        "institution_id": institution_id,
        "name": name,
        "address": address,
        "phone": value(row, "telno"),
        "institution_type": value(row, "clCdNm", "clcdnm"),
        "latitude": latitude,
        "longitude": longitude,
    }
