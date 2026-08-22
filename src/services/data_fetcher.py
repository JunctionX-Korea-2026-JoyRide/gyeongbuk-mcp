"""Download and verify pinned public-data inputs."""

from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import html
import re
import tempfile
import tomllib
import uuid
from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import urljoin, urlsplit
from zipfile import BadZipFile, ZipFile

import httpx

DownloadStrategy = Literal[
    "direct",
    "data_go_file",
    "hira_file",
    "mois_population_csv",
    "pohang_attachment",
]
SourceFormat = Literal["csv", "zip", "hwpx", "pdf"]
FetchStatus = Literal["verified", "downloaded"]

_ALLOWED_STRATEGIES = {
    "direct",
    "data_go_file",
    "hira_file",
    "mois_population_csv",
    "pohang_attachment",
}
_ALLOWED_FORMATS = {"csv", "zip", "hwpx", "pdf"}
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class DataFetchError(RuntimeError):
    """Actionable failure while loading, downloading, or validating a source."""


@dataclass(frozen=True, slots=True)
class DataSource:
    """One pinned public-data source from the manifest."""

    source_id: str
    name: str
    landing_url: str
    strategy: DownloadStrategy
    filename: str
    sha256: str
    source_format: SourceFormat
    as_of: str
    license_name: str
    attribution: str
    download_url: str | None = None
    encoding: str = "utf-8"
    required_headers: tuple[str, ...] = ()
    attachment_label: str | None = None


@dataclass(frozen=True, slots=True)
class SourceManifest:
    """Validated collection of unique pinned sources."""

    version: int
    sources: tuple[DataSource, ...]

    def select(self, source_ids: list[str] | None = None) -> tuple[DataSource, ...]:
        """Return all sources or the requested IDs in manifest order."""

        if not source_ids:
            return self.sources
        requested = set(source_ids)
        known = {source.source_id for source in self.sources}
        unknown = sorted(requested - known)
        if unknown:
            raise DataFetchError(f"알 수 없는 source ID입니다: {', '.join(unknown)}")
        return tuple(source for source in self.sources if source.source_id in requested)


def load_source_manifest(path: Path) -> SourceManifest:
    """Load and strictly validate a TOML data-source manifest."""

    try:
        with path.open("rb") as stream:
            raw = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise DataFetchError(f"데이터 manifest를 읽을 수 없습니다: {path}") from exc

    if raw.get("version") != 1:
        raise DataFetchError("data manifest version은 1이어야 합니다.")
    raw_sources = raw.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise DataFetchError("data manifest에 sources가 필요합니다.")

    sources = tuple(_parse_source(item) for item in raw_sources)
    _require_unique("source ID", [source.source_id for source in sources])
    _require_unique("filename", [source.filename for source in sources])
    return SourceManifest(version=1, sources=sources)


def validate_referenced_pdfs(manifest: SourceManifest, reference_csv: Path) -> None:
    """Ensure every PDF named by the reviewed timetable CSV is pinned."""

    try:
        with reference_csv.open(encoding="utf-8", newline="") as stream:
            referenced = {
                row["source_document"].strip()
                for row in csv.DictReader(stream)
                if row.get("source_document", "").strip().lower().endswith(".pdf")
            }
    except (OSError, KeyError) as exc:
        raise DataFetchError(f"지선 검수 CSV를 읽을 수 없습니다: {reference_csv}") from exc
    pinned = {source.filename for source in manifest.sources if source.source_format == "pdf"}
    missing = sorted(referenced - pinned)
    if missing:
        raise DataFetchError(f"manifest에 참조 PDF가 없습니다: {', '.join(missing)}")


