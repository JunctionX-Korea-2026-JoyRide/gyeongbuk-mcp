"""Shared HTTP and response parsing for Korean public-data APIs."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Mapping
from typing import Any, Protocol, cast

import httpx


class DataSourceError(RuntimeError):
    """A safe error raised when an external public-data source fails."""


class JsonGateway(Protocol):
    """Minimal gateway used by clients and test doubles."""

    async def get(self, url: str, params: Mapping[str, str | int | float]) -> dict[str, Any]:
        """Fetch and parse a public-data response."""


class HttpJsonGateway:
    """HTTP implementation supporting both JSON and standard XML envelopes."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout_seconds = timeout_seconds

    async def get(self, url: str, params: Mapping[str, str | int | float]) -> dict[str, Any]:
        """Fetch a response without exposing upstream exception details."""

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            raise DataSourceError("공공데이터 제공기관에 연결할 수 없습니다.") from exc

        try:
            payload = response.json()
            if not isinstance(payload, dict):
                raise DataSourceError("공공데이터 응답 형식이 올바르지 않습니다.")
            return cast(dict[str, Any], payload)
        except ValueError:
            try:
                return _xml_to_dict(response.text)
            except ET.ParseError as exc:
                raise DataSourceError("공공데이터 응답을 해석할 수 없습니다.") from exc


def require_service_key(service_key: str | None) -> str:
    """Return a configured key or raise an actionable, secret-safe error."""

    if service_key is None:
        raise DataSourceError("DATA_GO_KR_SERVICE_KEY 환경변수가 필요합니다.")
    return service_key


def extract_items(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Extract item rows from common data.go.kr response envelopes."""

    response = payload.get("response", payload)
    if not isinstance(response, Mapping):
        raise DataSourceError("공공데이터 응답에 response가 없습니다.")

    header = response.get("header")
    if isinstance(header, Mapping):
        code = str(header.get("resultCode", header.get("resultcode", "00")))
        if code not in {"0", "00", "NORMAL_CODE", "INFO-0"}:
            raise DataSourceError("공공데이터 제공기관이 오류를 반환했습니다.")

    body = response.get("body", response)
    if not isinstance(body, Mapping):
        return []
    items = body.get("items", body.get("data", []))
    if isinstance(items, Mapping):
        items = items.get("item", items.get("data", []))
    if items is None or items == "":
        return []
    if isinstance(items, Mapping):
        return [dict(items)]
    if isinstance(items, list):
        return [dict(item) for item in items if isinstance(item, Mapping)]
    return []


def value(row: Mapping[str, Any], *names: str) -> str | None:
    """Read the first non-empty field while tolerating API casing changes."""

    lower = {str(key).lower(): item for key, item in row.items()}
    for name in names:
        item = row.get(name, lower.get(name.lower()))
        if item is not None and str(item).strip():
            return str(item).strip()
    return None


def as_float(raw: str | None) -> float | None:
    """Parse a numeric API field."""

    if raw is None:
        return None
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def as_int(raw: str | None) -> int | None:
    """Parse an integer-like API field."""

    number = as_float(raw)
    return int(number) if number is not None else None


def _xml_to_dict(text: str) -> dict[str, Any]:
    root = ET.fromstring(text)
    return {root.tag: _element_value(root)} if root.tag != "response" else _element_value(root)


def _element_value(element: ET.Element) -> Any:
    children = list(element)
    if not children:
        return (element.text or "").strip()

    result: dict[str, Any] = {}
    for child in children:
        child_value = _element_value(child)
        if child.tag in result:
            existing = result[child.tag]
            if not isinstance(existing, list):
                result[child.tag] = [existing]
            result[child.tag].append(child_value)
        else:
            result[child.tag] = child_value
    return result
