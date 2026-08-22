# `search_nearby_bus_stops`

기준 좌표 근처의 버스정류장을 찾고, 경유 노선별 운행 횟수를 추정해 최소 운행 횟수
조건을 만족하는 정류장만 반환합니다.

## 입력

| 필드 | 형식 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `latitude` | float | 필수 | WGS84 위도 |
| `longitude` | float | 필수 | WGS84 경도 |
| `max_walk_minutes` | int, 1~120 | 10 | 정류장까지 최대 보행 추정시간 |
| `minimum_daily_trips` | int, 1~1000 | 5 | 정류장 전체 최소 일 운행 횟수 |
| `service_day` | `weekday`, `saturday`, `sunday` | `weekday` | 적용할 요일 유형 |

## 출력

| 필드 | JSON 형식 | 설명 |
| --- | --- | --- |
| `stops` | array of [`BusStopAccessibility`](../output-models.md#busstopaccessibility) | 조건을 만족하는 정류장. 거리 오름차순, 같은 거리면 일 운행 횟수 내림차순 |
| `service_day` | string | 적용한 `weekday`, `saturday`, `sunday` 중 하나 |
| `minimum_daily_trips` | integer | 적용한 정류장 최소 일 운행 횟수 |
| `source` | [`DataSourceMetadata`](../output-models.md#datasourcemetadata) | 정류장·노선·시간표 출처와 추정 방법 |
| `warnings` | list[string] | 배차 추정 및 데이터 한계에 관한 경고 |

시간표가 없는 정류장은 최소 횟수 조건을 판정할 수 없어 결과에서 제외합니다. 조건을 만족하는
정류장이 없으면 `stops`는 `[]`입니다. 노선의 `frequency_basis`는 다음 중 하나입니다.

- `published_trip_count`: 게시 시간표에서 검수한 명시 운행횟수
- `conservative_interval_estimate`: 첫차·막차와 최대 배차간격으로 계산한 보수적 하한
- `api_summary`: `DATA_MODE=api`에서 TAGO 요약값을 사용한 결과

다음은 형식을 보여주기 위한 예시이며 실제 값은 원본 갱신에 따라 달라집니다.

```json
{
  "stops": [
    {
      "stop_id": "example-stop-001",
      "name": "죽도시장",
      "coordinates": {"latitude": 36.034, "longitude": 129.365},
      "distance_m": 180.2,
      "estimated_walk_minutes": 4,
      "estimated_daily_trips": 12,
      "routes": [
        {
          "route_id": "example-route-001",
          "route_number": "206",
          "route_type": "간선",
          "daily_trips": 12,
          "first_bus": "06:00",
          "last_bus": "22:00",
          "interval_minutes": 90,
          "frequency_basis": "conservative_interval_estimate"
        }
      ]
    }
  ],
  "service_day": "weekday",
  "minimum_daily_trips": 5,
  "source": {
    "source_name": "전국 버스정류장 및 포항시 노선·시간표",
    "source_url": "https://www.pohang.go.kr/",
    "as_of": "2026-08-01",
    "is_estimated": true,
    "estimation_method": "게시 운행횟수 또는 첫차·막차·최대 배차간격의 보수적 하한"
  },
  "warnings": ["운행 횟수는 게시 시간표를 바탕으로 한 추정값입니다."]
}
```

## 데이터와 계산

- 정류장 좌표: 국토교통부 전국 버스정류장 위치정보 CSV
- 경유 노선: 포항시 시내버스 노선정보 CSV의 `노선명`–`승강장명칭`; 정규화된 정류장명으로
  전국 정류장 파일과 연결
- 간선 배차: 공식 첫차·막차·최대 배차간격으로
  `floor((막차 분 - 첫차 분) / 최대 배차간격) + 1` 계산
- 공식 페이지가 `1일 N회`를 직접 밝힌 노선은 명시값을 우선합니다.
- 지선 배차: 원본 노선 CSV의 정확한 `(노선명, 노선상세)` 패턴과 검수된 PDF 횟수를 연결
- 자정을 넘는 노선은 막차에 24시간을 더해 계산합니다.
- 지선 정류장은 실제로 포함하는 패턴만 합산합니다. 한 패턴에서 같은 정류장이 반복돼도
  운행 한 회당 한 번만 계산하고, 서로 다른 패턴이 겹치면 각각 합산합니다.

## 한계

- 간선은 배차간격 범위 중 최대값을 하루 내내 적용하므로 실제보다 낮은 보수적 추정치입니다.
- 포항 53개 노선 중 51개를 판정합니다. 안정적인 시간표가 없는 `임시노선`과 호출 기반
  `죽장DRT`만 횟수 미상으로 제외합니다.
- `장날`, `CALL`, 임시·요청 운행은 기본 일 횟수에서 제외하며 `경유` 표시는 별도 운행으로
  중복 계수하지 않습니다.
- 한 PDF에 혼재한 경로 중 원본 노선 CSV와 확실히 연결되는 검수 패턴만 사용합니다.
- 결행, 방학·공휴일 시간표와 실제 임시 변경을 반영하지 못할 수 있습니다.
- 포항시 게시 페이지가 요일별 값을 구분하지 않아 파일 모드의 `weekday`, `saturday`,
  `sunday`에는 검수 CSV에 동일한 값을 명시합니다.
- 한 번에 가까운 정류장 최대 20곳만 상세 결과로 만듭니다.
