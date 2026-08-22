# `search_nearby_stores`

기준 좌표에서 최대 2km 안의 영업 중 상가업소를 업종·상호 조건으로 검색합니다.

## 입력

| 필드 | 형식 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `latitude` | float | 필수 | WGS84 위도, 33.0~39.5 |
| `longitude` | float | 필수 | WGS84 경도, 124.0~132.0 |
| `radius_m` | int, 1~2000 | 1000 | 직선거리 검색 반경(m) |
| `industry_code` | string/null | null | 2·4·6자리 대/중/소분류 코드 |
| `industry_name` | string/null | null | 3단계 업종명 중 정규화된 부분 일치 |
| `name_query` | string/null | null | 상호명·지점명의 정규화된 부분 일치 |
| `result_limit` | int, 1~100 | 20 | 반환할 최대 업소 수 |

필터를 둘 이상 지정하면 모두 만족하는 업소만 반환합니다. 명칭 검색은 유니코드 NFKC로
정규화하고 공백·문장부호와 영문 대소문자를 무시합니다.

## 출력

| 필드 | JSON 형식 | 설명 |
| --- | --- | --- |
| `stores` | array of [`Store`](../output-models.md#store) | 거리·상호·업소번호 순 결과 |
| `radius_m` | integer | 적용한 검색 반경(m) |
| `walking_speed_m_per_minute` | number | 도보시간 환산 속도 |
| `source` | [`DataSourceMetadata`](../output-models.md#datasourcemetadata) | 출처, 기준일과 추정 방법 |
| `warnings` | list[string] | 결과 해석과 데이터 한계 |

조건을 만족하는 업소가 없으면 `stores`는 `[]`입니다.

```json
{
  "stores": [
    {
      "business_id": "MA0106202201A0000000",
      "name": "예시커피",
      "branch_name": "포항점",
      "industry_large_code": "I2",
      "industry_large_name": "음식",
      "industry_medium_code": "I212",
      "industry_medium_name": "비알코올",
      "industry_small_code": "I21201",
      "industry_small_name": "카페",
      "standard_industry_code": "I56221",
      "standard_industry_name": "커피 전문점",
      "address": "경상북도 포항시 북구 예시로 1",
      "coordinates": {"latitude": 36.036, "longitude": 129.365},
      "distance_m": 124.5,
      "estimated_walk_minutes": 3
    }
  ],
  "radius_m": 1000,
  "walking_speed_m_per_minute": 60.0,
  "source": {
    "source_name": "소상공인시장진흥공단 상가(상권)정보",
    "source_url": "https://www.data.go.kr/data/15083033/fileData.do",
    "as_of": "2026-06-30",
    "is_estimated": true,
    "estimation_method": "업소 좌표와 기준점의 직선거리를 분당 60m 보행속도로 환산"
  },
  "warnings": ["영업 상태는 원본 기준이며 실시간 영업 여부를 보장하지 않습니다."]
}
```

## 데이터와 계산

- 파일 모드: 2026-06-30 전국 ZIP의 경북 CSV 144,967곳을 SQLite에 적재
- API 모드: 소상공인시장진흥공단 `storeListInRadius`를 전체 페이지 조회
- 업종 코드: 길이에 따라 대분류(2), 중분류(4), 소분류(6)에 정확히 일치
- 거리: bounding box 후보에서 Haversine 직선거리로 최종 반경 판정
- 정렬: 거리 오름차순, 같으면 상호명과 상가업소번호 오름차순

## 한계

- 원본의 “영업 중” 상태는 실시간 확인 결과가 아닙니다.
- 영업시간과 전화번호는 원본에 없어 반환하지 않습니다.
- 상가업소번호는 원본 분류 개편 시 바뀔 수 있습니다.
- 도보시간은 실제 보행로가 아닌 직선거리 환산값입니다.
