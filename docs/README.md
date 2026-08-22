# 도구 문서

이 서버는 포항·경상북도 생활권을 공공데이터로 비교할 수 있도록 다음 MCP 도구를 제공합니다.

| 도구 | 용도 | 상태 |
| --- | --- | --- |
| [`search_nearby_hospitals`](tools/search-nearby-hospitals.md) | 기준점 주변 병원과 선택적 진료과목 조회 | 구현 |
| [`search_nearby_bus_stops`](tools/search-nearby-bus-stops.md) | 기준점 주변 정류장과 일 운행 횟수 추정 | 구현 |
| [`search_nearby_markets`](tools/search-nearby-markets.md) | 기준점 주변 등록 전통시장 조회 | 구현 |
| [`recommend_car_free_neighborhoods`](tools/recommend-car-free-neighborhoods.md) | 시장 중심 생활권 후보 종합 추천 | 구현 |
| [`get_age_population_ratio`](tools/get-age-population-ratio.md) | 행정구역별 연령대 인구 비율 | 구현 |
| [`get_safety_grade`](tools/get-safety-grade.md) | 시도·시군별 분야별 지역안전등급 | 구현 |

각 도구의 최상위 출력은 해당 도구 문서에, 재사용되는 중첩 객체의 필드·형식은
[출력 모델 계약](output-models.md)에 정리했습니다. 전체 데이터 출처와 선택 이유는
[데이터 출처](data-sources.md), 구현 순서와 완료 조건은 [구현 계획](implementation-plan.md)을
참고합니다.

## 공통 계산 규칙

- 좌표는 WGS84 위도·경도를 사용합니다.
- 보행시간은 `ceil(직선거리 / 분당 60m)`입니다. 속도는
  `WALKING_SPEED_M_PER_MINUTE`로 바꿀 수 있습니다.
- 직선거리 기반 시간은 실제 도보 경로가 아닙니다. 경사, 횡단보도, 보행로 단절, 건물
  출입구를 반영하지 않습니다.
- 모든 데이터 결과는 원본 출처, 기준일, 추정 여부, 추정 방법과 경고를 함께 반환합니다.

## 실행 준비

고정된 공식 원본을 내려받아 검증하고 로컬 DB를 생성합니다.

```bash
cp .env.example .env
make data-setup
```

```dotenv
DATA_MODE=file
LOCAL_DATABASE_PATH=data/processed/gyeongbuk.sqlite3
WALKING_SPEED_M_PER_MINUTE=60
```

그다음 서버를 실행합니다.

```bash
make run
```

서버 실행 중인 파일 모드에서는 인증키와 네트워크가 필요하지 않습니다. `DATA_MODE=api`로
바꾼 경우 병원·버스정류장·시장 조회에만 `DATA_GO_KR_SERVICE_KEY`가 필요하며 인구·안전
도구는 계속 로컬 DB를 사용합니다. `.env`는 Git에서 제외됩니다.
