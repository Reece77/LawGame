# Root tasks. Recipes avoid shell-specific syntax so they run under sh and cmd.exe.

.PHONY: check check-fast check-backend check-lint check-shard check-timing check-api check-frontend check-vendored dev gen-api golden e2e balance nightly balance-shard balance-summary nightly-shard

check: check-vendored check-backend check-timing check-api check-frontend

check-vendored:
	python3 tools/check_vendored.py

check-backend:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q -n auto -m "not timing and not nightly"

# PT-M11: CI's `check` runs the lint half and the tests (in SHARDS shards) as parallel jobs.
check-lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy

SHARDS = 3
SHARD = 0
check-shard:
	python3 tools/test_shard.py $(SHARDS) $(SHARD) --run

# Turn-time budgets run alone, after the parallel suite (TST's check-timing; PT-M5 T12).
check-timing:
	cd backend && uv run pytest -q -n 0 -m timing -s

# For local iteration only: the same without the golden seeds.
check-fast:
	cd backend && uv run ruff check . && uv run mypy && uv run pytest -q -n auto -m "not timing and not nightly" --ignore=tests/golden

# The generated client must match the API (ADR-0009).
check-api:
	cd frontend && pnpm gen:api && git diff --exit-code -- src/api

check-frontend:
	cd frontend && pnpm lint && pnpm typecheck && pnpm test

# The balance runner (docs/balance-targets.md, PT-M7): five strategies x 10 seeds x 132 turns,
# plus T5's difficulty runs and the T8/T9 variants; prints every target, exits 1 on a gate.
balance:
	uv run --project backend python tools/balance_runner.py --runs --long

# The long balance tests (CI: nightly.yml; dispatch it on a branch for long runs).
nightly:
	cd backend && uv run pytest -q -n auto --dist loadgroup -m nightly -s

# PT-M18 sub-task 2: CI's nightly in parallel jobs. The balance run by seed range (each shard
# saves its runs; the summary reads them all and prints every target, exiting 1 on a gate) and
# the nightly tests dealt by recorded duration (tests/nightly_shards.py).
BALANCE_SHARDS = 8
BALANCE_SHARD = 0
balance-shard:
	uv run --project backend python tools/balance_runner.py --runs --long --shard $(BALANCE_SHARD)/$(BALANCE_SHARDS) --save balance-results/shard-$(BALANCE_SHARD).pkl

balance-summary:
	uv run --project backend python tools/balance_runner.py --runs --long --summary balance-results
	cd backend && PTK_BALANCE_RESULTS=balance-results uv run pytest -q -n 0 -s -m balance_run

NIGHTLY_SHARDS = 6
NIGHTLY_SHARD = 0
nightly-shard:
	cd backend && uv run pytest -q -n auto --dist loadgroup -m "nightly and not balance_run" -rA --nightly-shard $(NIGHTLY_SHARD)/$(NIGHTLY_SHARDS) --nightly-durations-out nightly-durations/shard-$(NIGHTLY_SHARD).json

golden:
	cd backend && uv run pytest tests/golden -q --update-golden

gen-api:
	cd frontend && pnpm gen:api

e2e:
	cd frontend && pnpm exec playwright test

dev:
	cd backend && uv run python ../tools/dev.py
