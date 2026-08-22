"""Download or verify the pinned public-data inputs."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from services.data_fetcher import (  # noqa: E402
    DataFetcher,
    DataFetchError,
    load_source_manifest,
    validate_referenced_pdfs,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="고정된 공공데이터 원본을 다운로드·검증합니다.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT / "data/sources.toml",
        help="source manifest 경로",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data/raw",
        help="원본 저장 디렉터리",
    )
    parser.add_argument("--source", action="append", dest="source_ids", help="처리할 source ID")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="다운로드 없이 기존 파일 검증")
    mode.add_argument("--force", action="store_true", help="검증된 기존 파일도 다시 다운로드")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> None:
    manifest = load_source_manifest(args.manifest)
    validate_referenced_pdfs(
        manifest, PROJECT_ROOT / "data/reference/pohang_branch_pattern_frequencies.csv"
    )
    sources = manifest.select(args.source_ids)
    timeout = httpx.Timeout(30.0)
    headers = {"User-Agent": "gyeongbuk-mcp-data-fetcher/0.1"}
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        fetcher = DataFetcher(client, args.output_dir)
        for source in sources:
            status = await fetcher.fetch(source, check=args.check, force=args.force)
            print(f"{source.source_id}={status} ({source.filename})")


def main() -> None:
    """Run the fetch CLI with safe, source-specific errors."""

    args = _arguments()
    try:
        asyncio.run(_run(args))
    except DataFetchError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
