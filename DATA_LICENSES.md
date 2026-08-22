# 데이터 이용조건과 출처표시

프로젝트의 MIT 라이선스는 소스 코드에만 적용됩니다. `data/raw/`의 원본, 원본에서 생성한
SQLite, `data/reference/`의 검수 CSV에는 각 제공기관의 이용조건이 적용됩니다. 이 저장소와
GitHub Release는 원본 및 생성 SQLite를 재배포하지 않습니다.

| 데이터 | 제공기관 | 기준 | 이용조건 | 이 프로젝트의 이용 방식 |
| --- | --- | --- | --- | --- |
| 전국 병의원 및 약국 현황 | 건강보험심사평가원 | 2026.6 | [공공누리 제1유형(출처표시)](https://opendata.hira.or.kr/op/opc/selectOpenData.do?sno=11925) | 경북 기관과 진료과목을 추출하며 출처와 기준일을 결과에 표시 |
| 전국 버스정류장 위치정보 | 국토교통부 | 2025-10-31 | [이용허락범위 제한 없음](https://www.data.go.kr/data/15067528/fileData.do) | 경북 정류장만 추출 |
| 포항시 시내버스 노선정보 | 경상북도 포항시 | 2026-05-12 | [이용허락범위 제한 없음](https://www.data.go.kr/data/3034960/fileData.do) | 포항 노선과 정류장 순서를 구조화 |
| 전국전통시장표준데이터 | 소상공인시장진흥공단 | 자료 기준 2025-11-10, 페이지 수정 2025-11-26 | [공식 제공 페이지](https://www.data.go.kr/data/15012894/standard.do) 참조 | 경북 시장만 추출하며 원본은 재배포하지 않음 |
| 상가(상권)정보 | 소상공인시장진흥공단 | 2026-06-30 | [이용허락범위 제한 없음](https://www.data.go.kr/data/15083033/fileData.do) | 전국 ZIP에서 영업 중인 경북 상가업소만 추출하며 출처와 기준일을 표시 |
| 주민등록 연령별 인구현황 | 행정안전부 | 2026-07 | [공식 통계 페이지](https://jumin.mois.go.kr/ageStatMonth.do) 참조 | 경북 행정구역의 10세 구간을 구조화하며 원본은 재배포하지 않음 |
| 지역안전지수 산출 결과 | 행정안전부 | 2025년 공표, 2024년 통계 | [공공누리 제1유형(출처표시)](https://www.mois.go.kr/frt/bbs/type001/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000015&nttId=123072) | 경북 시도·시군구 등급을 추출하며 출처와 통계연도를 표시 |
| 포항시 버스노선 시간표 | 경상북도 포항시 | 2026-08-23 검수 | [공식 시간표 페이지](https://cn.pohang.go.kr/dept/contents.do?mid=0505070000) 참조 | 시간표를 사람이 검수한 배차 보조표로 구조화하며 원본 PDF는 재배포하지 않음 |

`data/reference/pohang_bus_frequencies.csv`와
`data/reference/pohang_branch_pattern_frequencies.csv`는 포항시 공식 시간표에서 사실 정보를
구조화한 파생 검수 자료입니다. 각 행은 원문 URL, 기준일, PDF 이름·페이지와 검수 메모를
포함합니다. 이 두 파일은 프로젝트 코드의 MIT 라이선스 적용 대상이 아니며 원출처의 이용조건을
따릅니다.

이 문서의 이용조건 확인일은 2026-08-23입니다. 원자료를 갱신할 때는 공식 페이지의 최신
이용조건을 다시 확인하고 `data/sources.toml`의 출처·기준일·해시를 함께 갱신해야 합니다.