class DataFetcher:
    """Fetch pinned inputs without replacing a valid local file prematurely."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        output_dir: Path,
        retry_delays: tuple[float, ...] = (1.0, 2.0, 4.0),
    ) -> None:
        self._client = client
        self._output_dir = output_dir
        self._retry_delays = retry_delays

    async def fetch(
        self, source: DataSource, *, check: bool = False, force: bool = False
    ) -> FetchStatus:
        """Verify one source or download it and replace atomically."""

        destination = self._output_dir / source.filename
        if destination.is_file():
            try:
                validate_source_file(source, destination)
            except DataFetchError:
                if check or not force:
                    raise DataFetchError(
                        f"[{source.source_id}] 기존 파일 검증에 실패했습니다. "
                        f"검수 후 --force로 다시 받으세요: {source.landing_url}"
                    ) from None
            else:
                if check or not force:
                    return "verified"
        elif check:
            raise DataFetchError(
                f"[{source.source_id}] 파일이 없습니다: {destination}\n{source.landing_url}"
            )

        try:
            content = await self._download(source)
        except DataFetchError as exc:
            if str(exc).startswith(f"[{source.source_id}]"):
                raise
            raise DataFetchError(
                f"[{source.source_id}] 다운로드에 실패했습니다: {source.landing_url}\n{exc}"
            ) from exc
        validate_source_bytes(source, content)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=f".{source.source_id}-",
            suffix=".tmp",
            dir=self._output_dir,
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        try:
            temporary_path.replace(destination)
        finally:
            temporary_path.unlink(missing_ok=True)
        return "downloaded"

    async def _download(self, source: DataSource) -> bytes:
        if source.strategy in {"direct", "data_go_file"}:
            return await self._get_required_url(source)
        if source.strategy == "hira_file":
            return await self._download_hira_file(source)
        if source.strategy == "mois_population_csv":
            return await self._download_population(source)
        if source.strategy == "pohang_attachment":
            return await self._download_pohang_attachment(source)
        raise DataFetchError(f"[{source.source_id}] 지원하지 않는 다운로드 전략입니다.")

    async def _get_required_url(
        self, source: DataSource, headers: dict[str, str] | None = None
    ) -> bytes:
        if source.download_url is None:
            raise DataFetchError(f"[{source.source_id}] download_url이 필요합니다.")
        response = await self._request("GET", source.download_url, headers=headers)
        return response.content

    async def _download_hira_file(self, source: DataSource) -> bytes:
        if source.download_url is None:
            raise DataFetchError(f"[{source.source_id}] download_url이 필요합니다.")
        if source.attachment_label is None:
            raise DataFetchError(f"[{source.source_id}] attachment_label이 필요합니다.")

        landing = await self._request("GET", source.landing_url)
        virtual_path = _hira_attachment_path(
            landing.text, source.attachment_label, source.source_id
        )
        payload = "".join(
            (
                "d01\fdownloadRequest\v",
                "d10\f_\v",
                f"d25\f{virtual_path}\v",
                f"d26\f{source.attachment_label}\v",
                f"d07\f{uuid.uuid4()}\v",
            )
        )
        encoded_payload = base64.b64encode(payload.encode()).decode()
        encrypted_parameter = base64.b64encode(f"R{encoded_payload}".encode()).decode()
        response = await self._request(
            "POST",
            source.download_url,
            data={"d00": encrypted_parameter.replace("+", "%2B"), "customValue": ""},
            headers={"Referer": source.landing_url},
        )
        return response.content

    async def _download_population(self, source: DataSource) -> bytes:
        if source.download_url is None:
            raise DataFetchError(f"[{source.source_id}] download_url이 필요합니다.")
        match = re.fullmatch(r"(\d{4})-(\d{2})", source.as_of)
        if match is None:
            raise DataFetchError(f"[{source.source_id}] as_of는 YYYY-MM 형식이어야 합니다.")
        year, month = match.groups()
        response = await self._request(
            "POST",
            source.download_url,
            data={
                "sltOrgType": "1",
                "sltOrgLvl1": "A",
                "sltOrgLvl2": "",
                "gender": "gender",
                "sum": "sum",
                "sltUndefType": "",
                "searchYearStart": year,
                "searchMonthStart": month,
                "searchYearEnd": year,
                "searchMonthEnd": month,
                "sltOrderType": "1",
                "sltOrderValue": "ASC",
                "sltArgTypes": "10",
                "sltArgTypeA": "0",
                "sltArgTypeB": "100",
                "category": "month",
            },
        )
        return response.content

    async def _download_pohang_attachment(self, source: DataSource) -> bytes:
        if source.attachment_label is None:
            raise DataFetchError(f"[{source.source_id}] attachment_label이 필요합니다.")
        landing = await self._request("GET", source.landing_url)
        attachment_id, file_id = _pohang_attachment_ids(
            landing.text, source.attachment_label, source.source_id
        )
        origin = _origin(source.landing_url)
        response = await self._request(
            "GET",
            urljoin(origin, "/common/file/download.do"),
            params={"atchFileId": attachment_id, "fileSn": file_id},
            headers={"Referer": source.landing_url},
        )
        return response.content

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: Any = None,
        data: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        last_error: Exception | None = None
        for attempt, delay in enumerate(self._retry_delays, start=1):
            try:
                response = await self._client.request(
                    method, url, params=params, data=data, headers=headers
                )
                response.raise_for_status()
                return response
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt == len(self._retry_delays):
                    break
                await asyncio.sleep(delay)
        raise DataFetchError(f"공식 데이터 다운로드에 실패했습니다: {url}") from last_error


def validate_source_file(source: DataSource, path: Path) -> None:
    """Validate one existing source file without exposing its contents."""

    try:
        content = path.read_bytes()
    except OSError as exc:
        raise DataFetchError(f"[{source.source_id}] 파일을 읽을 수 없습니다: {path}") from exc
    validate_source_bytes(source, content)


def validate_source_bytes(source: DataSource, content: bytes) -> None:
    """Validate checksum and the minimum structure required by the snapshot builder."""

    actual_hash = hashlib.sha256(content).hexdigest()
    if actual_hash != source.sha256:
        raise DataFetchError(
            f"[{source.source_id}] SHA-256이 manifest와 다릅니다. "
            f"원본 변경 여부를 검수하세요: {source.landing_url}"
        )
    if source.source_format == "pdf":
        if not content.startswith(b"%PDF-"):
            raise DataFetchError(f"[{source.source_id}] PDF 형식이 아닙니다.")
        return
    if source.source_format in {"zip", "hwpx"}:
        try:
            with ZipFile(BytesIO(content)) as archive:
                if archive.testzip() is not None:
                    raise DataFetchError(f"[{source.source_id}] ZIP 내부 파일이 손상되었습니다.")
                if (
                    source.source_format == "hwpx"
                    and "Contents/section0.xml" not in archive.namelist()
                ):
                    raise DataFetchError(f"[{source.source_id}] 지역안전지수 HWPX 형식이 아닙니다.")
        except BadZipFile as exc:
            raise DataFetchError(f"[{source.source_id}] ZIP 형식이 아닙니다.") from exc
        return
    if source.source_format == "csv":
        try:
            decoded = content.decode(source.encoding)
            header = next(csv.reader(StringIO(decoded)))
        except (UnicodeDecodeError, StopIteration, csv.Error) as exc:
            raise DataFetchError(f"[{source.source_id}] CSV를 읽을 수 없습니다.") from exc
        missing = sorted(set(source.required_headers) - set(header))
        if missing:
            raise DataFetchError(
                f"[{source.source_id}] CSV 필수 열이 없습니다: {', '.join(missing)}"
            )


def _parse_source(raw: object) -> DataSource:
    if not isinstance(raw, dict):
        raise DataFetchError("각 source는 TOML table이어야 합니다.")
    required = {
        "id",
        "name",
        "landing_url",
        "strategy",
        "filename",
        "sha256",
        "format",
        "as_of",
        "license",
        "attribution",
    }
    missing = sorted(required - raw.keys())
    if missing:
        raise DataFetchError(f"source 필수 필드가 없습니다: {', '.join(missing)}")
    for field in required:
        if not isinstance(raw[field], str) or not raw[field].strip():
            raise DataFetchError(f"source.{field}는 비어 있지 않은 문자열이어야 합니다.")
    strategy = str(raw["strategy"])
    source_format = str(raw["format"])
    filename = str(raw["filename"])
    sha256 = str(raw["sha256"])
    landing_url = str(raw["landing_url"])
    if strategy not in _ALLOWED_STRATEGIES:
        raise DataFetchError(f"지원하지 않는 source.strategy입니다: {strategy}")
    if source_format not in _ALLOWED_FORMATS:
        raise DataFetchError(f"지원하지 않는 source.format입니다: {source_format}")
    if Path(filename).name != filename:
        raise DataFetchError(f"source.filename에는 디렉터리를 사용할 수 없습니다: {filename}")
    if _SHA256_PATTERN.fullmatch(sha256) is None:
        raise DataFetchError(f"source.sha256 형식이 올바르지 않습니다: {raw['id']}")
    if urlsplit(landing_url).scheme != "https":
        raise DataFetchError(f"source.landing_url은 HTTPS여야 합니다: {raw['id']}")
    headers = raw.get("required_headers", [])
    if not isinstance(headers, list) or not all(isinstance(item, str) for item in headers):
        raise DataFetchError(f"source.required_headers 형식이 올바르지 않습니다: {raw['id']}")
    return DataSource(
        source_id=str(raw["id"]),
        name=str(raw["name"]),
        landing_url=landing_url,
        strategy=cast(DownloadStrategy, strategy),
        filename=filename,
        sha256=sha256,
        source_format=cast(SourceFormat, source_format),
        as_of=str(raw["as_of"]),
        license_name=str(raw["license"]),
        attribution=str(raw["attribution"]),
        download_url=_optional_string(raw, "download_url"),
        encoding=str(raw.get("encoding", "utf-8")),
        required_headers=tuple(headers),
        attachment_label=_optional_string(raw, "attachment_label"),
    )


def _optional_string(raw: dict[str, Any], field: str) -> str | None:
    value = raw.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise DataFetchError(f"source.{field}는 비어 있지 않은 문자열이어야 합니다.")
    return value


def _require_unique(label: str, values: list[str]) -> None:
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        raise DataFetchError(f"중복 {label}가 있습니다: {', '.join(duplicates)}")


def _pohang_attachment_ids(page: str, label: str, source_id: str) -> tuple[str, str]:
    for attributes in re.findall(r"<a\b([^>]*)>", page, flags=re.IGNORECASE):
        decoded = html.unescape(attributes)
        if label not in decoded:
            continue
        match = re.search(
            r"file\.download\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]",
            decoded,
        )
        if match is not None:
            return match.group(1), match.group(2)
    raise DataFetchError(f"[{source_id}] 공식 페이지에서 첨부파일을 찾을 수 없습니다: {label}")


def _hira_attachment_path(page: str, label: str, source_id: str) -> str:
    pattern = re.compile(
        r"DEXT5UPLOAD\.AddUploadedFile\(\s*['\"][^'\"]+['\"]\s*,\s*"
        r"['\"](?P<label>[^'\"]+)['\"]\s*,\s*['\"](?P<path>[^'\"]+)['\"]"
    )
    for match in pattern.finditer(page):
        if html.unescape(match.group("label")) == label:
            return html.unescape(match.group("path"))
    raise DataFetchError(f"[{source_id}] 공식 페이지에서 첨부파일을 찾을 수 없습니다: {label}")


def _origin(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}"
