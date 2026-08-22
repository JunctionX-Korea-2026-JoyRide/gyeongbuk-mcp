# AGENTS.md

## Project overview

This repository contains an MCP (Model Context Protocol) server that exposes location and public-data capabilities as tools for AI agents.

Keep the project focused on the MCP server. Do not add a frontend, chat UI, or standalone agent unless explicitly requested.

## Project structure

```text
src/
├── server.py       # MCP server entry point
├── tools/          # MCP tool definitions
├── services/       # Business logic
├── clients/        # External API clients
└── models/         # Input/output models

tests/
```

Keep MCP tool definitions thin. Put API access in `clients/` and reusable logic in `services/`.

## Development

- Use Python 3.12+.
- Use FastMCP for the MCP server.
- Use `uv` for dependency and environment management.
- Use type hints for all public functions.
- Prefer async I/O for external API calls.
- Keep dependencies minimal.

### Setup and validation commands

- Install dependencies: `uv sync`
- Run the server: `make run`
- Type-check: `make typecheck`
- Format: `make format`
- Check formatting: `make format-check`
- Lint: `make lint`
- Test: `make test`
- Run all non-mutating checks: `make check`
- Install pre-commit hooks: `make hooks`

## MCP tool guidelines

- Each tool should have one clear responsibility.
- Use descriptive tool names and concise docstrings.
- Use typed inputs and structured outputs.
- Return facts and metadata rather than LLM-generated reasoning.
- Keep outputs deterministic when possible.
- Handle missing data and external API failures explicitly.
- Do not expose secrets or internal exception details.

Example tools may include:

- `search_nearby_facilities`
- `get_public_transport_access`
- `get_safety_data`
- `get_location_metrics`
- `compare_locations`

## Testing

- Add tests for new tools and business logic.
- Mock external APIs in unit tests.
- Test invalid inputs, missing data, timeouts, and API failures.
- Run the full test suite before finishing a change.

## Security

- Never hardcode API keys or credentials.
- Read secrets from environment variables.
- Validate external inputs.
- Set timeouts on external HTTP requests.
- Do not log sensitive credentials.

## Agent instructions

When modifying the repository:

1. Inspect existing code before introducing new abstractions.
2. Prefer extending existing patterns over creating parallel implementations.
3. Keep changes scoped to the requested task.
4. Update tests when behavior changes.
5. Avoid unrelated refactors.
6. Verify the MCP server still starts and affected tools work before finishing.
