# `get_safety_grade`

경상북도 또는 시군의 공식 지역안전지수 등급을 반환합니다. 기본 분야는 범죄입니다.

## 입력

| 필드 | 형식 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `region` | string | 필수 | 전체·끝 지역명, 예: `경상북도 포항시`, `포항시` |
| `category` | 안전 분야 | `crime` | `traffic_accident`, `fire`, `crime`, `life_safety`, `suicide`, `infectious_disease` |
| `publication_year` | int/null | 최신 적재연도 | 지역안전지수 공표연도 |

## 출력

- 행정구역 명칭과 행정단위
- 분야와 1~5등급
- 공표연도, 실제 통계 기준연도, 비교 집단
- 등급 방향과 공식 출처, 해석 경고

## 데이터와 한계

[행정안전부 2025년 지역안전지수 산출 결과](https://www.mois.go.kr/frt/bbs/type001/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000015&nttId=123072)
HWPX를 직접 파싱합니다. 2024년 안전통계로 산출한 2025년 등급이며 1등급이 동일 행정단위
그룹 안에서 상대적으로 안전하고 5등급이 상대적으로 취약합니다. 이는 절대 범죄율, 사건별
위치, 특정 주소의 야간 안전을 뜻하지 않으므로 도구명도 `crime_rate`가 아닌
`safety_grade`를 사용합니다.
