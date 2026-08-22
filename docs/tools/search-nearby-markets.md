# `search_nearby_markets`

지역명으로 등록 전통시장을 조회한 뒤, 기준 좌표에서 보행 추정시간 안의 시장을 반환합니다.

## 입력

| 필드 | 형식 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `region` | string | 필수 | 도로명주소에 포함될 지역명, 예: `포항시` |
| `latitude` | float | 필수 | WGS84 위도 |
| `longitude` | float | 필수 | WGS84 경도 |
| `max_walk_minutes` | int, 1~120 | 15 | 시장까지 최대 보행 추정시간 |

## 출력

| 필드 | JSON 형식 | 설명 |
| --- | --- | --- |
| `markets` | array of [`TraditionalMarket`](../output-models.md#traditionalmarket) | 조건을 만족하는 시장. `distance_m` 오름차순 |
| `source` | [`DataSourceMetadata`](../output-models.md#datasourcemetadata) | 원본과 기준일 |
| `warnings` | list[string] | 대표 좌표와 등록시장 범위에 관한 경고 |

조건을 만족하는 시장이 없으면 `markets`는 `[]`입니다. 다음은 형식을 보여주기 위한 예시이며
실제 값은 원본 갱신에 따라 달라집니다.

```json
{
  "markets": [
    {
      "name": "예시시장",
      "address": "경상북도 포항시 북구 예시로 10",
      "market_type": "상설시장",
      "opening_cycle": "매일",
      "coordinates": {"latitude": 36.035, "longitude": 129.366},
      "distance_m": 250.7,
      "estimated_walk_minutes": 5,
      "reference_date": "2025-11-10"
    }
  ],
  "source": {
    "source_name": "전국전통시장표준데이터",
    "source_url": "https://www.data.go.kr/",
    "as_of": "2025-11-10",
    "is_estimated": true,
    "estimation_method": "Haversine 직선거리와 분당 보행속도"
  },
  "warnings": ["시장은 면적이 아닌 하나의 대표 좌표로 계산합니다."]
}
```

## 데이터와 계산

- 출처: 공공데이터포털 전국전통시장표준데이터
- 적재: 다운로드 CSV에서 경상북도 주소와 유효 좌표를 가진 시장을 SQLite에 저장
- 지역 검색: 도로명·지번주소를 SQLite 부분 일치
- 거리: 시장 대표 좌표와 기준 좌표의 Haversine 직선거리

## 한계

- 지자체가 인정한 전통시장만 포함하므로 동네 슈퍼, 마트, 비등록 상점가는 포함하지 않습니다.
- 시장은 면적을 가진 시설이지만 하나의 대표 좌표만 사용합니다.
- 도로명·지번주소가 모두 누락되거나 지역 표기가 다른 레코드는 제외될 수 있습니다.
