"""Tests for pinned public-data downloads and manifest validation."""

from __future__ import annotations

import asyncio
import base64
import hashlib
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import httpx
import pytest

from services.data_fetcher import (
    DataFetcher,
    DataFetchError,
    DataSource,
    DownloadStrategy,
    SourceFormat,
    load_source_manifest,
    validate_referenced_pdfs,
    validate_source_bytes,
    validate_source_file,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _source(
    content: bytes,
    *,
    strategy: DownloadStrategy = "direct",
    source_format: SourceFormat = "pdf",
    filename: str = "source.pdf",
) -> DataSource:
    return DataSource(
        source_id="source-1",
        name="테스트 원본",
        landing_url="https://example.test/landing",
        download_url="https://example.test/download",
        strategy=strategy,
        filename=filename,
        sha256=hashlib.sha256(content).hexdigest(),
        source_format=source_format,
        as_of="2026-07",
        license_name="test",
        attribution="test",
    )


def _client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler, follow_redirects=True)


def _zip_bytes(filename: str, content: bytes) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(filename, content)
    return buffer.getvalue()


def test_fetch_downloads_redirect_and_verifies_pdf(tmp_path: Path) -> None:
    content = b"%PDF-1.7\nvalid"
    source = _source(content)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/download":
            return httpx.Response(302, headers={"Location": "/actual"})
        return httpx.Response(200, content=content)

    async def run() -> str:
        async with _client(httpx.MockTransport(handler)) as client:
            return await DataFetcher(client, tmp_path, (0,)).fetch(source)

    assert asyncio.run(run()) == "downloaded"
    assert (tmp_path / source.filename).read_bytes() == content


def test_fetch_streams_and_verifies_large_zip_path(tmp_path: Path) -> None:
    content = _zip_bytes("stores.csv", b"header\nvalue")
    source = _source(
        content,
        strategy="data_go_file",
        source_format="zip",
        filename="stores.zip",
    )

    async def run() -> str:
        transport = httpx.MockTransport(lambda _: httpx.Response(200, content=content))
        async with _client(transport) as client:
            return await DataFetcher(client, tmp_path, (0,)).fetch(source)

    assert asyncio.run(run()) == "downloaded"
    assert (tmp_path / "stores.zip").read_bytes() == content


def test_fetch_skips_existing_valid_file_without_network(tmp_path: Path) -> None:
    content = b"%PDF-1.4\nexisting"
    source = _source(content)
    (tmp_path / source.filename).write_bytes(content)

    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be called")

    async def run() -> str:
        async with _client(httpx.MockTransport(handler)) as client:
            return await DataFetcher(client, tmp_path, (0,)).fetch(source)

    assert asyncio.run(run()) == "verified"


def test_check_rejects_missing_file(tmp_path: Path) -> None:
    source = _source(b"%PDF-1.4\nmissing")

    async def run() -> None:
        async with _client(httpx.MockTransport(lambda _: httpx.Response(500))) as client:
            await DataFetcher(client, tmp_path, (0,)).fetch(source, check=True)

    with pytest.raises(DataFetchError, match="파일이 없습니다"):
        asyncio.run(run())


def test_force_preserves_existing_file_when_download_checksum_differs(tmp_path: Path) -> None:
    existing = b"%PDF-1.4\nexisting"
    source = _source(existing)
    destination = tmp_path / source.filename
    destination.write_bytes(existing)

    async def run() -> None:
        transport = httpx.MockTransport(lambda _: httpx.Response(200, content=b"changed"))
        async with _client(transport) as client:
            await DataFetcher(client, tmp_path, (0,)).fetch(source, force=True)

    with pytest.raises(DataFetchError, match="SHA-256"):
        asyncio.run(run())
    assert destination.read_bytes() == existing


def test_fetch_retries_timeout_then_succeeds(tmp_path: Path) -> None:
    content = b"%PDF-1.4\nretried"
    source = _source(content)
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(200, content=content)

    async def run() -> None:
        async with _client(httpx.MockTransport(handler)) as client:
            await DataFetcher(client, tmp_path, (0, 0, 0)).fetch(source)

    asyncio.run(run())
    assert calls == 3


@pytest.mark.parametrize(
    ("source_format", "content", "message"),
    [
        ("pdf", b"not-pdf", "PDF 형식"),
        ("zip", b"not-zip", "ZIP 형식"),
        ("csv", b"wrong\nvalue", "필수 열"),
    ],
)
def test_source_validation_rejects_invalid_structure(
    source_format: SourceFormat, content: bytes, message: str
) -> None:
    source = _source(content, source_format=source_format, filename=f"source.{source_format}")
    if source_format == "csv":
        source = replace(source, required_headers=("required",))

    with pytest.raises(DataFetchError, match=message):
        validate_source_bytes(source, content)


def test_hwpx_validation_requires_section_zero() -> None:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/hwp+zip")
    content = buffer.getvalue()
    source = _source(content, source_format="hwpx", filename="source.hwpx")

    with pytest.raises(DataFetchError, match="HWPX 형식"):
        validate_source_bytes(source, content)


