# Gyeongbuk MCP

[![CI](https://github.com/JunctionX-Korea-2026-JoyRide/gyeongbuk-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/JunctionX-Korea-2026-JoyRide/gyeongbuk-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

경북 지역·공공 데이터를 AI 에이전트에 제공하는 FastMCP 서버입니다.

현재 병원, 버스정류장, 전통시장, 일반 상가업소, 연령별 인구 비율, 지역안전등급과 차 없는 고령자를 위한
시장 중심 생활권 추천 도구를 제공합니다. 기본 실행 모드는 공공데이터 원본 파일을 SQLite로
변환해 조회하므로 API 인증키나 외부 서버 연결이 필요하지 않습니다. 도구별 입력·출력과 데이터 한계는
[`docs/`](docs/README.md)를 참고하세요.

## 빠른 시작

Python 3.12 이상과 [uv](https://docs.astral.sh/uv/)가 필요합니다.

```bash
make sync
make data-setup
make run
```

`make data-setup`은 [`data/sources.toml`](data/sources.toml)에 고정된 공식 원본을 내려받아
SHA-256과 파일 형식을 검증한 다음 로컬 SQLite를 생성합니다. API 인증키는 필요하지 않습니다.
원본과 생성 DB는 Git과 GitHub Release에 포함하지 않습니다.

현재 내려받은 원본으로 생성한 스냅샷에는 경북 병의원 3,415곳, 진료과목 16,031건,
경북 정류장 29,735곳, 포항 노선 53개와 노선 패턴 196개, 배차 판정 가능한 포항 노선 51개,
전통시장 132곳, 경북 상가업소 144,967곳, 연령 구간 3,949건, 지역안전등급 138건이 들어갑니다.

필요하면 예제 설정을 복사합니다. 파일 모드에서는 인증키가 필요하지 않습니다.

```bash
cp .env.example .env
```

```dotenv
DATA_MODE=file
LOCAL_DATABASE_PATH=data/processed/gyeongbuk.sqlite3
```

API 모드를 임시로 사용할 때만 `DATA_MODE=api`와 `DATA_GO_KR_SERVICE_KEY`를 설정합니다.
API 모드는 병원·버스정류장·시장·상가업소 조회에 적용되며 인구·안전 도구는 계속 로컬 SQLite를
사용합니다. `.env`는 Git에서 제외되고 같은 이름의 셸·CI 환경변수가 `.env`보다 우선합니다.

## MCP 클라이언트 등록

stdio MCP 설정에 다음과 같이 등록합니다. `/absolute/path/gyeongbuk-mcp`를 실제 저장소의 절대
경로로 바꾸세요.

```json
{
  "mcpServers": {
    "gyeongbuk": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/gyeongbuk-mcp",
        "run",
        "fastmcp",
        "run",
        "src/server.py"
      ]
    }
  }
}
```

## 명령어

```bash
make run          # stdio MCP 서버 실행
make data-fetch   # 고정된 공식 원본 다운로드·검증
make data-check   # 네트워크 없이 기존 원본 검증
make data         # 기존 원본에서 로컬 SQLite 재생성
make data-setup   # 원본 다운로드 후 SQLite 생성
make format       # Ruff로 포매팅
make format-check # 포맷 변경 없이 검사
make lint         # Ruff 린트
make typecheck    # mypy 타입 체크
make test         # pytest 테스트
make audit        # Python 의존성 취약점 검사
make check        # 포맷, 린트, 타입, 테스트 전체 검사
make pre-commit   # 모든 파일에 pre-commit 훅 실행
```

각 명령은 `uv run ...`으로 직접 실행해도 됩니다.

개발에 참여하려면 [`CONTRIBUTING.md`](CONTRIBUTING.md), 취약점 제보는
[`SECURITY.md`](SECURITY.md)를 참고하세요.

## 구조

```text
src/
├── server.py       # FastMCP 서버 진입점
├── tools/          # MCP 도구 정의
├── services/       # 비즈니스 로직
├── clients/        # 외부 API 클라이언트
└── models/         # 입력/출력 모델
tests/
docs/                 # 도구 계약, 데이터 출처, 구현 계획
data/
├── raw/              # 직접 내려받은 원본(커밋 제외)
├── reference/        # 출처가 명시된 작은 보조 매핑
└── processed/        # 생성된 SQLite(커밋 제외)
scripts/
└── build_snapshot.py # 파일 정규화 진입점
```

## 라이선스

소스 코드는 [MIT License](LICENSE)로 배포합니다. 공공데이터 원본, 생성 SQLite와
`data/reference/`의 파생 검수 자료에는 MIT가 적용되지 않으며 각 제공기관의 이용조건을
따릅니다. 자세한 출처표시와 재배포 정책은 [`DATA_LICENSES.md`](DATA_LICENSES.md)를 참고하세요.
