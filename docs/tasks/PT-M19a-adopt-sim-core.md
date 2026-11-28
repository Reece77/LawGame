# PT-M19a: adopt sim-core v0.1.0

**Goal:** Partner Track runs on sim-core 0.1 (`Reece77/sim-core`, tag `v0.1.0`), per `docs/sim-core-plan.md` step 2 and sim-core's `docs/adoption.md` ("Both games", "Partner Track"), with golden snapshots and `tests/fixtures/state_hashes.json` unchanged. Lifting PT modules into sim-core is SC-2b, a separate session.

**ADR:** PT-0019 · **Depends on:** `pt-m18-done` · **Lane:** runs alone; sim-core is read-only here.

## Scope

1. Depend on `simcore[db,llm] @ git+https://github.com/Reece77/sim-core@v0.1.0`, locked; a test fails on any non-tag pin.
2. Replace rng (`StreamTable.build`, PT's rows, alias `partnership` → `governance`), money, dmath, scale, calendar and base errors with sim-core's; the AS IS `llm/` and `db/` copies with `simcore_llm` and `simcore_db`; the purity, call-site and golden plumbing with `simcore_testing`. Delete every replaced file; a test fails on a shadow copy.
3. Ledger on `simcore.kernel.ledger`: a Chart of three books (firm `""`, personal `9`, client money `C`), the paid-bill transfer as a `BookBridge`, `firm_id` → `entity_id`, practice and office in `dims`, balances keyed by currency in the mappers only; schema and persisted values unchanged.
4. Sub-states and the 12 phases registered in sim-core's slots in today's order; snapshots as `KpiProvider`s with persisted columns unchanged.
5. Hidden fields marked with `hidden_field()`; prompts built with `PublicFacts`.
6. `VENDORED.md` shrunk; `tools/check_vendored.py` checks `frontend/src/core/` against sim-core's `ui/MANIFEST.json` at the tag; PT's `format.ts`, `attr.ts` and `AttributeRange.tsx` stay PT's.

## Exit criteria

- [x] Golden snapshots and the state cache unchanged (never re-recorded).
- [x] `make check` and `make e2e` pass; T12's timing gate within budget.
- [x] Every existing test passes unweakened; changed tests only swap an import or a fixture path (one exception, decided by Reece, below).

## Decisions made

1. **Prerequisites (2026-11-28).** `pt-m18-done` exists (`fb72651`); sim-core is attached. No Actions secret exists or is needed: `Reece77/Sim-core` is public, and Plaza's CI already installs `v0.1.0` with no credential. CI's `uv sync --locked` fetches it the same way.
2. **Cuts by the exit test.** The brief says a move that would change a result is cut, and every test must pass with only import swaps. By those rules five moves are cut to 0.2 (ADR PT-0019 "Cuts"): the ledger entry type (`entity_id`, `dims`, client book as book `C` entries, `bridge_transfer`), currency-keyed balances in memory (the state cache digests `game.balances`), `GameState` as a `CoreState` (the digest hashes the root dataclass) and with it the `KpiProvider` snapshots, `LogItem`'s `entity_id`, and the inbox's render half. The chart, bridge, registries, codec contract, hidden markers and prompt checks are adopted without changing any entry, draw or digest.
3. **The one test changed beyond an import (Reece, 2026-11-28).** `test_streams_match_the_documented_seed_sequence`'s turns narrow from 0-2^33 to sim-core's domain 0-2^32-1 (2^32 and up are reserved for negative turns, TST ADR-0024). Its keys and assertion are unchanged.
4. **Calendar default.** sim-core's calendar defaults to January 2010. PT's 2005 default (pinned by `test_calendar.py`) is kept in `ptk/sim/dates.py`, which delegates to sim-core. Engine code passes `start_ym` everywhere.
5. **Hidden fields without a default** use `field(metadata={HIDDEN_KEY: True})` (sim-core's marker), because mypy reads `hidden_field()` as a default. Reported to Reece.
6. **`ptk/db/core.py`** is PT's binding of `simcore_db`: suffix, sync variable, migrations, turn SQL. Callers that imported `ptk.db.session`, `backup` or `migrate` import it.
7. **`check_vendored.py`** pins sim-core `v0.1.0`'s `ui/MANIFEST.json` SHA-256 (`1ecdf03b...`, the same value Plaza pins), and `.prettierignore` skips `src/core` (as Plaza's does).
8. **T12 readings** (this container, gates: minimum of five): two offices 157 ms, 2006 merger 164 ms, 2025 merger 225 ms, December 2025 132 ms, December 2034 131 ms. All are within 250 ms.

## Tests changed (imports and fixture paths only, except decision 3)

- Kernel imports: `ptk.sim.rng` → `ptk.sim.streams`, `ptk.sim.money|dmath|scale|calendar` → `simcore.kernel.*` (`test_calendar.py` → `ptk.sim.dates`), `ptk.llm.*` → `simcore_llm.*`, `ptk.db.session` → `ptk.db.core`, `from ptk.db import backup` → `from ptk.db import core as backup`.
- `test_sim_purity.py` and `test_rng_call_sites.py` call `simcore_testing`'s scanners (brief item 2). Every fixture case is unchanged. The call-site test gains a case pinning the one forwarded name.
- `conftest.py` loads `simcore_testing.plugin` for `--update-golden`.
- New: `test_core_pin.py`, `test_core_adoption.py`.
