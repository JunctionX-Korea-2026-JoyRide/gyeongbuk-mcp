# `recommend_car_free_neighborhoods`

전통시장을 생활권 중심점으로 삼아 병원과 버스 조건을 모두 만족하는 후보를 점수화합니다.
다음 질의의 1차 답변을 만들기 위한 종합 도구입니다.

> 차 없는 70대가 살기 좋은 포항 근처 동네 찾아줘. 병원은 15분 이내, 버스는 하루
> 5회 이상, 시장도 가까웠으면 좋겠어.

## 입력

| 필드 | 형식 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `region` | string | `포항시` | 시장 주소 검색 지역 |
| `hospital_max_walk_minutes` | int, 1~120 | 15 | 병원까지 최대 보행 추정시간 |
| `bus_max_walk_minutes` | int, 1~120 | 10 | 정류장까지 최대 보행 추정시간 |
| `minimum_daily_bus_trips` | int, 1~1000 | 5 | 정류장 최소 일 운행 추정 횟수 |
| `service_day` | 요일 유형 | `weekday` | 평일·토요일·일요일 중 하나 |
| `candidate_limit` | int, 1~50 | 20 | 평가할 시장 수 |
| `result_limit` | int, 1~10 | 5 | 반환할 후보 수 |

## 후보 생성과 필수 조건

1. `region` 안의 등록 전통시장 대표 좌표를 후보 중심점으로 만듭니다.
2. 각 중심점에서 병원과 버스정류장을 병렬 조회합니다.
3. 병원이 제한시간 안에 하나 이상 있어야 합니다.
4. 제한시간 안에 `minimum_daily_bus_trips` 이상인 정류장이 하나 이상 있어야 합니다.
5. 두 조건을 모두 통과한 후보만 점수화합니다.

이 방식의 후보명은 `죽도시장 생활권`처럼 표시됩니다. 행정동이나 주거 매물 단지를 직접
추천한다는 뜻은 아닙니다.

## 점수(100점)

| 항목 | 배점 | 계산 |
| --- | ---: | --- |
| 시장 | 25 | 등록시장 중심점이면 고정 |
| 병원 거리 | 40 | 가까울수록 증가 |
| 정류장 거리 | 20 | 가까울수록 증가 |
| 버스 운행량 | 15 | 최소 조건의 3배까지 선형 증가 |

필수 조건은 점수와 별개입니다. 점수가 높아도 현장 검증을 대체하지 않습니다.

## 출력

| 필드 | JSON 형식 | 설명 |
| --- | --- | --- |
| `region` | string | 평가에 사용한 지역 검색어 |
| `recommendations` | array of [`NeighborhoodRecommendation`](../output-models.md#neighborhoodrecommendation) | 점수 내림차순, 동점이면 후보명 오름차순인 추천 결과 |
| `criteria` | object | 실제 적용한 후보 평가 조건 |
| `warnings` | list[string] | 모든 후보에 공통인 데이터·해석 경고 |

`criteria`에는 `hospital_max_walk_minutes`, `bus_max_walk_minutes`,
`minimum_daily_bus_trips`, `service_day`, `market_requirement`, `candidate_limit`가
포함됩니다. 필수 조건을 모두 만족한 후보가 없으면 `recommendations`는 `[]`입니다.

```json
{
  "region": "포항시",
  "recommendations": [],
  "criteria": {
    "hospital_max_walk_minutes": 15,
    "bus_max_walk_minutes": 10,
    "minimum_daily_bus_trips": 5,
    "service_day": "weekday",
    "market_requirement": "registered_market_anchor",
    "candidate_limit": 20
  },
  "warnings": [
    "추천 결과가 없어도 입력 지역의 주거 부적합을 뜻하지 않습니다.",
    "보행시간은 실제 경로가 아닌 직선거리 추정값입니다."
  ]
}
```

각 추천 객체에는 순위, 점수, 중심 좌표, 가장 가까운 시장·병원, 조건을 통과한 정류장 최대
3곳, 추천 이유와 주의사항이 포함됩니다. 후속 답변에서는 먼저 후보를 제시하고 다음을
명시해야 합니다.

- 보행시간은 직선거리 추정값이며 버스 횟수는 간선의 보수적 하한 또는 지선의 게시 횟수라는 점
- 병원 진료과목·운영시간과 버스 실제 시간표를 재확인해야 한다는 점
- 경사, 보도, 횡단보도, 야간조명 같은 고령자 보행 안전은 현장 확인이 필요하다는 점

## 현재 제외된 요소

연령대 인구 비율과 범죄 분야 지역안전등급은 아직 점수에 들어가지 않습니다. 데이터
공간 단위가 각각 행정구역이고 시장 좌표와 바로 결합할 수 없기 때문에, 행정동·시군구
매핑을 추가한 다음 보조 지표로 결합할 계획입니다.

## 파일 모드 동작

추천 요청 중에는 외부 API를 호출하지 않습니다. 병원, 시장, 정류장–노선·패턴, 배차 자료를 모두
`data/processed/gyeongbuk.sqlite3`에서 읽습니다. 원본 갱신은 서버를 멈추지 않고 `make data`로
새 임시 DB를 완성한 뒤 원자적으로 교체할 수 있습니다.

버스 판정 범위는 포항 53개 노선 중 51개입니다. 지선은 후보 정류장을 실제 포함하는 검수
패턴의 횟수만 합산하며, `임시노선`과 `죽장DRT`, 장날·CALL·요청 운행은 기본 조건 판정에서
제외합니다.
