"""Market-centered recommendation logic for car-free older residents."""

from __future__ import annotations

import asyncio

from clients.tago import ServiceDay
from models.accessibility import (
    NeighborhoodRecommendation,
    NeighborhoodRecommendationResult,
    TraditionalMarket,
)
from services.accessibility import AccessibilityService


class NeighborhoodRecommendationService:
    """Rank market-centered areas satisfying medical and transit thresholds."""

    def __init__(self, accessibility: AccessibilityService) -> None:
        self._accessibility = accessibility

    async def recommend(
        self,
        region: str,
        hospital_max_walk_minutes: int = 15,
        bus_max_walk_minutes: int = 10,
        minimum_daily_bus_trips: int = 5,
        service_day: ServiceDay = "weekday",
        candidate_limit: int = 20,
        result_limit: int = 5,
    ) -> NeighborhoodRecommendationResult:
        """Return ranked candidates that pass all hard accessibility constraints."""

        markets = (await self._accessibility.markets_in_region(region))[:candidate_limit]
        candidates = await asyncio.gather(
            *(
                self._evaluate_market(
                    market,
                    hospital_max_walk_minutes,
                    bus_max_walk_minutes,
                    minimum_daily_bus_trips,
                    service_day,
                )
                for market in markets
            )
        )
        recommendations = [candidate for candidate in candidates if candidate is not None]
        recommendations.sort(key=lambda candidate: (-candidate.score, candidate.candidate_name))
        recommendations = recommendations[:result_limit]
        for rank, recommendation in enumerate(recommendations, start=1):
            recommendation.rank = rank

        warnings = [
            "후보 동네는 행정동이 아니라 전통시장 대표 좌표를 중심으로 한 생활권 대리값입니다.",
            "도보시간은 직선거리 기반이며 고령자 보행환경·경사·횡단시설은 반영하지 않습니다.",
            "버스 운행 횟수는 간선의 보수적 배차 하한과 정류장별 지선 게시 횟수를 합산한 값입니다.",
            "포항 53개 노선 중 51개를 판정하며 임시노선·죽장DRT와 조건부 운행은 "
            "기본 횟수에서 제외합니다.",
        ]
        if not markets:
            warnings.append("검색 지역에서 좌표가 있는 등록 전통시장을 찾지 못했습니다.")
        elif not recommendations:
            warnings.append("모든 필수 조건을 동시에 만족하는 시장 중심 후보를 찾지 못했습니다.")

        return NeighborhoodRecommendationResult(
            region=region,
            recommendations=recommendations,
            criteria={
                "hospital_max_walk_minutes": hospital_max_walk_minutes,
                "bus_max_walk_minutes": bus_max_walk_minutes,
                "minimum_daily_bus_trips": minimum_daily_bus_trips,
                "service_day": service_day,
                "market_requirement": "registered_market_anchor",
                "candidate_limit": candidate_limit,
            },
            warnings=warnings,
        )

    async def _evaluate_market(
        self,
        market: TraditionalMarket,
        hospital_max_walk_minutes: int,
        bus_max_walk_minutes: int,
        minimum_daily_bus_trips: int,
        service_day: ServiceDay,
    ) -> NeighborhoodRecommendation | None:
        origin = market.coordinates
        hospitals_result, bus_result = await asyncio.gather(
            self._accessibility.search_hospitals(origin, hospital_max_walk_minutes),
            self._accessibility.search_bus_stops(
                origin,
                bus_max_walk_minutes,
                minimum_daily_bus_trips,
                service_day,
            ),
        )
        if not hospitals_result.hospitals or not bus_result.stops:
            return None

        hospital = hospitals_result.hospitals[0]
        stops = bus_result.stops[:3]
        best_bus_trips = max(stop.estimated_daily_trips or 0 for stop in stops)
        hospital_score = 40 * max(
            0.0,
            1 - hospital.estimated_walk_minutes / max(hospital_max_walk_minutes, 1),
        )
        bus_distance_score = 20 * max(
            0.0,
            1 - stops[0].estimated_walk_minutes / max(bus_max_walk_minutes, 1),
        )
        bus_frequency_score = 15 * min(best_bus_trips / max(minimum_daily_bus_trips, 1), 3) / 3
        score = round(25 + hospital_score + bus_distance_score + bus_frequency_score, 1)
        return NeighborhoodRecommendation(
            rank=1,
            candidate_name=f"{market.name} 생활권",
            anchor=market.coordinates,
            score=score,
            nearest_market=market,
            nearest_hospital=hospital,
            qualifying_bus_stops=stops,
            reasons=[
                f"가장 가까운 병원이 보행 추정 {hospital.estimated_walk_minutes}분입니다.",
                f"조건을 만족하는 정류장이 {len(bus_result.stops)}곳입니다.",
                f"가장 운행이 많은 인근 정류장은 하루 약 {best_bus_trips}회입니다.",
                "등록 전통시장을 생활권 중심점으로 사용했습니다.",
            ],
            caveats=[
                "추천 전 현장 보행로, 경사, 조명, 횡단보도 확인이 필요합니다.",
                "병원 진료과목과 버스 실제 시간표는 최종 선택 전에 재확인해야 합니다.",
            ],
        )
