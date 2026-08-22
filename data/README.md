# 로컬 데이터 준비

MCP 런타임은 `data/processed/gyeongbuk.sqlite3`만 읽습니다. 아래 원본은
`make data-fetch`로 `data/raw/`에 저장하고 `make data`로 DB를 다시 만듭니다. 빌드 과정에서는 파일명을 믿지 않고
CSV 열 이름과 HIRA ZIP 내부 구성을 확인하므로 공공데이터포털의 한글 파일명을 그대로 써도
됩니다.

```bash
make data-setup  # 다운로드·검증 후 SQLite 생성
make data-check  # 다운로드 없이 기존 원본의 해시·형식 검증
```

다운로드 URL, 파일명, 기준일, SHA-256과 이용조건은 [`sources.toml`](sources.toml)에 고정합니다.
원자료가 갱신되어 해시가 달라지면 파일을 자동 수용하지 않고 공식 페이지를 안내하며 실패합니다.
새 버전을 사람이 검수한 뒤 manifest와 회귀 기대값을 함께 갱신해야 합니다.

| 원본 | 공식 다운로드 | 현재 기준 | 필수 열·내용 |
| --- | --- | --- | --- |
| HIRA 전국 병의원 및 약국 현황 ZIP | [공공데이터포털](https://www.data.go.kr/data/15051059/fileData.do) | 2026.6 | `1.병원정보서비스`, `5.…진료과목정보` XLSX |
| 전국 버스정류장 위치정보 CSV | [공공데이터포털](https://www.data.go.kr/data/15067528/fileData.do) | 2025-10-31 | 정류장번호, 정류장명, 위도, 경도, 도시코드 |
| 포항시 시내버스 노선정보 CSV | [공공데이터포털](https://www.data.go.kr/data/3034960/fileData.do) | 2026-05-12 | 노선명, 승강장명칭, 승강장순번 |
| 전국전통시장표준데이터 CSV | [공공데이터포털](https://www.data.go.kr/data/15012894/standard.do) | 자료 기준 2025-11-10, 페이지 수정 2025-11-26 | 시장명, 주소, 위도, 경도 |
| 전체 읍면동 연령별 인구현황 CSV | [행정안전부 주민등록 인구통계](https://jumin.mois.go.kr/ageStatMonth.do) | 2026-07 | 행정구역, 계 총인구수, 10세 연령 구간 |
| 지역안전지수 산출 결과 HWPX | [행정안전부](https://www.mois.go.kr/frt/bbs/type001/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000015&nttId=123072) | 2025년 공표(2024년 통계) | 시도·시군구별 6개 분야 등급 |

포항시 노선 파일의 `운행시간`은 배차 횟수가 아니라 노선 운행 소요시간입니다. 일 운행량은
[포항시 버스노선 시간표](https://cn.pohang.go.kr/dept/contents.do?mid=0505070000)를 다음 두
검수 파일로 구조화합니다.

- [`reference/pohang_bus_frequencies.csv`](reference/pohang_bus_frequencies.csv): 간선 22개
  노선의 첫차·막차·최대 배차간격 또는 게시 횟수
- [`reference/pohang_branch_pattern_frequencies.csv`](reference/pohang_branch_pattern_frequencies.csv):
  지선 29개 노선의 정확한 `노선상세`별 게시 횟수, 첫차·막차, PDF·페이지와 검수 메모

지선 검수 CSV가 참조하는 이미지형 PDF 13개는 `pohang_branch_*.pdf` 이름으로
`data/raw/`에 보관합니다. 빌더는 PDF 존재 여부와 헤더, 정확한 노선·상세 경로, 시간 형식,
요일별 0 이상 횟수, `schedule_id` 중복을 검사합니다. PDF는 OCR하지 않으며 게시 자료가
바뀌면 사람이 PDF와 CSV를 함께 검수합니다.

간선은 최대 배차간격을 사용한 보수적 하한을, 지선은 해당 정류장을 실제 포함하는 검수
패턴만 합산합니다. 같은 패턴에 같은 정류장이 반복돼도 한 번만 계산합니다. 포항 53개 노선
중 51개를 판정하며 `임시노선`과 호출형 `죽장DRT`는 횟수 미상입니다. `장날`, `CALL`, 임시·
요청 운행은 기본 횟수에서 제외하고 `경유` 표시는 별도 운행으로 더하지 않습니다.

## 생성 및 확인

```bash
uv sync
make data-setup
sqlite3 data/processed/gyeongbuk.sqlite3 \
  'select count(*) from hospitals;'
make check
```

빌더는 새 임시 DB가 완성된 뒤에만 기존 DB를 교체하고, 입력 파일별 SHA-256을 `metadata`
테이블에 기록합니다. 원본 파일과 생성 DB는 Git과 GitHub Release에서 제외합니다. 네트워크
없이 빌드해야 하는 환경은 검증된 원본을 별도로 배치한 뒤 `make data-check && make data`를
실행합니다.
