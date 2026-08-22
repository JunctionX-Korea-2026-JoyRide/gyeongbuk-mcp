# `search_nearby_hospitals`

기준 좌표에서 지정한 보행 추정시간 안의 병원을 가까운 순으로 반환합니다.

## 입력

| 필드 | 형식 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `latitude` | float | 필수 | WGS84 위도 |
| `longitude` | float | 필수 | WGS84 경도 |
| `max_walk_minutes` | int, 1~120 | 15 | 최대 보행 추정시간 |
| `department_code` | string/null | null | 심평원 진료과목 코드 필터 |
| `include_departments` | boolean | false | 기관별 진료과목 상세조회 여부 |

## 출력

| 필드 | JSON 형식 | 설명 |
| --- | --- | --- |
| `hospitals` | array of [`Hospital`](../output-models.md#hospital) | 조건을 만족하는 병원. `distance_m` 오름차순 |
| `max_walk_minutes` | integer | 요청에 적용한 최대 보행 추정시간(분) |
| `walking_speed_m_per_minute` | number | 계산에 적용한 분당 보행속도(m) |
| `source` | [`DataSourceMetadata`](../output-models.md#datasourcemetadata) | 원본, 기준월과 추정 방법 |
| `warnings` | list[string] | 결과 해석 및 데이터 한계에 관한 경고 |

조건을 만족하는 병원이 없으면 `hospitals`는 `[]`입니다. 파일 모드에서는
`include_departments=true`도 같은 SQLite에서 조회하므로 추가 외부 호출이 없습니다.

다음은 형식을 보여주기 위한 예시이며 실제 값은 원본 갱신에 따라 달라집니다.

```json
{
  "hospitals": [
    {
      "institution_id": "example-hospital-001",
      "name": "예시병원",
      "address": "경상북도 포항시 북구 예시로 1",
      "phone": "054-000-0000",
      "institution_type": "병원",
      "departments": ["내과"],
      "coordinates": {"latitude": 36.019, "longitude": 129.343},
      "distance_m": 420.5,
      "estimated_walk_minutes": 8
    }
  ],
  "max_walk_minutes": 15,
  "walking_speed_m_per_minute": 60.0,
  "source": {
    "source_name": "건강보험심사평가원 전국 병의원 및 약국 현황",
    "source_url": "https://opendata.hira.or.kr/",
    "as_of": "2026-06",
    "is_estimated": true,
    "estimation_method": "Haversine 직선거리와 분당 보행속도"
  },
  "warnings": ["보행시간은 실제 경로가 아닌 직선거리 추정값입니다."]
}
```

## 데이터와 계산

- 병원 목록: HIRA 전국 병의원 및 약국 현황 ZIP의 `1.병원정보서비스` XLSX
- 진료과목: 같은 ZIP의 `5.의료기관별상세정보서비스_03_진료과목정보` XLSX
- 적재 범위: 시도코드명이 `경북`이고 유효 좌표가 있는 기관
- 검색 반경: `max_walk_minutes × WALKING_SPEED_M_PER_MINUTE`
- 최종 필터: Haversine 직선거리로 반경 밖 응답 제거

## 한계

- 반환되는 진료과목은 신고 정보이며 당일 진료 가능 여부가 아닙니다.
- 운영시간, 예약 가능 여부, 응급실 운영 여부는 현재 평가하지 않습니다.
- “15분 이내”는 실제 길찾기 시간이 아니라 직선거리 환산값입니다.
