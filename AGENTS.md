# AGENTS.md

## Purpose

Shared implementation rules for Generator agents working in this repository.

## Active Contract

- Use `agent_id` UUIDs for identification.
- Do not introduce `api_key`, `caller_api_key`, `owner_email`, or similar legacy auth fields.
- Keep `agents/common.py` unchanged unless explicitly requested.
- Store UUIDs as `String(36)` in SQLite-backed SQLAlchemy models.

## Phase 1 Scope

- Backend: FastAPI + SQLAlchemy + Alembic + SQLite WAL
- MCP server: SSE transport on port `8100`
- Seed agents: PM, Research, Code, Marketing, Design
- Demo-critical end-to-end flows: Research + Code

## Quality Gates

- `uv run ruff check .`
- `uv run mypy backend/ agents/`
- `uv run pytest`
