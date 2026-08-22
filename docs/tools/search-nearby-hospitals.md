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

`hospitals`에 기관 ID, 상호명, 주소, 전화번호, 종별, 진료과목, 좌표, 직선거리,
보행 추정시간을 반환합니다. `source`에는 원본 파일, 기준월과 추정 방법을 담습니다.

파일 모드에서는 `include_departments=true`도 같은 SQLite에서 조회하므로 추가 외부 호출이
없습니다.

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
