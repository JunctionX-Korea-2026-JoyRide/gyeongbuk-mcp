.PHONY: sync run typecheck format format-check lint test check hooks pre-commit

sync:
	uv sync

run:
	uv run fastmcp run src/server.py:mcp

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

check: format-check lint typecheck test

hooks:
	uv run pre-commit install

pre-commit:
	uv run pre-commit run --all-files

