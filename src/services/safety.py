"""Business logic for official regional safety grades."""

from __future__ import annotations

from clients.local_data import LocalSafetyClient
from clients.public_data import DataSourceError
from models.location import DataSourceMetadata
from models.safety import SafetyCategory, SafetyGradeResult

SAFETY_SOURCE_URL = (
    "https://www.mois.go.kr/frt/bbs/type001/commonSelectBoardArticle.do"
    "?bbsId=BBSMSTR_000000000015&nttId=123072"
)


class SafetyService:
    """Select an unambiguous safety grade from the downloaded official document."""

    def __init__(self, client: LocalSafetyClient) -> None:
        self._client = client

    async def get_safety_grade(
        self,
        region: str,
        category: SafetyCategory,
        publication_year: int | None = None,
    ) -> SafetyGradeResult:
        """Return the newest matching relative safety grade."""

        rows = await self._client.grades(region, category, publication_year)
        if not rows:
            raise DataSourceError("조건에 맞는 경상북도 지역안전지수 자료가 없습니다.")
        if publication_year is None:
            latest = max(int(row["publication_year"]) for row in rows)
            rows = [row for row in rows if int(row["publication_year"]) == latest]
        regions = {str(row["region_name"]) for row in rows}
        if len(regions) != 1:
            names = ", ".join(sorted(regions)[:5])
            raise DataSourceError(f"지역명이 여러 행정구역과 일치합니다: {names}")
        row = rows[0]
        return SafetyGradeResult(
            region_name=str(row["region_name"]),
            region_level=str(row["region_level"]),
            category=category,
            grade=int(row["grade"]),
            grade_direction="1등급이 비교 그룹 내에서 상대적으로 안전하고 5등급이 취약합니다.",
            publication_year=int(row["publication_year"]),
            statistics_year=int(row["statistics_year"]),
            comparison_group=str(row["comparison_group"]),
            source=DataSourceMetadata(
                source_name="행정안전부 2025년 지역안전지수 산출 결과 HWPX",
                source_url=SAFETY_SOURCE_URL,
                as_of=str(row["publication_year"]),
            ),
            warnings=[
                "이 등급은 같은 행정단위 비교 그룹 안의 상대평가이며 절대 범죄율이 아닙니다.",
                "주소 단위 사건 위치나 시간대별 체감 치안을 나타내지 않습니다.",
            ],
        )
