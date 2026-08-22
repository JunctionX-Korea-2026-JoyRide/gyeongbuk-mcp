# Gyeongbuk MCP

경북 지역·공공 데이터를 AI 에이전트에 제공하는 FastMCP 서버입니다.

## 개발 환경

Python 3.12 이상과 [uv](https://docs.astral.sh/uv/)가 필요합니다.

```bash
make sync
make hooks
```

`uv sync`는 애플리케이션 및 개발 의존성을 `uv.lock`에 맞춰 설치합니다. `make hooks`는
커밋 전에 변경된 Python 파일만 포매팅, 린트, 타입 체크하도록 pre-commit 훅을 설치합니다.

## 명령어

```bash
make run          # stdio MCP 서버 실행
make format       # Ruff로 포매팅
make format-check # 포맷 변경 없이 검사
make lint         # Ruff 린트
make typecheck    # mypy 타입 체크
make test         # pytest 테스트
make check        # 포맷, 린트, 타입, 테스트 전체 검사
make pre-commit   # 모든 파일에 pre-commit 훅 실행
```

각 명령은 `uv run ...`으로 직접 실행해도 됩니다.

## 구조

```text
src/
├── server.py       # FastMCP 서버 진입점
├── tools/          # MCP 도구 정의
├── services/       # 비즈니스 로직
├── clients/        # 외부 API 클라이언트
└── models/         # 입력/출력 모델
tests/
```

