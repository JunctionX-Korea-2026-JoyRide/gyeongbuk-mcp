"""Business logic for age-population ratios."""

from __future__ import annotations

from clients.local_data import LocalDemographicsClient
from clients.public_data import DataSourceError
from models.demographics import AgePopulationRatioResult
from models.location import DataSourceMetadata

POPULATION_SOURCE_URL = "https://jumin.mois.go.kr/ageStatMonth.do"


class DemographicsService:
    """Calculate an age-range population share from downloaded ten-year bands."""

    def __init__(self, client: LocalDemographicsClient) -> None:
        self._client = client

    async def get_age_population_ratio(
        self, region: str, age_from: int, age_to: int, as_of: str | None = None
    ) -> AgePopulationRatioResult:
        """Return an inclusive age-range population count and percentage."""

        rows = await self._client.age_bands(region, as_of)
        if not rows:
            raise DataSourceError("조건에 맞는 경상북도 연령별 인구 자료가 없습니다.")
        if as_of is None:
            latest = max(str(row["as_of"]) for row in rows)
            rows = [row for row in rows if str(row["as_of"]) == latest]
        regions = {(str(row["region_code"]), str(row["region_name"])) for row in rows}
        if len(regions) != 1:
            names = ", ".join(sorted(name for _, name in regions)[:5])
            raise DataSourceError(f"지역명이 여러 행정구역과 일치합니다: {names}")

        selected = sorted(
            (
                row
                for row in rows
                if int(row["age_from"]) >= age_from and int(row["age_to"]) <= age_to
            ),
            key=lambda row: int(row["age_from"]),
        )
        if not selected or int(selected[0]["age_from"]) != age_from:
            raise DataSourceError(
                "현재 파일은 0~9, 10~19 같은 10세 구간 단위만 계산할 수 있습니다."
            )
        expected = age_from
        for row in selected:
            if int(row["age_from"]) != expected:
                raise DataSourceError("요청 연령 범위를 연속된 10세 구간으로 구성할 수 없습니다.")
            expected = int(row["age_to"]) + 1
        if expected - 1 != age_to:
            raise DataSourceError(
                "현재 파일은 0~9, 10~19 같은 10세 구간 단위만 계산할 수 있습니다."
            )

        first = selected[0]
        age_population = sum(int(row["population"]) for row in selected)
        total_population = int(first["total_population"])
        ratio = 0.0 if total_population == 0 else age_population / total_population * 100
        return AgePopulationRatioResult(
            region_code=str(first["region_code"]),
            region_name=str(first["region_name"]),
            region_level=str(first["region_level"]),
            age_from=age_from,
            age_to=age_to,
            age_population=age_population,
            total_population=total_population,
            ratio_percent=round(ratio, 2),
            as_of=str(first["as_of"]),
            source=DataSourceMetadata(
                source_name="행정안전부 주민등록 인구통계 연령별 인구현황 CSV",
                source_url=POPULATION_SOURCE_URL,
                as_of=str(first["as_of"]),
            ),
            warnings=[
                "주민등록인구 기준이며 실제 상주인구와 다를 수 있습니다.",
                "읍면동 자료는 행정동 기준이므로 법정동과 일치하지 않을 수 있습니다.",
            ],
        )
