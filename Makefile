.PHONY: sync data data-fetch data-check data-setup run typecheck format format-check lint test audit check hooks pre-commit

DATA_FETCH_ARGS ?=

sync:
	uv sync

data:
	uv run python scripts/build_snapshot.py

data-fetch:
	uv run python scripts/fetch_data.py $(DATA_FETCH_ARGS)

data-check:
	uv run python scripts/fetch_data.py --check

data-setup: data-fetch data

run:
	uv run fastmcp run src/server.py

typecheck:
	uv run mypy src tests

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

test:
	uv run pytest

audit:
	uv run pip-audit

check: format-check lint typecheck test

hooks:
	uv run pre-commit install

pre-commit:
	uv run pre-commit run --all-files
