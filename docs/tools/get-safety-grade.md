# `get_safety_grade`

경상북도 또는 시군의 공식 지역안전지수 등급을 반환합니다. 기본 분야는 범죄입니다.

## 입력

| 필드 | 형식 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `region` | string | 필수 | 전체·끝 지역명, 예: `경상북도 포항시`, `포항시` |
| `category` | 안전 분야 | `crime` | `traffic_accident`, `fire`, `crime`, `life_safety`, `suicide`, `infectious_disease` |
| `publication_year` | int/null | 최신 적재연도 | 지역안전지수 공표연도 |

## 출력

| 필드 | JSON 형식 | 설명 |
| --- | --- | --- |
| `region_name` | string | 조회된 전체 행정구역명 |
| `region_level` | string | 시도·시군구 등 행정단위 |
| `category` | string | 요청한 안전 분야 열거값 |
| `grade` | integer | 지역안전지수 등급, 1~5 |
| `grade_direction` | string | 낮은 등급이 더 안전하다는 방향 설명 |
| `publication_year` | integer | 지수 공표연도 |
| `statistics_year` | integer | 산출에 사용한 안전통계 기준연도 |
| `comparison_group` | string | 상대등급을 산출한 동일 행정단위 비교 집단 |
| `source` | [`DataSourceMetadata`](../output-models.md#datasourcemetadata) | 공식 원본과 공표 기준 |
| `warnings` | list[string] | 상대등급 해석과 공간 단위에 관한 경고 |

`category`는 입력에 정의된 여섯 열거값 중 하나입니다. 이 도구는 한 지역·분야의 단일 결과
객체를 반환하며, 지역이나 자료가 없으면 빈 객체가 아니라 MCP 도구 오류를 반환합니다.

```json
{
  "region_name": "경상북도 포항시",
  "region_level": "시군구",
  "category": "crime",
  "grade": 3,
  "grade_direction": "1등급이 상대적으로 안전하고 5등급이 상대적으로 취약합니다.",
  "publication_year": 2025,
  "statistics_year": 2024,
  "comparison_group": "시",
  "source": {
    "source_name": "행정안전부 지역안전지수",
    "source_url": "https://www.mois.go.kr/",
    "as_of": "2025",
    "is_estimated": false,
    "estimation_method": null
  },
  "warnings": ["등급은 동일 행정단위 그룹 안의 상대평가이며 절대 범죄율이 아닙니다."]
}
```

## 데이터와 한계

[행정안전부 2025년 지역안전지수 산출 결과](https://www.mois.go.kr/frt/bbs/type001/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000015&nttId=123072)
HWPX를 직접 파싱합니다. 2024년 안전통계로 산출한 2025년 등급이며 1등급이 동일 행정단위
그룹 안에서 상대적으로 안전하고 5등급이 상대적으로 취약합니다. 이는 절대 범죄율, 사건별
위치, 특정 주소의 야간 안전을 뜻하지 않으므로 도구명도 `crime_rate`가 아닌
`safety_grade`를 사용합니다.