def test_pohang_attachment_page_change_is_actionable(tmp_path: Path) -> None:
    content = b"%PDF-1.4\nattachment"
    source = replace(
        _source(content, strategy="pohang_attachment"),
        attachment_label="expected.pdf",
    )

    async def run() -> None:
        transport = httpx.MockTransport(lambda _: httpx.Response(200, text="<html></html>"))
        async with _client(transport) as client:
            await DataFetcher(client, tmp_path, (0,)).fetch(source)

    with pytest.raises(DataFetchError, match="첨부파일을 찾을 수 없습니다"):
        asyncio.run(run())


def test_hira_strategy_discovers_attachment_and_posts_encrypted_request(
    tmp_path: Path,
) -> None:
    content = _zip_bytes("hospital.csv", b"hospital")
    label = "hospital snapshot.zip"
    virtual_path = "/shared/data/uploadFiles/file/pinned.zip"
    source = replace(
        _source(content, strategy="hira_file", source_format="zip", filename="hira.zip"),
        attachment_label=label,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            script = (
                "DEXT5UPLOAD.AddUploadedFile('326801', "
                f"'{label}', '{virtual_path}', '123', '326801', uploadID);"
            )
            return httpx.Response(200, text=script)
        assert request.method == "POST"
        body = request.content.decode()
        d00 = next(part.removeprefix("d00=") for part in body.split("&") if part.startswith("d00="))
        outer = base64.b64decode(httpx.QueryParams(f"d00={d00}")["d00"])
        payload = base64.b64decode(outer.removeprefix(b"R")).decode()
        assert "d01\fdownloadRequest\v" in payload
        assert f"d25\f{virtual_path}\v" in payload
        assert f"d26\f{label}\v" in payload
        return httpx.Response(200, content=content)

    async def run() -> None:
        async with _client(httpx.MockTransport(handler)) as client:
            await DataFetcher(client, tmp_path, (0,)).fetch(source)

    asyncio.run(run())


def test_hira_strategy_rejects_changed_landing_page(tmp_path: Path) -> None:
    content = _zip_bytes("hospital.csv", b"hospital")
    source = replace(
        _source(content, strategy="hira_file", source_format="zip", filename="hira.zip"),
        attachment_label="missing.zip",
    )

    async def run() -> None:
        transport = httpx.MockTransport(lambda _: httpx.Response(200, text="<html></html>"))
        async with _client(transport) as client:
            await DataFetcher(client, tmp_path, (0,)).fetch(source)

    with pytest.raises(DataFetchError, match="첨부파일을 찾을 수 없습니다"):
        asyncio.run(run())


def test_population_download_posts_pinned_month(tmp_path: Path) -> None:
    content = "행정구역,2026년07월_계_총인구수\n경상북도,1".encode("cp949")
    source = replace(
        _source(
            content,
            strategy="mois_population_csv",
            source_format="csv",
            filename="population.csv",
        ),
        encoding="cp949",
        required_headers=("행정구역", "2026년07월_계_총인구수"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert b"searchYearStart=2026" in request.content
        assert b"searchMonthStart=07" in request.content
        return httpx.Response(200, content=content)

    async def run() -> None:
        async with _client(httpx.MockTransport(handler)) as client:
            await DataFetcher(client, tmp_path, (0,)).fetch(source)

    asyncio.run(run())


def test_project_manifest_is_complete() -> None:
    manifest = load_source_manifest(PROJECT_ROOT / "data/sources.toml")
    validate_referenced_pdfs(
        manifest, PROJECT_ROOT / "data/reference/pohang_branch_pattern_frequencies.csv"
    )
    assert len(manifest.sources) == 20
    assert {source.source_id for source in manifest.sources} >= {
        "hira-hospitals",
        "bus-stops",
        "pohang-routes",
        "traditional-markets",
        "commercial-businesses",
        "population-age",
        "safety-index",
    }


def test_project_manifest_matches_local_raw_files() -> None:
    manifest = load_source_manifest(PROJECT_ROOT / "data/sources.toml")
    paths = [PROJECT_ROOT / "data/raw" / source.filename for source in manifest.sources]
    if not all(path.is_file() for path in paths):
        pytest.skip("make data-fetch로 전체 원본을 받은 환경에서 실행합니다.")
    for source, path in zip(manifest.sources, paths, strict=True):
        validate_source_file(source, path)


def test_manifest_rejects_duplicate_ids(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.toml"
    entry = """
[[sources]]
id = "same"
name = "source"
landing_url = "https://example.test"
strategy = "direct"
filename = "{filename}"
sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
format = "pdf"
as_of = "2026"
license = "test"
attribution = "test"
"""
    manifest.write_text(
        "version = 1\n" + entry.format(filename="one.pdf") + entry.format(filename="two.pdf"),
        encoding="utf-8",
    )

    with pytest.raises(DataFetchError, match="중복 source ID"):
        load_source_manifest(manifest)
