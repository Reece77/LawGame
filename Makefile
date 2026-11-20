# Root tasks. Recipes avoid shell-specific syntax so they run under sh and cmd.exe.

.PHONY: check check-fast check-backend check-timing check-api check-frontend check-vendored dev gen-api golden e2e

check: check-vendored check-backend check-timing check-api check-frontend

check-vendored:
	python3 tools/check_vendored.py

check-backend:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q -n auto -m "not timing"

# Turn-time budgets run alone, after the parallel suite (TST's check-timing; PT-M5 T12).
check-timing:
	cd backend && uv run pytest -q -n 0 -m timing

# For local iteration only: the same without the golden seeds.
check-fast:
	cd backend && uv run ruff check . && uv run mypy && uv run pytest -q -n auto -m "not timing" --ignore=tests/golden

# The generated client must match the API (ADR-0009).
check-api:
	cd frontend && pnpm gen:api && git diff --exit-code -- src/api

check-frontend:
	cd frontend && pnpm lint && pnpm typecheck && pnpm test

golden:
	cd backend && uv run pytest tests/golden -q --update-golden

gen-api:
	cd frontend && pnpm gen:api

e2e:
	cd frontend && pnpm exec playwright test

dev:
	cd backend && uv run python ../tools/dev.py
