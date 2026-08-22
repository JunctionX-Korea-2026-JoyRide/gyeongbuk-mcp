# 출력 모델 계약

각 도구 문서의 최상위 응답과 함께 사용하는 공통·중첩 JSON 모델입니다. 표에 적힌 필드명과
형식은 공개 계약이며, 별도 표기가 없는 필드는 항상 응답에 포함됩니다.

## 공통 직렬화 규칙

- `list[T]` 필드는 결과가 없으면 `null`이 아니라 빈 배열 `[]`입니다.
- `T | null`로 표시한 필드만 JSON `null`이 될 수 있습니다.
- 거리의 단위는 미터이며 소수 첫째 자리까지, 비율은 퍼센트이며 소수 둘째 자리까지
  반올림합니다.
- `estimated_walk_minutes`는 직선거리를 설정된 분당 보행속도로 나눈 뒤 올림한 정수입니다.
- 조회 결과가 없으면 정상 응답 객체와 빈 결과 배열, 필요할 경우 `warnings`를 반환합니다.
- 입력 검증 실패, 데이터 소스 장애, 모호한 지역명은 정상 응답 객체가 아니라 MCP 도구
  오류로 전달됩니다. 내부 예외나 비밀정보는 노출하지 않습니다.

## `Coordinates`

| 필드 | JSON 형식 | 제약·의미 |
| --- | --- | --- |
| `latitude` | number | WGS84 위도, 33.0~39.5 |
| `longitude` | number | WGS84 경도, 124.0~132.0 |

## `DataSourceMetadata`

| 필드 | JSON 형식 | 제약·의미 |
| --- | --- | --- |
| `source_name` | string | 원본 데이터 또는 제공기관 이름 |
| `source_url` | string | 공식 랜딩 페이지 또는 원본 안내 URL |
| `as_of` | string \| null | 원본 기준월·기준일·공표연도. 소스에 따라 형식이 다름 |
| `is_estimated` | boolean | 응답에 추정 계산이 포함됐는지 여부 |
| `estimation_method` | string \| null | 추정 방법. 추정하지 않았거나 설명이 없으면 `null` |

## `Hospital`

| 필드 | JSON 형식 | 제약·의미 |
| --- | --- | --- |
| `institution_id` | string | 심평원 기관 식별자 |
| `name` | string | 기관명 |
| `address` | string | 주소 |
| `phone` | string \| null | 대표 전화번호 |
| `institution_type` | string \| null | 병원·의원 등 기관 종별 |
| `departments` | list[string] | 진료과목명. 조회하지 않았거나 없으면 `[]` |
| `coordinates` | [`Coordinates`](#coordinates) | 기관 대표 좌표 |
| `distance_m` | number | 기준점과의 직선거리(m), 0 이상 |
| `estimated_walk_minutes` | integer | 보행 추정시간(분), 0 이상 |

## `BusRouteFrequency`

| 필드 | JSON 형식 | 제약·의미 |
| --- | --- | --- |
| `route_id` | string | 노선 식별자 |
| `route_number` | string | 표시 노선번호 |
| `route_type` | string \| null | 간선·지선 등 노선 유형 |
| `daily_trips` | integer \| null | 해당 요일의 추정 일 운행 횟수, 0 이상 |
| `first_bus` | string \| null | 첫차 시각. 제공될 때 `HH:MM` 형식 |
| `last_bus` | string \| null | 막차 시각. 제공될 때 `HH:MM` 형식 |
| `interval_minutes` | integer \| null | 배차간격(분), 제공될 때 1 이상 |
| `frequency_basis` | string \| null | `published_trip_count`, `conservative_interval_estimate`, `api_summary` 중 하나 또는 `null` |

## `BusStopAccessibility`

| 필드 | JSON 형식 | 제약·의미 |
| --- | --- | --- |
| `stop_id` | string | 정류장 식별자 |
| `name` | string | 정류장명 |
| `coordinates` | [`Coordinates`](#coordinates) | 정류장 좌표 |
| `distance_m` | number | 기준점과의 직선거리(m), 0 이상 |
| `estimated_walk_minutes` | integer | 보행 추정시간(분), 0 이상 |
| `estimated_daily_trips` | integer \| null | 정류장을 지나는 판정 가능 노선의 일 운행 횟수 합계 |
| `routes` | array of [`BusRouteFrequency`](#busroutefrequency) | 경유 노선별 운행 정보 |

## `TraditionalMarket`

| 필드 | JSON 형식 | 제약·의미 |
| --- | --- | --- |
| `name` | string | 시장명 |
| `address` | string | 도로명주소 또는 지번주소 |
| `market_type` | string \| null | 상설시장·정기시장 등 시장 유형 |
| `opening_cycle` | string \| null | 개설주기 |
| `coordinates` | [`Coordinates`](#coordinates) | 시장 대표 좌표 |
| `distance_m` | number | 기준점과의 직선거리(m), 0 이상 |
| `estimated_walk_minutes` | integer | 보행 추정시간(분), 0 이상 |
| `reference_date` | string \| null | 원본 데이터 기준일. 제공될 때 `YYYY-MM-DD` 형식 |

## `NeighborhoodRecommendation`

| 필드 | JSON 형식 | 제약·의미 |
| --- | --- | --- |
| `rank` | integer | 응답 내 순위, 1 이상 |
| `candidate_name` | string | 시장 이름에서 만든 생활권 후보명 |
| `anchor` | [`Coordinates`](#coordinates) | 후보 평가 기준 좌표 |
| `score` | number | 종합점수, 0~100 |
| `nearest_market` | [`TraditionalMarket`](#traditionalmarket) | 기준점인 등록 전통시장 |
| `nearest_hospital` | [`Hospital`](#hospital) | 조건을 만족하는 가장 가까운 병원 |
| `qualifying_bus_stops` | array of [`BusStopAccessibility`](#busstopaccessibility) | 조건을 만족하는 가까운 정류장, 최대 3개 |
| `reasons` | list[string] | 점수와 필수 조건에 근거한 추천 이유 |
| `caveats` | list[string] | 직선거리·시간표·현장 확인 등에 관한 주의사항 |
