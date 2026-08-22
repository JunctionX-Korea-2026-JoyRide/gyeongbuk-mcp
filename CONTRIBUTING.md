# Contributing

## 개발 준비

Python 3.12 이상과 `uv`가 필요합니다.

```bash
make sync
make hooks
make check
```

MCP 도구는 한 가지 책임만 갖게 하고, 외부 API 접근은 `clients/`, 재사용 가능한 계산은
`services/`, 입력·출력 계약은 `models/`에 둡니다. 공개 함수에는 타입 힌트를 사용하고 동작을
바꾸면 테스트와 문서를 함께 수정해 주세요.

## 데이터 변경

원본을 처음 준비할 때는 `make data-setup`, 기존 원본의 무결성만 확인할 때는
`make data-check`를 사용합니다. 원자료 갱신 PR에는 다음을 함께 포함해야 합니다.

- 공식 출처와 이용조건 확인 결과
- `data/sources.toml`의 기준일과 SHA-256
- 변경된 스키마 적재 테스트와 실데이터 회귀 기대값
- 사람이 검수한 배차 자료라면 원문 페이지와 검수 메모

`data/raw/`, `data/processed/`, 원본 PDF, 생성 SQLite는 커밋하지 않습니다.

## 보안과 제출 전 확인

`.env`, API 키, 인증 쿠키나 개인 식별정보를 커밋하지 마세요. 제출 전 다음 명령을 실행합니다.

```bash
make check
make audit
git diff --check
```

보안 취약점은 공개 Issue 대신 [`SECURITY.md`](SECURITY.md)의 비공개 제보 절차를 이용해 주세요.
