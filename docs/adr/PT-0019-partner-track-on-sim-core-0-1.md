# ADR PT-0019: Partner Track on sim-core 0.1

- **Status:** Accepted (PT-M19a, 2026-11-28)
- **Context:** `docs/sim-core-plan.md` step 2 (SC-2's adoption half, run as PT-M19a), sim-core's `docs/adoption.md` ("Both games", "Partner Track"), sim-core ADRs SC-0001 to SC-0011. Amends ADR PT-0001 (the transplant ends for what sim-core provides) and ADR PT-0012 (the table's home).
- **Exit test:** golden snapshots and `tests/fixtures/state_hashes.json` unchanged, never re-recorded; every existing test passes unweakened; `make check`, `make e2e` and T12's timing gate within budget. A move that could not meet the test was cut, recorded below, and left for sim-core 0.2 (SC-2b).

## Decision

Partner Track depends on `simcore[db,llm] @ git+https://github.com/Reece77/sim-core@v0.1.0`, locked in `uv.lock` (commit `b2fc2db`). `tests/unit/test_core_pin.py` fails on any pin but a tag, in `pyproject.toml` and in the lock. sim-core is public, so CI's `uv sync --locked` fetches it with no secret. Plaza's CI does the same.

### Replaced modules (each PT copy deleted)

| PT before | Now | Notes |
| --- | --- | --- |
| `ptk/sim/rng.py` | `simcore.kernel.rng` | `ptk/sim/streams.py`: PT's 59 own rows (`OWN_ROWS`) built with `StreamTable.build(OWN_ROWS, aliases={"partnership": "governance"})`. `RngFactory` is sim-core's bound to that table, and still refuses negative turns and keys at PT's boundary. Every PT stream draws exactly as before (checked against the old factory, and by `test_core_adoption.py` against `derive`). New rows go into `OWN_ROWS` and ADR PT-0012's table. |
| `ptk/sim/money.py`, `dmath.py`, `scale.py` | `simcore.kernel.money`, `dmath`, `scale` | Byte-identical apart from the errors import. |
| `ptk/sim/calendar.py` | `simcore.kernel.calendar` | Engine code passes the save's start everywhere. PT's 2005 default start (pinned by `test_calendar.py`) lives in `ptk/sim/dates.py`, three wrappers over sim-core's functions. |
| base classes of `ptk/sim/errors.py` | `simcore.kernel.errors` | `SimError`, `UnbalancedEntryError`, `UnknownStreamError`, `InvalidMoneyError`, `InvalidDateError`, `InvalidSeedError`, `NotFoundError`, `InvalidDataError` are re-exported. PT's domain errors subclass them, and the API's `code` strings are the same. |
| `ptk/llm/base.py`, `anthropic_adapter.py`, `offline.py`, `settings.py` | `simcore_llm` (TST's newest) | PT's text kinds were never TST's `coo`/`explain`, so `story_text_kinds` stays empty and the mock's default marking reproduces today's behaviour. The `TextKind` cast in `events/service.py` is gone. The generated API client is unchanged. |
| `ptk/db/session.py`, `backup.py`, `migrate.py` | `simcore_db` (TST's newest) | `ptk/db/core.py` binds PT's suffix (`.ptk.sqlite`), sync variable (`PTK_SQLITE_SYNC`), migrations folder and `save_meta.current_turn` into a `Migrator` and thin wrappers. PT's tables, mappers, Alembic chain and inbox stay PT's. `migrations/env.py` becomes a ported file. |
| purity, call-site and `--update-golden` plumbing | `simcore_testing` | `test_sim_purity.py` calls `simcore_testing.purity` with PT's packages banned (root `ptk/`, so relative imports resolve as before). `test_rng_call_sites.py` calls `simcore_testing.call_sites`, which allows one forwarded name: `streams.RngFactory.stream` (a new test pins that it is the only one). `simcore_testing.plugin` registers `--update-golden`. PT keeps its golden script and files, because sim-core's `Golden` writes another file format. |
| `frontend/src/core/` (new) | sim-core `ui/` at `v0.1.0` | Copied unchanged with `MANIFEST.json`. `tools/check_vendored.py` pins the manifest's SHA-256 and checks every file. PT's screens keep PT's `lib/format.ts`, `lib/attr.ts` and `components/AttributeRange.tsx`. |

`ptk/config.py` stays (sim-core has no settings module). `tests/unit/test_core_adoption.py` fails if a replaced module reappears anywhere in `ptk/`, if `ptk/llm/` or the db copies return, or if a module of `ptk/sim` takes a sim-core kernel module's name. `errors`, `ledger` and `log` are allowed by name, for the reasons below.

### Adopted in part

- **Books.** `ptk/sim/ledger.py` declares PT's `CHART` with sim-core's `Book`, `BookBridge` and `Chart` types: the firm's book `""`, `personal` `"9"` and `client_money` `"C"`. It also declares the `bill_paid` bridge (client bank and owed-to-clients out, firm cash and receivables in, no leakage). A firm `LedgerEntry` and a `ClientBookEntry` are refused, as before and with the same error and message, when a line is outside their book of the chart. The paid-bill transfer reads its firm accounts from the bridge. No entry changes.
- **Turn.** The twelve phases register into sim-core's `PhaseRegistry` slots, one each. `PHASES` is the registry's frozen order, which a test compares with today's tuple and sim-core's `SLOTS`. sim-core 0.1 types `Phase` on its own `TurnContext` over a `CoreState`, so PT's phases are stored as opaque callables (a `cast`).
- **Sub-states.** `ptk/sim/state.py` registers GameState's 15 dataclass sub-states (`SUB_STATES`). Each passes `SubStateSpec`'s checks, and a played state's sub-states round-trip through sim-core's codec (test). The ten tuple fields (people, employments, ...) are not dataclasses and wait for 0.2's people spine.
- **Hidden values.** 20 fields on 9 types are marked: `Person.hidden`, `potential_ability`, `tags`, `portability_bp`; `Matter.hidden_conflict`, `merits`, `opposing_quality`; `Judge.traits`; `GeneralCounsel.personality`; `Claim.merit`, `size_cents`; `DisciplinaryCase.culpability`; `Bill.padding_cents`; `Partner.satisfaction`, `confidence`; `BookClient.adverse_client_id`. Fields with a default use `hidden_field(default=...)`. Fields without one use `field(metadata={HIDDEN_KEY: True})`, the same marker, because mypy treats `hidden_field()` as a default (a core issue, below). The marker is metadata only: no draw, order or digest changes.
- **Prompts.** The event prompt's whole context passes sim-core's `check_public`, and each line of a text prompt passes `PublicFacts.add`, so a record with a hidden field cannot reach a prompt. PT's renderings are unchanged: the event prompt's JSON allowlist (spec 16) and the text prompt's lines. `PublicFacts.render()` takes no mappings and renders `- name: value`, which would change every prompt.

### Cuts (left for sim-core 0.2 / SC-2b)

1. **The entry type** (`firm_id` → `entity_id`, practice and office into `LedgerLine.dims`, the client book's entries as `LedgerEntry`s in book `C`, bridges posted by `bridge_transfer`). About ten test files construct entries with `firm_id=` or read `e.firm_id`. `tests/property/test_ledger.py` pins the separate-book refusal at construction with `UnbalancedEntryError`, where sim-core refuses at posting with `BookError`. Changing them is more than an import swap. `bridge_transfer`'s two-line entries also differ from PT's monthly aggregated entries (by practice and office), which the golden fingerprint hashes.
2. **Balances keyed by currency.** sim-core's `apply_entries` keys `(entity, account, currency)`. The state cache digests `game.balances`, so a third key part changes every month's hash. PT keeps `(firm, account)` balances, and no mapper changed.
3. **`GameState` as a `CoreState`.** The state cache digests the state's root dataclass by module, name and fields. A `CoreState` root changes every hash. This also cuts the `KpiProvider` snapshots, because `KpiProvider` and `build_snapshot` are typed on `CoreState`. `FirmSnapshot.kpis()` and the `turn_snapshot` columns stay PT's.
4. **`LogItem`** (`firm_id` → `entity_id`, `link_kind` as `str`): tests read `item.firm_id`. PT's `ptk/sim/log.py` stays.
5. **Inbox rendering** (`simcore_db.inbox.render`): PT's `ptk/db/inbox.py` is a ported file with PT's queries. Its render half is left for 0.2 with the inbox templates' shape.
6. **Settled in advance:** PT's risk cases (float draws in PT's own order) and partnership votes (float points against `Body`'s integer weights) stay on PT's code. Neither `simcore.cases` nor `simcore.governance` is used.

### One test changed beyond an import (Reece's decision, 2026-11-28)

`tests/unit/test_pt_m18_speed.py::test_streams_match_the_documented_seed_sequence` drew turns 0 to 2^33. sim-core refuses turns of 2^32 and over: ADR-0024 maps a negative turn `-k` to 2^32 + k, so those ids are reserved. The test's turn range is now sim-core's domain, 0 to 2^32 - 1. Keys keep 0 to 2^34, and the assertion is unchanged. PT plays turns 0 to 359. The PT-M18 fast path the test was written for is deleted with `rng.py`.

## Consequences

- One copy of the kernel, `llm/` and `db/` for PT and Plaza. A sim-core fix reaches PT by moving the tag, not by re-copying, and `VENDORED.md` lists only TST files v3 still ports and the UI shell.
- T12 holds: the five cases read 157, 164, 225, 132 and 131 ms (gates, minimum of five) against the 250 ms budget, although sim-core's documented `SeedSequence` path is about 40% slower a stream than PT-M18's word-array path.
- 0.2 needs a `CoreState` digest story before PT can move its state: either a re-recording allowed for a pure structural move, with the golden snapshots as the result check, or a canonical form shared by PT's digest.

## Core issues reported to Reece

1. `simcore.kernel.hidden.hidden_field()` is not recognised by mypy's dataclass plugin as a field specifier, so a hidden field without a default makes every later required field an error ("Attributes without a default cannot follow attributes with one"). Example: `@dataclass class P: a: float = hidden_field(); b: int` fails `mypy`. sim-core's own `Case.true_odds_bp` works only because defaulted fields follow it.
2. `docs/adoption.md` says PT passes `start` at every calendar call. Engine code does, but `tests/unit/test_calendar.py` pins PT's default of January 2005, while sim-core's default is 2010.
3. `docs/adoption.md` calls sim-core a private repository needing a token. It is public, and neither game's CI uses a secret.
