# `get_age_population_ratio`

경상북도 행정구역의 주민등록인구에서 요청한 나이대의 인구수와 전체 인구 대비 비율을
반환합니다. 기본값은 70~79세입니다.

## 입력

| 필드 | 형식 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `region` | string | 필수 | 행정구역 코드 또는 전체·끝 지역명, 예: `4711054500`, `죽도동` |
| `age_from` | int, 0~130 | `70` | 포함할 최소 만 나이 |
| `age_to` | int, 0~130 | `79` | 포함할 최대 만 나이 |
| `as_of` | `YYYYMM`/null | 최신 적재월 | 기준년월 |

현재 원본이 10세 구간이므로 `70~79`, `60~79`처럼 완전한 구간 조합만 계산합니다.
`65~79`처럼 구간을 자르는 요청은 명시적 오류로 처리합니다.

## 출력

| 필드 | JSON 형식 | 설명 |
| --- | --- | --- |
| `region_code` | string | 조회된 행정구역 코드 |
| `region_name` | string | 조회된 전체 행정구역명 |
| `region_level` | string | 시도·시군구·읍면동 등 행정단위 |
| `age_from` | integer | 계산에 포함한 최소 만 나이 |
| `age_to` | integer | 계산에 포함한 최대 만 나이 |
| `age_population` | integer | 해당 연령대 주민등록인구, 0 이상 |
| `total_population` | integer | 해당 행정구역 전체 주민등록인구, 0 이상 |
| `ratio_percent` | number | 전체 인구 대비 비율(%), 0~100 |
| `as_of` | string | 기준년월, `YYYYMM` 형식 |
| `source` | [`DataSourceMetadata`](../output-models.md#datasourcemetadata) | 공식 원본과 기준월 |
| `warnings` | list[string] | 주민등록인구·행정동 기준에 관한 경고 |

이 도구는 한 행정구역의 단일 결과 객체를 반환합니다. 지역이 없거나 둘 이상으로 해석되면
빈 객체가 아니라 MCP 도구 오류를 반환합니다. 다음은 형식을 보여주기 위한 예시입니다.

```json
{
  "region_code": "4711054500",
  "region_name": "경상북도 포항시 북구 죽도동",
  "region_level": "읍면동",
  "age_from": 70,
  "age_to": 79,
  "age_population": 1234,
  "total_population": 20123,
  "ratio_percent": 6.13,
  "as_of": "202607",
  "source": {
    "source_name": "행정안전부 주민등록 인구통계",
    "source_url": "https://jumin.mois.go.kr/ageStatMonth.do",
    "as_of": "202607",
    "is_estimated": false,
    "estimation_method": null
  },
  "warnings": ["주민등록인구는 실제 상주인구와 다를 수 있습니다."]
}
```

## 데이터와 한계

[행정안전부 주민등록 인구통계](https://jumin.mois.go.kr/ageStatMonth.do)의 전체 읍면동
연령별 인구현황 CSV를 적재합니다. 현재 파일은 2026년 7월, 10세 구간이며 경상북도
시도·시군구·읍면동 행만 SQLite에 보관합니다. 주민등록인구는 실제 상주인구와 다를 수 있고
행정동은 법정동과 일치하지 않을 수 있습니다. 고령인구 비율은 수요를 설명하는 보조 지표이지
거주 적합성 자체를 증명하지 않습니다.
